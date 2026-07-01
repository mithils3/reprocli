from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.vllm.io import build_chat_completion_request
from reprocli_vllm.schema.output import FINAL_RESPONSE_FORMAT


def args(**overrides):
    defaults = {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 40,
        "max_tokens": 8192,
        "max_input_tokens": 128000,
        # build_chat_completion_request reads these directly (no fallback): every
        # real arg namespace (repro cli_resolve, vllm cli_args) always sets them.
        "tools": [{"type": "function", "function": {"name": "dummy_tool"}}],
        "response_format": FINAL_RESPONSE_FORMAT,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class VllmBatchRequestTests(unittest.TestCase):
    def test_final_request_uses_response_format(self) -> None:
        request = build_chat_completion_request(
            "model",
            "2501.00001",
            [{"role": "user", "content": "prompt"}],
            args(),
            include_tools=False,
        )

        body = request["body"]
        self.assertEqual(body["response_format"], FINAL_RESPONSE_FORMAT)
        self.assertNotIn("tools", body)

    def test_tool_request_does_not_use_response_format(self) -> None:
        request = build_chat_completion_request(
            "model",
            "2501.00001",
            [{"role": "user", "content": "prompt"}],
            args(),
            include_tools=True,
        )

        self.assertIn("tools", request["body"])
        self.assertNotIn("response_format", request["body"])


if __name__ == "__main__":
    unittest.main()
