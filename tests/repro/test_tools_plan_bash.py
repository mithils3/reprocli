from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import evidence
from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools.plan import update_plan
from reprocli_repro.tools.workspace_bash import workspace_bash


def _ctx(root: Path) -> ExecutionContext:
    ws, ref, ev = root / "workspace", root / "reference", root / "evidence"
    for p in (ws, ref, ev):
        p.mkdir(parents=True, exist_ok=True)
    evidence.init_evidence(ev)
    return ExecutionContext(arxiv_id="x", workspace=ws, reference=ref, evidence=ev)


class UpdatePlanTests(unittest.TestCase):
    PLAN = [
        {"step": "Install torch + verify GPU", "status": "completed"},
        {"step": "Clone repo and install deps", "status": "in_progress"},
        {"step": "Run the MRE and score", "status": "pending"},
    ]

    def test_records_plan_on_context_and_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            res = update_plan({"plan": self.PLAN, "explanation": "deps next"}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual(ctx.plan, self.PLAN)
            self.assertEqual(res["explanation"], "deps next")
            rendered = (ctx.evidence / "plan.md").read_text()
            self.assertIn("[x] Install torch + verify GPU", rendered)
            self.assertIn("[~] Clone repo and install deps", rendered)
            self.assertIn("[ ] Run the MRE and score", rendered)

    def test_replaces_previous_plan(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            update_plan({"plan": self.PLAN}, ctx)
            newer = [{"step": "Write report", "status": "in_progress"}]
            update_plan({"plan": newer}, ctx)
            self.assertEqual(ctx.plan, newer)

    def test_rejects_two_in_progress(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            bad = [
                {"step": "a", "status": "in_progress"},
                {"step": "b", "status": "in_progress"},
            ]
            res = update_plan({"plan": bad}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("in_progress", res["error"])
            self.assertEqual(ctx.plan, [])

    def test_rejects_bad_status_and_empty(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            self.assertFalse(update_plan({"plan": []}, ctx)["ok"])
            self.assertFalse(update_plan({"plan": [{"step": "x", "status": "doing"}]}, ctx)["ok"])
            self.assertFalse(update_plan({"plan": [{"step": "", "status": "pending"}]}, ctx)["ok"])


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
