from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro import evidence
from reprocli_repro.cluster import resolve_cluster
from reprocli_repro.context import Budget, ExecutionContext
from reprocli_repro.slurm import SessionHandle, StepResult
from reprocli_repro.tools import build_repro_tools, execute_repro_tool_call
from reprocli_repro.tools.run_gpu import run_gpu
from reprocli_repro.tools.run_gpu_schema import run_gpu_tool


def _ctx(root: Path, *, budget_hours: float = 8.0) -> ExecutionContext:
    ws, ref, ev = root / "workspace", root / "reference", root / "evidence"
    for p in (ws, ref, ev):
        p.mkdir(parents=True, exist_ok=True)
    evidence.init_evidence(ev)
    return ExecutionContext(
        arxiv_id="x",
        workspace=ws,
        reference=ref,
        evidence=ev,
        budget=Budget(total_h100_hours=budget_hours),
        cluster=resolve_cluster("deltaai"),
    )


def _handle(jobid: str | None = "555", *, ok: bool = True, stderr: str = "") -> SessionHandle:
    return SessionHandle(ok=ok, jobid=jobid, stderr=stderr, command=["salloc"])


def _step(stdout: str = "ok", stderr: str = "", *, rc: int = 0, elapsed: float = 1.0) -> StepResult:
    return StepResult(ok=rc == 0, returncode=rc, stdout=stdout, stderr=stderr, elapsed_s=elapsed, command=["srun"])


def _patch(*, acquire=None, run=None, release=None):
    """Patch the three slurm seams the session lifecycle calls (shared module attrs)."""
    return (
        mock.patch("reprocli_repro.slurm.acquire_session", return_value=acquire or _handle()),
        mock.patch("reprocli_repro.slurm.run_in_session", return_value=run if run is not None else _step()),
        mock.patch("reprocli_repro.slurm.release_session", side_effect=release or (lambda *_: None)),
    )


class RunGpuGuardrailTests(unittest.TestCase):
    def test_refuses_to_start_a_session_that_overspends_and_does_not_acquire(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d), budget_hours=1.0)
            acq, run, rel = _patch()
            with acq as a, run, rel:
                res = run_gpu({"command": "python train.py", "gpus": 4, "minutes": 60}, ctx)
            a.assert_not_called()  # refused before any allocation
            self.assertFalse(res["ok"])
            self.assertIn("refused", res["error"])
            self.assertEqual(ctx.budget.spent_h100_hours, 0.0)
            self.assertIn('"refused"', (ctx.evidence / "trajectory.jsonl").read_text())

    def test_acquire_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            acq, run, rel = _patch(acquire=_handle(None, ok=False, stderr="salloc: error: out of nodes"))
            with acq, run, rel:
                res = run_gpu({"command": "python a.py"}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("could not acquire", res["error"])
            self.assertIsNone(ctx.session)

    def test_missing_command_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            self.assertFalse(run_gpu({"command": "  "}, ctx)["ok"])

    def test_records_trajectory_and_command_log(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            acq, run, rel = _patch()
            with acq, run, rel:
                run_gpu({"command": "python train.py", "minutes": 5}, ctx)
            traj = (ctx.evidence / "trajectory.jsonl").read_text()
            self.assertIn('"type": "run_gpu"', traj)
            self.assertIn("python train.py", traj)
            self.assertIn("run_gpu", (ctx.evidence / "commands.log").read_text())


class GpuChoiceTests(unittest.TestCase):
    def test_schema_max_gpus_tracks_node_capacity(self):
        for cap in (4, 8):
            schema = run_gpu_tool(cap)["function"]["parameters"]["properties"]["gpus"]
            self.assertEqual(schema["maximum"], cap)
            self.assertEqual(schema["minimum"], 1)
        tool = next(t for t in build_repro_tools(8) if t["function"]["name"] == "run_gpu")
        self.assertEqual(tool["function"]["parameters"]["properties"]["gpus"]["maximum"], 8)

    def test_release_param_is_advertised(self):
        props = run_gpu_tool(4)["function"]["parameters"]["properties"]
        self.assertIn("release", props)
        self.assertEqual(props["release"]["type"], "boolean")

    def test_agent_gpu_choice_sizes_the_session(self):
        captured = {}

        def fake_acquire(cluster, *, gpus, minutes, timeout=None, partition=None):
            captured["gpus"] = gpus
            return _handle("555")

        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))  # deltaai: 4 GPU/node
            with mock.patch("reprocli_repro.slurm.acquire_session", side_effect=fake_acquire), \
                 mock.patch("reprocli_repro.slurm.run_in_session", return_value=_step()), \
                 mock.patch("reprocli_repro.slurm.release_session"):
                res = run_gpu({"command": "python train.py", "gpus": 3, "minutes": 10}, ctx)
            self.assertEqual(captured["gpus"], 3)
            self.assertEqual(res["gpus"], 3)
            self.assertNotIn("note", res)

    def test_over_capacity_request_is_clamped_and_noted(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))  # deltaai: cap 4
            acq, run, rel = _patch()
            with acq, run, rel:
                res = run_gpu({"command": "python train.py", "gpus": 9, "minutes": 10}, ctx)
            self.assertEqual(res["gpus"], 4)
            self.assertIn("clamped", res["note"])


class DispatchTests(unittest.TestCase):
    def test_run_gpu_is_advertised_and_routed(self):
        names = {t["function"]["name"] for t in build_repro_tools(4)}
        self.assertEqual(
            names,
            {"workspace_bash", "write_file", "apply_patch", "update_plan", "fetch_url", "list_partitions", "run_gpu"},
        )

    def test_execute_routes_run_gpu_through_context(self):
        call = {"function": {"name": "run_gpu", "arguments": {"command": "python x.py", "minutes": 5}}}
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            acq, run, rel = _patch()
            with acq, run, rel:
                res = execute_repro_tool_call(call, ctx)
            self.assertTrue(res["ok"], res)
            self.assertEqual(res["tool"], "run_gpu")

    def test_unknown_tool_reports_available(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            res = execute_repro_tool_call({"function": {"name": "nope", "arguments": {}}}, ctx)
            self.assertFalse(res["ok"])
            self.assertIn("run_gpu", res["error"])


if __name__ == "__main__":
    unittest.main()
