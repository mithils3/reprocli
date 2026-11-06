#!/usr/bin/env bash
# Sequential Codex sweeps on one login node: gpt-6.1-sol 1-24, then gpt-6-astra 1-8, then gpt-6.1-terra 1-24.
# Each sweep takes SKIP from skip_list.py (finished non-VOID runs and in-flight runs of that model).
#   nohup scripts/rebuttal/codex_arm/sequence_sweeps.sh > ~/seq.log 2>&1 &   (inside tmux)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="${PY:-${ROOT}/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-/work/nvme/bfvr/msalunkhe/rebuttal/codex}"
export PYTHONPATH="${ROOT}/src"

run_sweep() {  # model ranks parallel
  local model=$1 ranks=$2 par=$3 skip
  skip="$("${PY}" "${ROOT}/scripts/rebuttal/codex_arm/skip_list.py" --model "${model}")"
  echo "[$(date -u '+%F %T')] sweep ${model} ${ranks} parallel=${par} skip=${skip:-none}"
  SKIP="${skip}" MODEL="${model}" RANKS="${ranks}" MAX_PARALLEL="${par}" EST_RUN_USD=40 PY="${PY}" \
    bash "${ROOT}/scripts/rebuttal/codex_arm/codex_sweep.sh" > "${LOG_DIR}/sweep-${model}-seq-$(date -u +%H%M).log" 2>&1
  echo "[$(date -u '+%F %T')] done ${model} exit=$?"
}

run_sweep gpt-6.1-sol 1-24 3
run_sweep gpt-6-astra 1-8 2
run_sweep gpt-6.1-terra 1-24 2
echo "[$(date -u '+%F %T')] all sweeps finished"
