from __future__ import annotations

import io
import json
import socket
import sys
import unittest
import urllib.error
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.vllm import client, flex
from reprocli_vllm.vllm.endpoint import is_openai

OPENAI = "https://api.openai.com/v1"


class _Ok:
    def __init__(self, payload: dict) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Ok":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(f"{OPENAI}/chat/completions", code, "err", None, None)


def _sent_bodies(urlopen: MagicMock) -> list[dict]:
    return [json.loads(call.args[0].data.decode("utf-8")) for call in urlopen.call_args_list]


def _sent_timeouts(urlopen: MagicMock) -> list[float]:
    return [call.kwargs["timeout"] for call in urlopen.call_args_list]


def _flex_body() -> dict:
    return {"model": "gpt-6.1-terra", "messages": [], "service_tier": "flex"}


class ServiceTierEnvTests(unittest.TestCase):
    def test_unset_adds_nothing(self) -> None:
        body = {"model": "m"}
        with patch.dict("os.environ", {}, clear=True):
            flex.apply_service_tier(body)
        self.assertNotIn("service_tier", body)

    def test_flex_is_added_to_every_chat_body(self) -> None:
        body = {"model": "m"}
        with patch.dict("os.environ", {"REPROCLI_SERVICE_TIER": "flex"}, clear=True):
            flex.apply_service_tier(body)
        self.assertEqual(body["service_tier"], "flex")

    def test_body_value_wins(self) -> None:
        body = {"service_tier": "auto"}
        with patch.dict("os.environ", {"REPROCLI_SERVICE_TIER": "flex"}, clear=True):
            flex.apply_service_tier(body)
        self.assertEqual(body["service_tier"], "auto")

    def test_post_chat_completion_row_carries_tier(self) -> None:
        row = {"body": {"model": "gpt-6.1-terra", "messages": []}}
        with patch.dict("os.environ", {"REPROCLI_SERVICE_TIER": "flex"}, clear=True), \
                patch.object(client, "post_vllm_chat_completion",
                             side_effect=lambda url, body, t: body) as post:
            client.post_chat_completion_row(OPENAI, row, 30.0)
        self.assertEqual(post.call_args.args[1]["service_tier"], "flex")


class FlexTimeoutTests(unittest.TestCase):
    def test_flex_read_timeout_is_at_least_900(self) -> None:
        self.assertEqual(flex.read_timeout(300.0, _flex_body()), 900.0)
        self.assertEqual(flex.read_timeout(1800.0, _flex_body()), 1800.0)

    def test_standard_timeout_unchanged(self) -> None:
        self.assertEqual(flex.read_timeout(300.0, {"model": "m"}), 300.0)

    def test_flex_post_uses_900_second_socket_timeout(self) -> None:
        with patch.object(client.urllib.request, "urlopen", return_value=_Ok({"ok": 1})) as urlopen:
            client._post_body(OPENAI, _flex_body(), 30.0)
        self.assertEqual(_sent_timeouts(urlopen), [900.0])


class FlexRetryTests(unittest.TestCase):
    def test_429_then_success_backs_off_15_then_30(self) -> None:
        responses = [_http(429), _http(429), _Ok({"choices": []})]
        with patch.object(client.urllib.request, "urlopen", side_effect=responses) as urlopen, \
                patch("reprocli_vllm.vllm.flex.time") as clock_mod, \
                redirect_stderr(io.StringIO()):
            clock_mod.monotonic.side_effect = [0.0, 15.0]
            result = client._post_body(OPENAI, _flex_body(), 30.0)
        self.assertEqual(result, {"choices": []})
        self.assertEqual([c.args[0] for c in clock_mod.sleep.call_args_list], [15.0, 30.0])
        self.assertEqual(urlopen.call_count, 3)
        self.assertTrue(all(b["service_tier"] == "flex" for b in _sent_bodies(urlopen)))

    def test_read_timeout_is_retried(self) -> None:
        responses = [socket.timeout("read timed out"), _Ok({"ok": True})]
        with patch.object(client.urllib.request, "urlopen", side_effect=responses), \
                patch("reprocli_vllm.vllm.flex.time") as clock_mod, \
                redirect_stderr(io.StringIO()):
            clock_mod.monotonic.side_effect = [0.0]
            result = client._post_body(OPENAI, _flex_body(), 30.0)
        self.assertEqual(result, {"ok": True})
        clock_mod.sleep.assert_called_once_with(15.0)

    def test_400_is_not_retried_on_flex(self) -> None:
        with patch.object(client.urllib.request, "urlopen", side_effect=_http(400)) as urlopen, \
                patch("reprocli_vllm.vllm.flex.time") as clock_mod:
            with self.assertRaises(urllib.error.HTTPError):
                client._post_body(OPENAI, _flex_body(), 30.0)
        self.assertEqual(urlopen.call_count, 1)
        clock_mod.sleep.assert_not_called()

    def test_budget_exhausted_falls_back_to_standard_without_tier(self) -> None:
        now = {"t": 0.0}

        def sleep(seconds: float) -> None:
            now["t"] += seconds

        def monotonic() -> float:
            return now["t"]

        def urlopen_side_effect(request, timeout):
            if json.loads(request.data.decode("utf-8")).get("service_tier") == "flex":
                raise _http(429)
            return _Ok({"fallback": True})

        stderr = io.StringIO()
        with patch.object(client.urllib.request, "urlopen", side_effect=urlopen_side_effect) as urlopen, \
                patch("reprocli_vllm.vllm.flex.time") as clock_mod, \
                redirect_stderr(stderr):
            clock_mod.sleep.side_effect = sleep
            clock_mod.monotonic.side_effect = monotonic
            result = client._post_body(OPENAI, _flex_body(), 30.0)
        self.assertEqual(result, {"fallback": True})
        self.assertIn("flex-fallback", stderr.getvalue())
        self.assertLessEqual(sum(c.args[0] for c in clock_mod.sleep.call_args_list), 600.0)
        bodies = _sent_bodies(urlopen)
        self.assertEqual(bodies[-1].get("service_tier"), None)
        self.assertEqual(_sent_timeouts(urlopen)[-1], 30.0)


class OpenAIBodyShapeTests(unittest.TestCase):
    def _vllm_body(self) -> dict:
        return {
            "model": "gpt-6.1-terra",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 4096,
            "truncate_prompt_tokens": 8192,
            "top_k": 20,
            "chat_template_kwargs": {"enable_thinking": True},
            "provider": {"require_parameters": True},
            "repetition_penalty": 1.1,
            "reasoning_effort": "high",
            "tools": [{"type": "function", "function": {"name": "t"}}],
            "tool_choice": "auto",
        }

    def test_openai_gets_max_completion_tokens_and_no_vllm_fields(self) -> None:
        body = self._vllm_body()
        client.apply_openai_body_shape(body, OPENAI)
        self.assertNotIn("max_tokens", body)
        self.assertEqual(body["max_completion_tokens"], 4096)
        for key in ("truncate_prompt_tokens", "top_k", "chat_template_kwargs",
                    "provider", "repetition_penalty"):
            self.assertNotIn(key, body)
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertEqual(body["tool_choice"], "auto")

    def test_other_hosts_keep_every_field(self) -> None:
        for base in ("http://gh001:8000", "https://openrouter.ai/api/v1"):
            body = self._vllm_body()
            client.apply_openai_body_shape(body, base)
            self.assertEqual(body["max_tokens"], 4096)
            self.assertIn("top_k", body)
            self.assertNotIn("max_completion_tokens", body)

    def test_is_openai_checks_host(self) -> None:
        self.assertTrue(is_openai(OPENAI))
        self.assertFalse(is_openai("https://api.openai.com.example.org/v1"))
        self.assertFalse(is_openai("https://api.meta.ai/v1"))

    def test_full_row_path_on_openai(self) -> None:
        row = {"body": self._vllm_body()}
        env = {"REPROCLI_SERVICE_TIER": "flex", "REPROCLI_NO_TRUNCATE_PROMPT": "1",
               "REPROCLI_REASONING_EFFORT": "high"}
        with patch.dict("os.environ", env, clear=True), \
                patch.object(client, "post_vllm_chat_completion",
                             side_effect=lambda url, body, t: body) as post:
            client.post_chat_completion_row(OPENAI, row, 30.0)
            sent = post.call_args.args[1]
        self.assertEqual(sent["service_tier"], "flex")
        self.assertEqual(sent["max_completion_tokens"], 4096)
        self.assertNotIn("truncate_prompt_tokens", sent)
        self.assertNotIn("max_tokens", sent)


if __name__ == "__main__":
    unittest.main()
