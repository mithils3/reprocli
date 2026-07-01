#!/usr/bin/env bash
# Reproduce one paper, then grade THAT EXACT run with the S7 auditor and upload the
# verdict. The two agents are PAIRED on one bundle: we pin the reproduction's run_id,
# find the bundle it wrote, and point the auditor at that single run — never at
# <runs-dir>/<id>, which mixes every past attempt for the paper.
#
#   1. reprocli_repro (--run-id RID)  -> <runs-dir>/<id>/<budget>h/RID/{report.json,evidence/,stats.json}
#   2. run_arxiv... --mode audit      -> grades ONLY that bundle -> <verdicts>.jsonl + audit trace
#   3. reprocli_repro.audit_upload    -> PATCHes audit_* onto RID's repro_runs row
#
# Stage 3 patches an existing repro_runs row, so stage 1 must upload its telemetry:
# that needs SUPABASE_URL + SUPABASE_SERVICE_KEY in the environment (checked below).
#
# Usage:
#   scripts/reproduce/repro_audit_one.sh <paper-id> [split]
#   nohup scripts/reproduce/repro_audit_one.sh 2505.18513 dev > repro_audit_2505.18513.log 2>&1 &
#
# Env overrides (all optional):
#   MODEL AUDIT_MODEL ENDPOINT CLUSTER RUNS_DIR TOOL_ROUNDS BUDGET CLAIMS RUN_ID SUPABASE_URL

set -euo pipefail

PAPER_ID="${1:?usage: repro_audit_one.sh <paper-id> [split]}"
SPLIT="${2:-dev}"

MODEL="${MODEL:-deepseek/deepseek-v4-pro}"
AUDIT_MODEL="${AUDIT_MODEL:-$MODEL}"   # grader; set a different model to keep it independent
ENDPOINT="${ENDPOINT:-https://openrouter.ai/api/v1}"
CLUSTER="${CLUSTER:-deltaai}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}/agent_runs}"
TOOL_ROUNDS="${TOOL_ROUNDS:-25}"
BUDGET="${BUDGET:-}"   # empty = auto (derive the ceiling from the paper's selection band)
# The auditor grades against each paper's central claim + pinned success bar
# (match_target) from the canonical lockfile — the SAME source the agent read its
# target from — picking the split file that matches the run.
case "$SPLIT" in
  dev|validation) CLAIMS_FILE=dev_split.jsonl ;;
  *)              CLAIMS_FILE=eval_100.jsonl ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/Mithilss/reprobench-splits/${CLAIMS_FILE}}"
export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"

# Resolve the repo root (two levels up) so src/ and outputs/ resolve wherever this runs.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -z "${SUPABASE_SERVICE_KEY:-}" ]]; then
  echo "warning: SUPABASE_SERVICE_KEY is unset -- the run won't upload, so stage 3 will" >&2
  echo "         have no repro_runs row to grade. Set it (it's in your bashrc)." >&2
fi

# Pin a unique run id so we can find the exact bundle afterward and patch the exact row.
RID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')}"
VERDICTS="audit_${PAPER_ID}_extracted.jsonl"
GRADE_ROOT="$(mktemp -d)"
IDS_FILE="$(mktemp -t "audit_ids_${PAPER_ID}.XXXXXX")"
echo "$PAPER_ID" > "$IDS_FILE"
trap 'rm -rf "$GRADE_ROOT" "$IDS_FILE"' EXIT

echo ">>> [1/3] reproduce $PAPER_ID (run_id=$RID, split=$SPLIT, budget=${BUDGET:-auto}, model=$MODEL)"
repro_args=(--paper-id "$PAPER_ID" --split "$SPLIT" --run-id "$RID"
            --vllm-server-url "$ENDPOINT" --served-model-name "$MODEL" --cluster "$CLUSTER")
[[ -n "$BUDGET" ]] && repro_args+=(--budget-h100-hours "$BUDGET")
python -m reprocli_repro "${repro_args[@]}"

# Locate the exact bundle this reproduction wrote (unique by run id, any budget dir).
RUN_DIR="$(find "$RUNS_DIR/$PAPER_ID" -type d -name "$RID" -print -quit 2>/dev/null || true)"
if [[ -z "$RUN_DIR" ]]; then
  echo ">>> reproduction wrote no bundle for $RID (it failed hard); nothing to audit" >&2
  exit 1
fi
echo ">>> reproduced bundle: $RUN_DIR"

# Bind a clean grade root that maps <paper_id> -> THIS bundle, so the auditor grades
# exactly this run (its run-dir contract reads <runs-dir>/<paper_id>).
ln -s "$RUN_DIR" "$GRADE_ROOT/$PAPER_ID"

echo ">>> [2/3] audit $PAPER_ID (grader=$AUDIT_MODEL, tool-rounds=$TOOL_ROUNDS)"
# Stream the auditor to the app's Audits page, linked to the run it grades.
export REPROCLI_GRADED_RUN_ID="$RID"
PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py \
  --mode audit \
  --vllm-server-url "$ENDPOINT" \
  --served-model-name "$AUDIT_MODEL" \
  --model "$AUDIT_MODEL" \
  --runs-dir "$GRADE_ROOT" \
  --claims "$CLAIMS" \
  --paper-ids-file "$IDS_FILE" \
  --tool-rounds "$TOOL_ROUNDS" \
  --output "audit_${PAPER_ID}.jsonl" \
  --extracted-output "$VERDICTS" \
  --trace-output "audit_${PAPER_ID}_trace.jsonl" \
  --save-round-jsonl

echo ">>> [3/3] upload verdict for $PAPER_ID (run $RID) -> agent-logs"
PYTHONPATH=src python3 -m reprocli_repro.audit_upload \
  --verdicts "$VERDICTS" \
  --runs-dir "$RUNS_DIR" \
  --run-id "$RID" \
  --audit-model "$AUDIT_MODEL"

echo ">>> how the auditor graded $PAPER_ID:"
python3 - "$VERDICTS" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
if not rows:
    print("  (auditor wrote no rows)"); raise SystemExit
r = rows[0]
print(f"  score: {r.get('score')}/5   verdict: {r.get('verdict')}   reproduced: {r.get('reproduced')}")
if r.get("reported_score") is not None:
    print(f"  (a high cheat flag capped this from {r['reported_score']}/5)")
flags = r.get("cheat_flags") or []
if flags:
    print("  cheat_flags: " + ", ".join(f"{f.get('kind')}({f.get('severity')})" for f in flags))
rationale = r.get("rationale") or ""
if rationale:
    print("  rationale: " + str(rationale)[:600])
PY
echo ">>> done: $PAPER_ID  (auditor transcript: audit_${PAPER_ID}_trace.jsonl; raw responses: audit_${PAPER_ID}.jsonl)"
