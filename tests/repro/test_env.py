from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import env
from reprocli_repro.cluster import resolve_cluster


class ModulesPathTests(unittest.TestCase):
    def test_deltaai_cpu_step_is_a_clean_shell(self):
        # DeltaAI no longer defaults to a container. A CPU-setup step (on_gpu=False)
        # is a bare `cd && <cmd>` — NO `module load` (loading CUDA modules onto the
        # login shell shadows git's libcurl and breaks `git clone`).
        argv = env.exec_argv(resolve_cluster("deltaai"), "/ws", "git clone url")
        self.assertEqual(argv, ["bash", "-lc", "cd /ws && git clone url"])

    def test_deltaai_gpu_step_loads_cuda_modules(self):
        # A GPU step (on_gpu=True) gets the CUDA toolkit the CPU shell omits.
        argv = env.exec_argv(resolve_cluster("deltaai"), "/ws", "python train.py", on_gpu=True)
        self.assertEqual(argv[:2], ["bash", "-lc"])
        inner = argv[2]
        self.assertTrue(inner.startswith("cd /ws &&"))
        self.assertIn("module load python/3.11.9 cuda cudnn nccl", inner)
        self.assertIn("python train.py", inner)
        self.assertNotIn("apptainer", inner)

    def test_no_cluster_runs_bare_but_confined_to_workspace(self):
        argv = env.exec_argv(None, "/ws", "echo hi", on_gpu=True)
        self.assertEqual(argv, ["bash", "-lc", "cd /ws && echo hi"])

    def test_no_module_load_when_profile_has_no_modules(self):
        bare = resolve_cluster("delta-h200", modules=[])
        argv = env.exec_argv(bare, "/ws", "echo hi", on_gpu=True)
        self.assertEqual(argv, ["bash", "-lc", "cd /ws && echo hi"])


class ApptainerOptInTests(unittest.TestCase):
    def test_apptainer_image_opts_back_into_the_container(self):
        # Setting an image (per-run override) restores the container wrap, for both
        # CPU and GPU steps, and skips `module load`.
        c = resolve_cluster("deltaai", apptainer_image="/sw/ngc/pytorch.sif")
        argv = env.exec_argv(c, "/ws", "uv pip install torch")
        self.assertEqual(argv[:2], ["bash", "-lc"])
        inner = argv[2]
        self.assertTrue(inner.startswith("apptainer exec --nv --cleanenv "))
        self.assertIn("--bind /work/nvme", inner)               # scratch root bound
        self.assertIn("pytorch.sif", inner)                     # the base image
        self.assertNotIn("module load", inner)                  # modules are skipped
        self.assertIn("bash -c 'cd /ws && uv pip install torch'", inner)


if __name__ == "__main__":
    unittest.main()
