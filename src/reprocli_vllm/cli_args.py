"""Command-line argument definition, validation, and per-mode defaults.

Split out of run_arxiv_prompt_vllm.py to keep that entry point focused on the
run flow. ``parse_args`` returns a fully-resolved argparse Namespace: model
profile defaults applied, mode (classification/audit) settings filled in, and
all cross-argument validation enforced.
"""

from __future__ import annotations

import argparse

from .config import (
    AUDIT_CLAIMS_DEFAULT,
    AUDIT_DEFAULT_EXTRACTED,
    AUDIT_DEFAULT_OUTPUT,
    AUDIT_FINAL_NO_TOOLS_MESSAGE,
    AUDIT_PROMPT_FILE,
    AUDIT_RUBRIC_FILE,
    AUDIT_RUNS_DIR_DEFAULT,
    AUDIT_SYSTEM_MESSAGE,
    DEFAULT_EXTRACTED_OUTPUT,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_VLLM_DATASET,
    FINAL_NO_TOOLS_MESSAGE,
    PAPER_BUNDLE_DATASET_URL,
    WEB_SYSTEM_MESSAGE,
    WEB_TOOLS,
)
from .audit_schema import AUDIT_RESPONSE_FORMAT
from .tools.run_dir_tools import AUDIT_TOOLS
from .minimax_defaults import apply_model_defaults
from .trace_io import trace_output_path
from .vllm_cache import default_cache_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int)
    parser.add_argument(
        "--dataset",
        default=DEFAULT_VLLM_DATASET,
        help=(
            "Paper-bundle dataset with LaTeX and OpenReview supplements. "
            f"Default: {PAPER_BUNDLE_DATASET_URL}"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("classification", "audit"),
        default="classification",
        help="classification curates the artifact tier; audit grades an agent reproduction attempt against the rubric.",
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
        "--rubric-file",
        type=argparse_path,
        help="Audit rubric markdown injected into the audit prompt (default: rubric_audit.md).",
    )
    parser.add_argument(
        "--runs-dir",
        type=argparse_path,
        help=(
            "Root directory of agent reproduction runs; the auditor reads one "
            "run dir per paper at <runs-dir>/<arxiv_id> via the read-only "
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
            "Existing vLLM chat-completions server base URL. When set, the "
            "runner skips launching its embedded local server."
        ),
    )
    parser.add_argument(
        "--paper-ids-file",
        type=argparse_path,
        help=(
            "Run only the arXiv ids listed in this file (one per line), e.g. "
            "the output of `python -m reprocli_vllm.rerun select`."
        ),
    )
    parser.add_argument(
        "--hf-repo",
        help=(
            "Hugging Face dataset repo id (e.g. Mithilss/neurips-2025-results). "
            "When set, run outputs are pushed there incrementally and at the end."
        ),
    )
    parser.add_argument(
        "--hf-path-in-repo",
        default="",
        help="Optional subfolder inside the HF repo for the uploaded files.",
    )
    parser.add_argument(
        "--hf-upload-every",
        type=float,
        default=10.0,
        help="Minutes between incremental HF uploads (default: 10).",
    )
    parser.add_argument(
        "--hf-private",
        action="store_true",
        help="Create the HF repo as private when it does not exist yet.",
    )
    parser.add_argument("--vllm-cache-dir", type=argparse_path)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--max-input-tokens", type=int, default=128000)
    parser.add_argument("--tool-rounds", type=int, default=10)
    parser.add_argument("--max-repeated-tool-calls", type=int, default=2)
    parser.add_argument("--request-workers", type=int, default=8)
    parser.add_argument("--tensor-parallel-size", type=int)
    parser.add_argument("--distributed-executor-backend", choices=("mp", "ray"))
    parser.add_argument("--max-model-len", type=int)
    parser.add_argument("--gpu-memory-utilization", type=float)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--tool-call-parser")
    parser.add_argument("--reasoning-parser")
    parser.add_argument("--tokenizer-mode")
    parser.add_argument("--kv-cache-dtype")
    parser.add_argument("--block-size", type=int)
    parser.add_argument("--mm-encoder-tp-mode")
    parser.add_argument("--stream-first-response", action="store_true")
    parser.add_argument("--save-round-jsonl", action="store_true")
    parser.add_argument(
        "--structured-outputs-backend",
        default=None,
        help=(
            "Structured outputs backend for the embedded vLLM server, passed as "
            "--structured-outputs-config.backend (e.g. xgrammar). Defaults to "
            "the server's auto selection."
        ),
    )
    parser.add_argument(
        "--compilation-config",
        default=None,
        help="Optional vLLM compilation JSON override.",
    )
    args = parser.parse_args()
    apply_model_defaults(args)
    resolve_mode_settings(args)
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.num_prompts is not None and args.num_prompts < 1:
        parser.error("--num-prompts must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_repeated_tool_calls < 1:
        parser.error("--max-repeated-tool-calls must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.hf_upload_every <= 0:
        parser.error("--hf-upload-every must be > 0")
    if args.top_k is not None and args.top_k < 1:
        parser.error("--top-k must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within model context")
    if args.vllm_cache_dir is None:
        args.vllm_cache_dir = default_cache_dir(args.model)
    if args.trace_output is None:
        args.trace_output = trace_output_path(args.output)
    return args


def resolve_mode_settings(args: argparse.Namespace) -> None:
    """Fill prompt/output/schema/message defaults for the selected mode."""
    if args.mode == "audit":
        args.prompt_file = args.prompt_file or AUDIT_PROMPT_FILE
        args.rubric_file = args.rubric_file or AUDIT_RUBRIC_FILE
        args.output = args.output or AUDIT_DEFAULT_OUTPUT
        args.extracted_output = args.extracted_output or AUDIT_DEFAULT_EXTRACTED
        args.claims = args.claims or AUDIT_CLAIMS_DEFAULT
        args.runs_dir = args.runs_dir or AUDIT_RUNS_DIR_DEFAULT
        args.response_format = AUDIT_RESPONSE_FORMAT
        args.system_message = AUDIT_SYSTEM_MESSAGE
        args.final_no_tools_message = AUDIT_FINAL_NO_TOOLS_MESSAGE
        # The auditor explores the agent's run directory with read-only tools.
        args.tools = AUDIT_TOOLS
        args.use_tools = True
        return
    args.prompt_file = args.prompt_file or argparse_path("prompt.txt")
    args.output = args.output or DEFAULT_OUTPUT
    args.extracted_output = args.extracted_output or DEFAULT_EXTRACTED_OUTPUT
    args.response_format = None
    args.system_message = WEB_SYSTEM_MESSAGE
    args.final_no_tools_message = FINAL_NO_TOOLS_MESSAGE
    args.tools = WEB_TOOLS
    args.use_tools = True


def argparse_path(value: str):
    from pathlib import Path

    return Path(value)
