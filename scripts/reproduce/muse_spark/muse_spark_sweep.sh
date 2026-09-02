#!/usr/bin/env bash
# Run one tier of the frozen benchmark against Muse Spark 1.2 (contributor tier) on
# the Meta Model API, using the same paired S6->S7 flow as the GH200 sweeps:
# reproduce with a pinned run id, audit exactly that bundle, PATCH the verdict onto
# the same repro_runs row.
#
# Driver for the three tier entrypoints; do not call it directly:
#   scripts/reproduce/muse_spark/{easy,medium,hard}_muse_spark.sh
#
# Why this is a .sh and not an .sbatch, unlike its dsv4_flash/glm52 siblings:
# those scripts are sbatch because they SERVE the brain themselves on GH200 and the
# sweep has to live inside that allocation. Muse Spark is closed-weight and API-only,
# so there is no brain to serve and the orchestrator needs no GPU. Each paper still
# gets its own JIT GPU step from reprocli_repro, so run this from a login node:
#
#   nohup scripts/reproduce/muse_spark/easy_muse_spark.sh > easy_muse.log 2>&1 &
#
# The brain is a URL, so everything below is the sweep half of easy_dsv4_flash.sbatch
# with the serve half deleted: no vLLM flags, no parsers, no NCCL/CUDA env, no
# chat_template_kwargs (that knob is DeepSeek Think Max, meaningless here).
set -uo pipefail

TIER="${TIER:?set TIER=Easy|Medium|Hard (use the easy_/medium_/hard_ entrypoint)}"

# --- Config (override from the environment) ---------------------------------
ENDPOINT="${ENDPOINT:-https://api.meta.ai/v1}"
MODEL="${MODEL:-muse-spark-1.2-contributor}"   # rate-limited contributor tier
AUDIT_MODEL="${AUDIT_MODEL:-${MODEL}}"         # grader; set another id to keep it independent
SPLIT="${SPLIT:-eval}"                         # eval -> HF 'test' (frozen 100-paper benchmark)
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"     # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"
# The ceiling here is the contributor tier's request rate, not GPU nodes. Drop it if
# the per-paper logs fill with 429s that ATTEMPTS cannot absorb.
MAX_PARALLEL="${MAX_PARALLEL:-8}"
# Retry passes over the papers that finished WITHOUT a verdict. A genuine agent
# failure still writes a bundle and gets graded, so a missing verdict always means a
# harness/API casualty (no-bundle, api-down, audit-fail) -- the one thing worth
# re-spending. Benchmark results are never re-rolled.
ATTEMPTS="${ATTEMPTS:-3}"
RETRY_BACKOFF="${RETRY_BACKOFF:-60}"           # seconds; multiplied by the attempt number
ONLY_IDS="${ONLY_IDS:-}"                       # space-separated ids to run INSTEAD of the tier
RESUME="${RESUME:-1}"                          # 1 -> skip papers that already have a verdict

# The Meta Model API takes the key as a bearer token; the harness reads
# $REPROCLI_API_KEY (endpoint.py) and sends it on both loops.
#
# META_MODEL_KEY WINS over an inherited REPROCLI_API_KEY. The login shell that runs
# the OpenRouter/vLLM sweeps already exports REPROCLI_API_KEY, and deferring to it
# here sends an OpenRouter key to api.meta.ai, which 401s and surfaces as an
# unreachable endpoint. This sweep only ever talks to Meta, so the Meta key is the
# only correct value.
if [[ -z "${META_MODEL_KEY:-}" ]]; then
  echo "META_MODEL_KEY is unset -- generate a key at dev.meta.ai and export it" >&2
  echo "  (it lives in ~/.bashrc: source <(grep META_MODEL_KEY ~/.bashrc))" >&2
  exit 1
fi
if [[ -n "${REPROCLI_API_KEY:-}" && "${REPROCLI_API_KEY}" != "${META_MODEL_KEY}" ]]; then
  echo "note: overriding an inherited REPROCLI_API_KEY with META_MODEL_KEY for this sweep." >&2
fi
export REPROCLI_API_KEY="${META_MODEL_KEY}"
# OpenRouter-only knob; a stray value in the login env would put a 'provider' block
# on every request to Meta, which does not understand it.
unset REPROCLI_OPENROUTER_PROVIDER

# Reasoning depth. Chat Completions takes this top-level as reasoning_effort (the
# Responses API nests it as reasoning.effort, which this harness never posts).
# Muse Spark documents xhigh as maximum depth; it defaults to high server-side.
export REPROCLI_REASONING_EFFORT="${REASONING_EFFORT:-xhigh}"
# Muse Spark's model cards carry no context_length, so the window cannot be read
# off /v1/models the way a vLLM or OpenRouter card allows. State it explicitly for
# both loops; reprocli_repro resolves its input ceiling through the same env var.
export REPROCLI_CONTEXT_LENGTH="${MAX_MODEL_LEN:-1000000}"
# truncate_prompt_tokens is a vLLM extension that io.py puts on every body. Meta
# validates strictly and 400s on the unknown parameter at round 0 of BOTH loops,
# which reads as repro_rc=0 (the repro loop finalizes a failed call as an error
# terminal) plus audit_rc=1. Preflight cannot catch it: that probe only GETs
# /v1/models. Dropping it also drops server-side prompt clipping, so the window
# stated above and the harness's own compaction are the only ceiling left.
export REPROCLI_NO_TRUNCATE_PROMPT=1

# Repo root, so src/ and outputs/ resolve wherever this is launched from.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT}"
VENV="${VENV:-${ROOT}/.venv}"
# shellcheck disable=SC1091
[[ -f "${VENV}/bin/activate" ]] && source "${VENV}/bin/activate"
export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"

# Audit against the same canonical lockfile claim the agent targeted.
case "${SPLIT}" in
  dev|validation) CLAIMS_FILE="dev_split.jsonl" ;;
  *)              CLAIMS_FILE="eval_100.jsonl" ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/${LOCKFILE}/${CLAIMS_FILE}}"

# Keep the agent's heavy I/O (bundles, per-paper uv venvs) off $HOME; the agent still
# runs inside the Apptainer sandbox on a JIT GPU node, so its in-container HF pulls
# go to node-local /tmp exactly as in the GH200 sweeps.
export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
export APPTAINERENV_HF_HOME="${APPTAINERENV_HF_HOME:-/tmp/hf_cache}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT}/agent_runs}"
[[ -z "${HF_TOKEN:-}" ]] && echo "WARNING: HF_TOKEN unset; lockfile/bundle download may fail." >&2

export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"
if [[ -z "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "WARNING: SUPABASE_SERVICE_KEY unset; runs + verdicts will NOT upload to agent-logs." >&2
fi

RUN_TAG="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
export REPRO_BATCH_ID="${REPRO_BATCH_ID:-muse_spark-${RUN_TAG}}"
export REPRO_BATCH_LABEL="${REPRO_BATCH_LABEL:-muse_spark ${TIER} ${RUN_TAG}}"
TIER_LC="$(printf '%s' "${TIER}" | tr '[:upper:]' '[:lower:]')"
SWEEP_DIR="${SWEEP_DIR:-${REPRO_WORK_ROOT}/muse_spark_sweeps/${TIER_LC}/${RUN_TAG}}"
# Fatal: every per-paper log, verdict, and the status file lands here. The default
# lives under $REPRO_WORK_ROOT (the DeltaAI NVMe scratch), so this is what fires when
# the sweep is launched somewhere that scratch does not exist.
if ! mkdir -p "${SWEEP_DIR}" 2>/dev/null; then
  echo "cannot create sweep dir ${SWEEP_DIR}" >&2
  echo "  set REPRO_WORK_ROOT (or SWEEP_DIR) to a writable path." >&2
  exit 1
fi
if [[ -n "${ONLY_IDS}" ]]; then
  LOG_SUFFIX=".retry_${RUN_TAG}"
  STATUS_FILE="${SWEEP_DIR}/status.${RUN_TAG}.tsv"
else
  LOG_SUFFIX=""
  STATUS_FILE="${SWEEP_DIR}/status.tsv"
fi

# No wall countdown. The sbatch sweeps set REPRO_WALL_DEADLINE_EPOCH because SLURM
# really does kill the job hosting them; nothing kills this one, so an invented
# deadline would only push the agent to finalize early against a wall that does not
# exist. transcript.py omits the countdown when the var is unset, and it is cleared
# here in case the launching shell carried one in.
unset REPRO_WALL_DEADLINE_EPOCH

BUDGET_ARG=()
[[ -n "${BUDGET_H100_HOURS}" ]] && BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")

# --- Step 1: preflight the API ----------------------------------------------
# Report the status code. A bare `curl -f` collapses "key rejected" and "no route to
# the host" into one indistinguishable failure, which is exactly the confusion this
# preflight exists to prevent.
api_status() {
  curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
    -H "Authorization: Bearer ${REPROCLI_API_KEY}" \
    "${ENDPOINT%/v1}/v1/models" 2>/dev/null
}
api_ready() { [[ "$(api_status)" == "200" ]]; }

preflight_status="$(api_status)"
if [[ "${preflight_status}" != "200" ]]; then
  echo "preflight failed: GET ${ENDPOINT%/v1}/v1/models -> http=${preflight_status:-000}" >&2
  case "${preflight_status}" in
    401|403) echo "  key rejected. Regenerate at dev.meta.ai, and check nothing else in" >&2
             echo "  the login env is shadowing it (this sweep forces META_MODEL_KEY)." >&2 ;;
    000)     echo "  no HTTP response: DNS, egress, or timeout from this node." >&2 ;;
    *)       echo "  body: curl -sS -H \"Authorization: Bearer \$META_MODEL_KEY\" ${ENDPOINT%/v1}/v1/models" >&2 ;;
  esac
  exit 1
fi
# "Muse Spark 1.2 Contributor" is the console's display name; the request wants its
# model id. Confirm the id against what the API advertises rather than assuming the
# slug, and print the real list when it does not match.
if [[ "${CHECK_MODEL_ID:-1}" == "1" ]]; then
  python3 - "${ENDPOINT}" "${MODEL}" <<'PY' || exit 1
import sys
from reprocli_vllm.vllm.endpoint import fetch_served_models, normalize_server_url
served = fetch_served_models(normalize_server_url(sys.argv[1]))
if served and sys.argv[2] not in served:
    print(f"model id {sys.argv[2]!r} is not advertised by the API.", file=sys.stderr)
    print("advertised ids: " + ", ".join(served), file=sys.stderr)
    print("re-run with MODEL=<id> (or CHECK_MODEL_ID=0 to skip).", file=sys.stderr)
    raise SystemExit(1)
PY
fi
# Stated, never probed: Meta's model cards carry no window field, so
# fetch_served_context_length would raise for every run. REPROCLI_CONTEXT_LENGTH
# (exported above) is what both loops resolve their ceiling through.
MAX_MODEL_LEN="${REPROCLI_CONTEXT_LENGTH}"
# The auditor reserves 32768 tokens for its verdict, so its input ceiling is the rest.
AUDIT_MAX_INPUT_TOKENS="${AUDIT_MAX_INPUT_TOKENS:-$(( MAX_MODEL_LEN - 32768 ))}"

echo "sweep_dir=${SWEEP_DIR}  split=${SPLIT}  tier=${TIER}  model=${MODEL}"
echo "endpoint=${ENDPOINT}  window=${MAX_MODEL_LEN}  effort=${REPROCLI_REASONING_EFFORT}"
echo "rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}  attempts=${ATTEMPTS}"

# --- Step 2: enumerate the tier ---------------------------------------------
mapfile -t PAPER_IDS < <(
  python3 - "${LOCKFILE}" "${SPLIT}" "${TIER}" <<'PY'
import sys
from reprocli_repro.inputs import (
    DEFAULT_UNBANDED_BUDGET_H100_HOURS,
    band_max_hours,
    load_lockfile_rows,
)
rows = load_lockfile_rows(sys.argv[1], split=sys.argv[2])
want = sys.argv[3]
tier = [(pid, row) for pid, row in rows.items() if (row.get("tier") or "") == want]
# Smallest compute ceiling first, so cheap papers land results early.
tier.sort(key=lambda pr: band_max_hours(pr[1]) or DEFAULT_UNBANDED_BUDGET_H100_HOURS)
for pid, _ in tier:
    print(pid)
PY
)
if [[ "${#PAPER_IDS[@]}" -eq 0 ]]; then
  echo "no ${TIER}-tier papers in ${LOCKFILE} split=${SPLIT}" >&2; exit 1
fi

# Narrow to a retry list, keeping tier order; an id outside the tier is an error.
if [[ -n "${ONLY_IDS}" ]]; then
  declare -A in_tier=()
  for pid in "${PAPER_IDS[@]}"; do in_tier["${pid}"]=1; done
  keep=()
  for pid in ${ONLY_IDS}; do
    [[ -n "${in_tier[${pid}]:-}" ]] || {
      echo "ONLY_IDS: '${pid}' is not a ${TIER} paper in split '${SPLIT}'" >&2; exit 1; }
  done
  for pid in "${PAPER_IDS[@]}"; do
    for want in ${ONLY_IDS}; do
      [[ "${pid}" == "${want}" ]] && keep+=("${pid}")
    done
  done
  PAPER_IDS=("${keep[@]}")
fi
echo "split '${SPLIT}' tier '${TIER}' has ${#PAPER_IDS[@]} papers: ${PAPER_IDS[*]}"

# --- Step 3: reproduce + audit every paper, PAIRED on one bundle -------------
# One status row per paper per attempt: pid, repro rc, audit rc, upload, run id, attempt.
record() {
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "${ATTEMPT:-1}" >> "${STATUS_FILE}"
}

run_one() {
  local pid="$1"
  local log="${SWEEP_DIR}/repro_${pid}${LOG_SUFFIX}.log"
  local verdicts="${SWEEP_DIR}/audit_${pid}_extracted.jsonl"

  if [[ "${RESUME}" == "1" && -s "${verdicts}" ]]; then
    record "${pid}" "-" "resume-skip" "-" "-"
    echo "=== [$(date '+%F %T')] ${pid} already graded -> skip (${verdicts})"
    return 0
  fi

  # A paper dispatched against a dead endpoint dies in seconds and would be filed as a
  # model failure, so probe the exact call the worker makes before spending it.
  if ! api_ready; then
    record "${pid}" "-" "api-down" "-" "-"
    echo "!!! [$(date '+%F %T')] ${pid} NOT dispatched: API unreachable at ${ENDPOINT}"
    return 0
  fi

  local rid="${RUN_TAG}-${pid}-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  echo ">>> [$(date '+%F %T')] start ${pid} (run_id=${rid})"

  # (1) Reproduce. Sampling stays unset so the agent defers to Muse Spark's own
  # generation defaults; there is no chat-template knob to pin on this model.
  python3 -m reprocli_repro \
    --paper-id "${pid}" \
    --split "${SPLIT}" \
    --lockfile "${LOCKFILE}" \
    --run-id "${rid}" \
    "${BUDGET_ARG[@]}" \
    --tool-rounds "${TOOL_ROUNDS}" \
    --vllm-server-url "${ENDPOINT}" \
    --served-model-name "${MODEL}" \
    --model "${MODEL}" \
    --runs-dir "${RUNS_DIR}" \
    --output "${SWEEP_DIR}/reproduce_${pid}.jsonl" \
    --save-round-jsonl \
    >"${log}" 2>&1
  local rc=$?

  # (2) Locate this run's bundle, unique by run id across budget dirs.
  local run_dir
  run_dir="$(find "${RUNS_DIR}/${pid}" -type d -name "${rid}" -print -quit 2>/dev/null || true)"
  if [[ -z "${run_dir}" ]]; then
    record "${pid}" "${rc}" "no-bundle" "-" "${rid}"
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
    --max-tokens 32768 \
    --max-model-len "${MAX_MODEL_LEN}" \
    --output "${SWEEP_DIR}/audit_${pid}.jsonl" \
    --extracted-output "${verdicts}" \
    --trace-output "${SWEEP_DIR}/audit_${pid}_trace.jsonl" \
    --save-round-jsonl \
    >>"${log}" 2>&1
  local arc=$?
  rm -rf "${grade_root}"

  # (5) Upload only successful, nonempty verdicts to the pinned run_id.
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

  record "${pid}" "${rc}" "${arc}" "${uploaded}" "${rid}"
  echo "<<< [$(date '+%F %T')] done ${pid} repro_rc=${rc} audit_rc=${arc} upload=${uploaded} (bundle: ${run_dir})"
  return 0
}

dispatch_pass() {
  local run_pids=() inflight=0 pid
  for pid in "$@"; do
    run_one "${pid}" &
    run_pids+=("$!")
    inflight=$((inflight + 1))
    if (( inflight >= MAX_PARALLEL )); then
      wait -n
      inflight=$((inflight - 1))
    fi
  done
  wait "${run_pids[@]}" 2>/dev/null || true
}

# Papers still missing a verdict, in tier order. This is both the retry list and the
# final "did not finish" list, so the two can never disagree.
unfinished() {
  local pid
  for pid in "${PAPER_IDS[@]}"; do
    [[ -s "${SWEEP_DIR}/audit_${pid}_extracted.jsonl" ]] || printf '%s\n' "${pid}"
  done
}

: > "${STATUS_FILE}"
mapfile -t todo < <(printf '%s\n' "${PAPER_IDS[@]}")
for (( ATTEMPT=1; ATTEMPT<=ATTEMPTS; ATTEMPT++ )); do
  if (( ATTEMPT > 1 )); then
    backoff=$(( RETRY_BACKOFF * (ATTEMPT - 1) ))
    echo "===== attempt ${ATTEMPT}/${ATTEMPTS}: ${#todo[@]} paper(s) without a verdict;"\
         "sleeping ${backoff}s ====="
    printf '           %s\n' "${todo[@]}"
    sleep "${backoff}"
  fi
  export ATTEMPT
  dispatch_pass "${todo[@]}"
  mapfile -t todo < <(unfinished)
  (( ${#todo[@]} == 0 )) && break
done

# --- Summary ----------------------------------------------------------------
echo "===== ${TIER} paired reproduce+audit complete (${REPRO_BATCH_ID}) ====="
# Count each paper once, by its LAST attempt, so retries never inflate the totals.
FINAL_STATUS="${STATUS_FILE%.tsv}.final.tsv"
awk -F'\t' '{last[$1]=$0} END {for (p in last) print last[p]}' "${STATUS_FILE}" \
  | sort > "${FINAL_STATUS}"
repro_ok=$(awk -F'\t' '$2=="0"' "${FINAL_STATUS}" | wc -l)
audit_ok=$(awk -F'\t' '$3=="0"' "${FINAL_STATUS}" | wc -l)
upload_ok=$(awk -F'\t' '$4=="ok"' "${FINAL_STATUS}" | wc -l)
total=$(wc -l < "${FINAL_STATUS}")
mapfile -t stranded < <(unfinished)
if (( ${#stranded[@]} > 0 )); then
  echo "WARNING: ${#stranded[@]} paper(s) still have NO verdict after ${ATTEMPTS} attempt(s)"
  echo "         -- harness casualties, not model failures. Re-run the script to"
  echo "         re-pick them (RESUME=1 skips everything already graded):"
  awk -F'\t' -v ids="${stranded[*]}" '
    BEGIN { n = split(ids, want, " "); for (i = 1; i <= n; i++) miss[want[i]] = 1 }
    $1 in miss { print "           " $1 "  (" $3 ", attempt " $6 ")" }' "${FINAL_STATUS}"
fi
echo "reproduced ok: ${repro_ok}/${total}   audited ok: ${audit_ok}/${total}   uploaded ok: ${upload_ok}/${total}"
cat "${FINAL_STATUS}"
echo "run bundles : ${RUNS_DIR}/<arxiv_id>/<budget>h/<run_id>/"
echo "sweep dir   : ${SWEEP_DIR}"
