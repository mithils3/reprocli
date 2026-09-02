from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.audit.h100 import h100_band


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


if __name__ == "__main__":
    unittest.main()
