from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.inputs import (
    EpisodeInput,
    build_context,
    load_lockfile_rows,
    prepare_episodes,
    render_reproduce_prompt,
    resolve_run_paths,
    select_episode_rows,
)

PROMPT_FILE = Path(__file__).resolve().parents[2] / "prompts" / "prompt_reproduce.txt"

ROW = {
    "custom_id": "2505.11483",
    "central_claim": "msf-CNN uses 50% less RAM.",
    "claim_evidence": "Table 4 shows 8.56 kB vs 63 kB.",
    "mre_config": "Run analysis_optimization.py; peak_mem within 5%.",
    "agent_task": "Clone repo, install numpy, run the optimizer.",
    "match_target": {
        "config": "MBV2-w0.35, P1 unconstrained",
        "metric": "Peak RAM usage",
        "value": "8.56 kB",
        "scope": "MBV2-w0.35 model",
        "match_bar_kind": "point_estimate",
    },
    "paper_kind": "empirical",
    "tier": "Easy",
    "selection_band": "0-8",
    "h100_band": "0-8",
    "verified_links": {
        "code": ["https://github.com/TinyPART/msf-CNN"],
        "paper_or_project": [],
        "dataset": [],
        "weights": [],
    },
}


def _write_jsonl(tmp: Path, rows: list[dict]) -> Path:
    path = tmp / "lockfile.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def _args(tmp: Path, **over) -> argparse.Namespace:
    base = dict(
        prompt_file=PROMPT_FILE,
        lockfile=str(_write_jsonl(tmp, [ROW])),
        runs_dir=tmp / "runs",
        paper_id="2505.11483",
        num_prompts=None,
        seed=0,
        run_id="RID",
        budget_h100_hours=8.0,
    )
    base.update(over)
    return argparse.Namespace(**base)


class LoadAndSelectTests(unittest.TestCase):
    def test_load_local_jsonl_indexes_by_arxiv_id(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            rows = load_lockfile_rows(str(_write_jsonl(Path(d), [ROW])))
        self.assertIn("2505.11483", rows)

    def test_select_by_paper_id(self):
        rows = {"2505.11483": ROW, "2401.00002": dict(ROW, custom_id="2401.00002")}
        picked = select_episode_rows(rows, paper_id="2505.11483", num_prompts=None)
        self.assertEqual(len(picked), 1)
        self.assertEqual(picked[0]["custom_id"], "2505.11483")

    def test_select_missing_paper_id_errors(self):
        with self.assertRaises(SystemExit):
            select_episode_rows({"a": ROW}, paper_id="nope", num_prompts=None)

    def test_select_requires_a_mode(self):
        with self.assertRaises(SystemExit):
            select_episode_rows({"a": ROW}, paper_id=None, num_prompts=None)

    def test_num_prompts_sampling_is_seeded(self):
        rows = {str(i): dict(ROW, custom_id=str(i)) for i in range(10)}
        a = select_episode_rows(rows, paper_id=None, num_prompts=3, seed=7)
        b = select_episode_rows(rows, paper_id=None, num_prompts=3, seed=7)
        self.assertEqual([r["custom_id"] for r in a], [r["custom_id"] for r in b])
        self.assertEqual(len(a), 3)


class RunPathTests(unittest.TestCase):
    def test_run_dir_matches_s6_s7_contract(self):
        paths = resolve_run_paths(Path("/runs"), "2505.11483", 8.0, run_id="RID")
        self.assertEqual(str(paths.run_dir), "/runs/2505.11483/8h/RID")
        self.assertEqual(paths.workspace, paths.run_dir / "workspace")
        self.assertEqual(paths.reference, paths.run_dir / "reference")
        self.assertEqual(paths.evidence, paths.run_dir / "evidence")

    def test_fractional_budget_formats_cleanly(self):
        paths = resolve_run_paths(Path("/runs"), "x", 7.5, run_id="RID")
        self.assertEqual(str(paths.run_dir), "/runs/x/7.5h/RID")


class RenderTests(unittest.TestCase):
    def test_no_unfilled_placeholders(self):
        template = PROMPT_FILE.read_text(encoding="utf-8")
        paths = resolve_run_paths(Path("/runs"), "2505.11483", 8.0, run_id="RID")
        prompt = render_reproduce_prompt(template, ROW, budget=8.0, run_paths=paths)
        self.assertNotRegex(prompt, r"\{[A-Z][A-Z0-9_]*\}")
        self.assertIn("2505.11483", prompt)
        self.assertIn("8 H100-equivalent hours", prompt)
        self.assertIn("https://github.com/TinyPART/msf-CNN", prompt)

    def test_pinned_target_and_recipe_are_not_rendered(self):
        # The agent works the target out from the paper itself: no pinned success bar,
        # no spoon-fed config/value/scope, no MRE recipe or step-by-step task. Every
        # cell-defining field below must stay OUT of the prompt.
        template = PROMPT_FILE.read_text(encoding="utf-8")
        paths = resolve_run_paths(Path("/runs"), "2505.11483", 8.0, run_id="RID")
        prompt = render_reproduce_prompt(template, ROW, budget=8.0, run_paths=paths)
        self.assertNotIn("Pinned success bar", prompt)
        self.assertNotIn("reproduce a value close to the target", prompt)  # match_bar guidance
        self.assertNotIn("Peak RAM usage", prompt)  # match_target['metric']
        self.assertNotIn("P1 unconstrained", prompt)  # match_target['config']
        self.assertNotIn("analysis_optimization.py", prompt)  # mre_config
        self.assertNotIn("install numpy", prompt)  # agent_task
        # The central claim IS the anchor and still renders.
        self.assertIn("msf-CNN uses 50% less RAM", prompt)
        # And the agent is told to derive the target from the paper.
        self.assertIn("WORK IT OUT FROM THE PAPER", prompt)

    def test_signals_block_renders_when_present(self):
        template = PROMPT_FILE.read_text(encoding="utf-8")
        paths = resolve_run_paths(Path("/runs"), "2505.11483", 8.0, run_id="RID")
        row = dict(
            ROW,
            signals={
                "code_available": {
                    "value": False,
                    "verification": "tool_verified",
                    "evidence": "Repo is a release-pending TODO stub.",
                },
                "dataset_available": {
                    "value": True,
                    "verification": "paper_text_only",
                    "evidence": "D-NeRF is public.",
                },
                "weights_available": {
                    "value": False,
                    "verification": "not_applicable",
                    "evidence": "No checkpoints released.",
                },
                "dataset_is_standard": {
                    "value": True,
                    "verification": "paper_text_only",
                    "evidence": "Standard benchmark.",
                },
            },
        )
        prompt = render_reproduce_prompt(template, row, budget=8.0, run_paths=paths)
        self.assertIn("Code: no (classifier verification: tool_verified)", prompt)
        self.assertIn("Repo is a release-pending TODO stub.", prompt)
        self.assertIn("Dataset: yes", prompt)
        self.assertNotRegex(prompt, r"\{[A-Z][A-Z0-9_]*\}")

    def test_signals_block_falls_back_when_absent(self):
        template = PROMPT_FILE.read_text(encoding="utf-8")
        paths = resolve_run_paths(Path("/runs"), "2505.11483", 8.0, run_id="RID")
        # ROW carries no `signals` (a pre-signals lockfile row); the block must still fill.
        prompt = render_reproduce_prompt(template, ROW, budget=8.0, run_paths=paths)
        self.assertIn("No pre-assessed availability recorded", prompt)
        self.assertNotRegex(prompt, r"\{[A-Z][A-Z0-9_]*\}")

    def test_unfilled_placeholder_is_rejected(self):
        with self.assertRaises(ValueError):
            render_reproduce_prompt(
                "before {AGENT_TASK} {NOT_A_FIELD} after",
                ROW,
                budget=8.0,
                run_paths=resolve_run_paths(Path("/runs"), "x", 8.0, run_id="RID"),
            )


class PrepareEpisodesTests(unittest.TestCase):
    def test_prepare_one_episode_end_to_end(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            episodes = prepare_episodes(_args(Path(d)))
        self.assertEqual(len(episodes), 1)
        ep = episodes[0]
        self.assertIsInstance(ep, EpisodeInput)
        self.assertEqual(ep.arxiv_id, "2505.11483")
        self.assertTrue(str(ep.run_paths.run_dir).endswith("2505.11483/8h/RID"))
        self.assertNotRegex(ep.prompt, r"\{[A-Z][A-Z0-9_]*\}")

    def test_build_context_carries_episode_state(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            ep = prepare_episodes(_args(Path(d)))[0]
        ctx = build_context(ep)
        self.assertEqual(ctx.arxiv_id, "2505.11483")
        self.assertEqual(ctx.lockfile_row["tier"], "Easy")
        self.assertEqual(ctx.budget.total_h100_hours, 8.0)
        self.assertEqual(ctx.workspace, ep.run_paths.workspace)


if __name__ == "__main__":
    unittest.main()
