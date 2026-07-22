#!/bin/bash
# Serve GLM-5.2 UD-IQ3_S via llama.cpp on 4xGH200, then run every tier-Medium
# paper through the paired S6->S7 flow from scripts/reproduce/repro_audit_one.sh:
# reproduce with a pinned run id, audit exactly that bundle, and optionally
# upload the verdict.
#
#   sbatch scripts/reproduce/glm52/medium_glm52.sbatch
#
# Medium-tier sibling of easy_glm52.sbatch (see that header for the serve
# rationale: GLM-5.2 ships GGUF-first at a size vLLM cannot serve here, so
# Step 1 launches llama-server on the UD-IQ3_S 3-bit quant across all four
# GPUs, q8_0 KV pool in HBM, and hand-publishes the endpoint JSON contract).
# Every `run_gpu` experiment step still JIT-sallocs a SEPARATE ghx4 node; the
# orchestrator + auditor are cheap CPU processes sharing this brain node.
# Defaults to the eval split's Medium papers, MAX_PARALLEL=6, and RESUME=1 so
# re-submits after the 48h cap skip papers that already wrote a verdict.
#
#SBATCH -J repro_medium_glm52
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=288
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH --mem=440G
#SBATCH --time=48:00:00
#SBATCH -o slurm-repro-medium-glm52-%j.out
#SBATCH -e slurm-repro-medium-glm52-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Config (override from the environment) ---------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL_DIR="${MODEL_DIR:-/work/nvme/bfvr/msalunkhe/models/GLM-5.2-IQ3S}"
QUANT="${QUANT:-UD-IQ3_S}"                 # quant subdir + shard-name infix
# Shard count differs by quant, so glob shard 1 instead of pinning -of-000NN.
SHARD="${SHARD:-$(ls "${MODEL_DIR}/${QUANT}"/*-00001-of-*.gguf 2>/dev/null | head -1 || true)}"
SERVED_NAME="${SERVED_NAME:-zai-org/GLM-5.2}"
AUDIT_MODEL="${AUDIT_MODEL:-${SERVED_NAME}}"  # grader; this job serves one brain, so it defaults to it
PORT="${PORT:-8080}"
SPLIT="${SPLIT:-eval}"                    # eval -> HF 'test' (the frozen 100-paper benchmark)
TIER="${TIER:-Medium}"                      # only reproduce+grade rows of this tier
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"        # reproduction agent tool rounds
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"  # auditor's run-dir exploration rounds
MAX_PARALLEL="${MAX_PARALLEL:-6}"        # papers in flight at once; each adds 1 JIT ghx4 node
RESUME="${RESUME:-1}"                    # 1 -> skip papers that already have a verdict on disk
# llama.cpp brain knobs. The prompt cache is per-slot (runbook §9), so slots
# match MAX_PARALLEL and each slot gets CTX_SIZE/PARALLEL = 128K of context.
# The whole 768K q8_0 KV pool (~35 GiB) now lives in HBM (KV_IN_CPU=0): the
# UD-IQ3_S weights (~288 GiB) leave ~94 GiB free, so KV no longer competes for
# the last few GiB and decode stays on HBM instead of the C2C link. Set
# KV_IN_CPU=1 to push KV back to Grace RAM (needed only for a >340 GiB quant).
PARALLEL="${PARALLEL:-${MAX_PARALLEL}}"
CTX_SIZE="${CTX_SIZE:-$(( PARALLEL * 131072 ))}"
KV_IN_CPU="${KV_IN_CPU:-0}"

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
ENDPOINT_FILE="${ENDPOINT_FILE:-${SWEEP_DIR}/brain_endpoint.json}"
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

# No vLLM/NCCL env block here: llama-server does its own multi-GPU (runbook §9).
# The venv is still needed for the orchestrator, auditor, and upload tooling.
ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

export PATH="$HOME/llama.cpp/build/bin:$PATH"
command -v llama-server >/dev/null || { echo "llama-server not on PATH; build per tasks/serve-gguf-llamacpp-gh200.md §5" >&2; exit 1; }
[[ -f "${SHARD}" ]] || { echo "missing shard ${SHARD}; download per runbook §4" >&2; exit 1; }

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
echo "claims=${CLAIMS}"
echo "brain: shard=${SHARD}  ctx=${CTX_SIZE}  slots=${PARALLEL}  kv_in_cpu=${KV_IN_CPU}"
nvidia-smi topo -m || true

# --- Step 1: serve the brain (background), wait for /health ------------------
# Flags per runbook §6: shard 1 only (llama.cpp finds the rest), -ngl 99, no
# --split-mode/--tensor-split, q8_0 KV quant (drop -ctk/-ctv first if the
# server dies with a KV-type error). KV stays on HBM by default now; only when
# KV_IN_CPU=1 is --no-kv-offload added, spilling KV to Grace LPDDR over C2C.
KV_ARGS=()
if [[ "${KV_IN_CPU}" == "1" ]]; then KV_ARGS+=(--no-kv-offload); fi
CUDA_VISIBLE_DEVICES=0,1,2,3 llama-server \
  --model "${SHARD}" \
  --alias "${SERVED_NAME}" \
  -ngl 99 \
  "${KV_ARGS[@]}" \
  -ctk q8_0 -ctv q8_0 \
  --reasoning-preserve \
  --ctx-size "${CTX_SIZE}" --parallel "${PARALLEL}" \
  --cache-reuse 256 \
  --host 0.0.0.0 --port "${PORT}" \
  >"${SWEEP_DIR}/brain.log" 2>&1 &
SERVER_PID=$!
trap 'rm -f "${ENDPOINT_FILE}"; kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# llama.cpp is not wired into reprocli_serve, so publish the endpoint contract
# (src/reprocli_serve/endpoint.py keys) by hand: discover a routable Slingshot
# fabric IP (hsn0..hsn3) and write the JSON once /health goes green. GGUF load
# from shared NVMe is minutes, not the vLLM path's 45; 2h of polling is generous
# and a dead brain must kill the sweep, not idle under it (job 2602811).
HSN_IP="$(ip -4 -o addr show | awk '$2 ~ /^hsn/ {split($4, a, "/"); print a[1]; exit}')"
[[ -n "${HSN_IP}" ]] || { echo "no hsn interface found" >&2; exit 1; }
for _ in $(seq 1 720); do
  curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "brain exited before /health (see ${SWEEP_DIR}/brain.log)" >&2; exit 1
  fi
  sleep 10
done
curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null || { echo "timed out waiting for /health" >&2; exit 1; }

BASE_URL="http://${HSN_IP}:${PORT}/v1"
python3 - "${ENDPOINT_FILE}" <<PY
import json, socket, sys
payload = {
    "base_url": "${BASE_URL}",
    "host": "${HSN_IP}",
    "port": ${PORT},
    "served_model_name": "${SERVED_NAME}",
    "model_path": "${SHARD}",
    "node": socket.gethostname(),
    "job_id": "${OUTER_JOB}",
    "health": "ready",
}
with open(sys.argv[1], "w") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
PY
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
trap 'rm -f "${ENDPOINT_FILE}"; kill "${SERVER_PID}" ${BEACON_PID:+"${BEACON_PID}"} 2>/dev/null || true' EXIT

# The orchestrator + auditor auto-discover the URL + served model from this file.
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

# --- Step 3: scrub inherited SLURM_* so each run_gpu salloc/srun is clean ----
# Child srun inherits this allocation's env; scrub it for fresh JIT GPU steps.
for v in $(compgen -v | grep -E '^SLURM_' || true); do unset "$v"; done
export SLURM_EXPORT_ENV=ALL

# --- Step 4: reproduce + audit every Medium paper, PAIRED on one bundle --------
# Per paper: reproduce with a pinned run id, symlink <grade-root>/<id> to that
# exact bundle, audit it, then PATCH the verdict onto the same repro_runs row.
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

  # (1) Reproduce this paper; the brain URL comes from REPROCLI_ENDPOINT_FILE.
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
  # --max-model-len matches ONE llama.cpp slot (CTX_SIZE/PARALLEL), not the
  # vLLM siblings' 196K: a request longer than its slot gets truncated or
  # rejected by the server, so the client must size prompts to the slot.
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
    --max-model-len "$(( CTX_SIZE / PARALLEL ))" \
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
echo "reproduced ok: ${repro_ok}/${total}   audited ok: ${audit_ok}/${total}   uploaded ok: ${upload_ok}/${total}   (per-paper rc in ${STATUS_FILE})"
sort "${STATUS_FILE}"

# --- Summary ----------------------------------------------------------------
echo "===== ${TIER} sweep complete (job ${OUTER_JOB}) ====="
echo "run bundles : ${RUNS_DIR}/<arxiv_id>/<budget>h/<run_id>/"
echo "reproduce   : ${SWEEP_DIR}/reproduce_<arxiv_id>.jsonl  (status: ${STATUS_FILE})"
echo "grades      : ${SWEEP_DIR}/audit_<arxiv_id>_extracted.jsonl  (score/verdict/reproduced per paper)"
echo "audit trace : ${SWEEP_DIR}/audit_<arxiv_id>_trace.jsonl"
