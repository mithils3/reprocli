#!/usr/bin/env bash
# Rebuttal API-model runs: reproduce the subset papers (rebuttal/subset.json) on OpenAI
# or the Meta Model API through the thin harness. Derived from
# scripts/reproduce/muse_spark/muse_spark_sweep.sh, which is unchanged.
#
#   PROVIDER=openai MODEL=gpt-6.1-sol RANKS=1-12 nohup scripts/rebuttal/api_sweep.sh > core.log 2>&1 &
#   DRY_RUN=1 PROVIDER=openai MODEL=gpt-6.1-sol RANKS=1-24 scripts/rebuttal/api_sweep.sh
#   PROVIDER=openai MODEL=gpt-6.1-sol SMOKE=1 scripts/rebuttal/api_sweep.sh
#
# RANKS=1-12 is core, 13-24 extension; SMOKE=1 runs the dev smoke ids instead. Each
# paper runs on its own split (eval or dev) and takes its budget from its lockfile band.
#
# No in-sweep audit by default (SKIP_AUDIT=1): grading of record is done afterwards by
# Sonnet-5 (reprocli_claude). RESUME skips a paper that already has a report.json under
# this RUN_TAG, so pass the same RUN_TAG to resume.
#
# Spend guard: before each dispatch, the USD in the ledger for this provider plus
# (in-flight + 1) x EST_RUN_USD must stay under CAP_USD, else dispatch stops (spend-cap).
# Each finished run appends one ledger line priced from its stats.json.
set -uo pipefail

PROVIDER="${PROVIDER:?set PROVIDER=openai|meta}"
MODEL="${MODEL:?set MODEL=<model id>}"
RANKS="${RANKS:-}"
SMOKE="${SMOKE:-0}"
DRY_RUN="${DRY_RUN:-0}"
SKIP_AUDIT="${SKIP_AUDIT:-1}"
MAX_PARALLEL="${MAX_PARALLEL:-6}"
ATTEMPTS="${ATTEMPTS:-3}"
RETRY_BACKOFF="${RETRY_BACKOFF:-60}"           # seconds; multiplied by the attempt number
ONLY_IDS="${ONLY_IDS:-}"                       # space-separated ids to run INSTEAD of the selection
RESUME="${RESUME:-1}"
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"     # empty -> per-paper budget from the lockfile band
LOCKFILE="${LOCKFILE:-Mithilss/reclaim}"
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"
AUDIT_MODEL="${AUDIT_MODEL:-${MODEL}}"
SPEND_LEDGER="${SPEND_LEDGER:-/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl}"
ITEM="${ITEM:-rebuttal-${MODEL}}"

# --- Provider ---------------------------------------------------------------
case "${PROVIDER}" in
  openai)
    ENDPOINT="${ENDPOINT:-https://api.openai.com/v1}"
    KEY_VAR=OPENAI_API_KEY
    CONTEXT_LENGTH=256000                      # flex prices hold only up to 272k input
    REASONING="${REASONING_EFFORT:-high}"
    CAP_USD="${CAP_USD:-700}"
    ;;
  meta)
    ENDPOINT="${ENDPOINT:-https://api.meta.ai/v1}"
    KEY_VAR=META_MODEL_KEY
    CONTEXT_LENGTH="${MAX_MODEL_LEN:-1000000}"
    REASONING="${REASONING_EFFORT:-xhigh}"
    CAP_USD="${CAP_USD:-480}"
    ;;
  *) echo "PROVIDER must be openai or meta (got '${PROVIDER}')" >&2; exit 1 ;;
esac

case "${MODEL}" in
  gpt-6.1-terra) EST_DEFAULT=3 ;;
  gpt-6.1-sol)   EST_DEFAULT=6 ;;
  gpt-6-astra)   EST_DEFAULT=31 ;;
  muse-wonder-1.0) EST_DEFAULT=23 ;;
  *)             EST_DEFAULT="" ;;
esac
EST_RUN_USD="${EST_RUN_USD:-${EST_DEFAULT}}"
[[ -n "${EST_RUN_USD}" ]] || { echo "set EST_RUN_USD for model '${MODEL}'" >&2; exit 1; }

# The key is read from the environment only and never printed. The override is explicit
# because DeltaAI login shells export an OpenRouter key under REPROCLI_API_KEY.
if [[ -z "${!KEY_VAR:-}" ]]; then
  echo "${KEY_VAR} is unset -- load it: source <(rg '^export ${KEY_VAR}=' ~/.bashrc)" >&2
  exit 1
fi
if [[ -n "${REPROCLI_API_KEY:-}" ]]; then
  echo "note: overriding an inherited REPROCLI_API_KEY with ${KEY_VAR} for this sweep." >&2
fi
export REPROCLI_API_KEY="${!KEY_VAR}"
unset REPROCLI_OPENROUTER_PROVIDER
export REPROCLI_REASONING_EFFORT="${REASONING}"
export REPROCLI_CONTEXT_LENGTH="${CONTEXT_LENGTH}"
export REPROCLI_NO_TRUNCATE_PROMPT=1
export REPROCLI_SLURM_ACCOUNT=betw-dtai-gh
if [[ "${PROVIDER}" == "openai" ]]; then
  export REPROCLI_SERVICE_TIER=flex
else
  unset REPROCLI_SERVICE_TIER
fi

# --- Paths and batch ids ----------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}" || exit 1
VENV="${VENV:-${ROOT}/.venv}"
# shellcheck disable=SC1091
[[ -f "${VENV}/bin/activate" ]] && source "${VENV}/bin/activate"
export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"

export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/.cache}"
# Plain HTTP for the bundle: the xet path stalled mid-shard (2026-11-06) and 3 smokes waited on its lock.
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
export APPTAINERENV_HF_HOME="${APPTAINERENV_HF_HOME:-/tmp/hf_cache}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT}/agent_runs}"
[[ -z "${HF_TOKEN:-}" ]] && echo "WARNING: HF_TOKEN unset; lockfile/bundle download may fail." >&2

export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"
if [[ -z "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "WARNING: SUPABASE_SERVICE_KEY unset; runs will NOT upload to agent-logs." >&2
fi

RUN_TAG="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
export REPRO_BATCH_ID="rebuttal-${MODEL}-thin-${RUN_TAG}"
export REPRO_BATCH_LABEL="rebuttal ${MODEL} thin ${RUN_TAG}"
SWEEP_DIR="/work/nvme/bfvr/msalunkhe/rebuttal/sweeps/${MODEL}-thin/${RUN_TAG}"
if [[ "${DRY_RUN}" != "1" ]]; then
  mkdir -p "${SWEEP_DIR}" "$(dirname "${SPEND_LEDGER}")" 2>/dev/null || {
    echo "cannot create sweep dir ${SWEEP_DIR}" >&2; exit 1; }
fi
if [[ -n "${ONLY_IDS}" ]]; then
  LOG_SUFFIX=".retry_${RUN_TAG}"
  STATUS_FILE="${SWEEP_DIR}/status.${RUN_TAG}.tsv"
else
  LOG_SUFFIX=""
  STATUS_FILE="${SWEEP_DIR}/status.tsv"
fi

# No wall countdown: nothing kills these jobs, so an invented deadline would only push
# the agent to finalize early.
unset REPRO_WALL_DEADLINE_EPOCH

BUDGET_ARG=()
[[ -n "${BUDGET_H100_HOURS}" ]] && BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")

# --- Step 1: preflight the API ----------------------------------------------
api_status() {
  curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
    -H "Authorization: Bearer ${REPROCLI_API_KEY}" \
    "${ENDPOINT%/v1}/v1/models" 2>/dev/null
}
api_ready() { [[ "$(api_status)" == "200" ]]; }

if [[ "${DRY_RUN}" != "1" ]]; then
  preflight_status="$(api_status)"
  if [[ "${preflight_status}" != "200" ]]; then
    echo "preflight failed: GET ${ENDPOINT%/v1}/v1/models -> http=${preflight_status:-000}" >&2
    case "${preflight_status}" in
      401|403) echo "  key rejected for ${PROVIDER}. Check ${KEY_VAR} in ~/.bashrc." >&2 ;;
      000)     echo "  no HTTP response: DNS, egress, or timeout from this node." >&2 ;;
    esac
    exit 1
  fi
  python3 - "${ENDPOINT}" "${MODEL}" <<'PY' || exit 1
import sys
from reprocli_vllm.vllm.endpoint import fetch_served_models, normalize_server_url
served = fetch_served_models(normalize_server_url(sys.argv[1]))
if served and sys.argv[2] not in served:
    print(f"model id {sys.argv[2]!r} is not advertised by the API.", file=sys.stderr)
    print("advertised ids: " + ", ".join(served), file=sys.stderr)
    raise SystemExit(1)
PY
fi
MAX_MODEL_LEN="${REPROCLI_CONTEXT_LENGTH}"
AUDIT_MAX_INPUT_TOKENS="${AUDIT_MAX_INPUT_TOKENS:-$(( MAX_MODEL_LEN - 32768 ))}"

# --- Step 2: select papers, each with its split and lockfile budget -----------
if [[ "${SMOKE}" == "1" ]]; then
  SEL_MODE=smoke; SEL_SPEC=""
elif [[ -n "${RANKS}" ]]; then
  SEL_MODE=ranks; SEL_SPEC="${RANKS}"
else
  echo "set RANKS=1-12 (core), RANKS=13-24 (extension), or SMOKE=1" >&2; exit 1
fi
if ! PICK_TSV="$(python3 - "${ROOT}/rebuttal/subset.json" "${LOCKFILE}" "${SEL_MODE}" "${SEL_SPEC}" <<'PY'
import json, sys
from reprocli_repro.dataset import band_max_hours, load_lockfile_rows

sub_path, lockfile, mode, spec = sys.argv[1:5]
sub = json.load(open(sub_path))
if mode == "smoke":
    picks = [(r, "dev") for r in sub["smoke_dev"]]
else:
    lo, _, hi = spec.partition("-")
    lo, hi = int(lo), int(hi or lo)
    picks = [(r, "eval") for r in sub["core"] + sub["extension"] if lo <= r["rank"] <= hi]
if not picks:
    sys.exit(f"no papers for {mode} {spec!r}")
rows = {}
for r, split in picks:
    if split not in rows:
        rows[split] = load_lockfile_rows(lockfile, split=split)
    pid = r["paper_id"]
    row = rows[split].get(pid)
    if row is None:
        sys.exit(f"{pid} not in {lockfile} split {split}")
    lock_budget = band_max_hours(row)
    shown = "none" if lock_budget is None else f"{lock_budget:g}"
    match = "match" if lock_budget == float(r["budget_h100"]) else "MISMATCH"
    print("\t".join([pid, split, r["tier"], shown, f"{r['budget_h100']:g}", match]))
PY
)"; then
  echo "paper selection failed" >&2; exit 1
fi
PAPER_IDS=(); declare -A PAPER_SPLIT=() PAPER_TIER=() PAPER_BUDGET=()
while IFS=$'\t' read -r pid split tier budget _subset_budget match; do
  [[ "${match}" == "match" ]] || echo "WARNING: ${pid} lockfile band ${budget} != subset budget ${_subset_budget}" >&2
  PAPER_IDS+=("${pid}"); PAPER_SPLIT["${pid}"]="${split}"
  PAPER_TIER["${pid}"]="${tier}"; PAPER_BUDGET["${pid}"]="${budget}"
done <<< "${PICK_TSV}"

if [[ -n "${ONLY_IDS}" ]]; then
  keep=()
  for pid in "${PAPER_IDS[@]}"; do
    for want in ${ONLY_IDS}; do [[ "${pid}" == "${want}" ]] && keep+=("${pid}"); done
  done
  PAPER_IDS=("${keep[@]}")
fi

# --- Dry run: print the plan and the exact harness command, then stop ---------
repro_argv() {  # pid run_id
  REPRO_ARGV=(python3 -m reprocli_repro
    --paper-id "$1" --split "${PAPER_SPLIT[$1]}" --lockfile "${LOCKFILE}" --run-id "$2"
    ${BUDGET_ARG[@]+"${BUDGET_ARG[@]}"}
    --tool-rounds "${TOOL_ROUNDS}" --vllm-server-url "${ENDPOINT}"
    --served-model-name "${MODEL}" --model "${MODEL}" --runs-dir "${RUNS_DIR}"
    --output "${SWEEP_DIR}/reproduce_$1.jsonl" --save-round-jsonl)
}

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "DRY_RUN provider=${PROVIDER} model=${MODEL} endpoint=${ENDPOINT} window=${CONTEXT_LENGTH} effort=${REASONING}"
  echo "sweep_dir=${SWEEP_DIR}  batch=${REPRO_BATCH_ID}  parallel=${MAX_PARALLEL}  cap_usd=${CAP_USD}  est_run_usd=${EST_RUN_USD}  skip_audit=${SKIP_AUDIT}"
  echo "papers=${#PAPER_IDS[@]}"
  for pid in "${PAPER_IDS[@]}"; do
    echo "--- ${pid}  tier=${PAPER_TIER[$pid]}  split=${PAPER_SPLIT[$pid]}  budget_h100=${PAPER_BUDGET[$pid]}"
    repro_argv "${pid}" "${RUN_TAG}-${pid}-DRYRUN"
    printf '    %q ' "${REPRO_ARGV[@]}"; echo
  done
  exit 0
fi

echo "sweep_dir=${SWEEP_DIR}  batch=${REPRO_BATCH_ID}  provider=${PROVIDER}  model=${MODEL}"
echo "endpoint=${ENDPOINT}  window=${MAX_MODEL_LEN}  effort=${REPROCLI_REASONING_EFFORT}"
echo "rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}  attempts=${ATTEMPTS}  cap_usd=${CAP_USD}  est_run_usd=${EST_RUN_USD}"
echo "papers=${#PAPER_IDS[@]}: ${PAPER_IDS[*]}"

# --- Spend guard ------------------------------------------------------------
spent_usd() {  # sum of ledger usd for this provider, all items
  [[ -f "${SPEND_LEDGER}" ]] || { echo 0; return; }
  python3 - "${SPEND_LEDGER}" "${PROVIDER}" <<'PY'
import json, sys
total = 0.0
for line in open(sys.argv[1]):
    if not line.strip():
        continue
    try:
        row = json.loads(line)
    except ValueError:
        continue
    if row.get("provider") == sys.argv[2]:
        total += float(row.get("usd") or 0)
print(f"{total:.4f}")
PY
}
would_pass() {  # $1 = runs in flight including the one about to start
  awk -v s="$(spent_usd)" -v n="$1" -v e="${EST_RUN_USD}" -v c="${CAP_USD}" \
    'BEGIN { exit !(s + n * e > c) }'
}

# Append one ledger line for a finished run, priced from its stats.json. The
# prompt count includes cached tokens (OpenAI usage convention); completion includes
# reasoning. Flex-fallback calls are billed at standard, which is not counted here, so
# the flex price is a lower bound when fallback_lines > 0.
ledger_line() {  # pid run_id run_dir log
  local fb
  fb="$(rg -c 'flex-fallback' "$4" 2>/dev/null)"
  python3 - "$3/stats.json" "${SPEND_LEDGER}" "${PROVIDER}" "${MODEL}" "$1" "$2" "${fb:-0}" \
            "${ITEM}" "${EST_RUN_USD}" <<'PY'
import json, sys
from datetime import datetime, timezone
stats_path, ledger, provider, model, pid, rid, fb, item, est = sys.argv[1:10]
PRICES = {  # USD per 1M tokens: input, cached input, output
    "gpt-6.1-sol": (1.00, 0.05, 5.00), "gpt-6.1-terra": (0.50, 0.025, 2.50),
    "gpt-6-astra": (5.00, 0.50, 25.00), "muse-wonder-1.0": (4.00, 0.20, 20.00),
    "muse-spark-1.2": (1.25, 0.15, 4.25), "muse-spark-1.2-contributor": (1.25, 0.15, 4.25),
}
rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "item": item,
       "provider": provider, "model": model, "paper": pid, "run_id": rid,
       "flex_fallback_lines": int(fb)}
try:
    tok = json.load(open(stats_path))["tokens"]
    pt, ct, cached = int(tok["prompt"]), int(tok["completion"]), int(tok["cached"])
except (OSError, ValueError, KeyError):
    pt = ct = cached = 0
    rec["estimated"] = True
    usd = float(est)
else:
    price = PRICES.get(model)
    if price is None:
        rec["estimated"] = True
        usd = float(est)
    else:
        pin, pcached, pout = price
        usd = ((pt - cached) * pin + cached * pcached + ct * pout) / 1e6
rec.update({"in": pt, "cached": cached, "out": ct, "usd": round(usd, 4)})
with open(ledger, "a") as f:
    f.write(json.dumps(rec) + "\n")
PY
}

# --- Step 3: reproduce (+ optional audit) every paper ------------------------
record() {
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "${ATTEMPT:-1}" >> "${STATUS_FILE}"
}

# A paper is finished when this RUN_TAG already has a report.json (SKIP_AUDIT=1), or a
# non-empty verdict (audit on). A bundle with no report is a casualty and is re-run.
finished() {
  local pid="$1"
  if [[ "${SKIP_AUDIT}" == "1" ]]; then
    [[ -n "$(find "${RUNS_DIR}/${pid}" -path "*/${RUN_TAG}-${pid}-*/report.json" -print -quit 2>/dev/null)" ]]
  else
    [[ -s "${SWEEP_DIR}/audit_${pid}_extracted.jsonl" ]]
  fi
}

run_one() {
  local pid="$1"
  local split="${PAPER_SPLIT[${pid}]}"
  local log="${SWEEP_DIR}/repro_${pid}${LOG_SUFFIX}.log"
  local verdicts="${SWEEP_DIR}/audit_${pid}_extracted.jsonl"

  if [[ "${RESUME}" == "1" ]] && finished "${pid}"; then
    record "${pid}" "-" "resume-skip" "-" "-"
    echo "=== [$(date '+%F %T')] ${pid} already has a result -> skip"
    return 0
  fi

  if ! api_ready; then
    record "${pid}" "-" "api-down" "-" "-"
    echo "!!! [$(date '+%F %T')] ${pid} NOT dispatched: API unreachable at ${ENDPOINT}"
    return 0
  fi

  local rid="${RUN_TAG}-${pid}-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  echo ">>> [$(date '+%F %T')] start ${pid} split=${split} (run_id=${rid})"

  repro_argv "${pid}" "${rid}"
  "${REPRO_ARGV[@]}" >"${log}" 2>&1
  local rc=$?

  local run_dir
  run_dir="$(find "${RUNS_DIR}/${pid}" -type d -name "${rid}" -print -quit 2>/dev/null || true)"
  if [[ -z "${run_dir}" ]]; then
    record "${pid}" "${rc}" "no-bundle" "-" "${rid}"
    echo "<<< [$(date '+%F %T')] ${pid} repro_rc=${rc} wrote NO bundle (log: ${log})"
    return 0
  fi
  ledger_line "${pid}" "${rid}" "${run_dir}" "${log}"

  if [[ "${SKIP_AUDIT}" == "1" ]]; then
    record "${pid}" "${rc}" "skipped" "-" "${rid}"
    echo "<<< [$(date '+%F %T')] done ${pid} repro_rc=${rc} audit=skipped (bundle: ${run_dir})"
    return 0
  fi

  local grade_root ids_file
  grade_root="$(mktemp -d "${SWEEP_DIR}/grade_${pid}.XXXXXX")"
  ln -s "${run_dir}" "${grade_root}/${pid}"
  ids_file="${grade_root}/ids.txt"
  printf '%s\n' "${pid}" > "${ids_file}"

  local claims_file="eval_100.jsonl"
  [[ "${split}" == "dev" ]] && claims_file="dev_split.jsonl"
  REPROCLI_GRADED_RUN_ID="${rid}" \
  python3 src/run_arxiv_prompt_vllm.py \
    --mode audit \
    --vllm-server-url "${ENDPOINT}" \
    --served-model-name "${AUDIT_MODEL}" \
    --model "${AUDIT_MODEL}" \
    --runs-dir "${grade_root}" \
    --claims "hf://datasets/${LOCKFILE}/${claims_file}" \
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

  local uploaded="off"
  if [[ "${arc}" != "0" ]]; then
    uploaded="audit-fail"
  elif [[ ! -s "${verdicts}" ]]; then
    uploaded="no-verdict"
  elif [[ -n "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
    if python3 -m reprocli_repro.audit_upload \
         --verdicts "${verdicts}" --runs-dir "${RUNS_DIR}" \
         --run-id "${rid}" --audit-model "${AUDIT_MODEL}" >>"${log}" 2>&1; then
      uploaded="ok"
    else
      uploaded="upload-fail"
    fi
  fi

  record "${pid}" "${rc}" "${arc}" "${uploaded}" "${rid}"
  echo "<<< [$(date '+%F %T')] done ${pid} repro_rc=${rc} audit_rc=${arc} upload=${uploaded} (bundle: ${run_dir})"
  return 0
}

SPEND_STOP=0
dispatch_pass() {
  local run_pids=() inflight=0 pid stop=0 spent
  for pid in "$@"; do
    if (( stop == 0 && inflight >= MAX_PARALLEL )); then
      wait -n
      inflight=$((inflight - 1))
    fi
    if (( stop == 0 )) && would_pass $((inflight + 1)); then
      stop=1; SPEND_STOP=1
      spent="$(spent_usd)"
      echo "!!! [$(date '+%F %T')] spend-cap: ${spent} USD spent + $((inflight + 1)) x ${EST_RUN_USD} would pass ${CAP_USD}; no further dispatch"
    fi
    if (( stop )); then
      record "${pid}" "-" "spend-cap" "-" "-"
      continue
    fi
    run_one "${pid}" &
    run_pids+=("$!")
    inflight=$((inflight + 1))
  done
  wait "${run_pids[@]}" 2>/dev/null || true
}

unfinished() {
  local pid
  for pid in "${PAPER_IDS[@]}"; do
    finished "${pid}" || printf '%s\n' "${pid}"
  done
}

: > "${STATUS_FILE}"
mapfile -t todo < <(printf '%s\n' "${PAPER_IDS[@]}")
for (( ATTEMPT=1; ATTEMPT<=ATTEMPTS; ATTEMPT++ )); do
  if (( ATTEMPT > 1 )); then
    backoff=$(( RETRY_BACKOFF * (ATTEMPT - 1) ))
    echo "===== attempt ${ATTEMPT}/${ATTEMPTS}: ${#todo[@]} paper(s) without a result; sleeping ${backoff}s ====="
    printf '           %s\n' "${todo[@]}"
    sleep "${backoff}"
  fi
  export ATTEMPT
  dispatch_pass "${todo[@]}"
  (( SPEND_STOP )) && break
  mapfile -t todo < <(unfinished)
  (( ${#todo[@]} == 0 )) && break
done

# --- Summary ----------------------------------------------------------------
echo "===== rebuttal ${MODEL} thin paired run complete (${REPRO_BATCH_ID}) ====="
FINAL_STATUS="${STATUS_FILE%.tsv}.final.tsv"
awk -F'\t' '{last[$1]=$0} END {for (p in last) print last[p]}' "${STATUS_FILE}" \
  | sort > "${FINAL_STATUS}"
repro_ok=$(awk -F'\t' '$2=="0"' "${FINAL_STATUS}" | wc -l)
total=$(wc -l < "${FINAL_STATUS}")
mapfile -t stranded < <(unfinished)
if (( SPEND_STOP )); then
  echo "SPEND CAP: dispatch stopped; ${#stranded[@]} paper(s) not run. Raise CAP_USD only with the orchestrator's OK."
elif (( ${#stranded[@]} > 0 )); then
  echo "WARNING: ${#stranded[@]} paper(s) have no result after ${ATTEMPTS} attempt(s); re-run with the same RUN_TAG to re-pick them:"
  printf '           %s\n' "${stranded[@]}"
fi
echo "reproduced ok: ${repro_ok}/${total}   grading: $([[ "${SKIP_AUDIT}" == "1" ]] && echo 'skipped (SKIP_AUDIT=1)' || echo 'audit on')"
cat "${FINAL_STATUS}"
echo "run bundles : ${RUNS_DIR}/<arxiv_id>/<budget>h/<run_id>/"
echo "sweep dir   : ${SWEEP_DIR}"
