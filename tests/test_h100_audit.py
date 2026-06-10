from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.h100_audit import audit_h100_fields, h100_band


def estimate(**overrides) -> dict:
    base = {
        "hours": 17.92,
        "basis_kind": "paper_reported",
        "gpu_count": 8,
        "gpu_type": "A100 80GB",
        "wallclock_hours": 7,
        "h100_equivalent_multiplier": 0.32,
        "basis": "8xA100 for 7h",
    }
    base.update(overrides)
    return base


class BandTests(unittest.TestCase):
    def test_band_edges(self) -> None:
        self.assertEqual(h100_band(0), "0-8")
        self.assertEqual(h100_band(8), "0-8")
        self.assertEqual(h100_band(8.1), "8-32")
        self.assertEqual(h100_band(96), "32-96")
        self.assertEqual(h100_band(192), "96-192")
        self.assertEqual(h100_band(2_200_000), ">192")
        self.assertIsNone(h100_band(None))
        self.assertIsNone(h100_band("four"))


class AuditTests(unittest.TestCase):
    def test_consistent_arithmetic_passes(self) -> None:
        fields = audit_h100_fields({"h100_estimate": estimate()})
        self.assertEqual(fields["h100_hours_estimate"], 17.92)
        self.assertAlmostEqual(fields["h100_recomputed_hours"], 17.92)
        self.assertFalse(fields["h100_arithmetic_mismatch"])
        self.assertFalse(fields["h100_needs_human_review"])
        self.assertEqual(fields["h100_band"], "8-32")

    def test_mismatched_arithmetic_is_flagged(self) -> None:
        fields = audit_h100_fields({"h100_estimate": estimate(hours=100)})
        self.assertTrue(fields["h100_arithmetic_mismatch"])
        self.assertTrue(fields["h100_needs_human_review"])

    def test_missing_arithmetic_needs_review(self) -> None:
        fields = audit_h100_fields(
            {"h100_estimate": estimate(gpu_count=None, wallclock_hours=None)}
        )
        self.assertIsNone(fields["h100_recomputed_hours"])
        self.assertIsNone(fields["h100_arithmetic_mismatch"])
        self.assertTrue(fields["h100_needs_human_review"])

    def test_compute_unspecified_needs_review(self) -> None:
        fields = audit_h100_fields(
            {"h100_estimate": estimate(basis_kind="compute_unspecified")}
        )
        self.assertTrue(fields["h100_needs_human_review"])

    def test_basis_kind_is_prefixed_into_basis_text(self) -> None:
        fields = audit_h100_fields({"h100_estimate": estimate()})
        self.assertEqual(fields["h100_estimate_basis"], "paper_reported: 8xA100 for 7h")

    def test_legacy_flat_estimate_needs_review(self) -> None:
        fields = audit_h100_fields({"h100_hours_estimate": 4})
        self.assertEqual(fields["h100_band"], "0-8")
        self.assertTrue(fields["h100_needs_human_review"])


if __name__ == "__main__":
    unittest.main()
