#!/bin/bash
# Serve poolside/Laguna-S-2.1-INT4 on 2xGH200 (one ghx4 node's two-GPU share, TP=2),
# then run every tier-Easy paper through the paired S6->S7 flow from
# scripts/reproduce/repro_audit_one.sh: reproduce with a pinned run id, audit
# exactly that bundle, and optionally upload the verdict.
#
#   sbatch scripts/reproduce/laguna_s21/easy_laguna_s21.sbatch
#
# 2xGH200 sibling of easy_dsv4_flash.sbatch. Structural differences, all from
# tasks/serve-laguna-s21-vllm-gh200.md (verified 2026-07-21 on the FP8 checkpoint,
# vLLM 0.25.1) and the INT4 variant of the vLLM recipe:
#   - brain: poolside/Laguna-S-2.1-INT4, a 117.6B MoE (~8.5B active) agentic-coding
#     specialist, arch LagunaForCausalLM, sliding-window attention with per-head
#     gating in 36 of 48 layers. This is the roster's coding-specialist rung. vLLM
#     0.25.1 registers the arch and the poolside_v1 parsers natively -- no bump.
#   - INT4 (W4A16) weights are ~72 GiB, so TP=2 puts ~36 GiB on each 96 GB GPU and
#     leaves ~53 GiB/GPU for KV. That is roomier than the FP8 checkpoint the runbook
#     verified (~56.6 GiB/GPU of weights, ~33 GiB/GPU of KV), so this sweep runs the
#     verified flags with more headroom rather than less. INT4 also fits TP=1 on one
#     GH200; TP=2 is kept because the runbook verified it and because the brain job
#     bills 2 SU/h on its CPU/memory request either way.
#   - max_model_len 262144 is the CEILING, not a tuning choice: only the BF16 repo
#     goes to 1M and both quantized checkpoints cap at 256K. fp8 KV halves per-token
#     cost (~6 GiB/GPU for a full 256K sequence), so ~8 full-length transcripts fit
#     on GPU alone; the 64 GiB Grace CPU KV tier below covers MAX_PARALLEL=10 plus
#     the audit stream without evicting.
#   - THREE launch-env exports are REQUIRED, all of them disabling FlashInfer paths
#     that crash on GH200 (see the wall below). They live here, not in the profile,
#     because they are launch env rather than serve flags.
#   - The serve profile (laguna_s21) carries the poolside_v1 parsers, fp8 KV,
#     gpu_memory_utilization 0.93, max_model_len 262144, and the compilation config
#     that turns the RMSNorm+all-reduce fusion off. --disable-custom-all-reduce is
#     the third leg of that same wall and rides EXTRA_SERVE_ARGS below.
#   - top_k 20 is pinned via REPROCLI_TOP_K. Laguna's generation_config ships
#     temperature 1.0 / top_p 1.0 / top_k 20, and top_k is NOT an OpenAI
#     chat-completions field, so an OpenAI-compatible client drops it silently and
#     the model runs off-distribution. Deferring to generation_config does not save
#     you: vLLM only applies it to fields the request omits, and the omission is the
#     bug. Same class as the DSV4-Flash chat_template_kwargs plumbing.
#   - No Think Max / reasoning_effort knob: Laguna has no effort ladder. Its
#     generation_config turns thinking on by default and this sweep leaves it there,
#     so REPROCLI_CHAT_TEMPLATE_KWARGS stays unset.
#   - deep_gemm / libnvrtc / CXXABI import warnings are BENIGN here. Laguna has no
#     DSA indexer, so vLLM falls back to the TRITON FP8 MoE backend and serves fine.
#     Unlike V4-Flash, whose Lightning Indexer has no non-DeepGEMM fallback, there is
#     nothing to chase. Do not add the DeepGEMM LD_LIBRARY_PATH export.
# Defaults to the eval split's Easy papers, MAX_PARALLEL=10, RESUME=1.
#
#SBATCH -J repro_easy_laguna
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=144
#SBATCH --gpus-per-node=2
#SBATCH --gpu-bind=none
#SBATCH --mem=220G
#SBATCH --time=48:00:00
#SBATCH -o slurm-repro-easy-laguna-%j.out
#SBATCH -e slurm-repro-easy-laguna-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Config (override from the environment) ---------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-poolside/Laguna-S-2.1-INT4}"   # INT4 W4A16, ~72 GiB, fits 2xGH200 at TP=2
# The served name is the QUANTIZED id, not the upstream poolside/Laguna-S-2.1. The
# runbook keeps the upstream string for a hand-served brain (it hides a local dir
# path), but this sweep writes `model` into every repro_runs row, and a sweep that
# files INT4 results under the upstream name is unattributable later. That exact
# mistake -- a 4-bit AWQ checkpoint reported as its upstream -- is already one of
# the confounds in the MiniMax sweeps. Do not "fix" this back to the short name.
SERVED_NAME="${SERVED_NAME:-poolside/Laguna-S-2.1-INT4}"
TP="${TP:-2}"                            # GPUs for the brain; TP=1 also fits INT4
AUDIT_MODEL="${AUDIT_MODEL:-${SERVED_NAME}}"  # grader; this job serves one brain, so it defaults to it
# Parser escape hatch: the laguna_s21 profile defaults follow the recipe
# ("poolside_v1" for both). Override if a given vLLM build names them differently.
TOOL_PARSER="${TOOL_PARSER:-poolside_v1}"
REASONING_PARSER="${REASONING_PARSER:-poolside_v1}"
PORT="${PORT:-8000}"
SPLIT="${SPLIT:-eval}"                    # eval -> HF 'test' (the frozen 100-paper benchmark)
TIER="${TIER:-Easy}"                      # only reproduce+grade rows of this tier
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"        # reproduction agent tool rounds
AUDIT_TOOL_ROUNDS="${AUDIT_TOOL_ROUNDS:-40}"  # auditor's run-dir exploration rounds
MAX_PARALLEL="${MAX_PARALLEL:-10}"       # papers in flight at once; each adds 1 JIT ghx4 node
RESUME="${RESUME:-1}"                    # 1 -> skip papers that already have a verdict on disk
MAX_MODEL_LEN="${MAX_MODEL_LEN:-262144}" # Laguna's 256K ceiling; matches the profile default

# Laguna's generation_config: temperature 1.0, top_p 1.0, top_k 20, thinking on.
# top_p rides REPROCLI_TOP_P and the auditor's --top-p; top_k rides REPROCLI_TOP_K
# and the auditor's --top-k, so one knob each moves both loops. top_k is the one
# that an OpenAI-compatible client would otherwise drop on the floor.
TOP_P="${TOP_P:-1.0}"
TOP_K="${TOP_K:-20}"
export REPROCLI_TOP_P="${TOP_P}"
export REPROCLI_TOP_K="${TOP_K}"

# Turn the fused RMSNorm+all-reduce off. Without it the server dies at the profiling
# run behind a misleading async CUBLAS_STATUS_EXECUTION_FAILED; the real crash is
# FlashInfer auto-selecting the mnnvl symmetric-memory all-reduce, which this 2xGH200
# topology cannot do (illegal memory access in the CUDASymmetricMemory dtor). Same
# default-in-its-own-variable trap as the dsv4 scripts: bash ends a ${VAR:-...}
# default at the first unescaped "}", so an inline JSON default would silently append
# a stray brace to any operator override. Set COMPILATION_CONFIG=none to serve with
# vLLM's own defaults again (expect the crash above).
COMPILATION_CONFIG_DEFAULT='{"pass_config":{"fuse_allreduce_rms":false}}'
COMPILATION_CONFIG="${COMPILATION_CONFIG:-${COMPILATION_CONFIG_DEFAULT}}"
if [[ "${COMPILATION_CONFIG}" == "none" ]]; then
  COMPILATION_ARG=()
else
  COMPILATION_ARG=(--compilation-config "${COMPILATION_CONFIG}")
fi

# --disable-custom-all-reduce is the third leg of the same all-reduce wall (the other
# two are the fusion above and VLLM_ALLREDUCE_USE_SYMM_MEM=0 below). It is a default
# here, not a suggestion; override only to A/B the wall.
#   DFlash speculative decode is DEFERRED (perf pass, not correctness): it wants
#   --speculative-config '{"model":"poolside/Laguna-S-2.1-DFlash-INT4",
#   "num_speculative_tokens":15}' plus --moe-backend triton, and the draft model must
#   be quantization-matched to this checkpoint. Measure it against this baseline
#   before committing it to a sweep -- it changes decode numerics, not just speed.
EXTRA_SERVE_ARGS_DEFAULT="--disable-custom-all-reduce"
read -r -a EXTRA_SERVE_ARGS_ARR <<< "${EXTRA_SERVE_ARGS:-${EXTRA_SERVE_ARGS_DEFAULT}}"

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
SWEEP_DIR="${SWEEP_DIR:-${REPRO_WORK_ROOT}/easy_sweeps/${OUTER_JOB}}"
ENDPOINT_FILE="${ENDPOINT_FILE:-${SWEEP_DIR}/brain_endpoint.${OUTER_JOB}.json}"
IDS_FILE="${SWEEP_DIR}/easy_ids.txt"
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

# --- Laguna REQUIRED serve exports (tasks/serve-laguna-s21-vllm-gh200.md) ----
# All three disable FlashInfer paths that crash on GH200. Dropping any one of them
# reopens the all-reduce wall documented above.
export VLLM_BLOCKSCALE_FP8_GEMM_FLASHINFER=0   # FlashInfer blockscale FP8 GEMM off
export VLLM_ALLREDUCE_USE_SYMM_MEM=0           # no symmetric-memory (mnnvl) all-reduce
export VLLM_USE_FLASHINFER_SAMPLER=0           # FlashInfer sampler is fragile on this box
# NOTE: no DeepGEMM LD_LIBRARY_PATH here on purpose. Laguna has no DSA indexer, so
# the deep_gemm import failure is benign and vLLM serves via the TRITON FP8 MoE path.

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
echo "brain=${MODEL}  served_as=${SERVED_NAME}  tp=${TP}"
echo "parsers: tool=${TOOL_PARSER}  reasoning=${REASONING_PARSER}  max_model_len=${MAX_MODEL_LEN}"
echo "compilation_config=${COMPILATION_CONFIG}  extra_serve_args=${EXTRA_SERVE_ARGS_ARR[*]}"
echo "sampling: top_p=${TOP_P}  top_k=${TOP_K}  (temperature deferred to generation_config)"
echo "claims=${CLAIMS}"
nvidia-smi topo -m || true

# --- Step 1: serve the brain (background), wait for /health ------------------
# TP=${TP} on the allocated GH200s (laguna_s21 profile: fp8 KV, poolside_v1 parsers,
# max_model_len 262144, gpu_memory_utilization 0.93). --kv-offloading-* adds a 64 GiB
# Grace-RAM CPU KV tier (native OffloadingConnector, total across TP ranks) so ten
# concurrent 256K transcripts plus the audit stream don't evict each other. Parsers
# are passed explicitly so TOOL_PARSER / REASONING_PARSER can override the profile
# without a code edit.
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
  "${COMPILATION_ARG[@]}" \
  --endpoint-file "${ENDPOINT_FILE}" \
  -- --kv-offloading-backend native --kv-offloading-size 64 \
     "${EXTRA_SERVE_ARGS_ARR[@]}" &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# reprocli_serve writes ENDPOINT_FILE once /health is green. Laguna's startup is
# ~62s of weight load plus ~166s of torch.compile on a warm cache; a cold
# TORCHINDUCTOR_CACHE_DIR makes the compile step considerably longer.
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
  # Temperature defers to Laguna's generation_config (1.0); top_p and top_k ride
  # REPROCLI_TOP_P / REPROCLI_TOP_K set above.
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
  # Explicit temperature / top_p / top_k = Laguna's generation_config, sent because
  # the auditor client would otherwise drop top_k the same way the repro loop would.
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
    --top-k "${TOP_K}" \
    --max-input-tokens 128000 \
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
