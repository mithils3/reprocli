from __future__ import annotations

import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.vllm import client
from reprocli_vllm.vllm.endpoint import ENV_API_KEY, ENV_EXTRA_BODY, ENV_OPENROUTER_PROVIDER

JSON_SCHEMA_RF = {
    "type": "json_schema",
    "json_schema": {"name": "v", "schema": {"type": "object"}},
}


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

        def _fake_post(base_url, body, timeout, *, overlay_fields=()):
            seen["body"] = body
            return {"choices": []}

        with patch.dict("os.environ", {ENV_OPENROUTER_PROVIDER: "deepseek"}, clear=True):
            with patch.object(client, "post_vllm_chat_completion", _fake_post):
                client.post_chat_completion_row("http://h:8000", row, 1.0)

        self.assertEqual(
            seen["body"]["provider"], {"order": ["deepseek"], "allow_fallbacks": False}
        )


def _http_error(code: int, body: bytes) -> urllib.error.HTTPError:
    exc = urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(body))
    exc.reprocli_body = body.decode()  # what retry.annotate_http_error stashes
    return exc


class PrepareStructuredOutputTests(unittest.TestCase):
    def test_marks_strict_and_requires_parameters_with_key(self) -> None:
        body = {"response_format": JSON_SCHEMA_RF}
        with patch.dict("os.environ", {ENV_API_KEY: "sk-test"}, clear=True):
            client.prepare_structured_output(body)
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        self.assertTrue(body["provider"]["require_parameters"])
        # the shared response_format constant must not be mutated in place
        self.assertNotIn("strict", JSON_SCHEMA_RF["json_schema"])

    def test_noop_without_api_key(self) -> None:
        body = {"response_format": JSON_SCHEMA_RF}
        with patch.dict("os.environ", {}, clear=True):
            client.prepare_structured_output(body)
        self.assertNotIn("provider", body)
        self.assertNotIn("strict", body["response_format"]["json_schema"])

    def test_noop_for_non_json_schema(self) -> None:
        body = {"response_format": {"type": "json_object"}}
        with patch.dict("os.environ", {ENV_API_KEY: "sk-test"}, clear=True):
            client.prepare_structured_output(body)
        self.assertNotIn("provider", body)


class DowngradeResponseFormatTests(unittest.TestCase):
    def test_downgrades_on_provider_reject_400(self) -> None:
        body = {"response_format": JSON_SCHEMA_RF, "provider": {"require_parameters": True}}
        exc = _http_error(400, b'{"error":{"message":"This response_format type is unavailable now"}}')
        out = client.downgrade_response_format_on_reject(body, exc)
        self.assertEqual(out["response_format"], {"type": "json_object"})
        self.assertNotIn("provider", out)  # require_parameters dropped, block emptied

    def test_downgrades_on_no_capable_provider_404(self) -> None:
        body = {"response_format": JSON_SCHEMA_RF, "provider": {"require_parameters": True}}
        exc = _http_error(404, b'{"error":{"message":"No endpoints found that can handle the requested parameters"}}')
        out = client.downgrade_response_format_on_reject(body, exc)
        self.assertEqual(out["response_format"], {"type": "json_object"})

    def test_keeps_pinned_provider_order_on_downgrade(self) -> None:
        body = {
            "response_format": JSON_SCHEMA_RF,
            "provider": {"order": ["deepseek"], "require_parameters": True},
        }
        exc = _http_error(404, b"No allowed providers are available")
        out = client.downgrade_response_format_on_reject(body, exc)
        self.assertEqual(out["provider"], {"order": ["deepseek"]})

    def test_no_downgrade_for_unrelated_400(self) -> None:
        body = {"response_format": JSON_SCHEMA_RF}
        exc = _http_error(400, b'{"error":{"message":"context length exceeded"}}')
        self.assertIsNone(client.downgrade_response_format_on_reject(body, exc))

    def test_no_downgrade_when_no_json_schema(self) -> None:
        body = {"response_format": {"type": "json_object"}}
        exc = _http_error(400, b"This response_format type is unavailable now")
        self.assertIsNone(client.downgrade_response_format_on_reject(body, exc))


ANTHROPIC_OVERLAY = (
    '{"thinking": {"type": "adaptive"}, "output_config": {"effort": "high"},'
    ' "truncate_prompt_tokens": null}'
)


class ApplyBodyOverlayTests(unittest.TestCase):
    def test_noop_when_unset(self) -> None:
        body = {"model": "m", "truncate_prompt_tokens": 128000}
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(client.apply_body_overlay(body), [])
        self.assertEqual(body["truncate_prompt_tokens"], 128000)

    def test_adds_provider_fields_and_deletes_nulled_ones(self) -> None:
        body = {"model": "claude-opus-4-8", "truncate_prompt_tokens": 128000}
        with patch.dict("os.environ", {ENV_EXTRA_BODY: ANTHROPIC_OVERLAY}, clear=True):
            added = client.apply_body_overlay(body)
        self.assertEqual(body["thinking"], {"type": "adaptive"})
        self.assertEqual(body["output_config"], {"effort": "high"})
        self.assertNotIn("truncate_prompt_tokens", body)  # vLLM-only field, deleted
        self.assertEqual(sorted(added), ["output_config", "thinking"])  # deletions aren't "added"

    def test_row_body_is_overlaid_before_post(self) -> None:
        row = {"custom_id": "c1", "body": {"model": "m", "messages": []}}
        seen: dict = {}

        def _fake_post(base_url, body, timeout, *, overlay_fields=()):
            seen.update(body=body, overlay_fields=overlay_fields)
            return {"choices": []}

        with patch.dict("os.environ", {ENV_EXTRA_BODY: ANTHROPIC_OVERLAY}, clear=True):
            with patch.object(client, "post_vllm_chat_completion", _fake_post):
                client.post_chat_completion_row("https://api.anthropic.com", row, 1.0)

        self.assertEqual(seen["body"]["thinking"], {"type": "adaptive"})
        self.assertEqual(sorted(seen["overlay_fields"]), ["output_config", "thinking"])


class DropRejectedOverlayFieldsTests(unittest.TestCase):
    def test_drops_the_field_the_error_names(self) -> None:
        body = {"model": "m", "thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}}
        exc = _http_error(400, b'{"error":{"message":"unexpected parameter: output_config"}}')
        out, dropped = client.drop_rejected_overlay_fields(
            body, exc, ["thinking", "output_config"]
        )
        self.assertEqual(dropped, ["output_config"])
        self.assertNotIn("output_config", out)
        self.assertIn("thinking", out)  # only what the endpoint complained about

    def test_no_retry_for_unrelated_400(self) -> None:
        body = {"model": "m", "thinking": {"type": "adaptive"}}
        exc = _http_error(400, b'{"error":{"message":"context length exceeded"}}')
        self.assertEqual(client.drop_rejected_overlay_fields(body, exc, ["thinking"]), (None, []))

    def test_no_retry_for_non_400(self) -> None:
        body = {"model": "m", "thinking": {"type": "adaptive"}}
        exc = _http_error(500, b"thinking is broken upstream")
        self.assertEqual(client.drop_rejected_overlay_fields(body, exc, ["thinking"]), (None, []))

    def test_no_retry_without_overlay(self) -> None:
        body = {"model": "m"}
        exc = _http_error(400, b"thinking")
        self.assertEqual(client.drop_rejected_overlay_fields(body, exc, []), (None, []))


if __name__ == "__main__":
    unittest.main()
