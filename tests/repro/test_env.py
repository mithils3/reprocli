from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import env
from reprocli_repro.sandbox import Sandbox


class ExecArgvTests(unittest.TestCase):
    def test_bare_body_without_sandbox(self):
        # The pure builder shape: `cd <ws> && <cmd>`, no module load (the container
        # supplies the toolchain) and no container wrap (no sandbox passed).
        self.assertEqual(
            env.exec_argv("/ws", "git clone url"),
            ["bash", "-lc", "cd /ws && git clone url"],
        )

    def test_on_gpu_does_not_change_the_bare_body(self):
        # on_gpu only adds --nv *inside the sandbox*; with no sandbox the body is the
        # same — CUDA comes from the image, not a host `module load`.
        self.assertEqual(
            env.exec_argv("/ws", "python train.py", on_gpu=True),
            ["bash", "-lc", "cd /ws && python train.py"],
        )

    def test_sandbox_wraps_body_in_apptainer(self):
        sb = Sandbox(image="/img.sif", writable=(Path("/ws"),))
        argv = env.exec_argv("/ws", "uv pip install x", on_gpu=True, sandbox=sb)
        self.assertEqual(argv[0], "apptainer")
        self.assertIn("--nv", argv)  # GPU step passes the device through
        self.assertEqual(argv[-4], "/img.sif")  # image right before bash
        self.assertEqual(argv[-3:], ["bash", "-lc", "cd /ws && uv pip install x"])

    def test_cpu_sandbox_step_omits_nv(self):
        sb = Sandbox(image="/img.sif", writable=(Path("/ws"),))
        self.assertNotIn("--nv", env.exec_argv("/ws", "echo hi", sandbox=sb))


if __name__ == "__main__":
    unittest.main()
