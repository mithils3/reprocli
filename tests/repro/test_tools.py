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
            self.assertIn("git apply", (ctx.evidence / "commands.log").read_text())

    def test_patch_escaping_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            evil = "--- a/../evil.txt\n+++ b/../evil.txt\n@@ -0,0 +1 @@\n+pwn\n"
            res = apply_patch({"diff": evil}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("confined", res["error"])


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
