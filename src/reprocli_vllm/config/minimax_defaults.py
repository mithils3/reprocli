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


def apply_model_defaults(args: argparse.Namespace) -> None:
    """Fill the request-time length default.

    Sampling is left unset for every model unless the user set it explicitly:
    the request builder omits unset fields, so the served model's own
    generation_config defaults apply (vLLM recipe style).
    """
    args.max_model_len = args.max_model_len or MAX_MODEL_LEN
    args.min_p = getattr(args, "min_p", None)
