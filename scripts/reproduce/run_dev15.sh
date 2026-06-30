#!/bin/bash
# Login-node driver for the dev-15 reproduction sweep — the no-wall-cap path.
#
# Unlike reproduce_dev15_minimax_m2.sbatch (one ghx4 job that hosts brain +
# orchestrator and is bounded by the 48h partition limit), this runs the
# orchestrator on a LOGIN NODE: it holds no GPU, every `run_gpu` step JIT-`salloc`s
# its own ghx4 node, and the sweep can run as long as it needs. The brain still
# lives in its own ghx4 serve job.
#
# Run it detached so it survives your SSH session:
#   cd /u/msalunkhe/reprocli
#   nohup bash scripts/reproduce/run_dev15.sh > dev15_sweep.out 2>&1 &
#   # or inside tmux/screen
#
# Knobs (env): SUBMIT_SERVE=1 submits the brain if no healthy endpoint is found;
#   MAX_PARALLEL, BUDGET_H100_HOURS, TOOL_ROUNDS, SPLIT, SERVED_NAME, ENDPOINT_FILE.
#
# NOTE: dependency installs (`uv` venvs, CUDA torch wheels via workspace_bash) run
# HERE, on the shared login node. MAX_PARALLEL=5 means 5 concurrent installs — fine
# for a dev sweep, but be a good citizen; lower it if the login node is busy.

set -euo pipefail

REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M2.7}"
SPLIT="${SPLIT:-dev}"
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-40}"
MAX_PARALLEL="${MAX_PARALLEL:-5}"
SUBMIT_SERVE="${SUBMIT_SERVE:-0}"
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/endpoints/minimax_m2.json}"

export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
[[ -z "${HF_TOKEN:-}" ]] && echo "WARNING: HF_TOKEN unset; Hub downloads may fail." >&2

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

STAMP="$(date '+%Y%m%d_%H%M%S')"
SWEEP_DIR="${REPRO_WORK_ROOT}/dev15_sweeps/login_${STAMP}"
mkdir -p "${SWEEP_DIR}"
# Pass --budget-h100-hours only when a flat budget is set; otherwise the CLI
# derives each paper's ceiling from its selection band.
if [[ -n "${BUDGET_H100_HOURS}" ]]; then
  BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")
  BUDGET_LABEL="${BUDGET_H100_HOURS}h (flat)"
else
  BUDGET_ARG=()
  BUDGET_LABEL="per-band"
fi
echo "sweep_dir=${SWEEP_DIR}  split=${SPLIT}  budget=${BUDGET_LABEL}  rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}"

endpoint_healthy() {
  [[ -f "${ENDPOINT_FILE}" ]] || return 1
  local url
  url="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}" 2>/dev/null)" || return 1
  curl -fsS "${url}/health" >/dev/null 2>&1
}

# --- Brain: reuse a healthy one, else optionally submit the serve job --------
if ! endpoint_healthy; then
  if [[ "${SUBMIT_SERVE}" != "0" ]]; then
    echo "no healthy brain; submitting scripts/serve/serve_gh200.sbatch ..."
    ENDPOINT_FILE="${ENDPOINT_FILE}" sbatch scripts/serve/serve_gh200.sbatch
  else
    echo "waiting for an existing brain to publish ${ENDPOINT_FILE} (SUBMIT_SERVE=1 to launch one) ..."
  fi
  for _ in $(seq 1 720); do endpoint_healthy && break; sleep 5; done
fi
endpoint_healthy || { echo "no healthy brain at ${ENDPOINT_FILE}; aborting." >&2; exit 1; }
BASE_URL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}")"
echo "brain up at ${BASE_URL}"
export REPROCLI_ENDPOINT_FILE="${ENDPOINT_FILE}"

# --- Enumerate the dev split ------------------------------------------------
mapfile -t PAPER_IDS < <(
  python - "${LOCKFILE}" "${SPLIT}" <<'PY'
import sys
from reprocli_repro.inputs import load_lockfile_rows
for pid in load_lockfile_rows(sys.argv[1], split=sys.argv[2]):
    print(pid)
PY
)
[[ "${#PAPER_IDS[@]}" -gt 0 ]] || { echo "no papers in ${LOCKFILE} split=${SPLIT}" >&2; exit 1; }
echo "dev split '${SPLIT}' has ${#PAPER_IDS[@]} papers: ${PAPER_IDS[*]}"

STATUS_FILE="${SWEEP_DIR}/status.tsv"
: > "${STATUS_FILE}"

run_one() {
  local pid="$1"
  local log="${SWEEP_DIR}/repro_${pid}.log"
  echo ">>> [$(date '+%F %T')] start ${pid}"
  python -m reprocli_repro \
    --paper-id "${pid}" \
    --split "${SPLIT}" \
    --lockfile "${LOCKFILE}" \
    --cluster deltaai \
    "${BUDGET_ARG[@]}" \
    --tool-rounds "${TOOL_ROUNDS}" \
    --served-model-name "${SERVED_NAME}" \
    --output "${SWEEP_DIR}/reproduce_${pid}.jsonl" \
    --save-round-jsonl \
    >"${log}" 2>&1
  local rc=$?
  printf '%s\t%s\n' "${pid}" "${rc}" >> "${STATUS_FILE}"
  echo "<<< [$(date '+%F %T')] done  ${pid} rc=${rc} (log: ${log})"
  return 0
}

set +e   # one bad paper must not abort the sweep
inflight=0
for pid in "${PAPER_IDS[@]}"; do
  run_one "${pid}" &
  inflight=$((inflight + 1))
  if (( inflight >= MAX_PARALLEL )); then
    wait -n
    inflight=$((inflight - 1))
  fi
done
wait

echo "===== dev-15 sweep complete ====="
ok=$(awk -F'\t' '$2==0' "${STATUS_FILE}" | wc -l)
total=$(wc -l < "${STATUS_FILE}")
echo "papers ok: ${ok}/${total}  (per-paper rc in ${STATUS_FILE})"
sort "${STATUS_FILE}"
echo "run bundles: ${REPRO_WORK_ROOT}/agent_runs/<arxiv_id>/<budget>h/<run_id>/"
