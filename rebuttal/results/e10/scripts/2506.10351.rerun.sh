#!/bin/bash
# E10 environment check. Run dsv4-run-2506.10351 (2506.10351, DeepSeek-V4-Flash, tier run).
# SRC_LOG=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2506.10351/8h/2883229-2506.10351-832e14/evidence/commands.log
# Original: default seed 0. Wall 0.35 h. Measured 94.19 (EPN-612 test accuracy %, expC from scratch; report scoring_command); target 93.12 (EPN-612 test accuracy %).
# Usage: SEED=1 bash rerun.sh   (new seeds 1 and 2). Lines marked PATCH are not in the transcript.
set -euo pipefail
: "${SEED:?set SEED}"; export SEED
SRC=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2506.10351/8h/2883229-2506.10351-832e14/workspace
RUN=/work/nvme/bfvr/msalunkhe/rebuttal/e10/2506.10351/seed$SEED
R=$RUN/repro
if [ ! -d "$R/workspace" ]; then
  mkdir -p "$R/workspace" "$R/evidence"
  (cd "$SRC" && tar -cf - --exclude=./Cached-Supernets --exclude=./.venv .) | (cd "$R/workspace" && tar -xf -)
  ln -s "$SRC/.venv" "$R/workspace/.venv"
fi
# PATCH (not in transcript): transcript line 284 copies the wrappers and then runs expB (1259 s); only the copy is kept here, expB is not part of the scored number
mkdir -p "$R/evidence" && cp "$R/workspace/evidence"/run_exp*.sh "$R/evidence/"
# PATCH (not in transcript): wrapper hard-codes --seed 42 (line 14 of run_expC_fromscratch.sh)
sed -i "s/--seed 42 /--seed $SEED /" "$R/evidence/run_expC_fromscratch.sh"
# L285 ts 06:48:26 dur 1270s gpus 1
bash $R/evidence/run_expC_fromscratch.sh
