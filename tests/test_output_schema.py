from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.output_schema import (
    deterministic_score_and_tier,
    normalize_score_and_tier,
)


def classification_row(**signals: bool) -> dict:
    return {
        "signals": {
            name: {"value": value, "evidence": "test"}
            for name, value in signals.items()
        }
    }


class OutputSchemaTests(unittest.TestCase):
    def test_score_skips_missing_standard_dataset(self) -> None:
        row = classification_row(
            code_available=True,
            dataset_available=False,
            weights_available=True,
            dataset_is_standard=True,
        )

        self.assertEqual(deterministic_score_and_tier(row), (0, "Easy"))

    def test_score_counts_missing_custom_dataset(self) -> None:
        row = classification_row(
            code_available=True,
            dataset_available=False,
            weights_available=False,
            dataset_is_standard=False,
        )

        self.assertEqual(
            deterministic_score_and_tier(row),
            (4, "Artifact-Blocked"),
        )

    def test_normalize_preserves_mismatched_model_values(self) -> None:
        row = classification_row(
            code_available=True,
            dataset_available=False,
            weights_available=True,
            dataset_is_standard=True,
        )
        row.update({"score": 516, "tier": "Medium"})

        normalized = normalize_score_and_tier(row)

        self.assertEqual(normalized["score"], 0)
        self.assertEqual(normalized["tier"], "Easy")
        self.assertEqual(normalized["reported_score"], 516)
        self.assertEqual(normalized["reported_tier"], "Medium")


if __name__ == "__main__":
    unittest.main()
