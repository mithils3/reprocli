#!/usr/bin/env bash
# usage: sweep_ctl.sh STOP|CONT|LIST <model> <ranks>  -- signal codex_sweep.sh dispatchers matching MODEL and RANKS
act=$1; model=$2; ranks=$3
for p in $(pgrep -u "$USER" -f "codex_arm/codex_sweep.sh"); do
  e=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null)
  m=$(echo "$e" | sed -n 's/^MODEL=//p'); r=$(echo "$e" | sed -n 's/^RANKS=//p')
  st=$(awk '{print $3}' /proc/$p/stat)
  [[ "$m" == "$model" && ( -z "$ranks" || "$r" == "$ranks" ) ]] || continue
  case $act in STOP) kill -STOP $p;; CONT) kill -CONT $p;; esac
  echo "$(hostname -s) pid=$p model=$m ranks=$r state_before=$st action=$act"
done
