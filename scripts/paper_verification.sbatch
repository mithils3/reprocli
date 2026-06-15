#!/bin/bash
#SBATCH -J reprocli_paper_verification
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH --mem=256G
#SBATCH --time=4:00:00
#SBATCH -o slurm-verify-%j.out
#SBATCH -e slurm-verify-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail
export TORCHINDUCTOR_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/.cache/vllm
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export MASTER_ADDR=127.0.0.1
export VLLM_HOST_IP=127.0.0.1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
export NCCL_DEBUG_SUBSYS="${NCCL_DEBUG_SUBSYS:-INIT,ENV,NET}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"
export TORCH_NCCL_ENABLE_MONITORING="${TORCH_NCCL_ENABLE_MONITORING:-1}"
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}

ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli/

if [[ -z "${CXX:-}" || "${CXX}" == "CC" ]]; then
  if command -v g++ >/dev/null 2>&1; then
    export CXX="$(command -v g++)"
  elif command -v c++ >/dev/null 2>&1; then
    export CXX="$(command -v c++)"
  fi
fi
if [[ -n "${CXX:-}" ]]; then
  export TORCHINDUCTOR_CXX="${TORCHINDUCTOR_CXX:-${CXX}}"
fi

echo "host=$(hostname)"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
echo "SLURM_JOB_GPUS=${SLURM_JOB_GPUS:-unset}"
echo "SLURM_STEP_GPUS=${SLURM_STEP_GPUS:-unset}"
env | sort | grep -E '^(CUDA|NCCL|VLLM|SLURM|MASTER|OMP|TORCH|TRITON|SAFETENSORS)_' || true
nvidia-smi topo -m || true

# Verification mode is MRE-only and tools-off: each paper is one schema-forced
# generation from its MRE record (no paper bundle, no GitHub/HF tool loop).
python3 src/run_arxiv_prompt_vllm.py \
  --mode verification \
  --prompt-file prompt_verification.txt \
  --mre-records hf://datasets/Mithilss/neurips-2025-audit-pool/audit_pool_extracted.jsonl \
  --max-input-tokens 16000 \
  --max-tokens 12288 \
  --request-workers 128 \
  --vllm-cache-dir /projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache \
  --distributed-executor-backend mp \
  --output outputs/v5/audit_pool_verification_targets.jsonl \
  --extracted-output outputs/v5/audit_pool_verification_targets_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608 \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --hf-repo Mithilss/neurips-2025-audit-pool-targets
