"""Command-line argument definition, validation, and audit-mode defaults.

Split out of run_arxiv_prompt_vllm.py to keep that entry point focused on the
run flow. ``parse_args`` returns a fully-resolved argparse Namespace: model
profile defaults applied, audit-mode settings filled in, and all
cross-argument validation enforced.
"""

from __future__ import annotations

import argparse

from reprocli_vllm.config.config import (
    AUDIT_CLAIMS_DEFAULT,
    AUDIT_DEFAULT_EXTRACTED,
    AUDIT_DEFAULT_OUTPUT,
    AUDIT_FINAL_NO_TOOLS_MESSAGE,
    AUDIT_PROMPT_FILE,
    AUDIT_RUBRIC_FILE,
    AUDIT_RUNS_DIR_DEFAULT,
    AUDIT_SYSTEM_MESSAGE,
    DEFAULT_MODEL,
    MAX_REPEATED_TOOL_CALLS,
)
from reprocli_vllm.schema.audit import AUDIT_RESPONSE_FORMAT
from reprocli_vllm.tools.run_dir_tools import AUDIT_TOOLS
from reprocli_vllm.config.minimax_defaults import apply_model_defaults
from reprocli_vllm.runtime.trace_io import trace_output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int)
    parser.add_argument(
        "--mode",
        choices=("audit",),
        default="audit",
        help="audit grades an agent reproduction attempt against the rubric (the only mode).",
    )
    parser.add_argument(
        "--claims",
        type=argparse_path,
        help=(
            "Audit-pool rows (classifier extracted output) carrying the "
            "central_claim per paper, injected into the audit prompt. A local "
            "JSONL path or an hf://datasets/<owner>/<name>/<file> reference. "
            f"Default: {AUDIT_CLAIMS_DEFAULT}."
        ),
    )
    parser.add_argument(
        "--runs-dir",
        type=argparse_path,
        help=(
            "Root directory of agent reproduction runs; the auditor reads one "
            "run dir per paper at <runs-dir>/<arxiv_id> via the path-confined "
            f"run-dir tools (default: {AUDIT_RUNS_DIR_DEFAULT})."
        ),
    )
    parser.add_argument("--prompt-file", type=argparse_path)
    parser.add_argument("--output", type=argparse_path)
    parser.add_argument("--extracted-output", type=argparse_path)
    parser.add_argument("--trace-output", type=argparse_path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--vllm-server-url",
        help=(
            "Served vLLM chat-completions base URL. If omitted, the runner also "
            "checks $REPROCLI_SERVER_URL and the base_url in the file named by "
            "$REPROCLI_ENDPOINT_FILE (published by reprocli_serve). With no endpoint "
            "the auditor exits with an error — it does not self-host a model."
        ),
    )
    parser.add_argument(
        "--served-model-name",
        help=(
            "Model id to send in requests when attached to an existing server. "
            "Defaults to the single model the server advertises at /v1/models "
            "(also reads $REPROCLI_SERVED_MODEL)."
        ),
    )
    parser.add_argument(
        "--paper-ids-file",
        type=argparse_path,
        help="Run only the arXiv ids listed in this file (one per line).",
    )
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--max-input-tokens", type=int, default=128000)
    parser.add_argument("--tool-rounds", type=int, default=10)
    parser.add_argument("--request-workers", type=int, default=8)
    parser.add_argument("--max-model-len", type=int)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--stream-first-response", action="store_true")
    parser.add_argument("--save-round-jsonl", action="store_true")
    args = parser.parse_args()
    apply_model_defaults(args)
    resolve_mode_settings(args)
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.num_prompts is not None and args.num_prompts < 1:
        parser.error("--num-prompts must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.top_k is not None and args.top_k < 1:
        parser.error("--top-k must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within model context")
    if args.trace_output is None:
        args.trace_output = trace_output_path(args.output)
    return args


def resolve_mode_settings(args: argparse.Namespace) -> None:
    """Fill prompt/output/schema/message defaults for the audit mode."""
    args.prompt_file = args.prompt_file or AUDIT_PROMPT_FILE
    # The audit rubric is fixed; run_arxiv_prompt_vllm reads this attribute.
    args.rubric_file = AUDIT_RUBRIC_FILE
    args.output = args.output or AUDIT_DEFAULT_OUTPUT
    args.extracted_output = args.extracted_output or AUDIT_DEFAULT_EXTRACTED
    args.claims = args.claims or AUDIT_CLAIMS_DEFAULT
    args.runs_dir = args.runs_dir or AUDIT_RUNS_DIR_DEFAULT
    args.response_format = AUDIT_RESPONSE_FORMAT
    args.system_message = AUDIT_SYSTEM_MESSAGE
    args.final_no_tools_message = AUDIT_FINAL_NO_TOOLS_MESSAGE
    # The auditor explores the agent's run directory with the run-dir tools.
    args.tools = AUDIT_TOOLS
    args.use_tools = True
    # Fixed loop guard (was --max-repeated-tool-calls, never varied).
    args.max_repeated_tool_calls = MAX_REPEATED_TOOL_CALLS


def argparse_path(value: str):
    from pathlib import Path

    return Path(value)
