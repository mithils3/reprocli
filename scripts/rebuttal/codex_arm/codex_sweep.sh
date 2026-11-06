#!/usr/bin/env bash
# One BLAS/OpenMP thread per harness process: numpy's OpenBLAS starts 64 threads per process, and 8 runs on one login node hit the 1000-pid user cgroup (2026-11-06 Codex crash).
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# Codex-arm sweep: one codex_run.py per paper, on DeltaAI login node.
#   MODEL=gpt-6.1-terra RANKS=1-12 nohup scripts/rebuttal/codex_arm/codex_sweep.sh > sweep.log 2>&1 &
#   MODEL=gpt-6.1-terra SMOKE=1 scripts/rebuttal/codex_arm/codex_sweep.sh
# RANKS from rebuttal/subset.json (core and extension); SMOKE=1 runs the dev smoke ids. Each paper uses its
# lockfile split and band budget. Spend guard as in api_sweep.sh: ledger USD for openai plus
# (in-flight + 1) x EST_RUN_USD must stay under CAP_USD, else dispatch stops.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
MODEL="${MODEL:-gpt-6.1-terra}"
RANKS="${RANKS:-}"
SMOKE="${SMOKE:-0}"
MAX_PARALLEL="${MAX_PARALLEL:-4}"
CAP_USD="${CAP_USD:-700}"
EST_RUN_USD="${EST_RUN_USD:-25}"
LOCKFILE="${LOCKFILE:-Mithilss/reclaim}"
SPEND_LEDGER="${SPEND_LEDGER:-/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl}"
RUNS_DIR="${RUNS_DIR:-/work/nvme/bfvr/msalunkhe/reprocli/agent_runs}"
SWEEP_DIR="${SWEEP_DIR:-/work/nvme/bfvr/msalunkhe/rebuttal/codex/sweeps/${MODEL}-$(date -u +%Y%m%dT%H%M%SZ)}"
PY="${PY:-${ROOT}/.venv/bin/python}"
export PYTHONPATH="${ROOT}/src" REPROCLI_SLURM_ACCOUNT="${REPROCLI_SLURM_ACCOUNT:-betw-dtai-gh}"
[[ -n "${OPENAI_API_KEY:-}" ]] || { echo "source OPENAI_API_KEY from ~/.bashrc first" >&2; exit 1; }

if [[ "${SMOKE}" == "1" ]]; then SEL_MODE=smoke; SEL_SPEC=""
elif [[ -n "${RANKS}" ]]; then SEL_MODE=ranks; SEL_SPEC="${RANKS}"
else echo "set RANKS=1-12 (core), RANKS=13-24 (extension), or SMOKE=1" >&2; exit 1; fi

PICK_TSV="$("${PY}" - "${ROOT}/rebuttal/subset.json" "${LOCKFILE}" "${SEL_MODE}" "${SEL_SPEC}" <<'PY'
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
    row = rows[split].get(r["paper_id"])
    if row is None:
        sys.exit(f"{r['paper_id']} not in {lockfile} split {split}")
    band = band_max_hours(row)
    budget = band if band is not None else r["budget_h100"]
    print("\t".join([r["paper_id"], split, f"{budget:g}"]))
PY
)"
mkdir -p "${SWEEP_DIR}/logs"
echo "sweep_dir=${SWEEP_DIR} model=${MODEL} parallel=${MAX_PARALLEL} cap_usd=${CAP_USD} est_run_usd=${EST_RUN_USD}"
echo "${PICK_TSV}" | sed 's/^/  /'

spent_usd() {
  [[ -f "${SPEND_LEDGER}" ]] || { echo 0; return; }
  "${PY}" - "${SPEND_LEDGER}" <<'PY'
import json, sys
total = 0.0
for line in open(sys.argv[1]):
    try:
        row = json.loads(line)
    except ValueError:
        continue
    if row.get("provider") == "openai":
        total += float(row.get("usd") or 0)
print(f"{total:.4f}")
PY
}
would_pass() {  # $1 = runs in flight including the one about to start
  awk -v s="$(spent_usd)" -v n="$1" -v e="${EST_RUN_USD}" -v c="${CAP_USD}" \
    'BEGIN { exit !(s + n * e > c) }'
}

running=0
stopped=0
while IFS=$'\t' read -r pid split budget; do
  [[ -n "${pid}" ]] || continue
  while (( running >= MAX_PARALLEL )); do wait -n || true; running=$((running - 1)); done
  if would_pass $((running + 1)); then
    echo "!!! spend-cap: $(spent_usd) USD spent + $((running + 1)) x ${EST_RUN_USD} would pass ${CAP_USD}; no further dispatch"
    stopped=1; break
  fi
  echo ">>> [$(date -u '+%F %T')] start ${pid} split=${split} budget=${budget}"
  "${PY}" "${ROOT}/scripts/rebuttal/codex_arm/codex_run.py" --paper-id "${pid}" --split "${split}" \
    --budget-h100-hours "${budget}" --model "${MODEL}" --runs-dir "${RUNS_DIR}" \
    > "${SWEEP_DIR}/logs/${pid}.log" 2>&1 &
  running=$((running + 1))
done <<< "${PICK_TSV}"
wait || true
echo "done stopped=${stopped} ledger_openai_usd=$(spent_usd)"
