from __future__ import annotations

import argparse
import json

from .config import KIMI_K2_6_MODEL, MAX_MODEL_LEN


MINIMAX_COMPILATION_CONFIG = {"cudagraph_mode": "PIECEWISE"}


def apply_minimax_defaults(args: argparse.Namespace) -> None:
    apply_model_defaults(args)


def apply_model_defaults(args: argparse.Namespace) -> None:
    if is_kimi_k2_6(args.model):
        apply_kimi_defaults(args)
        return
    apply_minimax_profile(args)


def apply_minimax_profile(args: argparse.Namespace) -> None:
    args.tensor_parallel_size = args.tensor_parallel_size or 4
    args.max_model_len = args.max_model_len or MAX_MODEL_LEN
    args.gpu_memory_utilization = args.gpu_memory_utilization or 0.95
    args.tool_call_parser = args.tool_call_parser or "minimax_m2"
    args.reasoning_parser = args.reasoning_parser or "minimax_m2"
    args.tokenizer_mode = args.tokenizer_mode or None
    args.kv_cache_dtype = args.kv_cache_dtype or None
    args.block_size = args.block_size or None
    args.mm_encoder_tp_mode = args.mm_encoder_tp_mode or None
    args.enable_expert_parallel = False
    args.trust_remote_code = True
    args.temperature = 1.0 if args.temperature is None else args.temperature
    args.top_p = 0.95 if args.top_p is None else args.top_p
    args.top_k = 40 if args.top_k is None else args.top_k
    if args.compilation_config is None:
        args.compilation_config = json.dumps(MINIMAX_COMPILATION_CONFIG, separators=(",", ":"))


def apply_kimi_defaults(args: argparse.Namespace) -> None:
    args.tensor_parallel_size = args.tensor_parallel_size or 8
    args.max_model_len = args.max_model_len or MAX_MODEL_LEN
    args.gpu_memory_utilization = args.gpu_memory_utilization or 0.95
    args.tool_call_parser = args.tool_call_parser or "kimi_k2"
    args.reasoning_parser = args.reasoning_parser or "kimi_k2"
    args.mm_encoder_tp_mode = args.mm_encoder_tp_mode or "data"
    args.trust_remote_code = True


def is_kimi_k2_6(model: str) -> bool:
    return model == KIMI_K2_6_MODEL or model.rstrip("/").endswith("/Kimi-K2.6")
