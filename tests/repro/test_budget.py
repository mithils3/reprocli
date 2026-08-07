from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.budget import (
    affordable,
    charge,
    h100_equiv_hours,
    hw_multiplier,
    pre_authorized_cost,
    step_cost_hours,
)
from reprocli_repro.context import Budget


class MultiplierTests(unittest.TestCase):
    def test_hopper_class_parts_are_h100_equiv(self):
        # h100 is the reference unit; DeltaAI's gh200 shares the compute die at ~1.0.
        for hw in ("h100", "gh200"):
            self.assertEqual(hw_multiplier(hw), 1.0, hw)

    def test_unknown_hw_rejected(self):
        with self.assertRaises(SystemExit):
            hw_multiplier("tpu")

    def test_gh200_reduces_to_h100_equiv(self):
        # 2 GPUs for 1h on DeltaAI's GH200 cost 2.0 H100-equiv hours.
        self.assertEqual(h100_equiv_hours(2, 1.0, "gh200"), 2.0)


class CostTests(unittest.TestCase):
    def test_step_cost_uses_elapsed_seconds(self):
        self.assertAlmostEqual(step_cost_hours(4, 1800, "h100"), 2.0)  # 4 gpu x 0.5h

    def test_pre_authorized_uses_minutes_cap(self):
        self.assertAlmostEqual(pre_authorized_cost(4, 90, "h100"), 6.0)  # 4 gpu x 1.5h


class GuardrailTests(unittest.TestCase):
    def test_affordable_when_worst_case_fits(self):
        ok, reason = affordable(Budget(total_h100_hours=8.0), gpus=4, minutes=60, hw="h100")
        self.assertTrue(ok, reason)

    def test_rejected_when_worst_case_overspends(self):
        ok, reason = affordable(Budget(total_h100_hours=8.0), gpus=4, minutes=180, hw="h100")
        self.assertFalse(ok)
        self.assertIn("remaining", reason)

    def test_rejected_when_exhausted(self):
        b = Budget(total_h100_hours=8.0, spent_h100_hours=8.0)
        ok, reason = affordable(b, gpus=1, minutes=1, hw="h100")
        self.assertFalse(ok)
        self.assertIn("exhausted", reason)

    def test_charge_consumes_actual_elapsed(self):
        b = Budget(total_h100_hours=8.0)
        remaining = charge(b, gpus=2, elapsed_seconds=1800, hw="h100")  # 2 gpu x 0.5h = 1.0
        self.assertAlmostEqual(b.spent_h100_hours, 1.0)
        self.assertAlmostEqual(remaining, 7.0)


if __name__ == "__main__":
    unittest.main()
