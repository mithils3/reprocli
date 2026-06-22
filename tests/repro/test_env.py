from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import env
from reprocli_repro.cluster import resolve_cluster


class ModulesPathTests(unittest.TestCase):
    def test_loads_cuda_modules_and_cds(self):
        argv = env.exec_argv(resolve_cluster("deltaai"), "/ws", "uv pip install torch")
        self.assertEqual(argv[:2], ["bash", "-lc"])
        inner = argv[2]
        self.assertTrue(inner.startswith("cd /ws &&"))
        self.assertIn("module load python/3.11.9 cuda cudnn nccl", inner)
        self.assertIn("uv pip install torch", inner)

    def test_no_cluster_runs_bare_but_confined_to_workspace(self):
        argv = env.exec_argv(None, "/ws", "echo hi")
        self.assertEqual(argv, ["bash", "-lc", "cd /ws && echo hi"])

    def test_no_module_load_when_profile_has_no_modules(self):
        bare = resolve_cluster("deltaai", modules=[])
        argv = env.exec_argv(bare, "/ws", "echo hi")
        self.assertEqual(argv, ["bash", "-lc", "cd /ws && echo hi"])


if __name__ == "__main__":
    unittest.main()
