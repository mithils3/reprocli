#!/bin/bash
# run_gpu inside the sandbox for the mini-SWE-agent arm. It hands the call to the host's run_gpu tool through
# /repro/mail, waits for the host to answer, and prints the tool's JSON result. Exit code is the step's.
gpus=1 minutes=30 partition= release=false
while [ $# -gt 0 ]; do
  case "$1" in
    --gpus) gpus=$2; shift 2 ;;
    --minutes) minutes=$2; shift 2 ;;
    --partition) partition=$2; shift 2 ;;
    --release) release=true; shift ;;
    --) shift; break ;;
    *) break ;;
  esac
done
id=$(date +%s%N)-$$
req=/repro/mail/$id.tmp
mkdir -p "$req"
printf '%s' "$*" > "$req/command"
printf 'gpus=%s\nminutes=%s\npartition=%s\nrelease=%s\n' "$gpus" "$minutes" "$partition" "$release" > "$req/args"
mv "$req" "/repro/mail/$id"
while [ ! -f "/repro/mail/$id/done" ]; do sleep 1; done
cat "/repro/mail/$id/out"
exit "$(cat "/repro/mail/$id/rc")"
