#!/usr/bin/env bash
# Runs on gh-login01. Order: sol, then astra, then terra. Resumes paused dispatchers in turn.
C=/work/nvme/bfvr/msalunkhe/rebuttal/sweep_ctl.sh
has() { ssh -o BatchMode=yes "$1" "tmux has-session -t $2" 2>/dev/null; }
log() { echo "[$(date -u '+%F %T')] $*"; }
while has gh-login02 rb-codex-sol-b || has gh-login03 rb-codex-sol-ext; do sleep 300; done
log "sol done; resuming astra"; bash $C CONT gpt-6-astra 1-8
while tmux has-session -t rb-codex-astra-c 2>/dev/null; do sleep 300; done
log "astra done; resuming terra"; bash $C CONT gpt-6.1-terra 4-12
ssh -o BatchMode=yes gh-login02 "bash $C CONT gpt-6.1-terra 13-24"
log "all resumed"
