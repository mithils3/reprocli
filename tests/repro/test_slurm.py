from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cluster import Cluster, resolve_cluster
from reprocli_repro.slurm import build_command, run_step


class BuildCommandTests(unittest.TestCase):
    def test_builds_a_jit_salloc_for_deltaai(self):
        argv = build_command(
            resolve_cluster("deltaai"), "/ws", "python train.py", gpus=4, minutes=90
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
        # DeltaAI splices the apptainer-wrapped step in after srun.
        self.assertIn("apptainer exec --nv", inner)
        self.assertIn("pytorch_25.08-py3.sif", inner)
        self.assertIn("cd /ws", inner)
        self.assertIn("python train.py", inner)

    def test_rejects_profile_without_account(self):
        bare = Cluster(name="bare", hw="h100", gpus_per_node=1)
        with self.assertRaises(SystemExit):
            build_command(bare, "/ws", "x", gpus=1, minutes=1)

    def test_rejects_gpus_over_node_capacity(self):
        with self.assertRaises(SystemExit):
            build_command(resolve_cluster("deltaai"), "/ws", "x", gpus=8, minutes=1)


class RunStepTests(unittest.TestCase):
    def test_run_step_builds_salloc_and_populates_result(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="hello-step\n", stderr="")
        with mock.patch("reprocli_repro.slurm.subprocess.run", return_value=fake) as run:
            result = run_step(
                resolve_cluster("deltaai"), "/ws", "echo hello-step", gpus=1, minutes=1
            )
        self.assertTrue(result.ok, result.stderr)
        self.assertIn("hello-step", result.stdout)
        self.assertGreaterEqual(result.elapsed_s, 0.0)
        # The step it actually ran is the JIT salloc argv, not a bare subprocess.
        self.assertEqual(run.call_args.args[0][0], "salloc")


if __name__ == "__main__":
    unittest.main()
