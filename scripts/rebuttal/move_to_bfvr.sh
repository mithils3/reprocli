#!/usr/bin/env bash
# Every 2 min: move my PENDING rebuttal GPU jobs (salloc no-shell from ~/reprocli, repro_* brain jobs) from betw to bfvr.
# Distillation jobs (f1*, ut-u-*) are never touched.
while true; do
  squeue -u "$USER" -h -t PD -A betw-dtai-gh -o "%i %j" | while read -r j name; do
    case "$name" in
      repro_*) ;;
      no-shell) scontrol show job "$j" | rg -q "WorkDir=/u/msalunkhe/reprocli( |$)" || continue ;;
      *) continue ;;
    esac
    scontrol update JobId="$j" Account=bfvr-dtai-gh QOS=bfvr-dtai-gh && echo "[$(date -u '+%F %T')] moved $j $name"
  done
  sleep 120
done
