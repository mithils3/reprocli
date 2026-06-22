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
from reprocli_repro.slurm import StepResult
from reprocli_repro.tools import REPRO_TOOLS, build_repro_tools, execute_repro_tool_call
from reprocli_repro.tools.run_gpu import run_gpu, run_gpu_tool


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


def _step(stdout: str = "", stderr: str = "", *, rc: int = 0, elapsed: float = 1.0) -> StepResult:
    return StepResult(ok=rc == 0, returncode=rc, stdout=stdout, stderr=stderr, elapsed_s=elapsed, command=["salloc"])


class RunGpuMeteringTests(unittest.TestCase):
    def test_charges_run_time_from_markers_not_queue_wait(self):
        # 30s of marker-bracketed run inside a 600s wall (the extra 570s is queue).
        stderr = "__REPRO_GPU_T0__:1000.0\nreal output\n__REPRO_GPU_T1__:1030.0\n"
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", return_value=_step("done", stderr, elapsed=600.0)):
                res = run_gpu({"command": "python train.py", "gpus": 2, "minutes": 60}, ctx)
            self.assertTrue(res["ok"], res)
            self.assertAlmostEqual(res["run_seconds"], 30.0, places=1)
            # 2 gpu x (30/3600) h x 1.0 (gh200) = 0.016667 H100-h, not the 600s wall.
            self.assertAlmostEqual(res["cost_h100_hours"], 2 * 30 / 3600, places=4)
            self.assertAlmostEqual(ctx.budget.spent_h100_hours, 2 * 30 / 3600, places=4)
            # The agent never sees the timing markers.
            self.assertNotIn("__REPRO_GPU", res["stderr"])
            self.assertIn("real output", res["stderr"])

    def test_falls_back_to_wall_when_markers_absent(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", return_value=_step("ok", "", elapsed=1800.0)):
                res = run_gpu({"command": "echo hi", "gpus": 1, "minutes": 60}, ctx)
            self.assertAlmostEqual(res["run_seconds"], 1800.0, places=1)
            self.assertAlmostEqual(res["cost_h100_hours"], 0.5, places=4)  # 1 gpu x 0.5h

    def test_wrapped_command_brackets_user_command_with_markers(self):
        captured = {}

        def fake_run_step(cluster, workspace, cmd, **kw):
            captured["cmd"] = cmd
            captured["kw"] = kw
            return _step("ok", "")

        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", side_effect=fake_run_step):
                run_gpu({"command": "python eval.py", "minutes": 5}, ctx)
        self.assertIn("python eval.py", captured["cmd"])
        self.assertIn("__REPRO_GPU_T0__", captured["cmd"])
        self.assertIn("__REPRO_GPU_T1__", captured["cmd"])
        # Per-step subprocess timeout is the wall cap plus queue grace, not unbounded.
        self.assertEqual(captured["kw"]["minutes"], 5)
        self.assertGreater(captured["kw"]["timeout"], 5 * 60)

    def test_records_trajectory_and_command_log(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", return_value=_step("ok", "")):
                run_gpu({"command": "python train.py", "minutes": 5}, ctx)
            traj = (ctx.evidence / "trajectory.jsonl").read_text()
            self.assertIn('"type": "run_gpu"', traj)
            self.assertIn("python train.py", traj)
            self.assertIn("run_gpu", (ctx.evidence / "commands.log").read_text())


class RunGpuGuardrailTests(unittest.TestCase):
    def test_refuses_when_worst_case_overspends_and_does_not_launch(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d), budget_hours=1.0)
            with mock.patch("reprocli_repro.tools.run_gpu.run_step") as run:
                res = run_gpu({"command": "python train.py", "gpus": 4, "minutes": 60}, ctx)
            run.assert_not_called()  # refused before launch
            self.assertFalse(res["ok"])
            self.assertIn("refused", res["error"])
            self.assertEqual(ctx.budget.spent_h100_hours, 0.0)
            # The refusal is still recorded for the auditor.
            self.assertIn('"refused"', (ctx.evidence / "trajectory.jsonl").read_text())

    def test_missing_command_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            self.assertFalse(run_gpu({"command": "  "}, ctx)["ok"])


class GpuChoiceTests(unittest.TestCase):
    def test_schema_max_gpus_tracks_node_capacity(self):
        for cap in (4, 8):
            schema = run_gpu_tool(cap)["function"]["parameters"]["properties"]["gpus"]
            self.assertEqual(schema["maximum"], cap)
            self.assertEqual(schema["minimum"], 1)
        # build_repro_tools threads the cap through to the advertised run_gpu tool.
        tool = next(t for t in build_repro_tools(8) if t["function"]["name"] == "run_gpu")
        self.assertEqual(tool["function"]["parameters"]["properties"]["gpus"]["maximum"], 8)

    def test_agent_gpu_choice_is_honored(self):
        captured = {}

        def fake_run_step(cluster, workspace, cmd, **kw):
            captured.update(kw)
            return _step("ok", "")

        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))  # deltaai: 4 GPU/node
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", side_effect=fake_run_step):
                res = run_gpu({"command": "python train.py", "gpus": 3, "minutes": 10}, ctx)
            self.assertEqual(captured["gpus"], 3)
            self.assertEqual(res["gpus"], 3)
            self.assertNotIn("note", res)

    def test_over_capacity_request_is_clamped_and_noted(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))  # deltaai: cap 4
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", return_value=_step("ok", "")):
                res = run_gpu({"command": "python train.py", "gpus": 9, "minutes": 10}, ctx)
            self.assertEqual(res["gpus"], 4)
            self.assertIn("clamped", res["note"])


class DispatchTests(unittest.TestCase):
    def test_run_gpu_is_advertised_and_routed(self):
        names = {t["function"]["name"] for t in REPRO_TOOLS}
        self.assertEqual(names, {"workspace_bash", "read_file", "write_file", "apply_patch", "run_gpu"})

    def test_execute_routes_run_gpu_through_context(self):
        call = {"function": {"name": "run_gpu", "arguments": {"command": "python x.py", "minutes": 5}}}
        with tempfile.TemporaryDirectory() as d:
            ctx = _ctx(Path(d))
            with mock.patch("reprocli_repro.tools.run_gpu.run_step", return_value=_step("ok", "")):
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
