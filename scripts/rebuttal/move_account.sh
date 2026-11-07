#!/usr/bin/env bash
# Every 2 min: move my PENDING rebuttal GPU jobs (salloc no-shell from ~/reprocli or the rebuttal dirs,
# repro_* brain jobs, e10-* jobs) from SRC to DST account, QOS moved with it.
# Distillation jobs (f1*, ut-u-*) are never touched.
SRC=${SRC:-bfvr-dtai-gh} DST=${DST:-betw-dtai-gh}
while true; do
  squeue -u "$USER" -h -t PD -A "$SRC" -o "%i %j" | while read -r j name; do
    case "$name" in
      repro_*|e10-*) ;;
      no-shell) scontrol show job "$j" | rg -q "WorkDir=(/u/msalunkhe/reprocli|/work/nvme/bfvr/msalunkhe/(rebuttal|reprocli))" || continue ;;
      *) continue ;;
    esac
    scontrol update JobId="$j" Account="$DST" QOS="$DST" && echo "[$(date -u '+%F %T')] moved $j $name $SRC->$DST"
  done
  sleep 120
done
