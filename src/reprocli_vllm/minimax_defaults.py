from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import KIMI_K2_6_MODEL, MAX_MODEL_LEN


MINIMAX_COMPILATION_CONFIG = {"cudagraph_mode": "PIECEWISE"}


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
    if model == KIMI_K2_6_MODEL or model.rstrip("/").endswith("/Kimi-K2.6"):
        return True
    config_path = Path(model) / "config.json"
    if not config_path.exists():
        return False
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    architectures = config.get("architectures") or []
    return any(str(name).startswith("KimiK25") for name in architectures)
