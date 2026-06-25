#!/usr/bin/env bash
# Build a reprocli agent sandbox .sif: NVIDIA CUDA base + a full Python toolchain + the
# CLI tools our agents need.
#
# The default DeltaAI sandbox (cluster.py: DEFAULT_APPTAINER_SIF) is a raw NVIDIA CUDA
# image — it ships the CUDA toolkit + nvcc but no python3/git/curl/etc. This layers the
# tooling the reproduction agent relies on (run Python, clone code, fetch data, build
# C/Cython wheels, decode audio) into a derived read-only image. module load can't help
# here: the sandbox runs `apptainer exec --cleanenv --no-home`, so host modules never
# reach inside — the tools have to live in the image's own (correctly-linked) userland.
#
# Why a SYSTEM python3 (not just uv's downloaded CPython): repos build C/Cython extensions
# at install time (e.g. VITS `monotonic_align`). gcc needs `Python.h`, and with no system
# `python3-dev` the only headers live in uv's managed-CPython dir — which agents fail to
# find, so the build dies with `Python.h: No such file or directory` and the run stalls.
# Baking `python3.12` + `python3.12-dev` puts the headers at the conventional
# `/usr/include/python3.12/`, so `setup.py build_ext` / `uv pip install <C-ext pkg>` just
# work. `espeak-ng` is here for the same reason (phonemizer has no read-only fallback).
#
# Run on a login node (apt needs network). Then point DEFAULT_APPTAINER_SIF /
# --apptainer-image / $REPRO_APPTAINER_SIF at the output.
#
# Usage: bash build_cuda_sandbox.sh [BASE_SIF] [OUT_SIF]
set -euo pipefail

BASE_SIF="${1:-/work/nvme/bfvr/msalunkhe/cuda1290-cudnn-devel.sif}"
OUT_SIF="${2:-/work/nvme/bfvr/msalunkhe/cuda1290-agent.sif}"

# Keep Apptainer's cache/tmp off the small $HOME (VAST) quota — builds need scratch.
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-/work/nvme/bfvr/$USER/.apptainer/cache}"
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-/work/nvme/bfvr/$USER/.apptainer/tmp}"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

DEF="$(mktemp --suffix=.def)"
trap 'rm -f "$DEF"' EXIT

cat > "$DEF" <<DEFEOF
Bootstrap: localimage
From: ${BASE_SIF}

%post
    set -eux
    export DEBIAN_FRONTEND=noninteractive
    apt-get update

    # --- CLI tooling + C/C++ build chain + audio libs the agent relies on ---
    apt-get install -y --no-install-recommends \
        ca-certificates gnupg \
        git git-lfs \
        curl wget \
        unzip xz-utils \
        build-essential pkg-config cmake ninja-build \
        ffmpeg libsndfile1 sox \
        espeak-ng libespeak-ng1
    git lfs install --system || true

    # --- Python 3.12 toolchain: interpreter + dev headers + venv + pip ---
    # If the base distro doesn't carry python3.12 (e.g. Ubuntu 22.04), pull it from
    # deadsnakes so the version matches the prompt's \`--python 3.12\` and torch's cu129
    # aarch64 wheels.
    if ! apt-cache show python3.12 >/dev/null 2>&1; then
        apt-get install -y --no-install-recommends software-properties-common
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update
    fi
    apt-get install -y --no-install-recommends \
        python3.12 python3.12-dev python3.12-venv python3-pip
    # NOTE: Debian/Ubuntu DISABLE \`python3.12 -m ensurepip\` for the system interpreter
    # (it exits non-zero with "ensurepip is disabled"), so pip comes from the python3-pip
    # apt package instead — usable as \`python3.12 -m pip\`. uv is the primary installer;
    # pip is just a fallback, and the agent installs into venvs (no PEP-668 friction).
    # Expose python3/python on PATH via /usr/local/bin (precedes /usr/bin) WITHOUT
    # repointing the distro's own /usr/bin/python3 — apt's tooling depends on that one.
    ln -sf /usr/bin/python3.12 /usr/local/bin/python3
    ln -sf /usr/bin/python3.12 /usr/local/bin/python

    # --- uv: native aarch64 binary baked in, so the image is self-contained (the sandbox
    # also binds the host uv when present, which simply overrides this copy). ---
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

    rm -rf /var/lib/apt/lists/*

%test
    set -e
    export PATH=/usr/local/bin:/usr/local/cuda/bin:\${PATH}
    for t in git git-lfs curl wget unzip gcc nvcc cmake ninja python3 uv espeak-ng; do
        command -v "\$t" >/dev/null && echo "ok: \$t -> \$(command -v \$t)" \
            || { echo "MISSING: \$t"; exit 1; }
    done
    echo "python: \$(python3 --version)"
    python3 -m pip --version
    inc="\$(python3 -c 'import sysconfig; print(sysconfig.get_path("include"))')"
    test -f "\$inc/Python.h" && echo "ok: Python.h -> \$inc/Python.h" \
        || { echo "MISSING: Python.h (no dev headers)"; exit 1; }
DEFEOF

echo ">> building ${OUT_SIF}"
echo ">>   from  ${BASE_SIF}"
# --fakeroot lets apt-get write into the image via user namespaces. If it's disabled on
# this host, build the equivalent image where you have root/Docker and scp the .sif up.
apptainer build --fakeroot "$OUT_SIF" "$DEF"

echo ">> verifying tools inside the image"
apptainer exec "$OUT_SIF" bash -lc \
  'export PATH=/usr/local/bin:/usr/local/cuda/bin:$PATH; \
   which git git-lfs curl wget unzip gcc nvcc cmake ninja python3 uv espeak-ng; echo; \
   git --version; python3 --version; uv --version; espeak-ng --version | head -1'

echo ">> proving the Python dev toolchain can build+import a compiled extension"
# This is the exact capability the agent needs for VITS monotonic_align & friends: a
# C extension that compiles against the bundled Python.h and imports cleanly.
apptainer exec "$OUT_SIF" bash -lc '
  set -e
  export PATH=/usr/local/bin:/usr/local/cuda/bin:$PATH
  tmp=$(mktemp -d)
  cat > "$tmp/ext.c" <<EOF
#include <Python.h>
static struct PyModuleDef mod = {PyModuleDef_HEAD_INIT, "ext", NULL, -1, NULL};
PyMODINIT_FUNC PyInit_ext(void) { return PyModule_Create(&mod); }
EOF
  inc=$(python3 -c "import sysconfig; print(sysconfig.get_path(\"include\"))")
  gcc -shared -fPIC -I"$inc" "$tmp/ext.c" -o "$tmp/ext.so"
  (cd "$tmp" && python3 -c "import ext; print(\"ok: built and imported a C extension\")")
  rm -rf "$tmp"'

echo ">> done: $OUT_SIF"
