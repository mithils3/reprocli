from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import env, sandbox
from reprocli_repro.inputs import resolve_run_paths
from reprocli_repro.sandbox import (
    Sandbox,
    apptainer_usable,
    forward_env,
    from_run_paths,
    require_apptainer,
)
from reprocli_repro.workspace import create_layout

IMAGE = "/sw/user/NGC_containers/pytorch_25.08-py3.sif"
# A real .sif to run the functional confinement test against; absent in most CI.
TEST_SIF = os.environ.get("REPRO_TEST_SIF")


class WrapArgvTests(unittest.TestCase):
    def test_prefix_runs_inside_image_with_rw_and_ro_binds(self):
        sb = Sandbox(image=IMAGE, writable=(Path("/ws"), Path("/ev")), readonly=(Path("/ref"),))
        argv = sb.wrap_argv("cd /ws && echo hi")
        joined = " ".join(argv)
        self.assertEqual(argv[:4], ["apptainer", "exec", "--cleanenv", "--no-home"])
        self.assertEqual(argv[-3:], ["bash", "-lc", "cd /ws && echo hi"])
        # the image is the last apptainer arg, right before `bash`
        self.assertEqual(argv[-4], IMAGE)
        # node-local /tmp is always a real rw bind (bulk scratch — never a tmpfs)
        self.assertIn("--bind /tmp", joined)
        self.assertNotIn("--tmpfs", joined)
        # each writable root is a rw bind; reference is bound read-only
        self.assertIn("--bind /ws", joined)
        self.assertIn("--bind /ev", joined)
        self.assertIn("--bind /ref:/ref:ro", joined)

    def test_nv_only_when_requested(self):
        sb = Sandbox(image=IMAGE, writable=(Path("/ws"),))
        self.assertNotIn("--nv", sb.wrap_argv("echo hi"))  # default: CPU step, no GPU
        self.assertIn("--nv", sb.wrap_argv("echo hi", nv=True))  # GPU step


class ExecArgvIntegrationTests(unittest.TestCase):
    def test_exec_argv_wraps_only_when_sandbox_passed(self):
        # No sandbox -> the plain body (unchanged contract for the builders).
        self.assertEqual(env.exec_argv("/ws", "echo hi"), ["bash", "-lc", "cd /ws && echo hi"])
        # With a sandbox -> the same body, wrapped in apptainer; on_gpu drives --nv.
        sb = Sandbox(image=IMAGE, writable=(Path("/ws"),))
        argv = env.exec_argv("/ws", "echo hi", on_gpu=True, sandbox=sb)
        self.assertEqual(argv[0], "apptainer")
        self.assertIn("--nv", argv)
        self.assertEqual(argv[-1], "cd /ws && echo hi")


class RequireApptainerTests(unittest.TestCase):
    def test_require_raises_when_no_image(self):
        with self.assertRaises(SystemExit):
            require_apptainer(None)

    def test_require_raises_when_image_unusable(self):
        with mock.patch.object(sandbox, "_PROBE", {IMAGE: False}):
            with self.assertRaises(SystemExit):
                require_apptainer(IMAGE)

    def test_require_passes_when_usable(self):
        with mock.patch.object(sandbox, "_PROBE", {IMAGE: True}):
            require_apptainer(IMAGE)  # no raise


class ForwardEnvTests(unittest.TestCase):
    def test_hf_token_is_mirrored_for_cleanenv(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["HF_TOKEN"] = "secret"
            forward_env()
            # forwarded via APPTAINERENV_* so --cleanenv keeps it (no token on argv)
            self.assertEqual(os.environ["APPTAINERENV_HF_TOKEN"], "secret")


class FromRunPathsTests(unittest.TestCase):
    def test_builds_rw_and_ro_roots_and_creates_caches(self):
        with tempfile.TemporaryDirectory() as d:
            paths = resolve_run_paths(Path(d) / "runs", "2505.11483", 8.0, run_id="RID")
            create_layout(paths)
            cache = Path(d) / "cache"
            sb = from_run_paths(paths, image=IMAGE, caches=[cache])
            self.assertEqual(sb.image, IMAGE)
            self.assertTrue(cache.is_dir())  # cache root created up front for the rw bind
            for root in (paths.workspace, paths.evidence, cache):
                self.assertIn(root.resolve(), sb.writable)
            # reference is read-only; /tmp is bound by the prefix, not listed in writable
            self.assertIn(paths.reference.resolve(), sb.readonly)
            self.assertNotIn(Path("/tmp"), sb.writable)


@unittest.skipUnless(
    TEST_SIF and shutil.which("apptainer") and apptainer_usable(TEST_SIF),
    "no usable apptainer image (set REPRO_TEST_SIF to a real .sif to run)",
)
class FunctionalConfinementTests(unittest.TestCase):
    def test_writes_outside_the_episode_are_blocked(self):
        # `outside` lives under $HOME, which the container does NOT mount — a real
        # confinement check (it IS writable here without the sandbox). The workspace is
        # bound read-write; /tmp would be too, so the out-of-bounds dir can't be there.
        with tempfile.TemporaryDirectory() as wsroot, \
                tempfile.TemporaryDirectory(dir=Path.home()) as outside:
            ws = Path(wsroot) / "workspace"
            ws.mkdir()
            sb = Sandbox(image=TEST_SIF, writable=(ws.resolve(),))
            cmd = (
                "echo ok > inside.txt; "
                f"(echo bad > {outside}/leak.txt && echo WROTE) || echo BLOCKED"
            )
            proc = subprocess.run(
                env.exec_argv(str(ws), cmd, sandbox=sb),
                cwd=str(ws), capture_output=True, text=True, timeout=120,
            )
            # the workspace write lands; the write to the unmounted $HOME path is denied
            self.assertEqual((ws / "inside.txt").read_text().strip(), "ok")
            self.assertIn("BLOCKED", proc.stdout)
            self.assertFalse((Path(outside) / "leak.txt").exists())


if __name__ == "__main__":
    unittest.main()
