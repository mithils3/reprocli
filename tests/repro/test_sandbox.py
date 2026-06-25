from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import env, sandbox
from reprocli_repro.inputs import resolve_run_paths
from reprocli_repro.sandbox import Sandbox, bwrap_usable, from_run_paths, require_bwrap
from reprocli_repro.workspace import create_layout


class WrapArgvTests(unittest.TestCase):
    def test_prefix_binds_system_ro_and_episode_rw(self):
        sb = Sandbox(writable=(Path("/ws"), Path("/ev")))
        argv = sb.wrap_argv("cd /ws && echo hi")
        joined = " ".join(argv)
        self.assertEqual(argv[0], "bwrap")
        self.assertEqual(argv[-3:], ["bash", "-lc", "cd /ws && echo hi"])
        # whole system readable; real /dev + fresh /proc
        self.assertIn("--ro-bind / /", joined)
        self.assertIn("--dev-bind /dev /dev", joined)
        # node-local /tmp stays a real rw bind (NOT a tmpfs — bulk scratch lives there)
        self.assertIn("--bind /tmp /tmp", joined)
        self.assertNotIn("--tmpfs /tmp", joined)
        # each writable root is a rw bind
        self.assertIn("--bind /ws /ws", joined)
        self.assertIn("--bind /ev /ev", joined)


class ExecArgvIntegrationTests(unittest.TestCase):
    def test_exec_argv_wraps_only_when_sandbox_passed(self):
        # No sandbox -> the plain clean shell (unchanged contract for the builders).
        self.assertEqual(env.exec_argv(None, "/ws", "echo hi"), ["bash", "-lc", "cd /ws && echo hi"])
        # With a sandbox -> the same body, wrapped in bwrap.
        sb = Sandbox(writable=(Path("/ws"),))
        argv = env.exec_argv(None, "/ws", "echo hi", sandbox=sb)
        self.assertEqual(argv[0], "bwrap")
        self.assertEqual(argv[-1], "cd /ws && echo hi")


class RequireBwrapTests(unittest.TestCase):
    def test_require_raises_when_bwrap_unusable(self):
        with mock.patch.object(sandbox, "_PROBE", {"ok": False}):
            with self.assertRaises(SystemExit):
                require_bwrap()

    def test_require_passes_when_usable(self):
        with mock.patch.object(sandbox, "_PROBE", {"ok": True}):
            require_bwrap()  # no raise


class FromRunPathsTests(unittest.TestCase):
    def test_builds_writable_roots_and_creates_caches(self):
        with tempfile.TemporaryDirectory() as d:
            paths = resolve_run_paths(Path(d) / "runs", "2505.11483", 8.0, run_id="RID")
            create_layout(paths)
            cache = Path(d) / "cache"
            sb = from_run_paths(paths, caches=[cache])
            self.assertTrue(cache.is_dir())  # cache root created up front for the rw bind
            for root in (paths.workspace, paths.evidence, cache):
                self.assertIn(root.resolve(), sb.writable)
            # /tmp is bound by the prefix, not listed in writable
            self.assertNotIn(Path("/tmp"), sb.writable)


@unittest.skipUnless(bwrap_usable(), "bwrap not usable on this host")
class FunctionalConfinementTests(unittest.TestCase):
    def test_writes_outside_the_episode_are_blocked(self):
        # `outside` lives under $HOME, which the sandbox leaves read-only — a real
        # confinement check (it IS writable here without the sandbox). The workspace
        # is bound read-write; /tmp would be too, so the out-of-bounds dir can't be
        # there.
        with tempfile.TemporaryDirectory() as wsroot, \
                tempfile.TemporaryDirectory(dir=Path.home()) as outside:
            ws = Path(wsroot) / "workspace"
            ws.mkdir()
            sb = Sandbox(writable=(ws.resolve(),))
            cmd = (
                "echo ok > inside.txt; "
                f"(echo bad > {outside}/leak.txt && echo WROTE) || echo BLOCKED"
            )
            proc = subprocess.run(
                env.exec_argv(None, str(ws), cmd, sandbox=sb),
                cwd=str(ws), capture_output=True, text=True, timeout=60,
            )
            # the workspace write lands; the write to read-only $HOME is denied
            self.assertEqual((ws / "inside.txt").read_text().strip(), "ok")
            self.assertIn("BLOCKED", proc.stdout)
            self.assertFalse((Path(outside) / "leak.txt").exists())


if __name__ == "__main__":
    unittest.main()
