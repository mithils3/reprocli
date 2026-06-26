from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import evidence
from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools.files import apply_patch, write_file
from reprocli_repro.tools.workspace_bash import workspace_bash


def _ctx(root: Path) -> ExecutionContext:
    ws, ref, ev = root / "workspace", root / "reference", root / "evidence"
    for p in (ws, ref, ev):
        p.mkdir(parents=True, exist_ok=True)
    evidence.init_evidence(ev)
    return ExecutionContext(arxiv_id="x", workspace=ws, reference=ref, evidence=ev)


class FileToolTests(unittest.TestCase):
    def test_reference_copy_is_never_writable(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.reference / "paper.tex").write_text("ref body")
            blocked = write_file({"path": str(ctx.reference / "paper.tex"), "content": "x"}, ctx)
            self.assertFalse(blocked["ok"])
            self.assertIn("writable", blocked["error"])

    def test_write_creates_file_in_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            res = write_file({"path": "src/model.py", "content": "x = 1\n"}, ctx)
            self.assertTrue(res["ok"])
            self.assertEqual((ctx.workspace / "src" / "model.py").read_text(), "x = 1\n")

    def test_write_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            self.assertFalse(write_file({"path": "../escape.txt", "content": "x"}, ctx)["ok"])
            self.assertFalse(write_file({"path": "/etc/passwd", "content": "x"}, ctx)["ok"])


class ContainerPathTranslationTests(unittest.TestCase):
    """The agent uses the short in-container /repro paths; the host-side file tools must
    translate them back to the episode's real dirs and keep the same confinement."""

    def test_repro_workspace_path_maps_to_host_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            res = write_file({"path": "/repro/workspace/src/m.py", "content": "x=1\n"}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "src" / "m.py").read_text(), "x=1\n")

    def test_repro_evidence_path_is_writable(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            res = write_file({"path": "/repro/evidence/notes.md", "content": "hi\n"}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.evidence / "notes.md").read_text(), "hi\n")

    def test_repro_reference_path_stays_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            blocked = write_file({"path": "/repro/reference/paper.tex", "content": "x"}, ctx)
            self.assertFalse(blocked["ok"])

    def test_repro_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            evil = {"path": "/repro/workspace/../../etc/passwd", "content": "x"}
            self.assertFalse(write_file(evil, ctx)["ok"])


class ApplyPatchTests(unittest.TestCase):
    DIFF = "--- a/a.txt\n+++ b/a.txt\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"

    def test_edit_applies_and_is_saved(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "a.txt").write_text("a\nb\nc\n")
            res = apply_patch({"diff": self.DIFF}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "a.txt").read_text(), "a\nB\nc\n")
            self.assertEqual(len(list((ctx.evidence / "patches").glob("*.diff"))), 1)
            self.assertIn("apply_patch", (ctx.evidence / "commands.log").read_text())

    def test_patch_escaping_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            evil = "--- a/../evil.txt\n+++ b/../evil.txt\n@@ -0,0 +1 @@\n+pwn\n"
            res = apply_patch({"diff": evil}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("confined", res["error"])

    def test_workspace_prefixed_path_is_recovered(self):
        """The round-36 failure: agent bakes 'repro/workspace/' into the header."""
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "pkg").mkdir()
            (ctx.workspace / "pkg" / "m.py").write_text("a\nb\nc\n")
            diff = (
                "--- a/repro/workspace/pkg/m.py\n"
                "+++ b/repro/workspace/pkg/m.py\n"
                "@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"
            )
            res = apply_patch({"diff": diff}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "pkg" / "m.py").read_text(), "a\nB\nc\n")

    def test_v4a_update_with_fuzzy_context(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            # trailing whitespace in the file the patch's context omits
            (ctx.workspace / "f.py").write_text("def x():\n    return 1   \n")
            patch = (
                "*** Begin Patch\n"
                "*** Update File: f.py\n"
                "@@ def x():\n"
                "-    return 1\n"
                "+    return 2\n"
                "*** End Patch\n"
            )
            res = apply_patch({"diff": patch}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "f.py").read_text(), "def x():\n    return 2\n")

    def test_v4a_add_and_delete_and_rename(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "old.txt").write_text("keep\n")
            add = "*** Begin Patch\n*** Add File: sub/new.txt\n+hello\n+world\n*** End Patch\n"
            self.assertTrue(apply_patch({"diff": add}, ctx)["ok"])
            self.assertEqual((ctx.workspace / "sub" / "new.txt").read_text(), "hello\nworld\n")

            rename = "*** Begin Patch\n*** Update File: old.txt\n*** Move to: renamed.txt\n@@\n-keep\n+kept\n*** End Patch\n"
            self.assertTrue(apply_patch({"diff": rename}, ctx)["ok"])
            self.assertFalse((ctx.workspace / "old.txt").exists())
            self.assertEqual((ctx.workspace / "renamed.txt").read_text(), "kept\n")

            delete = "*** Begin Patch\n*** Delete File: sub/new.txt\n*** End Patch\n"
            self.assertTrue(apply_patch({"diff": delete}, ctx)["ok"])
            self.assertFalse((ctx.workspace / "sub" / "new.txt").exists())

    def test_missing_context_fails_without_touching_file(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "f.txt").write_text("a\nb\nc\n")
            patch = "*** Begin Patch\n*** Update File: f.txt\n@@\n-nonexistent\n+x\n*** End Patch\n"
            res = apply_patch({"diff": patch}, ctx)
            self.assertFalse(res["ok"])
            self.assertEqual((ctx.workspace / "f.txt").read_text(), "a\nb\nc\n")


class WorkspaceBashTests(unittest.TestCase):
    def test_runs_in_workspace_and_logs(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            res = workspace_bash({"command": "echo hi > out.txt"}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "out.txt").read_text().strip(), "hi")
            self.assertIn("echo hi > out.txt", (ctx.evidence / "commands.log").read_text())

    def test_clone_local_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "src_repo"
            src.mkdir()
            (src / "hello.txt").write_text("hi\n")
            env = "-c user.email=t@t -c user.name=t"
            subprocess.run(["bash", "-lc", f"git init -q {src} && cd {src} && git {env} add -A && git {env} commit -qm init"], check=True)
            ctx = _ctx(root / "ep")
            res = workspace_bash({"command": f"git clone -q {src} code"}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertTrue((ctx.workspace / "code" / "hello.txt").is_file())


if __name__ == "__main__":
    unittest.main()
