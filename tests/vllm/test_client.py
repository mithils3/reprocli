from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.vllm import client
from reprocli_vllm.vllm.endpoint import ENV_OPENROUTER_PROVIDER


class ApplyProviderRoutingTests(unittest.TestCase):
    def test_noop_when_unset(self) -> None:
        body = {"model": "deepseek/deepseek-v4-pro", "messages": []}
        with patch.dict("os.environ", {}, clear=True):
            client.apply_provider_routing(body)
        self.assertNotIn("provider", body)

    def test_pins_provider_when_set(self) -> None:
        body = {"model": "deepseek/deepseek-v4-pro", "messages": []}
        with patch.dict("os.environ", {ENV_OPENROUTER_PROVIDER: "deepseek"}, clear=True):
            client.apply_provider_routing(body)
        self.assertEqual(body["provider"], {"order": ["deepseek"], "allow_fallbacks": False})

    def test_does_not_clobber_existing_provider(self) -> None:
        body = {"provider": {"order": ["novita"]}}
        with patch.dict("os.environ", {ENV_OPENROUTER_PROVIDER: "deepseek"}, clear=True):
            client.apply_provider_routing(body)
        self.assertEqual(body["provider"], {"order": ["novita"]})


class PostRowInjectsProviderTests(unittest.TestCase):
    def test_row_body_is_pinned_before_post(self) -> None:
        row = {"custom_id": "c1", "body": {"model": "m", "messages": []}}
        seen: dict = {}

        def _fake_post(base_url, body, timeout):
            seen["body"] = body
            return {"choices": []}

        with patch.dict("os.environ", {ENV_OPENROUTER_PROVIDER: "deepseek"}, clear=True):
            with patch.object(client, "post_vllm_chat_completion", _fake_post):
                client.post_chat_completion_row("http://h:8000", row, 1.0)

        self.assertEqual(
            seen["body"]["provider"], {"order": ["deepseek"], "allow_fallbacks": False}
        )


if __name__ == "__main__":
    unittest.main()
