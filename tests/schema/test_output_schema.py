from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.schema.output import (
    FINAL_JSON_SCHEMA,
    deterministic_score_and_tier,
    normalize_score_and_tier,
)


def classification_row(**signals: bool) -> dict:
    return {
        "signals": {
            name: {"value": value, "verification": "tool_verified", "evidence": "test"}
            for name, value in signals.items()
        }
    }


class OutputSchemaTests(unittest.TestCase):
    def test_model_schema_does_not_request_score_or_tier(self) -> None:
        self.assertNotIn("score", FINAL_JSON_SCHEMA["required"])
        self.assertNotIn("tier", FINAL_JSON_SCHEMA["required"])
        self.assertNotIn("score", FINAL_JSON_SCHEMA["properties"])
        self.assertNotIn("tier", FINAL_JSON_SCHEMA["properties"])

    def test_model_schema_does_not_request_web_verification(self) -> None:
        self.assertNotIn("web_verification", FINAL_JSON_SCHEMA["required"])
        self.assertNotIn("web_verification", FINAL_JSON_SCHEMA["properties"])

    def test_model_schema_omits_match_bar(self) -> None:
        # The classifier no longer pins the success bar; the Stage-7 auditor owns
        # and derives it (see tests/audit and schema/audit.py).
        self.assertNotIn("match_bar", FINAL_JSON_SCHEMA["required"])
        self.assertNotIn("match_bar", FINAL_JSON_SCHEMA["properties"])

    def test_signals_require_verification_state(self) -> None:
        signal = FINAL_JSON_SCHEMA["properties"]["signals"]["properties"]["code_available"]
        self.assertIn("verification", signal["required"])
        self.assertIn("tool_searched_not_found", signal["properties"]["verification"]["enum"])

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

    def test_normalize_adds_score_without_reported_fields(self) -> None:
        row = classification_row(
            code_available=True,
            dataset_available=True,
            weights_available=False,
            dataset_is_standard=True,
        )

        normalized = normalize_score_and_tier(row)

        self.assertEqual(normalized["score"], 1)
        self.assertEqual(normalized["tier"], "Medium")
        self.assertNotIn("reported_score", normalized)
        self.assertNotIn("reported_tier", normalized)


if __name__ == "__main__":
    unittest.main()
