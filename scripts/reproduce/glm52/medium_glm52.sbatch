#!/bin/bash
# Medium-tier sibling of easy_glm52.sbatch (see that header for the serve
# rationale and doc pointers). Runs the paired reproduce->audit sweep over the
# eval split's Medium tier.
#   sbatch scripts/reproduce/glm52/medium_glm52.sbatch
#SBATCH -J repro_medium_glm52
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=288
#SBATCH --gpus-per-node=4
#SBATCH --mem=440G
#SBATCH --time=48:00:00
#SBATCH -o slurm-repro-medium-glm52-%j.out
#SBATCH -e slurm-repro-medium-glm52-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Config (override from the environment) ---------------------------------
export REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
export VENV="${VENV:-${REPROCLI}/.venv}"
export MODEL="${MODEL:-/work/nvme/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4}"
export SERVED_NAME="${SERVED_NAME:-zai-org/GLM-5.2}"
AUDIT_MODEL="${AUDIT_MODEL:-${SERVED_NAME}}"  # grader; this job serves one brain, so it defaults to it
export PORT="${PORT:-8000}"
SPLIT="${SPLIT:-eval}"                    # eval -> HF 'test' (the frozen 100-paper benchmark)
TIER="${TIER:-Medium}"                      # only reproduce+grade rows of this tier
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"        # reproduction agent tool rounds
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"  # auditor's run-dir exploration rounds
MAX_PARALLEL="${MAX_PARALLEL:-6}"        # papers in flight at once; each adds 1 JIT ghx4 node
RESUME="${RESUME:-1}"                    # 1 -> skip papers that already have a verdict on disk
# Brain knobs. MAX_MODEL_LEN must hold the auditor's 118k in + 32k out.
# vLLM shares ONE ~530k-token KV pool across all streams, where llama.cpp gave
# each slot its own 131k. MAX_PARALLEL=6 transcripts near full length would
# exceed that pool and vLLM starts preempting. The 8-agent benchmark only
# reached 17k-token transcripts (~136k total), so pool pressure at sweep scale
# is UNTESTED -- if throughput sags mid-sweep, lower MAX_PARALLEL first.
export TP="${TP:-4}"
export MAX_MODEL_LEN="${MAX_MODEL_LEN:-196608}"
export MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"   # MAX_PARALLEL papers + the audit stream
export GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
export IFACE="${IFACE:-hsn0}"

case "${SPLIT}" in
  dev|validation) CLAIMS_FILE="dev_split.jsonl" ;;
  *)              CLAIMS_FILE="eval_100.jsonl" ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/${LOCKFILE}/${CLAIMS_FILE}}"

export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
# APPTAINERENV_HF_HOME sends the in-container agent's HF pulls to node-local /tmp
# (clears per job); the served brain + orchestrator keep the persistent /work cache.
export APPTAINERENV_HF_HOME="${APPTAINERENV_HF_HOME:-/tmp/hf_cache}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT}/agent_runs}"
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARNING: HF_TOKEN is unset; the lockfile/bundle download from the Hub may fail." >&2
fi

export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"
if [[ -z "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "WARNING: SUPABASE_SERVICE_KEY is unset; runs + audit verdicts will NOT upload to agent-logs." >&2
fi

OUTER_JOB="${SLURM_JOB_ID:-local}"
export REPRO_BATCH_ID="${REPRO_BATCH_ID:-slurm-${OUTER_JOB}}"
export REPRO_BATCH_LABEL="${REPRO_BATCH_LABEL:-${SLURM_JOB_NAME:-repro_sweep} #${OUTER_JOB}}"
SWEEP_DIR="${SWEEP_DIR:-${REPRO_WORK_ROOT}/medium_sweeps/${OUTER_JOB}}"
ENDPOINT_FILE="${ENDPOINT_FILE:-${SWEEP_DIR}/brain_endpoint.${OUTER_JOB}.json}"
IDS_FILE="${SWEEP_DIR}/medium_ids.txt"
mkdir -p "${SWEEP_DIR}"

# Sweep-wall deadline (epoch) surfaced to the agent each round; from squeue %e, else --time cap.
if end_ts="$(squeue -h -j "${SLURM_JOB_ID}" -o '%e' 2>/dev/null)" \
   && [ -n "${end_ts}" ] \
   && REPRO_WALL_DEADLINE_EPOCH="$(date -d "${end_ts}" +%s 2>/dev/null)"; then
  :
else
  REPRO_WALL_DEADLINE_EPOCH="$(( $(date +%s) + 48 * 3600 ))"
fi
export REPRO_WALL_DEADLINE_EPOCH

export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export SAFETENSORS_FAST_GPU=1 CUDA_MODULE_LOADING=LAZY CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export NCCL_CUMEM_ENABLE=0 NCCL_CUMEM_HOST_ENABLE=0
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=1800
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1
unset VLLM_HOST_IP MASTER_ADDR MASTER_PORT   # per-node facts; inherited ones bind the wrong host
ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

[[ -d "${MODEL}" ]] || { echo "missing checkpoint ${MODEL}; download per runbook step 1" >&2; exit 1; }

echo "host=$(hostname)  job=${OUTER_JOB}  endpoint_file=${ENDPOINT_FILE}"
if [[ -n "${BUDGET_H100_HOURS}" ]]; then
  BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")
  BUDGET_LABEL="${BUDGET_H100_HOURS}h (flat)"
else
  BUDGET_ARG=()
  BUDGET_LABEL="per-band"
fi
echo "sweep_dir=${SWEEP_DIR}  split=${SPLIT}  tier=${TIER}  budget=${BUDGET_LABEL}  rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}"
echo "runs_dir=${RUNS_DIR}  resume=${RESUME}  audit_model=${AUDIT_MODEL}  audit_rounds=${AUDIT_TOOL_ROUNDS}"
echo "claims=${CLAIMS}"
echo "brain: ${MODEL}  tp=${TP}  max_model_len=${MAX_MODEL_LEN}  max_num_seqs=${MAX_NUM_SEQS}"
nvidia-smi topo -m || true

# --- Step 1: serve the brain across both nodes, wait for /health -------------
mapfile -t NODES < <(scontrol show hostnames "${SLURM_JOB_NODELIST}")
export NNODES="${#NODES[@]}"
export PP="${PP:-${NNODES}}"
HEAD_IP="$(
  srun --jobid="${SLURM_JOB_ID}" --nodes=1 --ntasks=1 --nodelist="${NODES[0]}" \
    bash -lc "ip -o -4 addr show ${IFACE} | awk '{split(\$4,a,\"/\"); print a[1]; exit}'"
)"
[[ -n "${HEAD_IP}" && "${HEAD_IP}" != 127.* ]] || {
  echo "bad HEAD_IP='${HEAD_IP}' from ${IFACE} on ${NODES[0]}" >&2; exit 1; }
export HEAD_IP
echo "nodes=${NNODES} head=${NODES[0]} head_ip=${HEAD_IP} tp=${TP} pp=${PP}"

# Two seconds here, versus ~7 min to fail at the DSA indexer.
srun --jobid="${SLURM_JOB_ID}" --nodes="${NNODES}" --ntasks="${NNODES}" bash -c \
  "source ${VENV}/bin/activate
   export LD_LIBRARY_PATH=${VENV}/lib/python3.11/site-packages/nvidia/cu13/lib:\${LD_LIBRARY_PATH:-}
   python -c 'import vllm.third_party.deep_gemm'" \
  || { echo "deep_gemm import failed; fix LD_LIBRARY_PATH per runbook C1" >&2; exit 1; }

srun --jobid="${SLURM_JOB_ID}" --nodes="${NNODES}" --ntasks="${NNODES}" \
  --ntasks-per-node=1 --gpus-per-task="${TP}" --cpus-per-task=32 \
  bash scripts/serve/glm52_2node.sh >"${SWEEP_DIR}/brain.log" 2>&1 &
SERVER_PID=$!
trap 'rm -f "${ENDPOINT_FILE}"; kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# ~9 min cold. A dead brain must kill the sweep, not leave it idling.
for _ in $(seq 1 720); do
  curl -sf "http://${HEAD_IP}:${PORT}/health" >/dev/null && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "brain exited before /health (see ${SWEEP_DIR}/brain.log)" >&2; exit 1
  fi
  sleep 10
done
curl -sf "http://${HEAD_IP}:${PORT}/health" >/dev/null || { echo "timed out waiting for /health" >&2; exit 1; }

BASE_URL="http://${HEAD_IP}:${PORT}/v1"
python3 - "${ENDPOINT_FILE}" <<PY
import json, sys
payload = {
    "base_url": "${BASE_URL}",
    "host": "${HEAD_IP}",
    "port": ${PORT},
    "served_model_name": "${SERVED_NAME}",
    "model_path": "${MODEL}",
    "node": "${NODES[0]}",
    "job_id": "${OUTER_JOB}",
    "health": "ready",
}
with open(sys.argv[1], "w") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
PY
echo "brain up at ${BASE_URL}"

BEACON_PID=""
if [[ -n "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  LOGFILE="$(scontrol show job "${OUTER_JOB}" 2>/dev/null | sed -n 's/.*StdOut=\([^ ]*\).*/\1/p' | head -1)"
  python -m reprocli_repro.metrics_beacon --role master --log-file "${LOGFILE:-/dev/null}" --interval 15 &
  BEACON_PID=$!
fi
trap 'rm -f "${ENDPOINT_FILE}"; kill "${SERVER_PID}" ${BEACON_PID:+"${BEACON_PID}"} 2>/dev/null || true' EXIT

export REPROCLI_ENDPOINT_FILE="${ENDPOINT_FILE}"

# --- Step 2: enumerate the Medium tier of the split ---------------------------
mapfile -t PAPER_IDS < <(
  python - "${LOCKFILE}" "${SPLIT}" "${TIER}" <<'PY'
import sys
from reprocli_repro.inputs import (
    DEFAULT_UNBANDED_BUDGET_H100_HOURS,
    band_max_hours,
    load_lockfile_rows,
)
rows = load_lockfile_rows(sys.argv[1], split=sys.argv[2])
want = sys.argv[3]
tier = [(pid, row) for pid, row in rows.items() if (row.get("tier") or "") == want]
# Smallest compute ceiling first: cheap papers land results early, and a
# long-budget paper hitting the sweep's wall clock wastes less of the queue.
tier.sort(key=lambda pr: band_max_hours(pr[1]) or DEFAULT_UNBANDED_BUDGET_H100_HOURS)
for pid, _ in tier:
    print(pid)
PY
)
if [[ "${#PAPER_IDS[@]}" -eq 0 ]]; then
  echo "no ${TIER}-tier papers found in ${LOCKFILE} split=${SPLIT}" >&2; exit 1
fi
printf '%s\n' "${PAPER_IDS[@]}" > "${IDS_FILE}"
echo "split '${SPLIT}' tier '${TIER}' has ${#PAPER_IDS[@]} papers: ${PAPER_IDS[*]}"
echo "ids -> ${IDS_FILE}"

# --- Step 3: scrub inherited SLURM_* so JIT sallocs/sruns start clean --------
for v in $(compgen -v | grep -E '^SLURM_' || true); do unset "$v"; done
export SLURM_EXPORT_ENV=ALL

# --- Step 4: reproduce + audit every Medium paper, PAIRED on one bundle --------
STATUS_FILE="${SWEEP_DIR}/status.tsv"

run_one() {
  local pid="$1"
  local log="${SWEEP_DIR}/repro_${pid}.log"
  local verdicts="${SWEEP_DIR}/audit_${pid}_extracted.jsonl"

  # Resume only unfinished papers after a wall-time cap.
  if [[ "${RESUME}" == "1" && -s "${verdicts}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "-" "resume-skip" "-" "-" >> "${STATUS_FILE}"
    echo "=== [$(date '+%F %T')] ${pid} already graded -> skip (${verdicts})"
    return 0
  fi

  local rid="${OUTER_JOB}-${pid}-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  echo ">>> [$(date '+%F %T')] start ${pid} (run_id=${rid})"

  # (1) Reproduce this paper.
  python -m reprocli_repro \
    --paper-id "${pid}" \
    --split "${SPLIT}" \
    --lockfile "${LOCKFILE}" \
    --run-id "${rid}" \
    "${BUDGET_ARG[@]}" \
    --tool-rounds "${TOOL_ROUNDS}" \
    --served-model-name "${SERVED_NAME}" \
    --output "${SWEEP_DIR}/reproduce_${pid}.jsonl" \
    --save-round-jsonl \
    >"${log}" 2>&1
  local rc=$?

  # (2) Locate this run's bundle by run id.
  local run_dir
  run_dir="$(find "${RUNS_DIR}/${pid}" -type d -name "${rid}" -print -quit 2>/dev/null || true)"
  if [[ -z "${run_dir}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${rc}" "no-bundle" "-" "${rid}" >> "${STATUS_FILE}"
    echo "<<< [$(date '+%F %T')] ${pid} repro_rc=${rc} wrote NO bundle -> skip audit (log: ${log})"
    return 0
  fi

  # (3) Point the auditor's <runs-dir>/<pid> at this bundle only.
  local grade_root ids_file
  grade_root="$(mktemp -d "${SWEEP_DIR}/grade_${pid}.XXXXXX")"
  ln -s "${run_dir}" "${grade_root}/${pid}"
  ids_file="${grade_root}/ids.txt"
  printf '%s\n' "${pid}" > "${ids_file}"

  # (4) Audit exactly this bundle and link the live audit to the graded run.
  REPROCLI_GRADED_RUN_ID="${rid}" \
  python3 src/run_arxiv_prompt_vllm.py \
    --mode audit \
    --vllm-server-url "${BASE_URL}" \
    --served-model-name "${AUDIT_MODEL}" \
    --model "${AUDIT_MODEL}" \
    --runs-dir "${grade_root}" \
    --claims "${CLAIMS}" \
    --paper-ids-file "${ids_file}" \
    --tool-rounds "${AUDIT_TOOL_ROUNDS}" \
    --max-input-tokens 118000 \
    --max-tokens 32768 \
    --max-model-len "${MAX_MODEL_LEN}" \
    --output "${SWEEP_DIR}/audit_${pid}.jsonl" \
    --extracted-output "${verdicts}" \
    --trace-output "${SWEEP_DIR}/audit_${pid}_trace.jsonl" \
    --save-round-jsonl \
    >>"${log}" 2>&1
  local arc=$?
  rm -rf "${grade_root}"

  # (5) Upload successful, nonempty verdicts to the pinned run_id.
  local uploaded="off"
  if [[ "${arc}" != "0" ]]; then
    uploaded="audit-fail"
  elif [[ ! -s "${verdicts}" ]]; then
    uploaded="no-verdict"
  elif [[ -n "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
    if python3 -m reprocli_repro.audit_upload \
         --verdicts "${verdicts}" \
         --runs-dir "${RUNS_DIR}" \
         --run-id "${rid}" \
         --audit-model "${AUDIT_MODEL}" >>"${log}" 2>&1; then
      uploaded="ok"
    else
      uploaded="upload-fail"
    fi
  fi

  printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${rc}" "${arc}" "${uploaded}" "${rid}" >> "${STATUS_FILE}"
  echo "<<< [$(date '+%F %T')] done ${pid} repro_rc=${rc} audit_rc=${arc} upload=${uploaded} (bundle: ${run_dir})"
  return 0
}

: > "${STATUS_FILE}"
set +e   # one bad paper must not abort the sweep
run_pids=()
inflight=0
for pid in "${PAPER_IDS[@]}"; do
  run_one "${pid}" &
  run_pids+=("$!")
  inflight=$((inflight + 1))
  if (( inflight >= MAX_PARALLEL )); then
    wait -n   # next paper to finish (the server never exits, so it's never this)
    inflight=$((inflight - 1))
  fi
done
wait "${run_pids[@]}" 2>/dev/null || true   # only the papers, not the brain
set -e
echo "===== ${TIER} paired reproduce+audit complete (job ${OUTER_JOB}) ====="
repro_ok=$(awk -F'\t' '$2=="0"' "${STATUS_FILE}" | wc -l)
audit_ok=$(awk -F'\t' '$3=="0"' "${STATUS_FILE}" | wc -l)
upload_ok=$(awk -F'\t' '$4=="ok"' "${STATUS_FILE}" | wc -l)
total=$(wc -l < "${STATUS_FILE}")
echo "reproduced ok: ${repro_ok}/${total}   audited ok: ${audit_ok}/${total}   uploaded ok: ${upload_ok}/${total}   (per-paper rc in ${STATUS_FILE})"
sort "${STATUS_FILE}"

# --- Summary ----------------------------------------------------------------
echo "===== ${TIER} sweep complete (job ${OUTER_JOB}) ====="
echo "run bundles : ${RUNS_DIR}/<arxiv_id>/<budget>h/<run_id>/"
echo "reproduce   : ${SWEEP_DIR}/reproduce_<arxiv_id>.jsonl  (status: ${STATUS_FILE})"
echo "grades      : ${SWEEP_DIR}/audit_<arxiv_id>_extracted.jsonl  (score/verdict/reproduced per paper)"
echo "audit trace : ${SWEEP_DIR}/audit_<arxiv_id>_trace.jsonl"
