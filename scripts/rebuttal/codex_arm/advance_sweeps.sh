#!/usr/bin/env bash
# sol (4 at a time) and astra (2 at a time) start together, sol first; terra starts once both have
# DISPATCHED all their papers (not when their longest run ends). PHASE=terra skips straight to the terra wait. Sweeps run under setsid so this script can die without touching them.
set -uo pipefail
R=~/reprocli; L=/work/nvme/bfvr/msalunkhe/rebuttal/codex; PY=$R/.venv/bin/python
export PYTHONPATH=$R/src
cd "$R" || exit 1
source <(rg '^export (OPENAI_API_KEY|HF_TOKEN)=' ~/.bashrc)
export HF_HOME=/work/nvme/bfvr/msalunkhe/.cache HF_HUB_DISABLE_XET=1 REPROCLI_SLURM_ACCOUNT=bfvr-dtai-gh
[[ -n "${OPENAI_API_KEY:-}" ]] || { echo "no OPENAI_API_KEY in ~/.bashrc" >&2; exit 1; }
log() { echo "[$(date -u '+%F %T')] $*"; }
starts() { rg -c '^>>> ' "$1" 2>/dev/null || echo 0; }
launch() {  # model ranks parallel tag -> echoes log path; returns number of papers to dispatch via global N
  local model=$1 ranks=$2 par=$3 tag=$4 skip lo hi n_rank n_skip
  skip="$($PY $R/scripts/rebuttal/codex_arm/skip_list.py --model "$model")"
  lo=${ranks%-*}; hi=${ranks#*-}; n_rank=$((hi - lo + 1))
  n_skip=$($PY - "$R/rebuttal/subset.json" "$lo" "$hi" "$skip" <<'PY'
import json, sys
sub = json.load(open(sys.argv[1])); lo, hi = int(sys.argv[2]), int(sys.argv[3])
ids = (sub.get("core") or []) + (sub.get("extension") or [])
ids = [r if isinstance(r, str) else r["paper_id"] for r in ids][lo - 1:hi]
print(sum(1 for i in sys.argv[4].split(",") if i and i in ids))
PY
)
  N=$((n_rank - n_skip)); OUT=$L/sweep-$model-$tag.log
  log "launch $model $ranks par=$par skip=${skip:-none} to_dispatch=$N log=$OUT"
  setsid nohup env SKIP="$skip" MODEL="$model" RANKS="$ranks" MAX_PARALLEL="$par" EST_RUN_USD=40 PY="$PY" \
    bash $R/scripts/rebuttal/codex_arm/codex_sweep.sh > "$OUT" 2>&1 < /dev/null &
  sleep 20  # let the sweep truncate its log before anyone counts start lines
}
if [[ "${PHASE:-all}" == all ]]; then
  launch gpt-6.1-sol 1-24 "${SOL_PAR:-4}" adv
  launch gpt-6-astra 1-8 2 adv
fi
S_LOG=$L/sweep-gpt-6.1-sol-adv.log; A_LOG=$L/sweep-gpt-6-astra-adv.log
while (( $(starts "$S_LOG") < 24 || $(starts "$A_LOG") < 8 )); do sleep 120; done; log "sol and astra dispatched"
launch gpt-6.1-terra 1-24 2 adv
log "all launched"
