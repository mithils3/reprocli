from __future__ import annotations

import argparse
import json

from .config import MAX_MODEL_LEN


COMPILATION_CONFIG = {
    "mode": 3,
    "pass_config": {"fuse_minimax_qk_norm": True},
}


def apply_minimax_defaults(args: argparse.Namespace) -> None:
    args.tensor_parallel_size = args.tensor_parallel_size or 4
    args.max_model_len = args.max_model_len or MAX_MODEL_LEN
    args.gpu_memory_utilization = args.gpu_memory_utilization or 0.98
    args.tool_call_parser = "minimax_m2"
    args.reasoning_parser = "minimax_m2"
    args.tokenizer_mode = None
    args.kv_cache_dtype = None
    args.block_size = None
    args.enable_expert_parallel = False
    args.trust_remote_code = True
    args.temperature = 1.0 if args.temperature is None else args.temperature
    args.top_p = 0.95 if args.top_p is None else args.top_p
    args.top_k = 40 if args.top_k is None else args.top_k
    if args.compilation_config is None:
        args.compilation_config = json.dumps(COMPILATION_CONFIG, separators=(",", ":"))
