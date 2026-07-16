"""Client-side request defaults for the auditor runner.

The auditor is a URL-only client: it only fills the request-time fields it POSTs
to an already-served brain. The vLLM engine/serve-launch flags (tensor parallel,
tool/reasoning parsers, compilation config, kv-cache dtype, ...) are NOT here —
they live in ``reprocli_serve/profiles.py``, the single source of truth for how a
model is served. They died out of this module with the embedded in-process server
(C2).
"""

from __future__ import annotations

import argparse

from reprocli_vllm.config.config import MAX_MODEL_LEN

# Request-time sampling the auditor sends to the served brain (previously the
# client half of the minimax serve profile).
AUDIT_TEMPERATURE = 1.0
AUDIT_TOP_P = 0.95
AUDIT_TOP_K = 40
# Qwen3.6 thinking-mode sampling for precise coding (top_p is 0.95 for both).
QWEN3_TEMPERATURE = 0.6
QWEN3_TOP_K = 20
QWEN3_MIN_P = 0.0


def _is_qwen3(model: str | None) -> bool:
    return bool(model) and "qwen3" in model.lower()


def apply_model_defaults(args: argparse.Namespace) -> None:
    """Fill the request-time sampling/length defaults the auditor POSTs.

    A Qwen3 brain gets its recommended thinking-mode sampling (temp 0.6 / top_k 20 /
    min_p 0.0, top_p unchanged at 0.95) for any field the user did not set explicitly;
    every other model keeps the MiniMax-recommended defaults.
    """
    qwen = _is_qwen3(getattr(args, "model", None))
    args.max_model_len = args.max_model_len or MAX_MODEL_LEN
    if args.temperature is None:
        args.temperature = QWEN3_TEMPERATURE if qwen else AUDIT_TEMPERATURE
    if args.top_p is None:
        args.top_p = AUDIT_TOP_P
    if args.top_k is None:
        args.top_k = QWEN3_TOP_K if qwen else AUDIT_TOP_K
    args.min_p = getattr(args, "min_p", None)
    if args.min_p is None and qwen:
        args.min_p = QWEN3_MIN_P
