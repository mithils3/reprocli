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
import re
from collections.abc import Callable
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
from reprocli_repro.inputs import new_run_id  # noqa: E402
from reprocli_repro import report as report_mod  # noqa: E402
from reprocli_repro.cli_args import parse_args as harness_parse_args  # noqa: E402
from reprocli_repro.tools import execute_repro_tool_call  # noqa: E402
from reprocli_repro.context import ExecutionContext  # noqa: E402

sys.path.insert(0, str(HERE.parent))
from codex_events import Recorder, attach_requests  # noqa: E402
from task_text import paper_task_text  # noqa: E402

CODEX_VENDOR = Path(os.environ.get(
    "CODEX_VENDOR_DIR",
    "/work/nvme/bfvr/msalunkhe/rebuttal/codex/node_modules/@openai/codex-linux-arm64"
    "/vendor/aarch64-unknown-linux-musl",
))
DEFAULT_RUNS_DIR = "/work/nvme/bfvr/msalunkhe/reprocli/agent_runs"
DEFAULT_LEDGER = "/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl"
DEFAULT_MODEL = "gpt-6.1-terra"
DEFAULT_WALL_HOURS = 48.0
WATCHDOG_SECONDS = 30
KILL_GRACE_SECONDS = 10

CONTAINER_CODEX = "/opt/codex/bin/codex"
CONTAINER_SHIM_DIR = "/opt/codex_arm"
CONTAINER_IO = "/codex_io"
CONTAINER_BRIDGE = f"{CONTAINER_IO}/bridge"
CONTAINER_HOME = f"{CONTAINER_IO}/codex_home"
CONTAINER_SCHEMA = f"{CONTAINER_IO}/report_schema.json"
CONTAINER_FINAL = f"{CONTAINER_IO}/final_message.json"
# Keep every request under the 256k input ceiling of the flex tier: Codex's window is pinned
# to 256k and it compacts its own history once the prompt passes 200k.
CONTEXT_WINDOW = 256000
AUTO_COMPACT_LIMIT = 200000
# Rate limits and 5xx errors are retried inside Codex with its own backoff; a turn that still
# fails with one of them is resumed by the launcher (MAX_RESUMES times, exponential backoff).
REQUEST_RETRIES = 100
MAX_RESUMES = 50
RESUME_BACKOFF_BASE = 30
RESUME_BACKOFF_CAP = 600
TRANSIENT = re.compile(
    r"429|rate.?limit|too many requests|overloaded|unexpected status 5\d\d|internal server error|"
    r"bad gateway|service unavailable|gateway timeout|stream closed|timed out|"
    r"flex capacity unavailable|capacity unavailable",
    re.IGNORECASE,
)
# OpenAI's flex-tier 429 ("Flex capacity unavailable"). After FLEX_FAILURES_BEFORE_FALLBACK in a row
# the run continues on the standard tier, priced at 2x flex from that point.
FLEX_CAPACITY = re.compile(r"flex capacity unavailable", re.IGNORECASE)
FLEX_FAILURES_BEFORE_FALLBACK = 3
FLEX = "flex"
STANDARD = "default"  # accepted by codex exec -c service_tier=... (verified: turn completes)
FRESH_PREFIX = (
    "The earlier session of this run stopped on a provider capacity error and cannot be resumed. "
    "Your progress is on disk: read /repro/evidence/plan.md, commands.log and the other evidence "
    "files, and check /repro/workspace, before you continue. The original task follows.\n\n"
)
RESUME_PROMPT = ("Continue the task from where it stopped. The previous request failed on a provider "
                 "error (rate limit or server error), which is not the end of the task.")
def exec_flags(tier: str) -> str:
    return EXEC_FLAGS_TEMPLATE.replace("{tier}", tier)  # not str.format: the provider table has braces


EXEC_FLAGS_TEMPLATE = (
    "--json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox "
    "-c model_reasoning_effort=high -c service_tier={tier} "
    f"-c model_context_window={CONTEXT_WINDOW} -c model_auto_compact_token_limit={AUTO_COMPACT_LIMIT} "
    # Built-in provider ids cannot be overridden, so the same endpoint is a custom provider
    # with the retry budget set; the key comes from OPENAI_API_KEY in the environment.
    "-c 'model_providers.openai-retry={name=\"OpenAI\",base_url=\"https://api.openai.com/v1\","
    "env_key=\"OPENAI_API_KEY\",wire_api=\"responses\","
    f"request_max_retries={REQUEST_RETRIES},stream_max_retries={REQUEST_RETRIES}}}' "
    "-c model_provider=openai-retry"
)


def codex_body(model: str, prompt: str, *, kind: str = "work", tier: str = FLEX) -> str:
    """The bash body run inside the sandbox: put the run_gpu shim on PATH, then exec codex.

    ``work`` starts the session, ``resume`` continues it after a transient failure, and
    ``final`` continues it once more with the report schema and no new work.
    """
    flags = exec_flags(tier)
    fresh_head = f"exec {CONTAINER_CODEX} exec {flags} -C /repro/workspace -m {shlex.quote(model)}"
    schema = f"--output-schema {CONTAINER_SCHEMA} -o {CONTAINER_FINAL}"
    head = {
        # `codex exec resume` keeps the session's stored service tier and ignores -c service_tier
        # overrides, so a run that falls back to the standard tier starts a fresh session instead.
        "fresh": fresh_head,
        "final_fresh": f"{fresh_head} {schema}",
        "work": f"exec {CONTAINER_CODEX} exec {flags} -C /repro/workspace -m {shlex.quote(model)}",
        "resume": f"exec {CONTAINER_CODEX} exec resume --last {flags} -m {shlex.quote(model)}",
        "final": (f"exec {CONTAINER_CODEX} exec resume --last {flags} -m {shlex.quote(model)} "
                  f"--output-schema {CONTAINER_SCHEMA} -o {CONTAINER_FINAL}"),
    }[kind]
    return (
        # Runtime thread caps: the login node allows 1000 threads+procs per user.
        f"export PATH={CONTAINER_SHIM_DIR}/bin:$PATH CODEX_HOME={CONTAINER_HOME} "
        "TOKIO_WORKER_THREADS=4 RAYON_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "
        f"CODEX_ARM_BRIDGE={CONTAINER_BRIDGE}; "
        f"{head} -- {shlex.quote(prompt)}"
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
        self.queue_wait_s = 0.0
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
            acquiring = self.ctx.session is None
            started = time.monotonic()
            result = execute_repro_tool_call(
                {"function": {"name": "run_gpu", "arguments": json.dumps(arguments)}}, self.ctx,
            )
            # Queue time is the wait from the request to the grant. It is not charged (the meter starts
            # at the grant, gpu_session.ensure_session) and is reported as queue_wait_minutes.
            session = self.ctx.session
            if acquiring and session is not None and session.started >= started:
                self.queue_wait_s += session.started - started
        self.recorder.log_gpu(result)
        return result

    def _reply(self, rid: str, result: dict[str, Any]) -> None:
        target = self.res / f"{rid}.json"
        staged = self.res / f"{rid}.tmp"
        staged.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        os.replace(staged, target)


class Interrupted(BaseException):
    """Raised in the main thread when SIGTERM or SIGINT reaches the launcher."""


def _interrupt(signum: int, _frame: Any) -> None:
    # Once interrupted, further signals are ignored so cleanup always finishes.
    if not getattr(_interrupt, "fired", False):
        _interrupt.fired = True  # type: ignore[attr-defined]
        raise Interrupted(signal.Signals(signum).name)


def _proc_rows() -> list[tuple[int, int, str]]:
    """(pid, pgid, state) for every process of this user, read from /proc."""
    rows = []
    uid = os.getuid()
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        try:
            if os.stat(entry.path).st_uid != uid:
                continue
            stat = Path(entry.path, "stat").read_text()
        except OSError:
            continue
        fields = stat.rsplit(")", 1)[1].split()
        rows.append((int(entry.name), int(fields[2]), fields[0]))
    return rows


def group_pids(pgid: int) -> set[int]:
    """Live (non-zombie) members of a process group."""
    return {pid for pid, group, state in _proc_rows() if group == pgid and state != "Z"}


def tagged_pids(tag: str) -> set[int]:
    """Live processes of this user whose environment carries ``CODEX_ARM_RUN=<tag>``."""
    wanted = f"CODEX_ARM_RUN={tag}".encode()
    found = set()
    for pid, _group, state in _proc_rows():
        if state == "Z":
            continue
        try:
            env = Path(f"/proc/{pid}/environ").read_bytes()
        except OSError:
            continue
        if wanted in env.split(b"\0"):
            found.add(pid)
    return found


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
        self.tag = ctx.run_dir.name
        # Apptainer forwards APPTAINERENV_* into the container as the plain name, so codex and
        # its children carry the tag in their environment.
        os.environ["APPTAINERENV_CODEX_ARM_RUN"] = self.tag
        self.stop_reason: str | None = None
        self.resumes: list[dict[str, Any]] = []
        self.tier = FLEX
        self.tier_fallback_at: str | None = None
        self.flex_streak = 0
        self.gave_up = False
        self.fresh_pending = False  # the next retry starts a fresh session (after a tier fallback)
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
        argv = bound.wrap_argv(body)
        # Own PID namespace: the agent cannot see or signal host processes such as a pending salloc.
        at = argv.index("apptainer")
        argv.insert(at + 2, "--pid")
        return argv

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
            if not self.bridge.refusing and self.ctx.budget.exhausted():
                self._stop("budget_exhausted")
                return
            if time.monotonic() > self.deadline:
                self._stop("wall_clock")
                return

    def _stop(self, reason: str) -> None:
        if self.stop_reason is None:
            self.stop_reason = reason
            self.recorder.log_line(f"STOP {reason}: terminating codex run {self.tag}")
        self.terminate()

    def terminate(self, grace: float = KILL_GRACE_SECONDS) -> None:
        """Stop every process of this run: its process group, and anything tagged with its run id.

        TERM first, KILL for whatever is still alive after ``grace`` seconds. Tagged processes
        are found through their environment (CODEX_ARM_RUN), so orphans that left the group
        (codex-code-mode-host, tool children) are still caught.
        """
        self.bridge.stop.set()
        pgid = self.proc.pid if self.proc is not None else None

        def signal_all(sig: int) -> None:
            if pgid is not None:
                try:
                    os.killpg(pgid, sig)
                except ProcessLookupError:
                    pass
            for pid in tagged_pids(self.tag):
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass

        def alive() -> set[int]:
            members = tagged_pids(self.tag)
            if pgid is not None:
                members |= group_pids(pgid)
            return members

        if not alive():
            return
        signal_all(signal.SIGTERM)
        deadline = time.monotonic() + grace
        while alive() and time.monotonic() < deadline:
            time.sleep(0.5)
        if alive():
            self.recorder.log_line(f"KILL {sorted(alive())} after {grace:g}s")
            signal_all(signal.SIGKILL)

    def _phase(self, body: str, label: str, events_path: Path) -> int:
        self.recorder.failure = None
        proc = self._launch(body, label)
        reader = threading.Thread(target=self._stream, args=(proc, events_path), daemon=True)
        reader.start()
        done = threading.Event()
        threading.Thread(target=self._watchdog, args=(done,), daemon=True).start()
        code = proc.wait()
        reader.join()
        done.set()
        return code

    def _transient_failure(self) -> bool:
        failure = self.recorder.failure
        return bool(failure) and bool(TRANSIENT.search(failure))

    def _wait(self, seconds: float, *, honor_stop: bool) -> None:
        """Sleep through the backoff; stop early on a budget or wall-clock stop when honored."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if honor_stop and self.stop_reason is not None:
                return
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))

    def _with_retries(self, first: Callable[[str], str], retry: Callable[[str], str],
                      fresh: Callable[[str], str], label: str, events_path: Path, *, honor_stop: bool) -> int:
        """One phase, resumed after transient provider failures (same session, backoff, MAX_RESUMES).

        A rate limit or a flex-capacity 429 is never the agent's own end of work. After
        FLEX_FAILURES_BEFORE_FALLBACK consecutive flex-capacity failures the run switches to the
        standard tier for the rest of the run. ``honor_stop=False`` (the final pass) keeps retrying
        after a budget stop, but still respects the wall clock.
        """
        rc = self._phase(first(self.tier), label, events_path)
        while self._transient_failure() and time.monotonic() < self.deadline:
            if honor_stop and self.stop_reason is not None:
                break
            if len(self.resumes) >= MAX_RESUMES:
                self.recorder.log_line(f"GIVE UP {label} after {MAX_RESUMES} resumes")
                self.gave_up = True
                if honor_stop:
                    self.stop_reason = "error"
                break
            failure = (self.recorder.failure or "")[:300]
            self.flex_streak = self.flex_streak + 1 if FLEX_CAPACITY.search(failure) else 0
            if self.flex_streak >= FLEX_FAILURES_BEFORE_FALLBACK and self.tier == FLEX:
                self.tier = STANDARD
                self.tier_fallback_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.fresh_pending = True
                self.flex_streak = 0
                self.recorder.log_line(f"TIER FALLBACK flex -> standard at {self.tier_fallback_at} "
                                       f"after {FLEX_FAILURES_BEFORE_FALLBACK} flex-capacity failures")
            n = len(self.resumes) + 1
            backoff = min(RESUME_BACKOFF_CAP, RESUME_BACKOFF_BASE * 2 ** (n - 1))
            self.resumes.append({
                "n": n, "phase": label, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "after": failure, "backoff_s": backoff, "tier": self.tier,
                "session": "fresh" if self.fresh_pending else "resume",
            })
            self.recorder.log_line(f"RESUME {n}/{MAX_RESUMES} ({label}) tier={self.tier} after {backoff}s "
                                   f"backoff; failure: {failure}")
            self._wait(backoff, honor_stop=honor_stop)
            if honor_stop and self.stop_reason is not None:
                break
            if self.fresh_pending:
                body = fresh(self.tier)
                self.fresh_pending = False
            else:
                body = retry(self.tier)
            rc = self._phase(body, f"{label}-resume{n}", events_path)
        if not self._transient_failure():
            self.flex_streak = 0
        return rc

    def execute(self, task: str, final_prompt: str) -> tuple[str, str]:
        """Run the work phase, then the final report pass. Returns (exit_reason, final report content)."""
        events_path = self.io_dir.parent / "codex_events.jsonl"
        self.bridge.start()
        rc = self._with_retries(
            lambda tier: codex_body(self.model, task, kind="work", tier=tier),
            lambda tier: codex_body(self.model, RESUME_PROMPT, kind="resume", tier=tier),
            lambda tier: codex_body(self.model, FRESH_PREFIX + task, kind="fresh", tier=tier),
            "work", events_path, honor_stop=True,
        )
        if self.stop_reason is None and rc != 0:
            self.stop_reason = "error"
        exit_reason = self.stop_reason or "natural"
        gpu_session.release(self.ctx, exit_reason)

        self.bridge.refusing = True
        final_body = lambda tier: codex_body(self.model, final_prompt, kind="final", tier=tier)  # noqa: E731
        final_fresh = lambda tier: codex_body(self.model, FRESH_PREFIX + final_prompt, kind="final_fresh", tier=tier)  # noqa: E731
        self._with_retries(final_body, final_body, final_fresh, "final", events_path, honor_stop=False)
        final = self.io_dir / "final_message.json"
        content = final.read_text(encoding="utf-8") if final.exists() else ""
        self.bridge.stop.set()
        return exit_reason, content


def cancel_pending_salloc() -> int:
    """SIGINT the salloc children this launcher still has pending, so teardown leaves no queued job."""
    me, cancelled = os.getpid(), 0
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        try:
            stat = Path(entry.path, "stat").read_text().rsplit(")", 1)[1].split()
            if int(stat[1]) != me:
                continue
            cmd = Path(entry.path, "cmdline").read_bytes().split(b"\0")
            if cmd and os.path.basename(cmd[0]) == b"salloc":
                os.kill(int(entry.name), signal.SIGINT)
                cancelled += 1
        except (OSError, ValueError, IndexError):
            continue
    return cancelled


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
    parser.add_argument("--split", help="lockfile split: eval or dev (default: harness default)")
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    own = build_parser().parse_args(argv)
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set; source it from ~/.bashrc first (value is never printed).")
    os.environ.setdefault("REPROCLI_SLURM_ACCOUNT", "bfvr-dtai-gh")
    # A run_gpu call waits for its grant without a limit, as the thin harness's call does in practice.
    os.environ.setdefault("REPRO_QUEUE_GRACE_HOURS", "500")  # poll timeouts overflow above ~572 h (int32 ms)
    os.environ.setdefault("APPTAINERENV_OPENAI_API_KEY", os.environ["OPENAI_API_KEY"])
    os.environ.setdefault("APPTAINERENV_CODEX_API_KEY", os.environ["OPENAI_API_KEY"])  # codex exec reads this one

    harness_argv = ["--paper-id", own.paper_id, "--runs-dir", own.runs_dir, "--model", own.model,
                    "--budget-h100-hours", str(own.budget_h100_hours)]
    # The arm is in the run id, so a Codex run is never mistaken for a thin-harness run in agent_runs/.
    run_id = own.run_id or f"codex-{own.model}-{new_run_id()}"
    for flag, value in (("--partition", own.partition), ("--apptainer-image", own.apptainer_image),
                        ("--lockfile", own.lockfile), ("--split", own.split), ("--run-id", run_id)):
        if value:
            harness_argv += [flag, value]
    args = harness_parse_args(harness_argv)
    sandbox.require_apptainer(args.cluster_profile.apptainer_image)
    sandbox.forward_env()

    (ep,) = inputs.prepare_episodes(args)
    task = own.task_text if own.task_text is not None else paper_task_text(ep.row, budget=ep.budget, harness="codex")
    sb = sandbox.from_run_paths(
        ep.run_paths, image=args.cluster_profile.apptainer_image,
        cpus=args.cluster_profile.sandbox_cpus, mem_gb=args.cluster_profile.sandbox_mem_gb,
    )
    workspace.prepare_workspace(ep.run_paths, arxiv_id=ep.arxiv_id, materialize_ref=False)
    (ep.run_paths.run_dir / "task.txt").write_text(task + "\n", encoding="utf-8")
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
        "work_command": codex_body(own.model, task, kind="work"),
        "resume_command": codex_body(own.model, RESUME_PROMPT, kind="resume"),
        "final_command": codex_body(own.model, args.final_no_tools_message, kind="final"),
        "standard_tier_value": STANDARD,
        "request_retries": REQUEST_RETRIES,
        "max_resumes": MAX_RESUMES,
        "task_text": task,
        "context_window": CONTEXT_WINDOW,
        "auto_compact_token_limit": AUTO_COMPACT_LIMIT,
        "sandbox": sb.status(),
    }, indent=2) + "\n", encoding="utf-8")

    recorder = Recorder(run_dir, ep.run_paths.evidence, own.model, ep.run_paths.workspace)
    run = Run(args, ctx, own.model, own.wall_hours, io_dir, recorder)
    signal.signal(signal.SIGTERM, _interrupt)
    signal.signal(signal.SIGINT, _interrupt)
    # A hangup (the tmux pane or sweep shell ending) must not kill a run mid-turn: the run then
    # has no report, no ledger row and no cleanup. Ignored hangups keep it alive.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    exit_reason, content = "error", ""
    try:
        exit_reason, content = run.execute(task, args.final_no_tools_message)
    except Interrupted as exc:
        recorder.log_line(f"STOP signal {exc}: codex run {run.tag} terminated")
        exit_reason, content = "interrupted", ""
    except Exception as exc:  # the bundle still gets a report.json, as in the thin harness
        recorder.log_line(f"ERROR launcher: {type(exc).__name__}: {exc}")
        exit_reason, content = "error", ""
    finally:
        run.terminate()
        cancel_pending_salloc()
        gpu_session.teardown_all([ctx])
    report_mod.write_episode_report(ctx, content, exit_reason)
    usage = recorder.write_usage()
    totals = attach_requests(run_dir, io_dir / "codex_home", own.model, run.tier_fallback_at)
    run_meta = json.loads((run_dir / "codex_run.json").read_text(encoding="utf-8"))
    run_meta["resumes"] = run.resumes
    run_meta["tier"] = run.tier
    run_meta["queue_wait_minutes"] = round(run.bridge.queue_wait_s / 60, 2)
    run_meta["tier_fallback_at"] = run.tier_fallback_at
    (run_dir / "codex_run.json").write_text(json.dumps(run_meta, indent=2) + "\n", encoding="utf-8")
    recorder.log_line(f"DONE exit_reason={exit_reason} usd={totals['usd']} requests={totals['requests']} "
                      f"resumes={len(run.resumes)}")
    append_ledger(Path(own.ledger), {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "item": own.item,
        "provider": "openai",
        "model": own.model,
        "in": totals["input_tokens"],
        "cached": totals["cached_input_tokens"],
        "out": totals["output_tokens"],
        "usd": totals["usd"],
        "requests": totals["requests"],
        "run_dir": str(run_dir),
        "arm": "codex",
    })
    print(f"run_dir={run_dir} exit_reason={exit_reason} usage={usage} usd={totals['usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
