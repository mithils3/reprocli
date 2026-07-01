#!/usr/bin/env bash
# Reproduce one paper, grade its bundle with the S7 auditor, and upload the verdict
# to the agent-logs app. Three decoupled stages, chained on success:
#
#   1. reprocli_repro            -> <runs-dir>/<id>/{report.json, evidence/, stats.json}
#   2. run_arxiv... --mode audit -> <verdicts>.jsonl  (graded 0-5 + verdict)
#   3. reprocli_repro.audit_upload -> PATCHes audit_* onto the run's repro_runs row
#
# Stage 3 patches an EXISTING repro_runs row, so stage 1 must upload its telemetry:
# that needs SUPABASE_URL + SUPABASE_SERVICE_KEY in the environment (checked below).
#
# Usage:
#   scripts/reproduce/repro_audit_one.sh <paper-id> [split]
#   nohup scripts/reproduce/repro_audit_one.sh 2505.18513 dev > repro_audit_2505.18513.log 2>&1 &
#
# Env overrides (all optional):
#   MODEL ENDPOINT CLUSTER RUNS_DIR TOOL_ROUNDS BUDGET SUPABASE_URL

set -euo pipefail

PAPER_ID="${1:?usage: repro_audit_one.sh <paper-id> [split]}"
SPLIT="${2:-dev}"

MODEL="${MODEL:-deepseek/deepseek-v4-pro}"
ENDPOINT="${ENDPOINT:-https://openrouter.ai/api/v1}"
CLUSTER="${CLUSTER:-deltaai}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}/agent_runs}"
TOOL_ROUNDS="${TOOL_ROUNDS:-25}"
BUDGET="${BUDGET:-}"   # empty = auto (derive the ceiling from the paper's selection band)
export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"

# Resolve the repo root (two levels up) so src/ and outputs/ resolve wherever this runs.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -z "${SUPABASE_SERVICE_KEY:-}" ]]; then
  echo "warning: SUPABASE_SERVICE_KEY is unset -- the run won't upload, so stage 3 will" >&2
  echo "         have no repro_runs row to grade. Set it (it's in your bashrc)." >&2
fi

VERDICTS="audit_${PAPER_ID}_extracted.jsonl"
IDS_FILE="$(mktemp -t "audit_ids_${PAPER_ID}.XXXXXX")"
echo "$PAPER_ID" > "$IDS_FILE"
trap 'rm -f "$IDS_FILE"' EXIT

echo ">>> [1/3] reproduce $PAPER_ID (split=$SPLIT, budget=${BUDGET:-auto})"
repro_args=(--paper-id "$PAPER_ID" --split "$SPLIT"
            --vllm-server-url "$ENDPOINT" --served-model-name "$MODEL" --cluster "$CLUSTER")
[[ -n "$BUDGET" ]] && repro_args+=(--budget-h100-hours "$BUDGET")
python -m reprocli_repro "${repro_args[@]}"

echo ">>> [2/3] audit $PAPER_ID (tool-rounds=$TOOL_ROUNDS)"
PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py \
  --mode audit \
  --vllm-server-url "$ENDPOINT" \
  --served-model-name "$MODEL" \
  --model "$MODEL" \
  --runs-dir "$RUNS_DIR" \
  --paper-ids-file "$IDS_FILE" \
  --tool-rounds "$TOOL_ROUNDS" \
  --output "audit_${PAPER_ID}.jsonl" \
  --extracted-output "$VERDICTS" \
  --save-round-jsonl

echo ">>> [3/3] upload verdict for $PAPER_ID -> agent-logs"
PYTHONPATH=src python3 -m reprocli_repro.audit_upload \
  --verdicts "$VERDICTS" \
  --runs-dir "$RUNS_DIR" \
  --audit-model "$MODEL"

echo ">>> done: $PAPER_ID"
