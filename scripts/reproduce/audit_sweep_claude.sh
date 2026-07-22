#!/usr/bin/env bash
# Grade every run of ONE sweep (sbatch batch) with Claude Opus 4.8 and upload the
# verdicts. Same Stage-7 auditor, same rubric, same OpenAI chat-completions dialect
# we already speak to vLLM/OpenRouter -- only the endpoint changes: Anthropic's
# OpenAI-compatible API (https://api.anthropic.com/v1/chat/completions).
#
#   1. reprocli_repro.batch_runs   -> binds each run_id of the batch to the exact
#                                     bundle it wrote, as a grade root of symlinks
#   2. run_arxiv_prompt_vllm       -> audits those bundles (tool loop -> verdict JSON)
#   3. reprocli_repro.audit_upload -> PATCHes audit_* onto each run's repro_runs row
#
# Extended thinking rides on REPROCLI_EXTRA_BODY, a JSON merge patch applied to every
# request body: adaptive thinking at high effort for Opus 4.8, and truncate_prompt_tokens
# (a vLLM-only field) deleted. If the endpoint rejects a knob, the client drops that
# field and retries once, printing "[extra_body] endpoint rejected ..." -- so check the
# log before trusting that a sweep was graded with thinking on.
#
# Cost note: the OpenAI-compatible layer does NOT do prompt caching, so every tool
# round re-sends the whole conversation at full input price. Smoke-test with LIMIT=1
# before turning it loose on 30 runs.
#
# Usage:
#   scripts/reproduce/audit_sweep_claude.sh <batch-id> [split]
#   LIMIT=1 scripts/reproduce/audit_sweep_claude.sh slurm-2687371          # smoke test
#   nohup scripts/reproduce/audit_sweep_claude.sh slurm-2687371 > audit_2687371.log 2>&1 &
#
# Env overrides: AUDIT_MODEL ENDPOINT EFFORT RUNS_DIR TOOL_ROUNDS WORKERS LIMIT
#                CLAIMS SUPABASE_URL REPROCLI_EXTRA_BODY SKIP_AUDITED

set -euo pipefail

BATCH="${1:?usage: audit_sweep_claude.sh <batch-id> [split]   (batch-id e.g. slurm-2687371)}"
SPLIT="${2:-eval}"

AUDIT_MODEL="${AUDIT_MODEL:-claude-opus-4-8}"
ENDPOINT="${ENDPOINT:-https://api.anthropic.com}"
EFFORT="${EFFORT:-high}"
RUNS_DIR="${RUNS_DIR:-${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}/agent_runs}"
TOOL_ROUNDS="${TOOL_ROUNDS:-25}"
WORKERS="${WORKERS:-4}"
export SUPABASE_URL="${SUPABASE_URL:-https://rjnkpoxwdslkgxjliakq.supabase.co}"

# The auditor grades against each paper's central claim + pinned success bar
# (match_target) from the canonical lockfile -- the same source the agent read from.
case "$SPLIT" in
  dev|validation) CLAIMS_FILE=dev_split.jsonl ;;
  *)              CLAIMS_FILE=eval_100.jsonl ;;
esac
CLAIMS="${CLAIMS:-hf://datasets/Mithilss/reprobench-splits/${CLAIMS_FILE}}"

# The agent core only ever reads REPROCLI_API_KEY (never another provider's key),
# so hand it the Anthropic one explicitly.
export REPROCLI_API_KEY="${REPROCLI_API_KEY:-${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY (or REPROCLI_API_KEY) to your Anthropic API key}}"
DEFAULT_EXTRA_BODY=$(printf '{"thinking":{"type":"adaptive"},"output_config":{"effort":"%s"},"truncate_prompt_tokens":null}' "$EFFORT")
export REPROCLI_EXTRA_BODY="${REPROCLI_EXTRA_BODY:-$DEFAULT_EXTRA_BODY}"

if [[ -z "${SUPABASE_SERVICE_KEY:-}" ]]; then
  echo "error: SUPABASE_SERVICE_KEY is unset -- needed to look up the batch's runs." >&2
  echo "       source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

GRADE_ROOT="$(mktemp -d)"
IDS_FILE="$(mktemp -t "audit_ids_${BATCH}.XXXXXX")"
trap 'rm -rf "$GRADE_ROOT" "$IDS_FILE"' EXIT
RAW="audit_${BATCH}.jsonl"
VERDICTS="audit_${BATCH}_extracted.jsonl"

echo ">>> [1/3] resolve run bundles for $BATCH under $RUNS_DIR"
resolve_args=(--batch "$BATCH" --runs-dir "$RUNS_DIR" --grade-root "$GRADE_ROOT" --ids-file "$IDS_FILE")
[[ -n "${LIMIT:-}" ]] && resolve_args+=(--limit "$LIMIT")
[[ -n "${SKIP_AUDITED:-}" ]] && resolve_args+=(--skip-audited)
python3 -m reprocli_repro.batch_runs "${resolve_args[@]}"
PAPERS=$(wc -l < "$IDS_FILE" | tr -d ' ')

echo ">>> [2/3] audit $PAPERS run(s) (grader=$AUDIT_MODEL @ $ENDPOINT, effort=$EFFORT,"
echo "          tool-rounds=$TOOL_ROUNDS, workers=$WORKERS, claims=$CLAIMS)"
python3 src/run_arxiv_prompt_vllm.py \
  --mode audit \
  --vllm-server-url "$ENDPOINT" \
  --served-model-name "$AUDIT_MODEL" \
  --model "$AUDIT_MODEL" \
  --runs-dir "$GRADE_ROOT" \
  --claims "$CLAIMS" \
  --paper-ids-file "$IDS_FILE" \
  --tool-rounds "$TOOL_ROUNDS" \
  --request-workers "$WORKERS" \
  --output "$RAW" \
  --extracted-output "$VERDICTS" \
  --trace-output "audit_${BATCH}_trace.jsonl" \
  --save-round-jsonl

echo ">>> [3/3] upload verdicts -> repro_runs (audit_model=$AUDIT_MODEL)"
# The grade root's symlinks resolve into each real bundle, whose stats.json names
# the run -- so every verdict patches the row of the run it graded.
python3 -m reprocli_repro.audit_upload \
  --verdicts "$VERDICTS" \
  --runs-dir "$GRADE_ROOT" \
  --audit-model "$AUDIT_MODEL"

echo ">>> how $AUDIT_MODEL graded $BATCH:"
python3 - "$VERDICTS" <<'PY'
import collections, json, sys

rows = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
scored = [r for r in rows if isinstance(r.get("score"), int)]
degraded = len(rows) - len(scored)
if scored:
    mean = sum(r["score"] for r in scored) / len(scored)
    print(f"  {len(scored)} graded, mean score {mean:.2f}/10, "
          f"reproduced {sum(1 for r in scored if r.get('reproduced'))}")
    for verdict, n in collections.Counter(r.get("verdict") for r in scored).most_common():
        print(f"    {verdict}: {n}")
    flagged = [r for r in scored if r.get("has_high_cheat_flag")]
    if flagged:
        print(f"    high cheat flag: {len(flagged)} ({', '.join(r['custom_id'] for r in flagged)})")
if degraded:
    print(f"  {degraded} row(s) produced no parseable verdict (see the raw output)")
PY
echo ">>> done: $BATCH  (verdicts: $VERDICTS; transcript: audit_${BATCH}_trace.jsonl; raw: $RAW)"
