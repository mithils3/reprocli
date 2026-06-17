from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.compaction import is_elided, microcompact


def tool_message(content: str) -> dict:
    return {"role": "tool", "tool_call_id": "x", "name": "t", "content": content}


def conversation(n_tools: int, body_chars: int = 50) -> list[dict]:
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]
    for i in range(n_tools):
        messages.append({"role": "assistant", "content": f"reason {i}"})
        messages.append(tool_message("R" * body_chars + f"#{i}"))
    return messages


def tool_contents(messages: list[dict]) -> list[str]:
    return [m["content"] for m in messages if m["role"] == "tool"]


class MicrocompactTests(unittest.TestCase):
    def test_noop_under_threshold(self):
        messages = conversation(5)
        snapshot = [dict(m) for m in messages]
        stats = microcompact(messages, keep_recent_tool_results=2, soft_limit_chars=10**9)
        self.assertFalse(stats["compacted"])
        self.assertEqual(stats["elided_messages"], 0)
        self.assertEqual(stats["chars_before"], stats["chars_after"])
        self.assertEqual(messages, snapshot)

    def test_elides_old_keeps_recent_k(self):
        messages = conversation(5, body_chars=200)
        stats = microcompact(messages, keep_recent_tool_results=2, soft_limit_chars=100)
        self.assertTrue(stats["compacted"])
        self.assertEqual(stats["elided_messages"], 3)
        contents = tool_contents(messages)
        self.assertTrue(all(is_elided(c) for c in contents[:3]))
        self.assertFalse(any(is_elided(c) for c in contents[3:]))
        # The most-recent K keep their real bytes; non-tool turns are untouched.
        self.assertTrue(contents[4].endswith("#4"))
        first_assistant = next(m for m in messages if m["role"] == "assistant")
        self.assertEqual(first_assistant["content"], "reason 0")
        self.assertLess(stats["chars_after"], stats["chars_before"])

    def test_keep_zero_elides_every_tool_result(self):
        messages = conversation(3, body_chars=200)
        stats = microcompact(messages, keep_recent_tool_results=0, soft_limit_chars=100)
        self.assertEqual(stats["elided_messages"], 3)
        self.assertTrue(all(is_elided(c) for c in tool_contents(messages)))

    def test_idempotent_second_pass(self):
        messages = conversation(5, body_chars=200)
        # soft_limit 1 forces the elision branch on every pass.
        microcompact(messages, keep_recent_tool_results=2, soft_limit_chars=1)
        snapshot = [dict(m) for m in messages]
        stats = microcompact(messages, keep_recent_tool_results=2, soft_limit_chars=1)
        self.assertFalse(stats["compacted"])
        self.assertEqual(stats["elided_messages"], 0)
        self.assertEqual(messages, snapshot)

    def test_keep_exceeds_available_is_noop(self):
        messages = conversation(2, body_chars=200)
        stats = microcompact(messages, keep_recent_tool_results=5, soft_limit_chars=1)
        self.assertEqual(stats["elided_messages"], 0)
        self.assertFalse(any(is_elided(c) for c in tool_contents(messages)))


if __name__ == "__main__":
    unittest.main()
