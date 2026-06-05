from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.batch_io import build_batch_request
from reprocli_vllm.output_schema import FINAL_RESPONSE_FORMAT


def args(**overrides):
    defaults = {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 40,
        "max_tokens": 8192,
        "max_input_tokens": 128000,
        "chat_template_kwargs": None,
        "disable_structured_final_output": False,
        "guided_decoding_backend": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class VllmBatchRequestTests(unittest.TestCase):
    def test_final_request_uses_response_format(self) -> None:
        request = build_batch_request(
            "model",
            "2501.00001",
            [{"role": "user", "content": "prompt"}],
            args(guided_decoding_backend="xgrammar:no-fallback"),
            include_tools=False,
        )

        body = request["body"]
        self.assertEqual(body["response_format"], FINAL_RESPONSE_FORMAT)
        # The request-level guided fields were removed in vLLM 0.12.0; the
        # backend is now selected at server startup, never in the request body.
        self.assertNotIn("guided_json", body)
        self.assertNotIn("guided_decoding_backend", body)
        self.assertNotIn("tools", body)

    def test_structured_final_output_can_be_disabled(self) -> None:
        request = build_batch_request(
            "model",
            "2501.00001",
            [{"role": "user", "content": "prompt"}],
            args(disable_structured_final_output=True),
            include_tools=False,
        )

        self.assertNotIn("response_format", request["body"])

    def test_tool_request_does_not_use_response_format(self) -> None:
        request = build_batch_request(
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
