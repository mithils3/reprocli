#!/usr/bin/env bash
# Mini-SWE-agent arm (muse-wonder-1.0) sweep: one miniswe_run.py per paper, on a DeltaAI login node.
#   RANKS=1-6 nohup scripts/rebuttal/miniswe_arm/miniswe_sweep.sh > sweep.log 2>&1 &
#   RANKS=1-6 DRY_RUN=1 scripts/rebuttal/miniswe_arm/miniswe_sweep.sh
# Same shape as codex_sweep.sh. SKIP=id,id drops papers. Spend guard: Meta ledger USD plus (in-flight + 1) x EST_RUN_USD
# must stay under CAP_USD, else dispatch stops. Each paper's lockfile band sets its GPU budget.
set -euo pipefail
trap '' HUP
# One BLAS/OpenMP thread per harness process (1000-pid user cgroup on login nodes).
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
MAX_PARALLEL="${MAX_PARALLEL:-2}"
CAP_USD="${CAP_USD:-480}"
EST_RUN_USD="${EST_RUN_USD:-23}"
ITEM="${ITEM:-E2}"
RANKS="${RANKS:-1-6}"
DRY_RUN="${DRY_RUN:-0}"
LOCKFILE="${LOCKFILE:-Mithilss/reclaim}"
SPEND_LEDGER="${SPEND_LEDGER:-/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl}"
RUNS_DIR="${RUNS_DIR:-/work/nvme/bfvr/msalunkhe/reprocli/agent_runs}"
SWEEP_DIR="${SWEEP_DIR:-/work/nvme/bfvr/msalunkhe/rebuttal/miniswe/sweep-core-a}"
BATCH_ID="${BATCH_ID:-rebuttal-muse-wonder-1.0-miniswe-core}"
export HF_HOME=/work/nvme/bfvr/msalunkhe/.cache HF_HUB_DISABLE_XET=1
export REPROCLI_SLURM_ACCOUNT="${REPROCLI_SLURM_ACCOUNT:-betw-dtai-gh}"
# shellcheck disable=SC1091
source "${ROOT}/scripts/rebuttal/miniswe_arm/env.sh"
SEL_PY="${ROOT}/.venv/bin/python"
RUN_PY="${ARM_VENV}/bin/python"
if [[ "${DRY_RUN}" != "1" ]]; then
  source <(rg '^export (META_MODEL_KEY|HF_TOKEN)=' ~/.bashrc)
  [[ -n "${META_MODEL_KEY:-}" ]] || { echo "META_MODEL_KEY not set after reading ~/.bashrc" >&2; exit 1; }
fi

mkdir -p "${SWEEP_DIR}/rows"
PICK_TSV="$(PYTHONPATH="${ROOT}/src" "${SEL_PY}" - "${ROOT}/rebuttal/subset.json" "${LOCKFILE}" "${RANKS}" "${SWEEP_DIR}/rows" <<'PY'
import json, os, sys
from reprocli_repro.dataset import band_max_hours, load_lockfile_rows

sub_path, lockfile, spec, rows_dir = sys.argv[1:5]
sub = json.load(open(sub_path))
lo, _, hi = spec.partition("-")
lo, hi = int(lo), int(hi or lo)
picks = [(r, "eval") for r in sub["core"] + sub["extension"] if lo <= r["rank"] <= hi]
skip = {x for x in os.environ.get("SKIP", "").split(",") if x}
picks = [(r, sp) for r, sp in picks if r["paper_id"] not in skip]
if not picks:
    sys.exit(f"no papers for ranks {spec!r}")
rows = load_lockfile_rows(lockfile, split="eval")
for r, split in picks:
    row = rows.get(r["paper_id"])
    if row is None:
        sys.exit(f"{r['paper_id']} not in {lockfile} split eval")
    band = band_max_hours(row)
    budget = band if band is not None else r["budget_h100"]
    row_path = os.path.join(rows_dir, f"row_{r['paper_id']}.json")
    json.dump(row, open(row_path, "w"))
    print("\t".join([r["paper_id"], split, f"{budget:g}", row_path]))
PY
)"
echo "sweep_dir=${SWEEP_DIR} model=muse-wonder-1.0 parallel=${MAX_PARALLEL} cap_usd=${CAP_USD} est_run_usd=${EST_RUN_USD}"
echo "${PICK_TSV}" | sed 's/^/  /'
if [[ "${DRY_RUN}" == "1" ]]; then
  echo "DRY_RUN=1: nothing dispatched"
  exit 0
fi

spent_usd() {
  [[ -f "${SPEND_LEDGER}" ]] || { echo 0; return; }
  "${SEL_PY}" - "${SPEND_LEDGER}" <<'PY'
import json, sys
total = 0.0
for line in open(sys.argv[1]):
    try:
        row = json.loads(line)
    except ValueError:
        continue
    if row.get("provider") == "meta":
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
while IFS=$'\t' read -r pid split budget row_path; do
  [[ -n "${pid}" ]] || continue
  while (( running >= MAX_PARALLEL )); do wait -n || true; running=$((running - 1)); done
  if would_pass $((running + 1)); then
    echo "!!! spend-cap: $(spent_usd) USD spent + $((running + 1)) x ${EST_RUN_USD} would pass ${CAP_USD}; no further dispatch"
    stopped=1; break
  fi
  stamp="$(date -u +%Y%m%dT%H%M%S)"
  run_id="miniswe-${pid}-${stamp}"
  echo ">>> [$(date -u '+%F %T')] start ${pid} run_id=${run_id} split=${split} budget=${budget}"
  (
    export PATH="$HOME/.local/bin:$PATH" PYTHONPATH="${ROOT}/src"
    cd "${ROOT}"
    exec "${RUN_PY}" -u scripts/rebuttal/miniswe_arm/miniswe_run.py --paper-id "${pid}" --paper-row "${row_path}" \
      --paper-budget-h100 "${budget}" --gpu-budget-h100 "${budget}" --runs-dir "${RUNS_DIR}" \
      --run-id "${run_id}" --batch-id "${BATCH_ID}" --item "${ITEM}" --ledger "${SPEND_LEDGER}"
  ) < /dev/null > "${SWEEP_DIR}/${pid}.log" 2>&1 &  # stdin from /dev/null: the harness must not read the sweep's stdin
  running=$((running + 1))
done <<< "${PICK_TSV}"
wait || true
echo "done stopped=${stopped} ledger_meta_usd=$(spent_usd)"
