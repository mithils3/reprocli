from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cli_resolve import (
    QWEN3_MIN_P,
    QWEN3_TEMPERATURE,
    QWEN3_TOP_K,
    TEMPERATURE,
    TOP_K,
    apply_sampling_for_model,
)


def _args() -> argparse.Namespace:
    # The MiniMax-recommended defaults apply_defaults resolves onto the namespace.
    return argparse.Namespace(temperature=TEMPERATURE, top_p=0.95, top_k=TOP_K, min_p=None)


def test_qwen3_model_switches_sampling():
    args = _args()
    apply_sampling_for_model(args, "Qwen/Qwen3.6-27B-FP8")
    assert args.temperature == QWEN3_TEMPERATURE
    assert args.top_k == QWEN3_TOP_K
    assert args.min_p == QWEN3_MIN_P
    assert args.top_p == 0.95  # top_p is unchanged


def test_minimax_model_keeps_defaults():
    args = _args()
    apply_sampling_for_model(args, "MiniMaxAI/MiniMax-M2.7")
    assert args.temperature == TEMPERATURE
    assert args.top_k == TOP_K
    assert args.min_p is None


def test_none_model_keeps_defaults():
    args = _args()
    apply_sampling_for_model(args, None)
    assert args.temperature == TEMPERATURE
    assert args.top_k == TOP_K
    assert args.min_p is None
