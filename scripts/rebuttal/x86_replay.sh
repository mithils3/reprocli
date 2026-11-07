#!/usr/bin/env bash
# Replay one aarch64 build failure on x86 (Delta). Usage: x86_replay.sh RUN_ID
# Reads $TSV (replay_cmds.tsv) and $RUNS (agent_runs root). Writes $OUT/result.txt.
set -u
RUN_ID=$1
TSV=${TSV:-/work/nvme/bfvr/msalunkhe/rebuttal/x86/replay_cmds.tsv}
RUNS=${RUNS:-/work/nvme/bfvr/msalunkhe/reprocli/agent_runs}
BASE=/work/nvme/bfvr/msalunkhe/rebuttal/x86
OUT=$BASE/$RUN_ID
# Venv, workspace and uv cache go on node-local disk: the bfvr project sits near its file cap.
T=${TMPDIR:-/tmp}/x86-$RUN_ID; export UV_CACHE_DIR=$T/uvcache
rm -rf "$OUT" "$T"; mkdir -p "$OUT" "$T/ws"

ROW=$(awk -F'\t' -v id="$RUN_ID" '$1==id' "$TSV")
CMD=$(printf '%s' "$ROW" | cut -f4)
RUNDIR=$RUNS/$(awk -F, -v id="$RUN_ID" '$1==id{print $NF}' "$BASE/build_failures.csv")
if [ "$CMD" = "NONE" ] || [ -z "$CMD" ]; then
  printf 'NOT_REPLAYABLE\nno install command in transcript\n' > "$OUT/result.txt"; exit 0
fi

uv venv -q "$T/venv" --python 3.12 || { echo "venv failed" > "$OUT/result.txt"; exit 1; }
export PY=$T/venv/bin/python
CMD=${CMD//\$PY/$PY}

# Copy only the requirements files the command names, from the run's read-only workspace.
for f in $(printf '%s' "$CMD" | tr ' ' '\n' | awk 'prev=="-r"{print} {prev=$0}' ); do
  (cd "$RUNDIR/workspace" 2>/dev/null && cp --parents "$f" "$T/ws/" 2>/dev/null)
done

cd "$T/ws"
bash -c "$CMD" > "$OUT/install.log" 2>&1
RC=$?

CHECK=""
if [ $RC -eq 0 ]; then
  PKG=$(printf '%s' "$CMD" | sed 's/.* install//' | tr ' ' '\n' | tr -d '"' | sed 's/[=<>\[].*//' | awk '/^[A-Za-z][A-Za-z0-9_.-]*$/{print; exit}' | tr '-' '_')
  CHECK=$("$PY" -c "import torch,sys; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" 2>&1 | tail -1)
  if [ -n "$PKG" ]; then
    CHECK="$CHECK | import $PKG: $("$PY" -c "import $PKG; print('ok')" 2>&1 | tail -1)"
  fi
fi

{ echo "RC=$RC"; echo "CMD=$CMD"; echo "CHECK=$CHECK"; echo "--- last 30 lines"; tail -30 "$OUT/install.log"; } > "$OUT/result.txt"
exit $RC

rm -rf "$T"
