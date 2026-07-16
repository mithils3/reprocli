#!/bin/bash
# Login-node / laptop driver: reproduce EVERY Easy-tier paper through the
# OpenRouter model nvidia/nemotron-3-ultra-550b-a55b:free, then grade THAT EXACT
# bundle with the S7 auditor and (optionally) upload the verdict. Paired
# reproduce+audit per paper, MAX_PARALLEL=5, mirroring the run_one loop in
# ../qwen3_27b/easy_qwen3_27b.sbatch — but the brain is a remote OpenRouter API,
# so there is NO GPU, no vLLM serve step, and no SLURM allocation. It is a plain
# background process you can nohup on a login node (or anywhere with outbound HTTPS).
#
#   cd /u/msalunkhe/reprocli   # or your repo checkout
#   export OPENROUTER_API_KEY=sk-or-...        # REQUIRED (see below)
#   nohup bash scripts/reproduce/nemotron_3_ultra/run_easy_nemotron.sh \
#         > easy_nemotron_sweep.out 2>&1 &
#   # or inside tmux/screen
#
# The paired flow per paper (same as repro_audit_one.sh, fanned out over the tier):
#   1. reprocli_repro (--run-id RID)  -> <runs-dir>/<id>/<budget>h/RID/ bundle
#   2. run_arxiv... --mode audit      -> grades ONLY that bundle -> verdicts.jsonl
#   3. reprocli_repro.audit_upload    -> PATCHes audit_* onto RID's repro_runs row
#
# RATE LIMITS / FREE TIER — READ THIS. nvidia/...:free is a free OpenRouter
# variant. Free models are throttled hard (order of ~20 req/min) AND capped per
# day (50/day with no credits, ~1000/day once your account holds >= $10). A full
# Easy sweep is dozens of papers x hundreds of agent turns, so the day cap WILL
# bite before rate limiting does — this driver cannot conjure quota it doesn't
# have. What it DOES do: every brain call already goes through
# reprocli_vllm.vllm.retry.with_retries, which retries 429/5xx with exponential
# backoff and honors the server's Retry-After header. We raise the attempt budget
# (REPROCLI_HTTP_MAX_ATTEMPTS, default 30 here vs the stock 8) so a run rides out
# a sustained throttle instead of dying on the first wall. If you hit the *daily*
# cap, the run will still eventually error out per paper — resume it the next day
# (RESUME=1 skips papers that already wrote a verdict). Lower MAX_PARALLEL to be
# gentler on the per-minute limit; pin a paid provider with the paid slug (drop
# the :free suffix) if you have credits and want it to actually finish.
#
# Env knobs (all optional; defaults in []):
#   MODEL/SERVED_NAME [nvidia/nemotron-3-ultra-550b-a55b:free]  brain + grader slug
#   AUDIT_MODEL [=SERVED_NAME]      grader; set a different slug to keep it independent
#   ENDPOINT [https://openrouter.ai/api/v1]                     OpenRouter base URL
#   SPLIT [eval]  TIER [Easy]  LOCKFILE [Mithilss/reprobench-splits]
#   BUDGET_H100_HOURS []            empty = per-paper ceiling from the selection band
#   TOOL_ROUNDS [300]  AUDIT_TOOL_ROUNDS [40]  MAX_PARALLEL [5]  RESUME [1]
#   REPROCLI_HTTP_MAX_ATTEMPTS [30] retry budget per brain call (429/5xx backoff)
#   REPROCLI_OPENROUTER_PROVIDER [] optional provider slug(s) to pin routing
#   REPROCLI/VENV                   repo root + venv to activate

set -euo pipefail

# --- Config (override from the environment) ---------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-nvidia/nemotron-3-ultra-550b-a55b:free}"
SERVED_NAME="${SERVED_NAME:-${MODEL}}"
AUDIT_MODEL="${AUDIT_MODEL:-${SERVED_NAME}}"   # grader; the same OpenRouter brain by default
ENDPOINT="${ENDPOINT:-https://openrouter.ai/api/v1}"
SPLIT="${SPLIT:-eval}"                    # eval -> HF 'test' (the frozen 100-paper benchmark)
TIER="${TIER:-Easy}"                      # only reproduce+grade rows of this tier
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"        # reproduction agent tool rounds
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"  # auditor's run-dir exploration rounds
MAX_PARALLEL="${MAX_PARALLEL:-5}"        # papers in flight at once (num parallel = 5)
RESUME="${RESUME:-1}"                    # 1 -> skip papers that already have a verdict on disk
# Auditor context caps (override if the model advertises a smaller window).
AUDIT_MAX_INPUT_TOKENS="${AUDIT_MAX_INPUT_TOKENS:-128000}"
AUDIT_MAX_TOKENS="${AUDIT_MAX_TOKENS:-32768}"
AUDIT_MAX_MODEL_LEN="${AUDIT_MAX_MODEL_LEN:-262144}"

# Ride out free-tier throttling: bump the per-call retry budget well above the
# stock 8 so 429s back off and retry (Retry-After honored) instead of aborting.
export REPROCLI_HTTP_MAX_ATTEMPTS="${REPROCLI_HTTP_MAX_ATTEMPTS:-30}"
# Point the reproduce + audit clients at OpenRouter. The auditor is passed
# --vllm-server-url explicitly; the reproduce agent auto-discovers this env var.
export REPROCLI_SERVER_URL="${ENDPOINT}"

# Audit against the same canonical lockfile claim the agent targeted.
case "${SPLIT}" in
  dev|validation) CLAIMS_FILE="dev_split.jsonl" ;;
  *)              CLAIMS_FILE="eval_100.jsonl" ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/${LOCKFILE}/${CLAIMS_FILE}}"

# --- Auth: OpenRouter bearer token is REQUIRED ------------------------------
# resolve_api_key() reads REPROCLI_API_KEY, then OPENROUTER_API_KEY. Fail loudly
# now rather than as a 401 on the first brain call, dozens of papers deep.
if [[ -z "${OPENROUTER_API_KEY:-}${REPROCLI_API_KEY:-}" ]]; then
  echo "ERROR: no OpenRouter key in the environment. Export OPENROUTER_API_KEY" >&2
  echo "       (or REPROCLI_API_KEY) before launching this sweep." >&2
  exit 1
fi

# Keep the agent's heavy I/O (bundles, per-paper uv venvs) off $HOME.
export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT}/agent_runs}"
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARNING: HF_TOKEN is unset; the lockfile/claims download from the Hub may fail." >&2
fi

# Agent-logs upload is opt-in: reproduce upserts repro_runs, then audit_upload
# PATCHes audit_* onto the pinned run_id.
export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"
if [[ -z "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "WARNING: SUPABASE_SERVICE_KEY is unset; runs + audit verdicts will NOT upload to agent-logs." >&2
fi

# Sweep-wall countdown surfaced to the agent every tool round (transcript.py
# reads this): only meaningful if this driver happens to be launched inside a
# SLURM allocation. Normally it is a plain login-node nohup'd process with no
# SLURM_JOB_ID and no #SBATCH --time cap to fall back to, so it stays unset and
# the countdown line is simply omitted (the daily/rate-limit caps above are the
# real ceiling here, not a SLURM wall).
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  if end_ts="$(squeue -h -j "${SLURM_JOB_ID}" -o '%e' 2>/dev/null)" \
     && [[ -n "${end_ts}" ]] \
     && REPRO_WALL_DEADLINE_EPOCH="$(date -d "${end_ts}" +%s 2>/dev/null)"; then
    export REPRO_WALL_DEADLINE_EPOCH
  fi
fi

# --- Activate the repo venv --------------------------------------------------
if command -v module >/dev/null 2>&1; then
  module load python/3.11.9 || true
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

STAMP="$(date '+%Y%m%d_%H%M%S')"
SWEEP_DIR="${REPRO_WORK_ROOT}/easy_sweeps/nemotron_${STAMP}"
mkdir -p "${SWEEP_DIR}"
# One batch id groups this sweep's runs in the run viewer (no SLURM job id here).
export REPRO_BATCH_ID="${REPRO_BATCH_ID:-nemotron-${STAMP}}"
export REPRO_BATCH_LABEL="${REPRO_BATCH_LABEL:-easy nemotron-3-ultra ${STAMP}}"
IDS_FILE="${SWEEP_DIR}/easy_ids.txt"
STATUS_FILE="${SWEEP_DIR}/status.tsv"

if [[ -n "${BUDGET_H100_HOURS}" ]]; then
  BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")
  BUDGET_LABEL="${BUDGET_H100_HOURS}h (flat)"
else
  BUDGET_ARG=()
  BUDGET_LABEL="per-band"
fi
echo "sweep_dir=${SWEEP_DIR}  endpoint=${ENDPOINT}  model=${SERVED_NAME}"
echo "split=${SPLIT}  tier=${TIER}  budget=${BUDGET_LABEL}  rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}"
echo "runs_dir=${RUNS_DIR}  resume=${RESUME}  audit_model=${AUDIT_MODEL}  audit_rounds=${AUDIT_TOOL_ROUNDS}"
echo "retry_attempts=${REPROCLI_HTTP_MAX_ATTEMPTS}  provider=${REPROCLI_OPENROUTER_PROVIDER:-<default routing>}"
echo "claims=${CLAIMS}"

# --- Enumerate the Easy tier of the split, smallest budget first ------------
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
# Smallest compute ceiling first: cheap papers land results early.
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

# --- Reproduce + audit one paper, PAIRED on one bundle ----------------------
run_one() {
  local pid="$1"
  local log="${SWEEP_DIR}/repro_${pid}.log"
  local verdicts="${SWEEP_DIR}/audit_${pid}_extracted.jsonl"

  # Resume only unfinished papers (e.g. after a daily-cap abort).
  if [[ "${RESUME}" == "1" && -s "${verdicts}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "-" "resume-skip" "-" "-" >> "${STATUS_FILE}"
    echo "=== [$(date '+%F %T')] ${pid} already graded -> skip (${verdicts})"
    return 0
  fi

  local rid="${STAMP}-${pid}-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  echo ">>> [$(date '+%F %T')] start ${pid} (run_id=${rid})"

  # (1) Reproduce this paper against the OpenRouter brain.
  python -m reprocli_repro \
    --paper-id "${pid}" \
    --split "${SPLIT}" \
    --lockfile "${LOCKFILE}" \
    --run-id "${rid}" \
    --vllm-server-url "${ENDPOINT}" \
    --served-model-name "${SERVED_NAME}" \
    "${BUDGET_ARG[@]}" \
    --tool-rounds "${TOOL_ROUNDS}" \
    --output "${SWEEP_DIR}/reproduce_${pid}.jsonl" \
    --save-round-jsonl \
    >"${log}" 2>&1
  local rc=$?

  # (2) Locate this run's bundle, unique by run id across budget dirs.
  local run_dir
  run_dir="$(find "${RUNS_DIR}/${pid}" -type d -name "${rid}" -print -quit 2>/dev/null || true)"
  if [[ -z "${run_dir}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${rc}" "no-bundle" "-" "${rid}" >> "${STATUS_FILE}"
    echo "<<< [$(date '+%F %T')] ${pid} repro_rc=${rc} wrote NO bundle -> skip audit (log: ${log})"
    return 0
  fi

  # (3) Make the auditor's <runs-dir>/<pid> contract resolve to this bundle only.
  local grade_root ids_file
  grade_root="$(mktemp -d "${SWEEP_DIR}/grade_${pid}.XXXXXX")"
  ln -s "${run_dir}" "${grade_root}/${pid}"
  ids_file="${grade_root}/ids.txt"
  printf '%s\n' "${pid}" > "${ids_file}"

  # (4) Audit exactly this bundle and link the live audit to the graded run.
  REPROCLI_GRADED_RUN_ID="${rid}" \
  python3 src/run_arxiv_prompt_vllm.py \
    --mode audit \
    --vllm-server-url "${ENDPOINT}" \
    --served-model-name "${AUDIT_MODEL}" \
    --model "${AUDIT_MODEL}" \
    --runs-dir "${grade_root}" \
    --claims "${CLAIMS}" \
    --paper-ids-file "${ids_file}" \
    --tool-rounds "${AUDIT_TOOL_ROUNDS}" \
    --max-input-tokens "${AUDIT_MAX_INPUT_TOKENS}" \
    --max-tokens "${AUDIT_MAX_TOKENS}" \
    --max-model-len "${AUDIT_MAX_MODEL_LEN}" \
    --output "${SWEEP_DIR}/audit_${pid}.jsonl" \
    --extracted-output "${verdicts}" \
    --trace-output "${SWEEP_DIR}/audit_${pid}_trace.jsonl" \
    --save-round-jsonl \
    >>"${log}" 2>&1
  local arc=$?
  rm -rf "${grade_root}"

  # (5) Upload only successful, nonempty audit verdicts to the pinned run_id.
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
    wait -n
    inflight=$((inflight - 1))
  fi
done
wait "${run_pids[@]}" 2>/dev/null || true
set -e

# --- Summary ----------------------------------------------------------------
echo "===== ${TIER} paired reproduce+audit complete (nemotron ${STAMP}) ====="
repro_ok=$(awk -F'\t' '$2=="0"' "${STATUS_FILE}" | wc -l)
audit_ok=$(awk -F'\t' '$3=="0"' "${STATUS_FILE}" | wc -l)
upload_ok=$(awk -F'\t' '$4=="ok"' "${STATUS_FILE}" | wc -l)
total=$(wc -l < "${STATUS_FILE}")
echo "reproduced ok: ${repro_ok}/${total}   audited ok: ${audit_ok}/${total}   uploaded ok: ${upload_ok}/${total}"
sort "${STATUS_FILE}"
echo "run bundles : ${RUNS_DIR}/<arxiv_id>/<budget>h/<run_id>/"
echo "reproduce   : ${SWEEP_DIR}/reproduce_<arxiv_id>.jsonl  (status: ${STATUS_FILE})"
echo "grades      : ${SWEEP_DIR}/audit_<arxiv_id>_extracted.jsonl  (score/verdict/reproduced per paper)"
echo "audit trace : ${SWEEP_DIR}/audit_<arxiv_id>_trace.jsonl"
