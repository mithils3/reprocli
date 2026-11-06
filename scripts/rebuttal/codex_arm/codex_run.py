"""Run the OpenAI Codex CLI as the reproduction agent, inside the harness's sandbox.

The launcher reuses the harness's own setup (episode rows, run directory, workspace,
Apptainer sandbox, budget, GPU session, report writer). Codex runs in the same
``apptainer exec`` wrapper as a thin-harness step, with the same binds and CPU and RAM
caps. Its stock tools and system prompt stay as they are. The one addition is ``run_gpu``,
a shim on PATH inside the sandbox that forwards each call to this process. This process
then calls the harness's own ``run_gpu`` handler, so allocation, budget metering and
evidence match the thin harness.

Usage (DeltaAI login node, venv from ~/reprocli):
    source <(rg '^export OPENAI_API_KEY=' ~/.bashrc)
    python codex_run.py --paper-id 2401.00001 --budget-h100-hours 0.05 \
        --task-text "Run ..." --model gpt-6.1-terra
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_SRC = HERE.parents[2] / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from reprocli_repro import gpu_session, inputs, sandbox, workspace  # noqa: E402
from reprocli_repro import report as report_mod  # noqa: E402
from reprocli_repro.cli_args import parse_args as harness_parse_args  # noqa: E402
from reprocli_repro.tools import execute_repro_tool_call  # noqa: E402
from reprocli_repro.context import ExecutionContext  # noqa: E402

from codex_events import Recorder  # noqa: E402

CODEX_VENDOR = Path(os.environ.get(
    "CODEX_VENDOR_DIR",
    "/work/nvme/bfvr/msalunkhe/rebuttal/codex/node_modules/@openai/codex-linux-arm64"
    "/vendor/aarch64-unknown-linux-musl",
))
DEFAULT_RUNS_DIR = "/work/nvme/bfvr/msalunkhe/rebuttal/codex/runs"
DEFAULT_LEDGER = "/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl"
DEFAULT_MODEL = "gpt-6.1-terra"
DEFAULT_WALL_HOURS = 48.0
WATCHDOG_SECONDS = 30
KILL_GRACE_SECONDS = 60

CONTAINER_CODEX = "/opt/codex/bin/codex"
CONTAINER_SHIM_DIR = "/opt/codex_arm"
CONTAINER_IO = "/codex_io"
CONTAINER_BRIDGE = f"{CONTAINER_IO}/bridge"
CONTAINER_HOME = f"{CONTAINER_IO}/codex_home"
CONTAINER_SCHEMA = f"{CONTAINER_IO}/report_schema.json"
CONTAINER_FINAL = f"{CONTAINER_IO}/final_message.json"
EXEC_FLAGS = (
    "--json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox "
    "-c model_reasoning_effort=high -c service_tier=flex"
)


def codex_body(model: str, prompt: str, *, resume: bool, final_extra: str = "") -> str:
    """The bash body run inside the sandbox: put the run_gpu shim on PATH, then exec codex."""
    if resume:
        head = f"exec {CONTAINER_CODEX} exec resume --last {EXEC_FLAGS} -m {shlex.quote(model)}"
        head += f" --output-schema {CONTAINER_SCHEMA} -o {CONTAINER_FINAL}"
    else:
        head = (f"exec {CONTAINER_CODEX} exec {EXEC_FLAGS} -C /repro/workspace "
                f"-m {shlex.quote(model)}")
    return (
        f"export PATH={CONTAINER_SHIM_DIR}/bin:$PATH CODEX_HOME={CONTAINER_HOME} "
        f"CODEX_ARM_BRIDGE={CONTAINER_BRIDGE}; "
        f"{head} {final_extra}-- {shlex.quote(prompt)}"
    )


class Bridge:
    """Serves run_gpu requests written by the in-sandbox shim, one at a time."""

    def __init__(self, io_dir: Path, ctx: ExecutionContext, recorder: Recorder) -> None:
        self.req = io_dir / "bridge" / "req"
        self.res = io_dir / "bridge" / "res"
        self.req.mkdir(parents=True, exist_ok=True)
        self.res.mkdir(parents=True, exist_ok=True)
        self.ctx = ctx
        self.recorder = recorder
        self.lock = threading.Lock()
        self.refusing = False
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="codex-bridge", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _loop(self) -> None:
        while not self.stop.is_set():
            for path in sorted(self.req.glob("*.json")):
                try:
                    request = json.loads(path.read_text(encoding="utf-8"))
                    path.unlink()
                except (OSError, ValueError):
                    continue
                result = self._serve(request.get("arguments") or {})
                self._reply(str(request.get("id") or path.stem), result)
            self.stop.wait(0.5)

    def _serve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.refusing:
            return {"ok": False, "tool": "run_gpu", "error": "Tools are off: the final report pass is running."}
        with self.lock:
            result = execute_repro_tool_call(
                {"function": {"name": "run_gpu", "arguments": json.dumps(arguments)}}, self.ctx,
            )
        self.recorder.log_gpu(result)
        return result

    def _reply(self, rid: str, result: dict[str, Any]) -> None:
        target = self.res / f"{rid}.json"
        staged = self.res / f"{rid}.tmp"
        staged.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        os.replace(staged, target)


class Run:
    """One Codex run: work phase, then a schema-constrained final report pass."""

    def __init__(self, args: argparse.Namespace, ctx: ExecutionContext, model: str, wall_hours: float,
                 io_dir: Path, recorder: Recorder) -> None:
        self.args = args
        self.ctx = ctx
        self.model = model
        self.deadline = time.monotonic() + wall_hours * 3600
        self.io_dir = io_dir
        self.recorder = recorder
        self.bridge = Bridge(io_dir, ctx, recorder)
        self.stop_reason: str | None = None
        self.proc: subprocess.Popen | None = None

    def _launch(self, body: str, label: str) -> subprocess.Popen:
        argv = self.sandbox_argv(body)
        self.recorder.phase = label
        self.recorder.log_line(f"launch {label}: codex exec ({self.model})")
        proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=(self.io_dir / f"codex_stderr_{label}.log").open("w"),
            start_new_session=True, text=True, encoding="utf-8",
        )
        self.proc = proc
        return proc

    def sandbox_argv(self, body: str) -> list[str]:
        sb = self.ctx.sandbox
        extra = (
            sandbox.Bind(str(CODEX_VENDOR), "/opt/codex", ro=True),
            sandbox.Bind(str(HERE), CONTAINER_SHIM_DIR, ro=True),
            sandbox.Bind(str(self.io_dir), CONTAINER_IO),
        )
        bound = dataclasses.replace(sb, binds=sb.binds + extra)
        return bound.wrap_argv(body)

    def _stream(self, proc: subprocess.Popen, events_path: Path) -> None:
        with events_path.open("a", encoding="utf-8") as sink:
            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue
                sink.write(line + "\n")
                sink.flush()
                try:
                    event = json.loads(line)
                except ValueError:
                    self.recorder.log_line(f"non-json stdout: {line[:500]}")
                    continue
                self.recorder.handle(event)

    def _watchdog(self, done: threading.Event) -> None:
        while not done.wait(WATCHDOG_SECONDS):
            if self.ctx.session is not None and self.bridge.lock.acquire(blocking=False):
                try:
                    gpu_session.charge_accrued(self.ctx)
                finally:
                    self.bridge.lock.release()
            if self.ctx.budget.exhausted():
                self._stop("budget_exhausted")
                return
            if time.monotonic() > self.deadline:
                self._stop("wall_clock")
                return

    def _stop(self, reason: str) -> None:
        if self.stop_reason is None:
            self.stop_reason = reason
            self.recorder.log_line(f"STOP {reason}: terminating codex (pid {self.proc.pid if self.proc else '-'})")
        proc = self.proc
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            threading.Timer(KILL_GRACE_SECONDS, self._kill, args=(proc,)).start()

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)

    def _phase(self, body: str, label: str, events_path: Path) -> int:
        proc = self._launch(body, label)
        reader = threading.Thread(target=self._stream, args=(proc, events_path), daemon=True)
        reader.start()
        done = threading.Event()
        threading.Thread(target=self._watchdog, args=(done,), daemon=True).start()
        code = proc.wait()
        reader.join()
        done.set()
        return code

    def execute(self, task: str, final_prompt: str) -> tuple[str, str]:
        """Run both phases. Returns (exit_reason, final report content)."""
        events_path = self.io_dir.parent / "codex_events.jsonl"
        self.bridge.start()
        rc = self._phase(codex_body(self.model, task, resume=False), "work", events_path)
        if self.stop_reason is None and rc != 0:
            self.stop_reason = "error"
        exit_reason = self.stop_reason or "natural"
        gpu_session.release(self.ctx, exit_reason)

        self.bridge.refusing = True
        final_extra = ""
        self._phase(codex_body(self.model, final_prompt, resume=True, final_extra=final_extra),
                    "final", events_path)
        final = self.io_dir / "final_message.json"
        content = final.read_text(encoding="utf-8") if final.exists() else ""
        self.bridge.stop.set()
        return exit_reason, content


def codex_version() -> str:
    out = subprocess.run([str(CODEX_VENDOR / "bin" / "codex"), "--version"], capture_output=True, text=True)
    return out.stdout.strip()


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--budget-h100-hours", type=float, required=True)
    parser.add_argument("--task-text", help="replace the rendered reproduction prompt with this text")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR)
    parser.add_argument("--wall-hours", type=float, default=DEFAULT_WALL_HOURS)
    parser.add_argument("--ledger", default=DEFAULT_LEDGER)
    parser.add_argument("--item", default="YGTR-codex")
    parser.add_argument("--partition")
    parser.add_argument("--apptainer-image")
    parser.add_argument("--lockfile")
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    own = build_parser().parse_args(argv)
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set; source it from ~/.bashrc first (value is never printed).")
    os.environ.setdefault("REPROCLI_SLURM_ACCOUNT", "betw-dtai-gh")
    os.environ.setdefault("APPTAINERENV_OPENAI_API_KEY", os.environ["OPENAI_API_KEY"])
    os.environ.setdefault("APPTAINERENV_CODEX_API_KEY", os.environ["OPENAI_API_KEY"])  # codex exec reads this one

    harness_argv = ["--paper-id", own.paper_id, "--runs-dir", own.runs_dir, "--model", own.model,
                    "--budget-h100-hours", str(own.budget_h100_hours)]
    for flag, value in (("--partition", own.partition), ("--apptainer-image", own.apptainer_image),
                        ("--lockfile", own.lockfile), ("--run-id", own.run_id)):
        if value:
            harness_argv += [flag, value]
    args = harness_parse_args(harness_argv)
    sandbox.require_apptainer(args.cluster_profile.apptainer_image)
    sandbox.forward_env()

    (ep,) = inputs.prepare_episodes(args)
    task = own.task_text if own.task_text is not None else ep.prompt
    sb = sandbox.from_run_paths(
        ep.run_paths, image=args.cluster_profile.apptainer_image,
        cpus=args.cluster_profile.sandbox_cpus, mem_gb=args.cluster_profile.sandbox_mem_gb,
    )
    workspace.prepare_workspace(ep.run_paths, arxiv_id=ep.arxiv_id, materialize_ref=False)
    ctx = inputs.build_context(ep)
    ctx.cluster = args.cluster_profile
    ctx.sandbox = sb

    run_dir = ep.run_paths.run_dir
    io_dir = run_dir / "codex_io"
    (io_dir / "codex_home").mkdir(parents=True, exist_ok=True)
    (io_dir / "report_schema.json").write_text(json.dumps(report_mod.REPORT_JSON_SCHEMA), encoding="utf-8")
    (run_dir / "codex_run.json").write_text(json.dumps({
        "codex_version": codex_version(),
        "codex_binary": str(CODEX_VENDOR / "bin" / "codex"),
        "model": own.model,
        "budget_h100_hours": own.budget_h100_hours,
        "wall_hours": own.wall_hours,
        "work_command": codex_body(own.model, task, resume=False),
        "final_command": codex_body(own.model, args.final_no_tools_message, resume=True),
        "task_text": task,
        "sandbox": sb.status(),
    }, indent=2) + "\n", encoding="utf-8")

    recorder = Recorder(run_dir, ep.run_paths.evidence, own.model, ep.run_paths.workspace)
    run = Run(args, ctx, own.model, own.wall_hours, io_dir, recorder)
    try:
        exit_reason, content = run.execute(task, args.final_no_tools_message)
    except Exception as exc:  # the bundle still gets a report.json, as in the thin harness
        recorder.log_line(f"ERROR launcher: {type(exc).__name__}: {exc}")
        exit_reason, content = "error", ""
    finally:
        gpu_session.teardown_all([ctx])
    report_mod.write_episode_report(ctx, content, exit_reason)
    usage = recorder.write_usage()
    totals = recorder.totals()
    recorder.log_line(f"DONE exit_reason={exit_reason} usd={totals['usd']} turns={totals['turns']}")
    append_ledger(Path(own.ledger), {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "item": own.item,
        "provider": "openai",
        "model": own.model,
        "in": totals["input_tokens"],
        "cached": totals["cached_input_tokens"],
        "out": totals["output_tokens"],
        "usd": totals["usd"],
        "run_dir": str(run_dir),
        "arm": "codex",
    })
    print(f"run_dir={run_dir} exit_reason={exit_reason} usage={usage} usd={totals['usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
