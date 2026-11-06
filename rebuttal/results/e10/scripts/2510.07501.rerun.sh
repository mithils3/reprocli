#!/bin/bash
# E10 environment check. Run muse-retrain-2510.07501 (2510.07501, muse-wonder-1.0, tier retrain).
# SRC_LOG=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2510.07501/8h/20260816T133804Z-2510.07501-b58d86/evidence/commands.log
# Original: default seed 0. Wall 0.16 h. Measured -0.2241 (bias, 100 reps, n=2000, large_n=300000, seed 42); target -0.20 (Table 1, Scenario M1, MR estimator, always-survivor).
# Usage: SEED=1 bash rerun.sh   (new seeds 1 and 2). Lines marked PATCH are not in the transcript.
set -euo pipefail
# SUBST ["--seed 42 --out $R/evidence/results_m1_100.json", "--seed $SEED --out $R/evidence/results_m1_100.json"]
: "${SEED:?set SEED}"; export SEED
SRC=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2510.07501/8h/20260816T133804Z-2510.07501-b58d86/workspace
RUN=/work/nvme/bfvr/msalunkhe/rebuttal/e10/2510.07501/seed$SEED
R=$RUN/repro
if [ ! -d "$R/workspace" ]; then
  mkdir -p "$R/workspace" "$R/evidence"
  (cd "$SRC" && tar -cf - --exclude=./Cached-Supernets --exclude=./.venv .) | (cd "$R/workspace" && tar -xf -)
  ln -s "$SRC/.venv" "$R/workspace/.venv"
fi
# L1181 ts 14:04:03 dur 79s gpus 1
PYTHONUNBUFFERED=1 $R/workspace/.venv/bin/python $R/workspace/final_m1.py --reps 100 --n 2000 --large_n 300000 --seed $SEED --out $R/evidence/results_m1_100.json 2>&1 | tee $R/evidence/run_m1_100.log; cat $R/evidence/results_m1_100.json | head -n 100
# L1197 ts 14:13:41 dur 0s gpus 0
cat $R/evidence/results_m1_100.json | python3 -c "import json; d=json.load(open('$R/evidence/results_m1_100.json')); print(f\"100 bias {d['bias']:.4f} sd {d['sd']:.4f} mean {d['mean_estimate']:.4f} true {d['true_value']:.4f}\")"
