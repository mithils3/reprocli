from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.rerun import merge_extracted, needs_rerun, select_rerun_ids


class NeedsRerunTests(unittest.TestCase):
    def test_incomplete_and_degraded_rows_rerun(self) -> None:
        self.assertTrue(needs_rerun({"verification_status": "incomplete"}))
        self.assertTrue(needs_rerun({"verification_status": "degraded"}))
        self.assertFalse(needs_rerun({"verification_status": "verified"}))

    def test_h100_mismatch_reruns_even_when_verified(self) -> None:
        row = {"verification_status": "verified", "h100_arithmetic_mismatch": True}
        self.assertTrue(needs_rerun(row))

    def test_legacy_rows_use_web_verification_and_signals(self) -> None:
        self.assertTrue(needs_rerun({"web_verification": "partial", "signals": {}}))
        self.assertTrue(needs_rerun({"web_verification": "unavailable", "signals": {}}))
        self.assertTrue(needs_rerun({"raw_content": "junk"}))
        self.assertFalse(needs_rerun({"web_verification": "available", "signals": {}}))


class FileTests(unittest.TestCase):
    def test_select_and_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base = root / "base.jsonl"
            update = root / "update.jsonl"
            write_jsonl(
                base,
                [
                    {"custom_id": "1", "verification_status": "verified", "signals": {}},
                    {"custom_id": "2", "verification_status": "incomplete", "signals": {}},
                    {"custom_id": "3", "verification_status": "degraded"},
                ],
            )
            write_jsonl(
                update,
                [{"custom_id": "2", "verification_status": "verified", "signals": {}}],
            )

            self.assertEqual(select_rerun_ids(base), ["2", "3"])

            merged = merge_extracted(base, update)
            by_id = {row["custom_id"]: row for row in merged}
            self.assertEqual(len(merged), 3)
            self.assertEqual(by_id["2"]["verification_status"], "verified")
            self.assertEqual(by_id["2"]["superseded_run_count"], 1)
            self.assertNotIn("superseded_run_count", by_id["1"])


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
