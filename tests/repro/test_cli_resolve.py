from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cli_resolve import (
    QWEN3_MIN_P,
    QWEN3_TEMPERATURE,
    QWEN3_TOP_K,
    QWEN3_TOP_P,
    apply_sampling_for_model,
)


def _args() -> argparse.Namespace:
    # apply_defaults leaves sampling unset: requests omit the fields, so the
    # served model's generation_config defaults apply.
    return argparse.Namespace(temperature=None, top_p=None, top_k=None, min_p=None)


def test_qwen3_model_pins_sampling():
    args = _args()
    apply_sampling_for_model(args, "Qwen/Qwen3.6-27B-FP8")
    assert args.temperature == QWEN3_TEMPERATURE
    assert args.top_p == QWEN3_TOP_P
    assert args.top_k == QWEN3_TOP_K
    assert args.min_p == QWEN3_MIN_P


def test_minimax_model_keeps_sampling_unset():
    args = _args()
    apply_sampling_for_model(args, "MiniMaxAI/MiniMax-M2.7")
    assert args.temperature is None
    assert args.top_p is None
    assert args.top_k is None
    assert args.min_p is None


def test_none_model_keeps_sampling_unset():
    args = _args()
    apply_sampling_for_model(args, None)
    assert args.temperature is None
    assert args.top_p is None
    assert args.top_k is None
    assert args.min_p is None
