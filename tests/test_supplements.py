from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.supplements import supplement_manifest_lines


class SupplementPromptManifestTests(unittest.TestCase):
    def test_manifest_omits_size_and_sha_noise(self) -> None:
        lines = supplement_manifest_lines(
            [
                {
                    "relative_path": "code/train.py",
                    "extension": ".py",
                    "file_size": 1234,
                    "sha256": "abc123",
                }
            ]
        )

        self.assertEqual(lines, ["- code/train.py | .py"])
        self.assertNotIn("bytes", lines[0])
        self.assertNotIn("sha256", lines[0])


if __name__ == "__main__":
    unittest.main()
