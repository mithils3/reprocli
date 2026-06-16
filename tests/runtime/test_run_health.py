from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.runtime.run_health import (
    degraded_row,
    finalize_extracted_row,
    loop_telemetry,
    verification_status,
)


def signals(states: dict[str, str], values: dict[str, bool] | None = None) -> dict:
    values = values or {}
    return {
        "signals": {
            name: {
                "value": values.get(name, True),
                "verification": state,
                "evidence": "test",
            }
            for name, state in states.items()
        }
    }


ALL_VERIFIED = {
    "code_available": "tool_verified",
    "dataset_available": "tool_verified",
    "weights_available": "tool_searched_not_found",
    "dataset_is_standard": "tool_verified",
}


class VerificationStatusTests(unittest.TestCase):
    def test_searched_not_found_counts_as_verified(self) -> None:
        row = signals(ALL_VERIFIED)
        self.assertEqual(verification_status(row, {"exit_reason": "natural"}), "verified")

    def test_paper_text_only_signal_is_incomplete(self) -> None:
        row = signals({**ALL_VERIFIED, "weights_available": "paper_text_only"})
        self.assertEqual(verification_status(row, {"exit_reason": "natural"}), "incomplete")

    def test_tool_failed_signal_is_incomplete(self) -> None:
        row = signals({**ALL_VERIFIED, "code_available": "tool_failed"})
        self.assertEqual(verification_status(row, {"exit_reason": "natural"}), "incomplete")

    def test_not_applicable_signals_do_not_block_verified(self) -> None:
        row = signals({name: "not_applicable" for name in ALL_VERIFIED})
        self.assertEqual(verification_status(row, {"exit_reason": "natural"}), "verified")

    def test_forced_exits_are_incomplete(self) -> None:
        row = signals(ALL_VERIFIED)
        for reason in ("round_limit", "repeated_call_cutoff", "context_budget"):
            self.assertEqual(verification_status(row, {"exit_reason": reason}), "incomplete")

    def test_input_overflow_is_degraded(self) -> None:
        row = signals(ALL_VERIFIED)
        tool_loop = {"exit_reason": "natural", "telemetry": {"input_overflow": True}}
        self.assertEqual(verification_status(row, tool_loop), "degraded")

    def test_missing_signals_are_degraded(self) -> None:
        self.assertEqual(verification_status({}, {}), "degraded")
        self.assertEqual(verification_status({"signals": "junk"}, {}), "degraded")

    def test_zero_tool_calls_with_applicable_signals_is_incomplete(self) -> None:
        row = signals(ALL_VERIFIED)
        tool_loop = {"exit_reason": "natural", "telemetry": {"tool_calls": 0}}
        self.assertEqual(verification_status(row, tool_loop), "incomplete")

    def test_legacy_rows_without_verification_field_are_incomplete(self) -> None:
        row = signals(ALL_VERIFIED)
        for signal in row["signals"].values():
            del signal["verification"]
        self.assertEqual(verification_status(row, {"exit_reason": "natural"}), "incomplete")


class FinalizeRowTests(unittest.TestCase):
    def test_degraded_rows_are_never_scored(self) -> None:
        row = signals(ALL_VERIFIED)
        tool_loop = {"exit_reason": "natural", "telemetry": {"input_overflow": True}}
        final = finalize_extracted_row(row, tool_loop)
        self.assertEqual(final["verification_status"], "degraded")
        self.assertIsNone(final["score"])
        self.assertIsNone(final["tier"])

    def test_non_empirical_papers_get_out_of_scope_tier(self) -> None:
        row = {**signals({name: "not_applicable" for name in ALL_VERIFIED}), "paper_kind": "theoretical"}
        final = finalize_extracted_row(row, {"exit_reason": "natural"})
        self.assertIsNone(final["score"])
        self.assertEqual(final["tier"], "Out-of-Scope-Non-Empirical")

    def test_empirical_paper_is_scored_with_alias(self) -> None:
        values = {"weights_available": False}
        row = {**signals(ALL_VERIFIED, values), "paper_kind": "empirical"}
        final = finalize_extracted_row(row, {"exit_reason": "natural"})
        self.assertEqual(final["score"], 1)
        self.assertEqual(final["tier"], "Medium")
        self.assertEqual(final["web_verification"], "available")
        self.assertEqual(final["exit_reason"], "natural")

    def test_model_reported_web_verification_is_preserved(self) -> None:
        row = {**signals(ALL_VERIFIED), "web_verification": "unavailable"}
        final = finalize_extracted_row(row, {"exit_reason": "natural"})
        self.assertEqual(final["reported_web_verification"], "unavailable")
        self.assertEqual(final["web_verification"], "available")

    def test_degraded_row_helper_keeps_raw_content(self) -> None:
        row = degraded_row("2501.00001", "garbage", None, {"exit_reason": "natural"})
        self.assertEqual(row["verification_status"], "degraded")
        self.assertIsNone(row["score"])
        self.assertEqual(row["raw_content"], "garbage")


class TelemetryTests(unittest.TestCase):
    def test_counts_tool_calls_and_errors(self) -> None:
        messages = [
            {"role": "tool", "content": '{"ok": true}'},
            {"role": "tool", "content": '{"ok": false, "error": "boom"}'},
            {"role": "assistant", "content": "x" * 400},
        ]
        telemetry = loop_telemetry(messages, max_input_tokens=100)
        self.assertEqual(telemetry["tool_calls"], 2)
        self.assertEqual(telemetry["tool_errors"], 1)
        self.assertTrue(telemetry["input_overflow"])

    def test_no_overflow_within_budget(self) -> None:
        telemetry = loop_telemetry([{"role": "user", "content": "hi"}], max_input_tokens=100)
        self.assertFalse(telemetry["input_overflow"])


if __name__ == "__main__":
    unittest.main()
