#!/usr/bin/env bash
# Build a reprocli agent sandbox .sif: NVIDIA CUDA base + the CLI tools our agents need.
#
# The default DeltaAI sandbox (cluster.py: DEFAULT_APPTAINER_SIF) is a raw NVIDIA CUDA
# image — it ships the CUDA toolkit + nvcc but no git/curl/etc. This layers the tooling
# the reproduction agent relies on (clone code, fetch data, build C/Cython wheels, decode
# audio) into a derived read-only image. module load can't help here: the sandbox runs
# `apptainer exec --cleanenv --no-home`, so host modules never reach inside — the tools
# have to live in the image's own (correctly-linked) userland.
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
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        ca-certificates \
        git git-lfs \
        curl wget \
        unzip xz-utils \
        build-essential pkg-config \
        ffmpeg libsndfile1
    git lfs install --system || true
    rm -rf /var/lib/apt/lists/*

%test
    set -e
    export PATH=/usr/local/cuda/bin:\${PATH}
    for t in git git-lfs curl wget unzip gcc nvcc; do
        command -v "\$t" >/dev/null && echo "ok: \$t -> \$(command -v \$t)" \
            || { echo "MISSING: \$t"; exit 1; }
    done
DEFEOF

echo ">> building ${OUT_SIF}"
echo ">>   from  ${BASE_SIF}"
# --fakeroot lets apt-get write into the image via user namespaces. If it's disabled on
# this host, build the equivalent image where you have root/Docker and scp the .sif up.
apptainer build --fakeroot "$OUT_SIF" "$DEF"

echo ">> verifying tools inside the image"
apptainer exec "$OUT_SIF" bash -lc \
  'export PATH=/usr/local/cuda/bin:$PATH; \
   which git git-lfs curl wget unzip gcc nvcc; echo; \
   git --version; curl --version | head -1; gcc --version | head -1'

echo ">> done: $OUT_SIF"
