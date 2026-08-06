#!/bin/bash
# Serve DeepSeek-V4-Flash-0731 on 2xGH200 (one ghx4 node's two-GPU share, TP=2), then
# run every tier-Medium paper through the paired S6->S7 flow from
# scripts/reproduce/repro_audit_one.sh: reproduce with a pinned run id, audit
# exactly that bundle, and optionally upload the verdict.
#
#   sbatch scripts/reproduce/dsv4_flash/medium_dsv4_flash.sbatch
#
# Medium-tier sibling of easy_dsv4_flash.sbatch (see that header for the full serve
# rationale: DeepSeek-V4-Flash-0731 on 2xGH200 at TP=2, ~155 GiB of weights, the
# REQUIRED kv_cache_dtype fp8 + DeepGEMM LD_LIBRARY_PATH +
# VLLM_USE_FLASHINFER_SAMPLER=0, Think Max pinned via REPROCLI_CHAT_TEMPLATE_KWARGS,
# and top_p 0.95 on both loops because both are agentic). If vLLM refuses to start
# for want of KV blocks, rerun on the whole node:
# sbatch --gpus-per-node=4 --export=ALL,TP=4 <this file>.
#
# Defaults to the eval split's 32 Medium papers, MAX_PARALLEL=10, and RESUME=1 so
# re-submits after the 48h cap skip papers that already wrote a verdict. The
# deepseek_v4 profile pins no max_num_seqs (vLLM's 256 default) and V4's MLA keeps
# per-sequence KV small even at max_model_len 409600, so 10 papers plus one audit
# stream sit far inside the brain; what binds at this width is ghx4 queue pressure
# from 10 concurrent JIT allocations, not the brain.
# Worst-case compute budget is ~920 H100-h (15x8 + 13x32 + 4x96); actual spend is
# typically well under the per-paper band caps since the agent stops when it
# converges. Max Effort measured ~2.5x verbosity on the AA index, so wall clock
# burns faster than the round budget suggests -- expect a re-submit to finish the
# tail. That verbosity fed V4's unbounded prior-turn CoT replay and killed 16 of
# 27 scored runs in sweep 2883229 on context_budget; the fix is the 1M ceiling
# above (409600 served, 376832 to the agent vs the old flat 128000), not a lower
# rung. 1M was tried and killed the engine (job 2889476). Max is the AA
# Intelligence Index 40 anchor, so keeping it keeps the capability axis.
#
#SBATCH -J repro_medium_dsv4
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=144
#SBATCH --gpus-per-node=2
#SBATCH --gpu-bind=none
#SBATCH --mem=220G
#SBATCH --time=48:00:00
#SBATCH -o slurm-repro-medium-dsv4-%j.out
#SBATCH -e slurm-repro-medium-dsv4-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Config (override from the environment) ---------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-deepseek-ai/DeepSeek-V4-Flash-0731}"   # native INT8/FP8, ~155 GiB, fits 2xGH200 at TP=2
SERVED_NAME="${SERVED_NAME:-deepseek-ai/DeepSeek-V4-Flash-0731}"
TP="${TP:-2}"                            # GPUs for the brain; TP=4 needs sbatch --gpus-per-node=4
AUDIT_MODEL="${AUDIT_MODEL:-${SERVED_NAME}}"  # grader; this job serves one brain, so it defaults to it
# Parser escape hatch: the deepseek_v4 profile defaults follow Model Selection
# Notes ("parser deepseek_v4"). If a given vLLM build names the V4 tool parser
# differently (e.g. deepseek_v3), override these without touching the profile.
TOOL_PARSER="${TOOL_PARSER:-deepseek_v4}"
REASONING_PARSER="${REASONING_PARSER:-deepseek_v4}"
PORT="${PORT:-8000}"
SPLIT="${SPLIT:-eval}"                    # eval -> HF 'test' (the frozen 100-paper benchmark)
TIER="${TIER:-Medium}"                    # only reproduce+grade rows of this tier
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"        # reproduction agent tool rounds
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"  # auditor's run-dir exploration rounds
MAX_PARALLEL="${MAX_PARALLEL:-10}"       # papers in flight at once; each adds 1 JIT ghx4 node
RESUME="${RESUME:-1}"                    # 1 -> skip papers that already have a verdict on disk
MAX_MODEL_LEN="${MAX_MODEL_LEN:-409600}" # 400*1024, just over the Think Max floor; matches the deepseek_v4 profile default
# The auditor is a URL-only client with no served-window lookup of its own, so its
# input ceiling is derived here: the served window less the 32768 it reserves for the
# verdict. The repro agent needs no equivalent -- it reads the window off /v1/models.
AUDIT_MAX_INPUT_TOKENS=$(( MAX_MODEL_LEN - 32768 ))
# DeepSeek's agentic-scenario recommendation for 0731 (the card's other value, 1.0, is
# for non-agentic use). Applied to the repro agent via REPROCLI_TOP_P and to the
# auditor via --top-p, so one knob moves both loops.
TOP_P="${TOP_P:-0.95}"
export REPROCLI_TOP_P="${TOP_P}"

# Pin Think Max on every request (repro loop + auditor tool loop). The client's
# apply_chat_template_kwargs reads this and never clobbers a per-request override.
# The default is held in its own variable: bash ends a ${VAR:-...} default at the
# first unescaped "}", so an inline JSON default silently appends a stray brace to
# any operator override, and the unparseable value is dropped whole (endpoint.py).
CHAT_TEMPLATE_KWARGS_DEFAULT='{"thinking": true, "reasoning_effort": "max"}'
export REPROCLI_CHAT_TEMPLATE_KWARGS="${REPROCLI_CHAT_TEMPLATE_KWARGS:-${CHAT_TEMPLATE_KWARGS_DEFAULT}}"

# Audit against the same canonical lockfile claim the agent targeted.
case "${SPLIT}" in
  dev|validation) CLAIMS_FILE="dev_split.jsonl" ;;
  *)              CLAIMS_FILE="eval_100.jsonl" ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/${LOCKFILE}/${CLAIMS_FILE}}"

# Keep the agent's heavy I/O (bundles, per-paper uv venvs, run bundles) off $HOME.
export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
# The reproduction AGENT runs inside the Apptainer sandbox; send ONLY its in-container HF
# pulls (per-paper models + datasets, the bulk that filled /work) to node-local /tmp, which
# clears per job. APPTAINERENV_HF_HOME wins inside the wrap (sandbox.forward_env honors a
# pre-set value), so the served brain + orchestrator above keep the persistent /work cache.
export APPTAINERENV_HF_HOME="${APPTAINERENV_HF_HOME:-/tmp/hf_cache}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT}/agent_runs}"
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARNING: HF_TOKEN is unset; the lockfile/bundle download from the Hub may fail." >&2
fi

# Agent-logs upload is opt-in: the reproduce sink upserts repro_runs, then
# audit_upload PATCHes audit_* onto the pinned run_id.
export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"
if [[ -z "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  echo "WARNING: SUPABASE_SERVICE_KEY is unset; runs + audit verdicts will NOT upload to agent-logs." >&2
fi

OUTER_JOB="${SLURM_JOB_ID:-local}"
# One batch id per sbatch launch groups this sweep's runs in the viewer; the
# REPRO_* vars survive the SLURM_* env scrub below (override to join an old batch).
export REPRO_BATCH_ID="${REPRO_BATCH_ID:-slurm-${OUTER_JOB}}"
export REPRO_BATCH_LABEL="${REPRO_BATCH_LABEL:-${SLURM_JOB_NAME:-repro_sweep} #${OUTER_JOB}}"
SWEEP_DIR="${SWEEP_DIR:-${REPRO_WORK_ROOT}/medium_sweeps/${OUTER_JOB}}"
ENDPOINT_FILE="${ENDPOINT_FILE:-${SWEEP_DIR}/brain_endpoint.${OUTER_JOB}.json}"
IDS_FILE="${SWEEP_DIR}/medium_ids.txt"
mkdir -p "${SWEEP_DIR}"

# Sweep-wall countdown surfaced to the agent every tool round (transcript.py reads
# this): the absolute epoch when SLURM kills this job. squeue %e is the scheduler's
# own end time; fall back to now + the #SBATCH --time cap if it is unavailable.
if end_ts="$(squeue -h -j "${SLURM_JOB_ID}" -o '%e' 2>/dev/null)" \
   && [ -n "${end_ts}" ] \
   && REPRO_WALL_DEADLINE_EPOCH="$(date -d "${end_ts}" +%s 2>/dev/null)"; then
  :
else
  REPRO_WALL_DEADLINE_EPOCH="$(( $(date +%s) + 48 * 3600 ))"
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

# --- DeepSeek-V4-Flash REQUIRED serve exports (tasks/serve-dsv4flash-vllm-gh200.md) --
# 1. DeepGEMM needs libnvrtc.so.13, or the server dies with "Sparse Attention
#    Indexer CUDA op requires DeepGEMM support" (V4's Lightning Indexer has no
#    non-DeepGEMM fallback). vLLM's vendored deep_gemm is the one that matters.
export LD_LIBRARY_PATH="${VENV}/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}"
# 2. FlashInfer's top-k/top-p sampling kernel crashes the profile run on GH200
#    (TopKMaskLogits: invalid resource handle). Native torch sampler instead.
export VLLM_USE_FLASHINFER_SAMPLER=0

ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

echo "host=$(hostname)  job=${OUTER_JOB}  endpoint_file=${ENDPOINT_FILE}"
# Empty budget means the CLI derives the paper ceiling from its selection band.
if [[ -n "${BUDGET_H100_HOURS}" ]]; then
  BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")
  BUDGET_LABEL="${BUDGET_H100_HOURS}h (flat)"
else
  BUDGET_ARG=()
  BUDGET_LABEL="per-band"
fi
echo "sweep_dir=${SWEEP_DIR}  split=${SPLIT}  tier=${TIER}  budget=${BUDGET_LABEL}  rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}"
echo "runs_dir=${RUNS_DIR}  resume=${RESUME}  audit_model=${AUDIT_MODEL}  audit_rounds=${AUDIT_TOOL_ROUNDS}"
echo "brain=${MODEL}  tp=${TP}"
echo "parsers: tool=${TOOL_PARSER}  reasoning=${REASONING_PARSER}  max_model_len=${MAX_MODEL_LEN}"
echo "think_max_kwargs=${REPROCLI_CHAT_TEMPLATE_KWARGS}"
echo "claims=${CLAIMS}"
nvidia-smi topo -m || true

# --- Step 1: serve the brain (background), wait for /health ------------------
# TP=${TP} on the allocated GH200s (deepseek_v4 profile: fp8 KV, deepseek_v4 parsers,
# max_model_len 409600). --kv-offloading-* adds a 100 GiB Grace-RAM CPU KV tier
# (native OffloadingConnector, total across TP ranks) so multi-agent transcripts
# don't thrash the thin GPU KV. Parsers are passed explicitly so TOOL_PARSER /
# REASONING_PARSER can override the profile without a code edit.
# Never inherit an endpoint from a requeue of this same job id.
rm -f "${ENDPOINT_FILE}"
python -m reprocli_serve \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --tensor-parallel-size "${TP}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --tool-call-parser "${TOOL_PARSER}" \
  --reasoning-parser "${REASONING_PARSER}" \
  --endpoint-file "${ENDPOINT_FILE}" \
  -- --kv-offloading-backend native --kv-offloading-size 100 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# reprocli_serve writes ENDPOINT_FILE once /health is green. DeepGEMM JIT-compiles
# kernels on the first request after startup, so the health wait can be long.
for _ in $(seq 1 720); do
  [[ -f "${ENDPOINT_FILE}" ]] && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "brain exited before publishing an endpoint" >&2; exit 1
  fi
  sleep 5
done
[[ -f "${ENDPOINT_FILE}" ]] || { echo "timed out waiting for ${ENDPOINT_FILE}" >&2; exit 1; }

# A resume points SWEEP_DIR at a predecessor's directory. Refuse an endpoint this
# job did not publish: attaching to a dead node's address burns every paper the
# dispatch loop reaches before the real brain overwrites the file.
BASE_URL="$(python3 - "${ENDPOINT_FILE}" "${OUTER_JOB}" <<'PY'
import json, sys

payload = json.load(open(sys.argv[1]))
owner = str(payload.get("job_id", ""))
if owner != sys.argv[2]:
    raise SystemExit(f"endpoint {sys.argv[1]} was published by job {owner!r}, not {sys.argv[2]!r}")
print(payload["base_url"])
PY
)" || exit 1
curl -fsS "${BASE_URL}/health" >/dev/null || { echo "brain unreachable at ${BASE_URL}" >&2; exit 1; }
echo "brain up at ${BASE_URL}"

# Host telemetry (optional; same opt-in as the agent-logs upload): one master
# beacon samples this node + tails this job's .out into host_status.log_tail.
# Per-run beacons ride each JIT allocation (spawned by gpu_session).
BEACON_PID=""
if [[ -n "${SUPABASE_SERVICE_KEY:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]]; then
  LOGFILE="$(scontrol show job "${OUTER_JOB}" 2>/dev/null | sed -n 's/.*StdOut=\([^ ]*\).*/\1/p' | head -1)"
  python -m reprocli_repro.metrics_beacon --role master --log-file "${LOGFILE:-/dev/null}" --interval 15 &
  BEACON_PID=$!
fi
trap 'kill "${SERVER_PID}" ${BEACON_PID:+"${BEACON_PID}"} 2>/dev/null || true' EXIT

# The orchestrator + auditor auto-discover the URL + served model from this file.
export REPROCLI_ENDPOINT_FILE="${ENDPOINT_FILE}"

# --- Step 2: enumerate the Easy tier of the split ---------------------------
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

# --- Step 3: scrub inherited SLURM_* so each run_gpu salloc/srun is clean ----
# Child srun inherits this allocation's env; scrub it for fresh JIT GPU steps.
for v in $(compgen -v | grep -E '^SLURM_' || true); do unset "$v"; done
export SLURM_EXPORT_ENV=ALL

# --- Step 4: reproduce + audit every Easy paper, PAIRED on one bundle --------
# Per paper: reproduce with a pinned run id, symlink <grade-root>/<id> to that
# exact bundle, audit it, then PATCH the verdict onto the same repro_runs row.
STATUS_FILE="${SWEEP_DIR}/status.tsv"

# The brain can be reachable at sweep start and gone later (node loss, OOM kill,
# a requeue of the serve step). A paper dispatched against a dead address dies in
# seconds and every path below returns 0, so it would be filed as a model failure
# and never retried. Probe /models -- the exact call the worker makes -- and wait
# rather than spend the paper. reprocli_serve publishes base_url without a /v1
# suffix and the glm52 scripts publish one with it, so normalize before probing.
brain_ready() {
  curl -fsS --max-time 10 "${BASE_URL%/v1}/v1/models" >/dev/null 2>&1
}

wait_for_brain() {
  local tries="${1:-60}"
  for _ in $(seq 1 "${tries}"); do
    brain_ready && return 0
    sleep 10
  done
  return 1
}

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

  if ! wait_for_brain 60; then
    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "-" "brain-down" "-" "-" >> "${STATUS_FILE}"
    echo "!!! [$(date '+%F %T')] ${pid} NOT dispatched: brain unreachable at ${BASE_URL}"
    return 0
  fi

  local rid="${OUTER_JOB}-${pid}-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  echo ">>> [$(date '+%F %T')] start ${pid} (run_id=${rid})"

  # (1) Reproduce this paper; the brain URL comes from REPROCLI_ENDPOINT_FILE.
  # Sampling stays unset so the agent defers to DeepSeek's generation_config
  # (temp 1.0 / top_p 1.0 for Think Max); the effort itself rides
  # REPROCLI_CHAT_TEMPLATE_KWARGS.
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
  # Explicit temperature 1.0 / top_p ${TOP_P} = DeepSeek's recommendation for an
  # agentic loop; the effort itself rides REPROCLI_CHAT_TEMPLATE_KWARGS.
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
    --temperature 1.0 \
    --top-p "${TOP_P}" \
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
# Track only per-paper PIDs; the brain server is also a background child.
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
harness_fail=$(awk -F'\t' '$3=="no-bundle" || $3=="brain-down"' "${STATUS_FILE}" | wc -l)
if (( harness_fail > 0 )); then
  echo "WARNING: ${harness_fail} paper(s) failed WITHOUT producing a bundle -- harness casualties,"
  echo "         not model failures. They wrote no verdict, so RESUME=1 re-picks them:"
  awk -F'\t' '$3=="no-bundle" || $3=="brain-down" {print "           " $1 "  (" $3 ")"}' "${STATUS_FILE}"
fi
echo "reproduced ok: ${repro_ok}/${total}   audited ok: ${audit_ok}/${total}   uploaded ok: ${upload_ok}/${total}   (per-paper rc in ${STATUS_FILE})"
sort "${STATUS_FILE}"

# --- Summary ----------------------------------------------------------------
echo "===== ${TIER} sweep complete (job ${OUTER_JOB}) ====="
echo "run bundles : ${RUNS_DIR}/<arxiv_id>/<budget>h/<run_id>/"
echo "reproduce   : ${SWEEP_DIR}/reproduce_<arxiv_id>.jsonl  (status: ${STATUS_FILE})"
echo "grades      : ${SWEEP_DIR}/audit_<arxiv_id>_extracted.jsonl  (score/verdict/reproduced per paper)"
echo "audit trace : ${SWEEP_DIR}/audit_<arxiv_id>_trace.jsonl"
