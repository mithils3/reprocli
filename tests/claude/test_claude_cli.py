from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_claude import __main__ as cli
from reprocli_claude import agent
from reprocli_repro.batch_runs import Run
from tests.claude.test_claude_agent import VERDICT, StubClient, _text


class SelectionTests(unittest.TestCase):
    def test_requires_something_to_grade(self) -> None:
        with self.assertRaises(SystemExit):
            cli.parse_args(["--runs-dir", "x"])

    def test_split_picks_the_matching_claims_file(self) -> None:
        args = cli.parse_args(["--batch", "slurm-1", "--split", "dev"])
        self.assertTrue(args.claims.endswith("dev_split.jsonl"))
        self.assertTrue(cli.parse_args(["--batch", "slurm-1"]).claims.endswith("eval_100.jsonl"))

    def test_output_paths_are_named_after_the_batch(self) -> None:
        args = cli.parse_args(["--batch", "slurm-2687371"])
        self.assertEqual(args.output.name, "audit_slurm-2687371.jsonl")
        self.assertEqual(args.extracted_output.name, "audit_slurm-2687371_extracted.jsonl")

    def test_paper_ids_resolve_to_their_newest_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "2505.1" / "8h" / "run-a"
            bundle.mkdir(parents=True)
            (bundle / "report.json").write_text("{}", encoding="utf-8")
            args = cli.parse_args(["--paper-ids", "2505.1", "2505.2", "--runs-dir", tmp])
            runs = cli.select_runs(args)
        self.assertEqual([run.arxiv_id for run in runs], ["2505.1"])  # 2505.2 has no bundle
        self.assertEqual(runs[0].bundle, bundle)


class AuditRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle = Path(self.tmp.name) / "bundle"
        self.bundle.mkdir()
        (self.bundle / "report.json").write_text('{"reproduced": false}', encoding="utf-8")
        self.args = cli.parse_args([
            "--paper-ids", "2505.1",
            "--runs-dir", self.tmp.name,
            "--output", str(Path(self.tmp.name) / "raw.jsonl"),
            "--extracted-output", str(Path(self.tmp.name) / "verdicts.jsonl"),
            "--no-stream",
        ])
        self.run = Run(run_id="rid-1", arxiv_id="2505.1", status="finished",
                       budget=8.0, audit_score=None, bundle=self.bundle)

    def _row(self, client: StubClient) -> dict:
        return cli.audit_run(client, self.run, "grade this", self.args, None)

    def test_writes_both_jsonl_files_and_returns_the_verdict(self) -> None:
        row = self._row(StubClient([_text(json.dumps(VERDICT))] * 2))
        self.assertEqual(row["score"], 9)
        self.assertEqual(row["verdict"], "reproduced")
        verdicts = [json.loads(line) for line in Path(self.args.extracted_output).read_text().splitlines()]
        self.assertEqual(verdicts[0]["custom_id"], "2505.1")
        self.assertEqual(verdicts[0]["score"], 9)
        raw = [json.loads(line) for line in Path(self.args.output).read_text().splitlines()]
        self.assertEqual(raw[0]["run_id"], "rid-1")
        self.assertEqual(raw[0]["bundle"], str(self.bundle))
        self.assertIn("cost_usd", raw[0]["usage"])

    def test_unparseable_submission_lands_as_a_degraded_row(self) -> None:
        row = self._row(StubClient([_text("no json here")] * 2))
        self.assertIsNone(row["score"])
        self.assertEqual(row["verification_status"], "degraded")

    def test_high_cheat_flag_caps_the_score_through_the_shared_finalizer(self) -> None:
        cheated = {
            **VERDICT,
            "cheat_flags": [
                {"kind": "echoed_prose_number", "evidence": "report.json", "severity": "high"}
            ],
        }
        row = self._row(StubClient([_text(json.dumps(cheated))] * 2))
        self.assertEqual(row["score"], 0)
        self.assertEqual(row["reported_score"], 9)
        self.assertEqual(row["verdict"], "disqualified")

    def test_usage_is_returned_for_the_cost_summary(self) -> None:
        row = self._row(StubClient([_text(json.dumps(VERDICT))] * 2))
        self.assertIsInstance(row["usage"], agent.Usage)
        self.assertGreater(row["usage"].output, 0)


class SummaryTests(unittest.TestCase):
    def test_summary_survives_a_mix_of_graded_and_degraded_rows(self) -> None:
        usage = agent.Usage()
        usage.add(type("U", (), {"input_tokens": 100, "output_tokens": 10,
                                 "cache_creation_input_tokens": 0,
                                 "cache_read_input_tokens": 900})())
        rows = [{"score": 8, "reproduced": True, "usage": usage}, {"score": None, "usage": usage}]
        args = argparse.Namespace(extracted_output=Path("v.jsonl"))
        cli._summarize(rows, args)  # prints to stderr; must not raise on the None score


if __name__ == "__main__":
    unittest.main()
