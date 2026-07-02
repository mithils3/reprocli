from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import evidence
from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools.files import apply_patch, write_file


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

    def test_miss_error_quotes_nearby_file_text(self):
        """A near-miss should show the agent the file's real text, not a dead end."""
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "f.py").write_text("def f():\n    return 41\n    # tail\n")
            # context drifted: model thinks the body is 'return 99'
            patch = (
                "*** Begin Patch\n*** Update File: f.py\n@@ def f():\n"
                "-    return 99\n+    return 0\n*** End Patch\n"
            )
            res = apply_patch({"diff": patch}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("Closest match", res["error"])
            self.assertIn("return 41", res["error"])  # quotes the real line

    def test_out_of_order_hunks_get_an_actionable_error(self):
        """Second hunk targets a line the first hunk's cursor already passed."""
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "f.txt").write_text("one\ntwo\nthree\nfour\n")
            patch = (
                "*** Begin Patch\n*** Update File: f.txt\n"
                "@@\n-three\n+THREE\n"   # hunk A (lower in file) first
                "@@\n-one\n+ONE\n"       # hunk B (higher in file) second
                "*** End Patch\n"
            )
            res = apply_patch({"diff": patch}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("earlier hunk", res["error"])
            self.assertEqual((ctx.workspace / "f.txt").read_text(), "one\ntwo\nthree\nfour\n")

    def test_unprefixed_context_line_is_tolerated(self):
        """A flush-left context line that lost its leading space must not abort the patch."""
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "m.py").write_text("import os\nx = 1\n")
            patch = (
                "*** Begin Patch\n*** Update File: m.py\n@@\n"
                "import os\n"          # <- no leading space; should be read as context
                "-x = 1\n+x = 2\n*** End Patch\n"
            )
            res = apply_patch({"diff": patch}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "m.py").read_text(), "import os\nx = 2\n")

    def test_crlf_file_keeps_its_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "w.txt").write_bytes(b"a\r\nb\r\nc\r\n")
            patch = "*** Begin Patch\n*** Update File: w.txt\n@@\n-b\n+B\n*** End Patch\n"
            res = apply_patch({"diff": patch}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "w.txt").read_bytes(), b"a\r\nB\r\nc\r\n")

    def test_json_escaped_patch_is_recovered(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            (ctx.workspace / "a.txt").write_text("a\nb\nc\n")
            escaped = self.DIFF.replace("\n", "\\n")  # arrives as one physical line
            res = apply_patch({"diff": escaped}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual((ctx.workspace / "a.txt").read_text(), "a\nB\nc\n")

    def test_arg_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            self.assertTrue(write_file({"file_path": "p.txt", "text": "hi\n"}, ctx)["ok"])
            self.assertEqual((ctx.workspace / "p.txt").read_text(), "hi\n")
            (ctx.workspace / "a.txt").write_text("a\nb\nc\n")
            self.assertTrue(apply_patch({"patch": self.DIFF}, ctx)["ok"])


if __name__ == "__main__":
    unittest.main()
