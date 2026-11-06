#!/bin/bash
# E10 environment check. Run muse-retrain-2505.17836 (2505.17836, muse-wonder-1.0, tier retrain).
# SRC_LOG=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2505.17836/8h/20260816T133804Z-2505.17836-5f483b/evidence/commands.log
# Original: default seed 0. Wall 0.12 h. Measured 0.03947 (final_mean, average normalized absolute error, 100 trials, t=80000, 2D Grid n=500); target ~0.05 (GoRank estimate at t=80000).
# Usage: SEED=1 bash rerun.sh   (new seeds 1 and 2). Lines marked PATCH are not in the transcript.
set -euo pipefail
: "${SEED:?set SEED}"; export SEED
SRC=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2505.17836/8h/20260816T133804Z-2505.17836-5f483b/workspace
RUN=/work/nvme/bfvr/msalunkhe/rebuttal/e10/work/2505.17836/seed$SEED
R=${R_OVERRIDE:-$RUN/repro}
if [ ! -d "$R/workspace" ]; then
  mkdir -p "$R/workspace" "$R/evidence"
  (cd "$SRC" && tar -cf - --exclude=./Cached-Supernets --exclude=./.venv .) | (cd "$R/workspace" && tar -xf -)
fi
# PATCH (not in transcript): the config sets experiment.seed (line 2); the original used 42
rg -q '^  seed: 42$' "$R/workspace/repo/configs/exp_target.yaml" && sed -i "s/^  seed: 42$/  seed: $SEED/" "$R/workspace/repo/configs/exp_target.yaml"
# L1 ts 13:40:47 dur 148s gpus 0
uv venv $R/workspace/.venv --python 3.12 2>&1 | tail -20
uv pip install --python $R/workspace/.venv/bin/python --index-url https://download.pytorch.org/whl/cu129 torch torchvision torchaudio 2>&1 | tail -20
ls -la $R/workspace/.venv/bin/python
ls -la $R/reference/ 2>&1 | head -50
# L159 ts 13:47:33 dur 98s gpus 1
cd $R/workspace/repo && PYTHONUNBUFFERED=1 $R/workspace/.venv/bin/python run_experiments.py --exp_name exp_target 2>&1 | tee $R/evidence/exp_target_run.log
echo "EXIT:$?"
ls -lh results/outputs/exp_target/
cat results/outputs/exp_target/config.yaml
$R/workspace/.venv/bin/python << 'PY'
import pickle, numpy as np, os
p="results/outputs/exp_target/results.pkl"
with open(p,"rb") as f:
    r=pickle.load(f)
print("keys", list(r.keys()))
print("names", r["names"])
mre=r["mean_relative_error"]
sre=r["std_relative_error"]
for k in mre:
    print(f"--- {k} ---")
    print("mean at 0,10k,20k,40k,60k,80k:", [float(mre[k][t]) for t in [0,10000,20000,40000,60000,79999]])
    print("final mean", float(mre[k][-1]), "std", float(sre[k][-1]))
    # also compute histogram?
    # Save full series to evidence
    np.save(f"$R/evidence/mean_{k.replace(' ','_').replace('(','').replace(')','')}.npy", mre[k])
    np.save(f"$R/evidence/std_{k.replace(' ','_').replace('(','').replace(')','')}.npy", sre[k])
    # also get all_relative_errors distribution? Not saved separately, but we have mean/std
PY
echo "=== done ==="
# also inspect data.npy existence
ls -lh $R/evidence/
# L229 ts 13:48:15 dur 0s gpus 0
cat $R/evidence/metrics_detailed.json 2>&1
cat $R/evidence/exp_target_run.log 2>&1
ls -lh $R/workspace/repo/results/outputs/exp_target/ 2>&1
cat $R/workspace/repo/configs/exp_target.yaml 2>&1
cp $R/workspace/repo/results/outputs/exp_target/results.pkl $R/evidence/results_exp_target.pkl 2>&1
cp $R/workspace/repo/results/outputs/exp_target/config.yaml $R/evidence/config_exp_target.yaml 2>&1
ls -lh $R/evidence/ 2>&1
