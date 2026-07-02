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


def apply_model_defaults(args: argparse.Namespace) -> None:
    """Fill the request-time sampling/length defaults the auditor POSTs."""
    args.max_model_len = args.max_model_len or MAX_MODEL_LEN
    args.temperature = AUDIT_TEMPERATURE if args.temperature is None else args.temperature
    args.top_p = AUDIT_TOP_P if args.top_p is None else args.top_p
    args.top_k = AUDIT_TOP_K if args.top_k is None else args.top_k
