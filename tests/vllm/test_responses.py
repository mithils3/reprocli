from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.runtime.trace_io import assistant_message
from reprocli_vllm.vllm import client
from reprocli_vllm.vllm.io import response_message
from reprocli_vllm.vllm.responses import (
    REASONING_KEY,
    request_to_responses,
    response_to_chat,
    strip_openai_private,
)

OPENAI = "https://api.openai.com/v1"
REASONING_ITEM = {"id": "rs_1", "type": "reasoning", "summary": [], "encrypted_content": "enc=="}
BASH_TOOL = {"type": "function", "function": {
    "name": "bash", "description": "run a command",
    "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}},
}}


class _Ok:
    def __init__(self, payload: dict) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Ok":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _responses_object() -> dict:
    return {
        "id": "resp_1",
        "model": "gpt-6.1-terra",
        "status": "completed",
        "service_tier": "flex",
        "output": [
            REASONING_ITEM,
            {"type": "function_call", "id": "fc_1", "call_id": "call_abc",
             "name": "bash", "arguments": "{\"cmd\": \"echo hi\"}", "status": "completed"},
        ],
        "usage": {
            "input_tokens": 1200, "input_tokens_details": {"cached_tokens": 1000},
            "output_tokens": 300, "output_tokens_details": {"reasoning_tokens": 250},
            "total_tokens": 1500,
        },
    }


class RequestTranslationTests(unittest.TestCase):
    def test_system_becomes_instructions_and_messages_map(self) -> None:
        body = {"model": "gpt-6.1-terra", "messages": [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
        ]}
        out = request_to_responses(body)
        self.assertEqual(out["instructions"], "be terse")
        self.assertEqual(out["input"], [{"role": "user", "content": "hi"}])
        self.assertEqual(out["store"], False)
        self.assertEqual(out["include"], ["reasoning.encrypted_content"])

    def test_tool_round_maps_function_call_and_output(self) -> None:
        body = {"model": "m", "messages": [
            {"role": "assistant", "tool_calls": [{"id": "call_abc", "type": "function",
             "function": {"name": "bash", "arguments": "{\"cmd\": \"echo hi\"}"}}]},
            {"role": "tool", "tool_call_id": "call_abc", "content": "hi\n"},
        ]}
        out = request_to_responses(body)
        self.assertEqual(out["input"][0], {"type": "function_call", "call_id": "call_abc",
                                           "name": "bash", "arguments": "{\"cmd\": \"echo hi\"}"})
        self.assertEqual(out["input"][1], {"type": "function_call_output",
                                           "call_id": "call_abc", "output": "hi\n"})

    def test_tools_tool_choice_limits_effort_and_format(self) -> None:
        body = {
            "model": "m", "messages": [], "tools": [BASH_TOOL],
            "tool_choice": {"type": "function", "function": {"name": "bash"}},
            "max_completion_tokens": 4096, "reasoning_effort": "high",
            "service_tier": "flex",
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "report", "schema": {"type": "object"}}},
        }
        out = request_to_responses(body)
        self.assertEqual(out["tools"][0]["name"], "bash")
        self.assertEqual(out["tools"][0]["parameters"]["type"], "object")
        self.assertNotIn("function", out["tools"][0])
        self.assertEqual(out["tool_choice"], {"type": "function", "name": "bash"})
        self.assertEqual(out["max_output_tokens"], 4096)
        self.assertEqual(out["reasoning"], {"effort": "high"})
        self.assertEqual(out["service_tier"], "flex")
        self.assertEqual(out["text"]["format"], {"type": "json_schema", "name": "report",
                                                 "schema": {"type": "object"}, "strict": False})

    def test_reasoning_items_precede_that_turns_function_calls(self) -> None:
        body = {"model": "m", "messages": [
            {"role": "assistant", REASONING_KEY: [REASONING_ITEM],
             "tool_calls": [{"id": "call_abc", "function": {"name": "bash", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_abc", "content": "ok"},
        ]}
        kinds = [item.get("type") for item in request_to_responses(body)["input"]]
        self.assertEqual(kinds, ["reasoning", "function_call", "function_call_output"])
        self.assertEqual(request_to_responses(body)["input"][0], REASONING_ITEM)

    def test_strip_removes_private_keys_for_other_providers(self) -> None:
        messages = [{"role": "assistant", "content": "x", REASONING_KEY: [REASONING_ITEM]}]
        stripped = strip_openai_private(messages)
        self.assertEqual(stripped, [{"role": "assistant", "content": "x"}])
        self.assertIn(REASONING_KEY, messages[0])


class ResponseTranslationTests(unittest.TestCase):
    def test_function_call_becomes_tool_calls_with_call_id(self) -> None:
        message = response_to_chat(_responses_object())["choices"][0]["message"]
        self.assertEqual(message["tool_calls"], [{"id": "call_abc", "type": "function",
             "function": {"name": "bash", "arguments": "{\"cmd\": \"echo hi\"}"}}])
        self.assertEqual(message[REASONING_KEY], [REASONING_ITEM])

    def test_text_output_and_finish_reasons(self) -> None:
        text = {"status": "completed", "output": [
            {"type": "message", "role": "assistant",
             "content": [{"type": "output_text", "text": "{\"status\":\"ok\"}"}]}]}
        chat = response_to_chat(text)
        self.assertEqual(chat["choices"][0]["message"]["content"], "{\"status\":\"ok\"}")
        self.assertEqual(chat["choices"][0]["finish_reason"], "stop")
        cut = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"},
               "output": []}
        self.assertEqual(response_to_chat(cut)["choices"][0]["finish_reason"], "length")

    def test_usage_and_service_tier_map(self) -> None:
        chat = response_to_chat(_responses_object())
        self.assertEqual(chat["usage"]["prompt_tokens"], 1200)
        self.assertEqual(chat["usage"]["prompt_tokens_details"]["cached_tokens"], 1000)
        self.assertEqual(chat["usage"]["completion_tokens"], 300)
        self.assertEqual(chat["usage"]["completion_tokens_details"]["reasoning_tokens"], 250)
        self.assertEqual(chat["service_tier"], "flex")


class ReasoningCarryOverTests(unittest.TestCase):
    def test_round_trip_through_loop_message_keeps_reasoning(self) -> None:
        row = {"response": {"body": response_to_chat(_responses_object())}}
        message = response_message(row)
        tool_calls = message["tool_calls"]
        stored = assistant_message(message, tool_calls)
        self.assertEqual(stored[REASONING_KEY], [REASONING_ITEM])
        next_request = request_to_responses({"model": "m", "messages": [
            stored,
            {"role": "tool", "tool_call_id": "call_abc", "content": "hi"},
        ]})
        kinds = [item.get("type") for item in next_request["input"]]
        self.assertEqual(kinds, ["reasoning", "function_call", "function_call_output"])

    def test_plain_assistant_message_without_key_is_unchanged(self) -> None:
        stored = assistant_message({"content": "done"}, [])
        self.assertNotIn(REASONING_KEY, stored)


class OpenAIPostPathTests(unittest.TestCase):
    def test_row_goes_to_responses_and_returns_chat_shape(self) -> None:
        row = {"body": {"model": "gpt-6.1-terra", "messages": [
            {"role": "user", "content": "run echo hi"}], "tools": [BASH_TOOL],
            "max_tokens": 4096, "truncate_prompt_tokens": 8192, "reasoning_effort": "high"}}
        env = {"REPROCLI_SERVICE_TIER": "flex", "REPROCLI_NO_TRUNCATE_PROMPT": "1"}
        with patch.dict("os.environ", env, clear=True), \
                patch.object(client.urllib.request, "urlopen",
                             return_value=_Ok(_responses_object())) as urlopen:
            chat = client.post_chat_completion_row(OPENAI, row, 30.0)
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/v1/responses"))
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent["service_tier"], "flex")
        self.assertEqual(sent["reasoning"], {"effort": "high"})
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 900.0)
        self.assertEqual(chat["choices"][0]["message"]["tool_calls"][0]["id"], "call_abc")

    def test_flex_429_then_success_on_responses_path(self) -> None:
        import urllib.error
        row = {"body": {"model": "m", "messages": [{"role": "user", "content": "x"}]}}
        calls = [urllib.error.HTTPError(OPENAI, 429, "busy", None, None), _Ok(_responses_object())]
        env = {"REPROCLI_SERVICE_TIER": "flex"}
        with patch.dict("os.environ", env, clear=True), \
                patch.object(client.urllib.request, "urlopen", side_effect=calls), \
                patch("reprocli_vllm.vllm.flex.time") as clock, \
                redirect_stderr(io.StringIO()):
            clock.monotonic.side_effect = [0.0]
            chat = client.post_chat_completion_row(OPENAI, row, 30.0)
        self.assertEqual(chat["usage"]["prompt_tokens"], 1200)
        clock.sleep.assert_called_once_with(15.0)

    def test_non_openai_keeps_chat_path_and_strips_private_keys(self) -> None:
        row = {"body": {"model": "m", "messages": [
            {"role": "assistant", REASONING_KEY: [REASONING_ITEM], "content": "x"}]}}
        with patch.object(client, "post_vllm_chat_completion",
                          side_effect=lambda url, body, t: body) as post:
            client.post_chat_completion_row("http://gh001:8000", row, 1.0)
        sent = post.call_args.args[1]
        self.assertEqual(sent["messages"], [{"role": "assistant", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
