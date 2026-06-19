from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.inputs import resolve_run_paths
from reprocli_repro.workspace import build_venv, create_layout, prepare_workspace

ROW = {
    "arxiv_id": "2505.11483",
    "paper_tex_files": [{"relative_path": "main.tex", "text": "x"}],
    "supplement_files": [{"relative_path": "code/run.py", "content": b"print(1)\n"}],
}


class CreateLayoutTests(unittest.TestCase):
    def test_creates_all_four_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            paths = resolve_run_paths(Path(d) / "runs", "2505.11483", 8.0, run_id="RID")
            create_layout(paths)
            for sub in (paths.run_dir, paths.workspace, paths.reference, paths.evidence):
                self.assertTrue(sub.is_dir(), sub)


class BuildVenvTests(unittest.TestCase):
    def test_uv_builds_empty_venv(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "workspace"
            ws.mkdir()
            res = build_venv(ws)
            self.assertTrue(res["ok"], res)
            self.assertTrue((ws / ".venv").is_dir())


class PrepareWorkspaceTests(unittest.TestCase):
    def test_full_offline_setup(self):
        with tempfile.TemporaryDirectory() as d:
            paths = resolve_run_paths(Path(d) / "runs", "2505.11483", 8.0, run_id="RID")
            result = prepare_workspace(paths, arxiv_id="2505.11483", reference_row=ROW)
            # layout + evidence sinks
            self.assertTrue(paths.workspace.is_dir())
            self.assertTrue((paths.evidence / "commands.log").is_file())
            self.assertTrue((paths.evidence / "patches").is_dir())
            # reference materialized from the row (no network)
            self.assertTrue(result.reference["ok"])
            self.assertTrue((paths.reference / "supplement" / "code" / "run.py").is_file())
            self.assertTrue((paths.reference / "MANIFEST.txt").is_file())
            # empty per-paper venv built, never the shared .venv
            self.assertTrue(result.venv["ok"], result.venv)
            self.assertTrue((paths.workspace / ".venv").is_dir())

    def test_can_skip_venv_and_reference(self):
        with tempfile.TemporaryDirectory() as d:
            paths = resolve_run_paths(Path(d) / "runs", "x", 8.0, run_id="RID")
            result = prepare_workspace(paths, arxiv_id="x", make_venv=False, materialize_ref=False)
            self.assertIsNone(result.venv)
            self.assertIsNone(result.reference)
            self.assertTrue(paths.workspace.is_dir())
            self.assertFalse((paths.workspace / ".venv").exists())


if __name__ == "__main__":
    unittest.main()
