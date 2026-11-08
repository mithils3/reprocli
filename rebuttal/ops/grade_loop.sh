#!/bin/bash
O=/work/nvme/bfvr/msalunkhe/rebuttal/ops
# Every 30 min on DeltaAI: grade finished frontier runs (grade_arms.py keeps the Anthropic $200 gate), then rebuild the data book.
cd ~/reprocli || exit 1
while true; do
  git pull -q 2>/dev/null
  echo "[$(date "+%F %T")] grade pass" >> $O/grade_loop.log
  timeout 3h bash scripts/rebuttal/grade_arms.sh >> $O/grade_loop.log 2>&1
  python3 -I scripts/rebuttal/build_databook.py --out-dir /work/nvme/bfvr/msalunkhe/rebuttal/databook >> $O/grade_loop.log 2>&1
  sleep 1800
done
