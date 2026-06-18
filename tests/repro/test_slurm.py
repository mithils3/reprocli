from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cluster import resolve_cluster
from reprocli_repro.slurm import build_command, run_step


class BuildCommandTests(unittest.TestCase):
    def test_local_is_plain_bash_without_modules(self):
        argv = build_command(
            resolve_cluster("deltaai"), "/ws", "python train.py", gpus=1, minutes=10, executor="local"
        )
        self.assertEqual(argv[:2], ["bash", "-lc"])
        self.assertIn("cd /ws", argv[2])
        self.assertIn("python train.py", argv[2])
        self.assertNotIn("module load", argv[2])  # modules skipped off-cluster

    def test_slurm_builds_a_jit_salloc_for_deltaai(self):
        argv = build_command(
            resolve_cluster("deltaai"), "/ws", "python train.py", gpus=4, minutes=90, executor="slurm"
        )
        self.assertEqual(argv[0], "salloc")
        self.assertIn("-A", argv)
        self.assertIn("betw-dtai-gh", argv)
        self.assertIn("-p", argv)
        self.assertIn("ghx4", argv)
        self.assertIn("--gpus=4", argv)
        self.assertIn("--time=90", argv)
        self.assertIn("srun", argv)
        inner = argv[-1]
        self.assertIn("cd /ws", inner)
        self.assertIn("module load python/3.11.9", inner)
        self.assertIn("python train.py", inner)

    def test_slurm_rejects_profile_without_account(self):
        with self.assertRaises(SystemExit):
            build_command(resolve_cluster("local"), "/ws", "x", gpus=1, minutes=1, executor="slurm")

    def test_slurm_rejects_gpus_over_node_capacity(self):
        with self.assertRaises(SystemExit):
            build_command(resolve_cluster("deltaai"), "/ws", "x", gpus=8, minutes=1, executor="slurm")

    def test_unknown_executor_rejected(self):
        with self.assertRaises(SystemExit):
            build_command(resolve_cluster("deltaai"), "/ws", "x", gpus=1, minutes=1, executor="nope")


class RunStepTests(unittest.TestCase):
    def test_local_run_executes_and_times(self):
        result = run_step(
            resolve_cluster("local"), "/", "echo hello-step", gpus=1, minutes=1, executor="local"
        )
        self.assertTrue(result.ok, result.stderr)
        self.assertIn("hello-step", result.stdout)
        self.assertGreaterEqual(result.elapsed_s, 0.0)
        self.assertEqual(result.executor, "local")


if __name__ == "__main__":
    unittest.main()
