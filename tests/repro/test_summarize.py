from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import summarize
from reprocli_repro.summarize import (
    accumulate_files,
    choose_cut,
    serialize_span,
    summarize_compact,
)


def _args() -> SimpleNamespace:
    return SimpleNamespace(top_p=0.95, max_tokens=8192, max_input_tokens=128000)


def _write_call(path: str) -> dict:
    return {
        "id": "c1",
        "function": {"name": "write_file", "arguments": json.dumps({"path": path, "content": "x"})},
    }


def _bash_call() -> dict:
    return {"id": "c2", "function": {"name": "workspace_bash", "arguments": json.dumps({"command": "ls"})}}


def _tool(content: str, call_id: str = "c1") -> dict:
    return {"role": "tool", "tool_call_id": call_id, "name": "t", "content": content}


def _conversation() -> list[dict]:
    # system, big user prompt, write_file turn, bash turn, final assistant.
    return [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U" * 200},
        {"role": "assistant", "content": "writing", "tool_calls": [_write_call("b.py")]},
        _tool("T" * 200, "c1"),
        {"role": "assistant", "content": "running", "tool_calls": [_bash_call()]},
        _tool("R" * 200, "c2"),
        {"role": "assistant", "content": "x"},
    ]


def _fake_summary(text: str):
    def _post(base_url, request, timeout):
        return {"choices": [{"message": {"content": text}}]}

    return _post


class ChooseCutTests(unittest.TestCase):
    def test_noop_when_everything_fits_in_keep_window(self):
        messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "hi"}]
        self.assertLessEqual(choose_cut(messages, keep_recent_tokens=10_000), 1)

    def test_never_starts_tail_on_a_tool_result(self):
        messages = _conversation()
        # Tiny keep window so the raw token-walk would stop on a tool result; the
        # snap rule must back the cut onto the assistant that owns it.
        cut = choose_cut(messages, keep_recent_tokens=10)
        self.assertGreater(cut, 1)
        self.assertNotEqual(messages[cut]["role"], "tool")

    def test_tail_keeps_tool_calls_with_their_results(self):
        messages = _conversation()
        cut = choose_cut(messages, keep_recent_tokens=10)
        tail = messages[cut:]
        # Every assistant tool_call id in the tail must have its tool result in the tail.
        result_ids = {m.get("tool_call_id") for m in tail if m.get("role") == "tool"}
        for m in tail:
            for call in m.get("tool_calls") or []:
                self.assertIn(call["id"], result_ids)


class SerializeSpanTests(unittest.TestCase):
    def test_renders_roles_and_truncates(self):
        span = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "ok", "tool_calls": [_bash_call()]},
            _tool("Z" * 5000, "c2"),
        ]
        text = serialize_span(span)
        self.assertIn("[User]: hello", text)
        self.assertIn("[Assistant tool calls]: workspace_bash(", text)
        self.assertIn("[Tool result]:", text)
        self.assertIn("chars]", text)  # the 5000-char tool result was capped
        self.assertNotIn("Z" * 5000, text)


class AccumulateFilesTests(unittest.TestCase):
    def test_collects_writes_merges_previous_and_dedups(self):
        span = [
            {"role": "assistant", "tool_calls": [_write_call("b.py")]},
            {"role": "assistant", "tool_calls": [_bash_call()]},  # not a write — ignored
            {"role": "assistant", "tool_calls": [_write_call("b.py")]},  # dup
        ]
        self.assertEqual(accumulate_files(span, ["a.py"]), ["a.py", "b.py"])


class SummarizeCompactTests(unittest.TestCase):
    def test_pins_task_prompt_rewrites_head_and_keeps_tail(self):
        messages = _conversation()
        original = [dict(m) for m in messages]
        summarize.post_chat_completion_row = _fake_summary("## Goal\nrun it")
        stats = summarize_compact(
            messages,
            server_url="http://x",
            model="m",
            args=_args(),
            custom_id="2401.1",
            keep_recent_tokens=10,
        )
        self.assertTrue(stats["compacted"])
        self.assertEqual(messages[0], original[0])  # system preserved
        self.assertEqual(messages[1], original[1])  # task prompt pinned verbatim
        self.assertEqual(messages[2]["role"], "user")  # summary injected as user message
        self.assertIn("run it", messages[2]["content"])
        self.assertIn("b.py", messages[2]["content"])  # modified-files block
        self.assertEqual(messages[-1], original[-1])  # recent tail preserved verbatim
        self.assertNotEqual(messages[3]["role"], "tool")  # tail starts at a safe boundary
        self.assertEqual(stats["modified_files"], ["b.py"])

    def test_task_prompt_survives_compaction_verbatim(self):
        # The definition-of-done (anchor metric + tolerance) lives in the task prompt;
        # it must be kept verbatim, never folded into the lossy summary — otherwise the
        # agent can lose it and finalize prematurely with no measured result.
        messages = _conversation()
        messages[1] = {"role": "user", "content": "TASK: reproduce FID=90.68 ±3 anchor"}
        summarize.post_chat_completion_row = _fake_summary("## Goal\nrun it")
        stats = summarize_compact(
            messages, server_url="http://x", model="m", args=_args(),
            custom_id="2401.1", keep_recent_tokens=10,
        )
        self.assertTrue(stats["compacted"])
        self.assertEqual(messages[1]["content"], "TASK: reproduce FID=90.68 ±3 anchor")

    def test_cumulative_modified_files(self):
        messages = _conversation()
        summarize.post_chat_completion_row = _fake_summary("summary")
        stats = summarize_compact(
            messages,
            server_url="http://x",
            model="m",
            args=_args(),
            custom_id="2401.1",
            keep_recent_tokens=10,
            previous_modified=["a.py"],
        )
        self.assertEqual(stats["modified_files"], ["a.py", "b.py"])

    def test_noop_on_empty_summary(self):
        messages = _conversation()
        snapshot = [dict(m) for m in messages]
        summarize.post_chat_completion_row = _fake_summary("   ")
        stats = summarize_compact(
            messages, server_url="http://x", model="m", args=_args(),
            custom_id="2401.1", keep_recent_tokens=10,
        )
        self.assertFalse(stats["compacted"])
        self.assertEqual(stats["reason"], "empty-summary")
        self.assertEqual(messages, snapshot)

    def test_noop_on_summary_error(self):
        messages = _conversation()
        snapshot = [dict(m) for m in messages]

        def _boom(base_url, request, timeout):
            raise RuntimeError("endpoint down")

        summarize.post_chat_completion_row = _boom
        stats = summarize_compact(
            messages, server_url="http://x", model="m", args=_args(),
            custom_id="2401.1", keep_recent_tokens=10,
        )
        self.assertFalse(stats["compacted"])
        self.assertIn("summary-error", stats["reason"])
        self.assertEqual(messages, snapshot)

    def test_noop_when_nothing_old_enough(self):
        messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "hi"}]
        stats = summarize_compact(
            messages, server_url="http://x", model="m", args=_args(),
            custom_id="2401.1", keep_recent_tokens=10_000,
        )
        self.assertFalse(stats["compacted"])
        self.assertEqual(stats["reason"], "nothing-old-enough")


if __name__ == "__main__":
    unittest.main()
