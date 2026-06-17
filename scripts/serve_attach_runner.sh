#!/bin/bash
# Attach a reprocli consumer (CC half) to a server stood up by reprocli_serve.
#
# This is the whole point of the split: the brain (classifier / auditor /
# reproduction agent) is model-agnostic and only makes HTTP requests, so it
# attaches to the server purely by URL. Swap providers by changing the URL.
#
#   ENDPOINT_FILE=/projects/bgnp/msalunkhe/endpoints/minimax_m2.json \
#     bash scripts/serve_attach_runner.sh --num-prompts 2
set -euo pipefail

ENDPOINT_FILE="${ENDPOINT_FILE:-/projects/bgnp/msalunkhe/endpoints/minimax_m2.json}"
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"

if [[ ! -f "${ENDPOINT_FILE}" ]]; then
  echo "No endpoint file at ${ENDPOINT_FILE}; is the server job running?" >&2
  exit 1
fi

# Pull the published URL + served model name (python: no jq dependency).
read -r SERVER_URL SERVED_NAME < <(
  python3 - "${ENDPOINT_FILE}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(d["base_url"], d.get("served_model_name", ""))
PY
)
echo "Attaching to ${SERVER_URL} (model ${SERVED_NAME})"

cd "${REPROCLI}"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"

# Option A (explicit flag): pass the URL straight through.
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "${SERVER_URL}" \
  --model "${SERVED_NAME}" \
  "$@"

# Option B (zero-flag): the runner also auto-discovers the URL from the same
# file via the env seam, so this is equivalent to Option A:
#   export REPROCLI_ENDPOINT_FILE="${ENDPOINT_FILE}"
#   python3 src/run_arxiv_prompt_vllm.py --model "${SERVED_NAME}" "$@"
