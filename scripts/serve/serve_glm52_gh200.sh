#!/usr/bin/env bash
# Serve GLM-5.2 AWQ-INT4 (cyankiwi/GLM-5.2-AWQ-INT4) on one 4xGH200 node.
#
# This exists because the environment is load-bearing and survives neither a new
# shell nor a new allocation. Three things bite, all of them silently, and each
# one costs ~45 min to discover the hard way. Bring-up notes: 2026-07-15,
# gh068/gh151, vLLM 0.25.1. Companion to tasks/serve-gguf-llamacpp-gh200.md,
# which covers the llama.cpp/GGUF path.
#
#   bash scripts/serve/serve_glm52_gh200.sh
#   CPU_OFFLOAD_GB=28 MAX_MODEL_LEN=65536 bash scripts/serve/serve_glm52_gh200.sh
#
# Then benchmark it (the script waits for /health on its own):
#   python scripts/serve/bench_serve.py --model zai-org/GLM-5.2

set -euo pipefail

REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-${REPROCLI}/.venv}"
# Node-local /tmp: FASTER than /work/nvme (local NVMe, no network hop, and
# vLLM's auto-prefetch stays off either way because the 410 GiB checkpoint
# exceeds 90% of RAM). The cost is that it dies with the allocation and is
# invisible to other nodes -- fine for single-node serving, re-download on a
# new node. See tasks/serve-gguf-llamacpp-gh200.md section 4.
MODEL="${MODEL:-/tmp/GLM-5-2/}"
SERVED_NAME="${SERVED_NAME:-zai-org/GLM-5.2}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

# Sizing. Weights are 410.12 GiB against 4x95.6 = 382 GiB HBM, so offload is
# forced, not a tuning choice. MEASURED at CPU_OFFLOAD_GB=28: "Model loading
# took 78.57 GiB", leaving only 10.3 GiB at util 0.93 -- not enough for a bf16
# KV pool at 131k (~11.0 GiB), hence 36. Raise this or drop MAX_MODEL_LEN if KV
# init OOMs; lower it if the offload stalls (see the NUMA note below).
CPU_OFFLOAD_GB="${CPU_OFFLOAD_GB:-36}"   # PER GPU. x4 = pinned host memory.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-131072}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-8}"
GPU_UTIL="${GPU_UTIL:-0.93}"
TP_SIZE="${TP_SIZE:-4}"

# --- 1. gcc 14 --------------------------------------------------------------
# The prebuilt aarch64 deep_gemm wheel needs CXXABI_1.3.15 (gcc 14). The spack
# python module drags in gcc-runtime/13.2.1, which tops out at 1.3.14, and its
# lib dir wins on LD_LIBRARY_PATH. Cray's gcc-native/14 is loaded by default but
# does NOT reorder it; the spack gcc/14.2.0 module does.
if ! command -v module >/dev/null 2>&1 && [[ -f /etc/profile.d/lmod.sh ]]; then
  # shellcheck disable=SC1091
  source /etc/profile.d/lmod.sh
fi
module load gcc/14.2.0 || echo "warn: gcc/14.2.0 not loaded; standalone deep_gemm will fail (bundled still works)"

module load python/3.11.9 || true
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

# --- 2. libnvrtc.so.13 ------------------------------------------------------
# torch is 2.11.0+cu130, so the vendored vllm.third_party.deep_gemm wants CUDA
# 13's NVRTC. It ships in the venv but is not on the loader path. Without this,
# GLM-5.2 dies at "Sparse Attention Indexer CUDA op requires DeepGEMM support"
# -- vLLM checks whether DeepGEMM *imports*, not whether it works, so a missing
# .so surfaces as a capability error rather than an ImportError.
# NB: nvidia/cuda_nvrtc/lib holds libnvrtc.so.12 -- the wrong one. It is cu13.
CU13_LIB="$(python -c 'import os,sysconfig;p=os.path.join(sysconfig.get_paths()["purelib"],"nvidia","cu13","lib");print(p if os.path.isdir(p) else "")')"
if [[ -n "${CU13_LIB}" ]]; then
  export LD_LIBRARY_PATH="${CU13_LIB}:${LD_LIBRARY_PATH:-}"
else
  echo "warn: nvidia/cu13/lib not found; if DeepGEMM fails: uv pip install nvidia-cuda-nvrtc-cu13"
fi
# gcc 14's libstdc++ ahead of spack's 13.2.1, so the standalone deep_gemm also
# imports. Optional (the bundled one satisfies vLLM) but it silences the warning
# spam and gives vLLM its preferred DeepGEMM. libstdc++ is ABI-backward-compatible.
if command -v gcc >/dev/null 2>&1; then
  STDCXX_DIR="$(dirname "$(gcc -print-file-name=libstdc++.so.6)")"
  [[ -d "${STDCXX_DIR}" ]] && export LD_LIBRARY_PATH="${STDCXX_DIR}:${LD_LIBRARY_PATH}"
fi

# --- 3. Standardized DeltaAI env block (shared with serve_gh200.sbatch) ------
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export VLLM_HOST_IP=127.0.0.1
export MASTER_ADDR=127.0.0.1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export OMP_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}"
ulimit -l unlimited || true

# --- 4. Preflight -----------------------------------------------------------
# Fail in seconds, not 45 minutes. Startup is ~15 min of weight loading plus
# ~17 min of torch.compile before anything touches the indexer or the KV cache.
echo "== preflight =="
python -c "import torch; print(f'torch {torch.__version__} cuda {torch.version.cuda}')"
python -c "import vllm.third_party.deep_gemm" \
  && echo "deep_gemm: bundled OK" \
  || { echo "FATAL: vllm.third_party.deep_gemm will not import -> the DSA indexer will refuse to build."; exit 1; }
python -c "import deep_gemm" 2>/dev/null && echo "deep_gemm: standalone OK" || echo "deep_gemm: standalone unavailable (fine, bundled is used)"
[[ -d "${MODEL}" || -n "${MODEL##/*}" ]] || { echo "FATAL: MODEL ${MODEL} not found"; exit 1; }
echo "host=$(hostname) model=${MODEL} offload=${CPU_OFFLOAD_GB}GiB/gpu (x${TP_SIZE} = $((CPU_OFFLOAD_GB * TP_SIZE))GiB pinned)"
free -g | head -2

# --- 5. Serve ---------------------------------------------------------------
# DO NOT ADD --kv-cache-dtype fp8. It selects the FLASHMLA_SPARSE backend, whose
# fp8_ds_mla layout is 656 B/token/layer while vLLM's profiling reshape assumes
# the 576-element bf16 MLA latent. Startup dies at KV init with
#   RuntimeError: shape '[16, 64, 576]' is invalid for input of size 671744
# (671744 / (16*64) = 656 exactly). Known upstream, no fix:
#   https://github.com/vllm-project/recipes/issues/565
# Without the flag the backend picks FLASH_ATTN_MLA_SPARSE and init proceeds.
# The cost is a ~2x bigger KV pool, which is what CPU_OFFLOAD_GB=36 pays for.
#
# Parsers are glm47 (tool) / glm45 (reasoning) per the vLLM GLM-5.2 recipe. They
# do not match the model name; that is correct, not a typo.
#
# Expert parallel is left off: it changes which params are resident vs offloaded,
# which is not a variable you want in play during bring-up.
set -x
exec vllm serve "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --tensor-parallel-size "${TP_SIZE}" \
  --cpu-offload-gb "${CPU_OFFLOAD_GB}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --max-num-seqs "${MAX_NUM_SEQS}" \
  --gpu-memory-utilization "${GPU_UTIL}" \
  --tool-call-parser glm47 \
  --reasoning-parser glm45 \
  --enable-auto-tool-choice \
  --trust-remote-code \
  --host "${HOST}" --port "${PORT}"

# --- Open items -------------------------------------------------------------
# * TP0's pinned-memory allocation (uva.py _maybe_offload_to_cpu) stalled >15 min
#   at CPU_OFFLOAD_GB=36 while TP1/2/3 finished in seconds. py-spy showed it
#   ACTIVE in a tensor factory, not blocked. Unresolved. Suspected NUMA: each
#   Grace is local to exactly one Hopper, and vLLM has no per-worker NUMA
#   binding (its TP workers are children of one process, so srun --cpu-bind
#   would pin all four to the SAME node -- worse). Diagnose with
#   `numastat -p <TP0 pid>`. https://dnhkng.github.io/posts/gh200-benchmarking-part-3-glm52/
#   measured 8.5x (2.39 -> 20.31 tok/s) from local NUMA placement alone on
#   2xGH200 + GLM-5.2 + offload, but publishes no binding recipe.
# * Whether this path beats llama.cpp IQ4_XS at all is UNMEASURED. Decode is
#   likely a wash (llama.cpp measured 40 t/s; the blog got 43 on vLLM). PREFILL
#   is the open question and the reason to finish: llama.cpp gets only ~575 t/s
#   because --split-mode layer is pipeline-parallel at ~48% GPU util, while vLLM
#   does real TP. Run scripts/serve/bench_serve.py to settle it.
# * Download (~3-6 min, 83 shards, plain flags -- no HF_XET_HIGH_PERFORMANCE):
#     hf download cyankiwi/GLM-5.2-AWQ-INT4 --local-dir /tmp/GLM-5-2
