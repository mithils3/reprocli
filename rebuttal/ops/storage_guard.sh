#!/bin/bash
# Every 30 min: pack workspace/ of rebuttal runs that are graded or VOID (verified tar via zip_cold.sh), log the bfvr file count, alert past 16.8M.
O=/work/nvme/bfvr/msalunkhe/rebuttal/ops; A=/work/hdd/bfvr/msalunkhe/from-nvme/reprocli/agent_runs
G=/work/nvme/bfvr/msalunkhe/rebuttal/grading/grades.jsonl
export RECENT_DAYS=0 GUARD=$A/ DEST= ONE=1
while true; do
  python3 - "$A" "$G" > $O/guard_list.txt <<"P"
import json,os,sys,glob
A,G=sys.argv[1:3]
graded={os.path.basename(json.loads(l)["run_dir"].rstrip("/")) for l in open(G) if l.strip()}
for ws in sorted(glob.glob(f"{A}/*/*/*/workspace")):
    run=os.path.dirname(ws); rid=os.path.basename(run)
    if os.path.islink(ws) or not os.path.isdir(ws): continue
    if os.path.exists(f"{run}/VOID") or rid in graded: print(ws)
P
  if [ -s $O/guard_list.txt ]; then mapfile -t L < $O/guard_list.txt; nice -n 19 bash /work/hdd/bfvr/msalunkhe/zip_cold.sh "${L[@]}" >> $O/storage_guard.log 2>&1; fi
  f=$(lfs quota -p 20421 /work/nvme | tail -1 | awk "{print \$6}"); echo "[$(date "+%F %T")] bfvr_files=$f" >> $O/storage_guard.log
  [ "$f" -gt 16800000 ] && echo "[$(date "+%F %T")] ALERT bfvr_files=$f" >> $O/storage_alert.log
  sleep 1800
done
