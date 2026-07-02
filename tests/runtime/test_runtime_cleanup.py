from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from reprocli_vllm.config.config import DEFAULT_MODEL, MINIMAX_M2_MODEL
from run_arxiv_prompt_vllm import parse_args


class RuntimeCleanupTests(unittest.TestCase):
    def test_audit_client_sampling_defaults_are_active(self) -> None:
        """The auditor is a URL-only client: parse_args fills the request-time
        sampling fields it POSTs to the served brain (serve-launch flags now live
        in reprocli_serve/profiles.py, not here)."""
        with patch.object(sys, "argv", ["run_arxiv_prompt_vllm.py"]):
            args = parse_args()

        self.assertEqual(DEFAULT_MODEL, MINIMAX_M2_MODEL)
        self.assertEqual(args.model, MINIMAX_M2_MODEL)
        self.assertEqual(args.max_model_len, 196608)
        self.assertEqual(args.temperature, 1.0)
        self.assertEqual(args.top_p, 0.95)
        self.assertEqual(args.top_k, 40)


if __name__ == "__main__":
    unittest.main()
