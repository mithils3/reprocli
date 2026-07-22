from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import batch_runs


def _row(arxiv_id: str, run_id: str, **over) -> dict:
    row = {
        "arxiv_id": arxiv_id,
        "run_id": run_id,
        "status": "finished",
        "started_at": "2026-07-21T10:00:00Z",
        "audit_score": None,
    }
    row.update(over)
    return row


class SelectRunsTests(unittest.TestCase):
    def test_keeps_the_newest_attempt_per_paper(self) -> None:
        rows = [
            _row("2505.1", "old", started_at="2026-07-21T09:00:00Z"),
            _row("2505.1", "new", started_at="2026-07-21T11:00:00Z"),
        ]
        runs = batch_runs.select_runs(rows)
        self.assertEqual([(r.arxiv_id, r.run_id) for r in runs], [("2505.1", "new")])

    def test_drops_running_rows_by_default(self) -> None:
        rows = [_row("2505.1", "r1", status="running"), _row("2505.2", "r2")]
        self.assertEqual([r.arxiv_id for r in batch_runs.select_runs(rows)], ["2505.2"])
        self.assertEqual(
            [r.arxiv_id for r in batch_runs.select_runs(rows, include_running=True)],
            ["2505.1", "2505.2"],
        )

    def test_skip_audited_leaves_only_ungraded_papers(self) -> None:
        rows = [_row("2505.1", "r1", audit_score=7), _row("2505.2", "r2")]
        runs = batch_runs.select_runs(rows, skip_audited=True)
        self.assertEqual([r.arxiv_id for r in runs], ["2505.2"])

    def test_ignores_rows_without_ids(self) -> None:
        self.assertEqual(batch_runs.select_runs([{"status": "finished"}]), [])


class BundleResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.runs_dir = Path(self.tmp.name) / "agent_runs"
        # Two attempts at the same paper, as a re-run leaves behind.
        for run_id in ("run-old", "run-new"):
            (self.runs_dir / "2505.1" / "8h" / run_id).mkdir(parents=True)
        self.addCleanup(self.tmp.cleanup)

    def test_finds_the_bundle_of_one_specific_run(self) -> None:
        found = batch_runs.bundle_for(self.runs_dir, "2505.1", "run-new")
        self.assertEqual(found, self.runs_dir / "2505.1" / "8h" / "run-new")

    def test_missing_run_or_paper_is_none(self) -> None:
        self.assertIsNone(batch_runs.bundle_for(self.runs_dir, "2505.1", "run-gone"))
        self.assertIsNone(batch_runs.bundle_for(self.runs_dir, "9999.9", "run-new"))

    def test_resolve_splits_present_from_missing(self) -> None:
        runs = batch_runs.select_runs([_row("2505.1", "run-new"), _row("2505.2", "run-x")])
        resolved, missing = batch_runs.resolve_bundles(runs, self.runs_dir)
        self.assertEqual([r.arxiv_id for r in resolved], ["2505.1"])
        self.assertEqual([r.arxiv_id for r in missing], ["2505.2"])

    def test_grade_root_maps_paper_id_to_that_run_only(self) -> None:
        runs = batch_runs.select_runs([_row("2505.1", "run-new")])
        resolved, _ = batch_runs.resolve_bundles(runs, self.runs_dir)
        grade_root = Path(self.tmp.name) / "grade"
        batch_runs.build_grade_root(resolved, grade_root)
        link = grade_root / "2505.1"
        self.assertTrue(link.is_symlink())
        # The auditor's <runs-dir>/<paper_id> contract now resolves to ONE attempt.
        self.assertEqual(link.resolve(), (self.runs_dir / "2505.1" / "8h" / "run-new").resolve())

    def test_grade_root_is_rebuildable(self) -> None:
        runs = batch_runs.select_runs([_row("2505.1", "run-old")])
        resolved, _ = batch_runs.resolve_bundles(runs, self.runs_dir)
        grade_root = Path(self.tmp.name) / "grade"
        batch_runs.build_grade_root(resolved, grade_root)
        resolved[0].bundle = self.runs_dir / "2505.1" / "8h" / "run-new"
        batch_runs.build_grade_root(resolved, grade_root)  # stale link replaced, not an error
        self.assertEqual(
            (grade_root / "2505.1").resolve(),
            (self.runs_dir / "2505.1" / "8h" / "run-new").resolve(),
        )

    def test_ids_file_lists_one_paper_per_line(self) -> None:
        runs = batch_runs.select_runs([_row("2505.1", "run-new"), _row("2505.2", "run-new")])
        path = batch_runs.write_ids_file(Path(self.tmp.name) / "ids.txt", runs)
        self.assertEqual(path.read_text().split(), ["2505.1", "2505.2"])


if __name__ == "__main__":
    unittest.main()
