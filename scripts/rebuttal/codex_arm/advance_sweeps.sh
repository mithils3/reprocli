#!/usr/bin/env bash
# Start order sol -> astra -> terra, advancing when the previous sweep has DISPATCHED all its papers
# (not when its longest run ends). Sweeps run under setsid so this script can die without touching them.
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
}
launch gpt-6.1-sol 1-24 "${SOL_PAR:-4}" adv; S_LOG=$OUT; S_N=$N
while (( $(starts "$S_LOG") < S_N )); do sleep 120; done; log "sol dispatched $S_N"
launch gpt-6-astra 1-8 2 adv; A_LOG=$OUT; A_N=$N
while (( $(starts "$A_LOG") < A_N )); do sleep 120; done; log "astra dispatched $A_N"
launch gpt-6.1-terra 1-24 2 adv
log "all launched"
