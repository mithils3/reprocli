#!/bin/bash
# Repair the casualties of a venv mutation during a live sweep.
#
# On 2026-07-14 a pip install ran against ${VENV} while job 2652648 was mid-flight.
# A pip upgrade uninstalls before it reinstalls, so for a few seconds the package
# dirs did not exist. Every paper the sweep launched inside that window died on
# `import datasets` -> ModuleNotFoundError (huggingface_hub, then filelock) before
# writing a bundle, and one paper's *audit* died the same way. Because run_one
# returns 0 on the no-bundle path, the sweep would have finished "clean" with 27 of
# 34 Easy papers and no failure surfaced anywhere but status.tsv.
#
# These are harness casualties, not model failures: they must be rerun, not scored.
# This job does two kinds of repair against ONE served brain:
#
#   REPAIR_IDS    - full reproduce+audit, for papers whose bundle never existed
#   REAUDIT_RUNS  - audit only, for papers whose bundle is fine but whose audit died
#                   ("<paper_id>=<run_id>"; the verdict PATCHes onto that same row)
#
# Defaults target job 2652648. Both lists are overridable, so this stays the tool
# for the next time a sweep gets shot in the back:
#
#   sbatch scripts/reproduce/minimax_m2/repair_easy_minimax.sbatch
#   REPAIR_IDS="2505.14827 2504.12397" REAUDIT_RUNS="" sbatch .../repair_easy_minimax.sbatch
#
# It writes into the ORIGINAL sweep dir so the repaired verdicts land beside the
# survivors and the set is complete for downstream analysis, and it keeps the
# original REPRO_BATCH_ID so the viewer shows one coherent batch rather than an
# orphan of six. It never truncates anything the original job owns: its own status
# goes to status_repair.tsv and its logs to repair_<id>.log, leaving the original
# tracebacks intact as the forensic record.
#
#SBATCH -J repro_easy_repair
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=2
#SBATCH --gpu-bind=none
#SBATCH --mem=220G
#SBATCH --time=24:00:00
#SBATCH -o slurm-repro-repair-%j.out
#SBATCH -e slurm-repro-repair-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- What to repair (override from the environment) -------------------------
ORIG_JOB="${ORIG_JOB:-2652648}"
# The six no-bundle papers from status.tsv: rc=1, killed on import at ~19:59:0x.
REPAIR_IDS="${REPAIR_IDS:-2505.14827 2505.24864 2504.12397 2505.23305 2506.18896 2412.11979}"
# 2506.21724 reproduced fine (bundle intact, row uploaded) but its audit hit the
# same window and exited in ~84s, where a healthy audit takes 2-5min. Re-audit
# only: no GPU reproduce, and the verdict PATCHes onto the original run_id.
REAUDIT_RUNS="${REAUDIT_RUNS:-2506.21724=${ORIG_JOB}-2506.21724-d6dac2}"

# --- Config (mirrors easy_minimax_m2.sbatch) --------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-cyankiwi/MiniMax-M2.7-AWQ-4bit}"   # 4-bit AWQ W4A16, fits 2xGH200
SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M2.7}"
AUDIT_MODEL="${AUDIT_MODEL:-${SERVED_NAME}}"
PORT="${PORT:-8000}"
SPLIT="${SPLIT:-eval}"
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"
MAX_PARALLEL="${MAX_PARALLEL:-7}"        # 6 repairs + 1 re-audit -> everything in flight at once
RESUME="${RESUME:-1}"                    # 1 -> skip papers that already have a verdict on disk

case "${SPLIT}" in
  dev|validation) CLAIMS_FILE="dev_split.jsonl" ;;
  *)              CLAIMS_FILE="eval_100.jsonl" ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/${LOCKFILE}/${CLAIMS_FILE}}"

export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT}/agent_runs}"
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARNING: HF_TOKEN is unset; the lockfile/bundle download from the Hub may fail." >&2
fi

export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"
if [[ -z "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "WARNING: SUPABASE_SERVICE_KEY is unset; runs + audit verdicts will NOT upload to agent-logs." >&2
fi

OUTER_JOB="${SLURM_JOB_ID:-local}"
# Join the ORIGINAL batch: the repaired papers belong to that sweep's 34, not to a
# separate run of six. The viewer groups on batch_id.
export REPRO_BATCH_ID="${REPRO_BATCH_ID:-slurm-${ORIG_JOB}}"
export REPRO_BATCH_LABEL="${REPRO_BATCH_LABEL:-repro_easy_minimax #${ORIG_JOB}}"
SWEEP_DIR="${SWEEP_DIR:-${REPRO_WORK_ROOT}/easy_sweeps/${ORIG_JOB}}"
# The original job may still be serving its own brain on this port from another
# node; our endpoint file must not collide with the one it published.
ENDPOINT_FILE="${ENDPOINT_FILE:-${SWEEP_DIR}/brain_endpoint_repair_${OUTER_JOB}.json}"
STATUS_FILE="${SWEEP_DIR}/status_repair.tsv"
mkdir -p "${SWEEP_DIR}"

if end_ts="$(squeue -h -j "${SLURM_JOB_ID}" -o '%e' 2>/dev/null)" \
   && [ -n "${end_ts}" ] \
   && REPRO_WALL_DEADLINE_EPOCH="$(date -d "${end_ts}" +%s 2>/dev/null)"; then
  :
else
  REPRO_WALL_DEADLINE_EPOCH="$(( $(date +%s) + 24 * 3600 ))"
fi
export REPRO_WALL_DEADLINE_EPOCH

# --- Standardized DeltaAI serve env block (shared with scripts/serve/*) ------
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export MASTER_ADDR=127.0.0.1
export VLLM_HOST_IP=127.0.0.1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"

ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

echo "host=$(hostname)  job=${OUTER_JOB}  repairing=${ORIG_JOB}  endpoint_file=${ENDPOINT_FILE}"
echo "sweep_dir=${SWEEP_DIR}  batch=${REPRO_BATCH_ID}  parallel=${MAX_PARALLEL}  resume=${RESUME}"
echo "repair_ids=${REPAIR_IDS}"
echo "reaudit_runs=${REAUDIT_RUNS}"

# --- Step 0: preflight the venv ---------------------------------------------
# The whole reason this job exists. Import what a paper imports on its way to the
# lockfile, before we burn an hour of GH200 time serving a brain for papers that
# will die on import anyway. Fail loudly here instead of silently there.
python - <<'PY' || { echo "PREFLIGHT FAILED: ${VENV} is broken (mid-install?). Fix it, then resubmit." >&2; exit 1; }
import filelock, huggingface_hub  # noqa: F401  the two that vanished under job 2652648
from datasets import load_dataset  # noqa: F401
from reprocli_repro.inputs import prepare_episodes  # noqa: F401
print("preflight ok: filelock + huggingface_hub + datasets + reprocli_repro import cleanly")
PY

# Resolve every re-audit bundle up front for the same reason: a typo'd or missing
# run id should abort now, not after the brain is up.
declare -A REAUDIT_DIR=()
for spec in ${REAUDIT_RUNS}; do
  pid="${spec%%=*}"; rid="${spec#*=}"
  [[ "${pid}" != "${spec}" ]] || { echo "REAUDIT_RUNS entry '${spec}' is not <paper_id>=<run_id>" >&2; exit 1; }
  d="$(find "${RUNS_DIR}/${pid}" -type d -name "${rid}" -print -quit 2>/dev/null || true)"
  [[ -n "${d}" ]] || { echo "no bundle for re-audit ${pid} run_id=${rid} under ${RUNS_DIR}/${pid}" >&2; exit 1; }
  REAUDIT_DIR["${pid}"]="${d}"
  echo "preflight ok: re-audit ${pid} -> ${d}"
done

nvidia-smi topo -m || true

if [[ -n "${BUDGET_H100_HOURS}" ]]; then
  BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")
else
  BUDGET_ARG=()
fi

# --- Step 1: serve the brain (background), wait for /health ------------------
python -m reprocli_serve \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --tensor-parallel-size 2 \
  --max-model-len 196608 \
  --distributed-executor-backend mp \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --endpoint-file "${ENDPOINT_FILE}" \
  -- --kv-offloading-backend native --kv-offloading-size 64 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

for _ in $(seq 1 720); do
  [[ -f "${ENDPOINT_FILE}" ]] && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "brain exited before publishing an endpoint" >&2; exit 1
  fi
  sleep 5
done
[[ -f "${ENDPOINT_FILE}" ]] || { echo "timed out waiting for ${ENDPOINT_FILE}" >&2; exit 1; }

BASE_URL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}")"
curl -fsS "${BASE_URL}/health" >/dev/null && echo "brain up at ${BASE_URL}"

BEACON_PID=""
if [[ -n "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  LOGFILE="$(scontrol show job "${OUTER_JOB}" 2>/dev/null | sed -n 's/.*StdOut=\([^ ]*\).*/\1/p' | head -1)"
  python -m reprocli_repro.metrics_beacon --role master --log-file "${LOGFILE:-/dev/null}" --interval 15 &
  BEACON_PID=$!
fi
trap 'kill "${SERVER_PID}" ${BEACON_PID:+"${BEACON_PID}"} 2>/dev/null || true' EXIT

export REPROCLI_ENDPOINT_FILE="${ENDPOINT_FILE}"

# --- Step 2: scrub inherited SLURM_* so each run_gpu salloc/srun is clean ----
for v in $(compgen -v | grep -E '^SLURM_' || true); do unset "$v"; done
export SLURM_EXPORT_ENV=ALL

# --- Step 3: audit one existing bundle ---------------------------------------
# Shared by both paths: symlink <grade-root>/<pid> to exactly one bundle so the
# auditor's <runs-dir>/<pid> contract can only resolve to it, grade, then PATCH
# the verdict onto that pinned run_id.
audit_bundle() {
  local pid="$1" rid="$2" run_dir="$3" log="$4"
  local verdicts="${SWEEP_DIR}/audit_${pid}_extracted.jsonl"
  local grade_root ids_file
  grade_root="$(mktemp -d "${SWEEP_DIR}/grade_${pid}.XXXXXX")"
  ln -s "${run_dir}" "${grade_root}/${pid}"
  ids_file="${grade_root}/ids.txt"
  printf '%s\n' "${pid}" > "${ids_file}"

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
    --max-input-tokens 128000 \
    --max-tokens 8192 \
    --max-model-len 196608 \
    --output "${SWEEP_DIR}/audit_${pid}.jsonl" \
    --extracted-output "${verdicts}" \
    --trace-output "${SWEEP_DIR}/audit_${pid}_trace.jsonl" \
    --save-round-jsonl \
    >>"${log}" 2>&1
  local arc=$?
  rm -rf "${grade_root}"

  AUDIT_UPLOADED="off"
  if [[ "${arc}" != "0" ]]; then
    AUDIT_UPLOADED="audit-fail"
  elif [[ ! -s "${verdicts}" ]]; then
    AUDIT_UPLOADED="no-verdict"
  elif [[ -n "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
    if python3 -m reprocli_repro.audit_upload \
         --verdicts "${verdicts}" \
         --runs-dir "${RUNS_DIR}" \
         --run-id "${rid}" \
         --audit-model "${AUDIT_MODEL}" >>"${log}" 2>&1; then
      AUDIT_UPLOADED="ok"
    else
      AUDIT_UPLOADED="upload-fail"
    fi
  fi
  return "${arc}"
}

# --- Step 4: full repair (reproduce + audit) ---------------------------------
repair_one() {
  local pid="$1"
  local log="${SWEEP_DIR}/repair_${pid}.log"
  local verdicts="${SWEEP_DIR}/audit_${pid}_extracted.jsonl"

  if [[ "${RESUME}" == "1" && -s "${verdicts}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "-" "resume-skip" "-" "-" >> "${STATUS_FILE}"
    echo "=== [$(date '+%F %T')] ${pid} already graded -> skip (${verdicts})"
    return 0
  fi

  local rid="${OUTER_JOB}-${pid}-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  echo ">>> [$(date '+%F %T')] repair ${pid} (run_id=${rid})"

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

  local run_dir
  run_dir="$(find "${RUNS_DIR}/${pid}" -type d -name "${rid}" -print -quit 2>/dev/null || true)"
  if [[ -z "${run_dir}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${rc}" "no-bundle" "-" "${rid}" >> "${STATUS_FILE}"
    echo "<<< [$(date '+%F %T')] ${pid} repro_rc=${rc} wrote NO bundle AGAIN -> check ${log}"
    return 0
  fi

  audit_bundle "${pid}" "${rid}" "${run_dir}" "${log}"
  local arc=$?
  printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${rc}" "${arc}" "${AUDIT_UPLOADED}" "${rid}" >> "${STATUS_FILE}"
  echo "<<< [$(date '+%F %T')] done ${pid} repro_rc=${rc} audit_rc=${arc} upload=${AUDIT_UPLOADED} (bundle: ${run_dir})"
  return 0
}

# --- Step 5: re-audit only (bundle already good) -----------------------------
reaudit_one() {
  local pid="$1" rid="$2" run_dir="$3"
  local log="${SWEEP_DIR}/repair_${pid}.log"
  echo ">>> [$(date '+%F %T')] re-audit ${pid} (run_id=${rid}, bundle: ${run_dir})"
  audit_bundle "${pid}" "${rid}" "${run_dir}" "${log}"
  local arc=$?
  printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "reaudit" "${arc}" "${AUDIT_UPLOADED}" "${rid}" >> "${STATUS_FILE}"
  echo "<<< [$(date '+%F %T')] done ${pid} audit_rc=${arc} upload=${AUDIT_UPLOADED}"
  return 0
}

# --- Step 6: run them --------------------------------------------------------
: > "${STATUS_FILE}"   # ours alone; the original job owns status.tsv and still appends to it
set +e
run_pids=()
inflight=0
launch() {   # keep at most MAX_PARALLEL papers in flight
  run_pids+=("$1")
  inflight=$((inflight + 1))
  if (( inflight >= MAX_PARALLEL )); then
    wait -n
    inflight=$((inflight - 1))
  fi
}

# Re-audits first: they need no GPU and finish in minutes, so they are out of the
# way before the reproduces settle into the pool.
for spec in ${REAUDIT_RUNS}; do
  pid="${spec%%=*}"; rid="${spec#*=}"
  reaudit_one "${pid}" "${rid}" "${REAUDIT_DIR[${pid}]}" &
  launch "$!"
done
for pid in ${REPAIR_IDS}; do
  repair_one "${pid}" &
  launch "$!"
done
wait "${run_pids[@]}" 2>/dev/null || true
set -e

# --- Summary -----------------------------------------------------------------
echo "===== repair of job ${ORIG_JOB} complete (job ${OUTER_JOB}) ====="
total=$(wc -l < "${STATUS_FILE}")
audit_ok=$(awk -F'\t' '$3=="0"' "${STATUS_FILE}" | wc -l)
upload_ok=$(awk -F'\t' '$4=="ok"' "${STATUS_FILE}" | wc -l)
echo "audited ok: ${audit_ok}/${total}   uploaded ok: ${upload_ok}/${total}"
sort "${STATUS_FILE}"
# Say it loudly: a silent no-bundle is exactly what cost job 2652648 seven papers.
still_broken=$(awk -F'\t' '$3=="no-bundle"{print $1}' "${STATUS_FILE}")
if [[ -n "${still_broken}" ]]; then
  echo "!!! STILL NO BUNDLE (rerun these): ${still_broken}" >&2
fi
echo "verdicts    : ${SWEEP_DIR}/audit_<arxiv_id>_extracted.jsonl"
echo "repair logs : ${SWEEP_DIR}/repair_<arxiv_id>.log   (status: ${STATUS_FILE})"
echo "the ${ORIG_JOB} Easy tier is whole when 34 audit_*_extracted.jsonl files exist:"
echo "  ls ${SWEEP_DIR}/audit_*_extracted.jsonl | wc -l"
