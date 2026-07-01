"""The GPU step — the reproduction agent's interactive GPU shell.

Everything else the agent does (clone, venv, installs, edits, inspecting data) is
cheap CPU work in ``workspace_bash``; ``run_gpu`` is the one tool that provisions a
GPU. The first call ACQUIRES one ``salloc`` allocation that **stays held**; every
later call runs into the same node (``slurm.run_in_session``) with no new queue
wait, so the agent installs torch, verifies CUDA, and runs the experiment as
successive ``run_gpu`` calls on one allocation instead of re-queueing each time.
The agent frees it with ``release=true`` the moment it is done; ``gpu_session``
also releases it at episode teardown.

Every step's output is *streamed* to ``evidence/gpu_step_<n>.log`` as it arrives
(``slurm.run_in_session`` tees it), so a step killed at the --time wall or our
timeout still leaves everything it printed on disk — and this tool returns the
tail instead of nothing. Blind re-runs of killed jobs were the single biggest
compute sink in the 06-29 batch.

The tool is the budget meter's enforcement point. The held node is billed by
**wall clock** — ``gpus x (held seconds) x hw`` — because the GPU is reserved across
the agent's reasoning/install gaps, not only while a command runs:

* **before acquiring** -- ``budget.affordable`` refuses to start a session whose
  worst case (``gpus x minutes x hw``, the ``--time`` pre-authorization) would
  overspend the remaining H100-hour budget;
* **before reusing** -- a launch onto a held session with under
  ``STALE_LAUNCH_SECONDS`` of --time left is refused outright (the command could
  only be killed);
* **after each step / on release** -- ``gpu_session.charge_accrued`` bills the wall
  held since the last charge (the loop guardrail charges it between rounds too, so a
  long reasoning gap on a held node still depletes the budget);
* **either way** -- one structured row lands in ``evidence/trajectory.jsonl`` and the
  command in ``evidence/commands.log`` so the auditor can re-trace what ran and cost.

When the charge drives the budget to zero the loop's guardrail releases the session
and force-finals the episode on the next round (``loop.apply_guardrails``).
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_DEFAULT_CHARS

from reprocli_repro import budget as budget_mod
from reprocli_repro import evidence as evidence_mod
from reprocli_repro import gpu_session, slurm
from reprocli_repro.context import ExecutionContext
from reprocli_repro.sandbox import CONTAINER_EVIDENCE
from reprocli_repro.tools import output as output_mod
from reprocli_repro.tools.run_gpu_notes import (
    STALE_LAUNCH_SECONDS,
    bounded,
    clamp_note,
    expiry_warning,
    reuse_note,
    stale_refusal,
)

# Defaults/bounds for the model-set knobs, applied on the call that *starts* a
# session. ``gpus`` is capped to the node by ``slurm.build_acquire``; ``minutes`` is
# the SLURM ``--time`` (the hold's lifetime and the budget pre-authorization).
DEFAULT_GPUS = 1
DEFAULT_MINUTES = 30
MAX_MINUTES = 24 * 60
# Bound an acquire that never returns (wedged in queue) without killing a legitimate
# long queue wait: wait the hold's own wall cap plus this grace before giving up.
QUEUE_GRACE_SECONDS = 4 * 3600
# Chars of streamed output returned when the step was killed (wall/timeout): the
# tail is where the last checkpoint line / progress state / traceback is.
KILL_TAIL_CHARS = 4000


def run_gpu(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    """Run one command on the held GPU allocation (acquiring/releasing as asked)."""
    for field, label in (("cluster", "cluster profile"), ("workspace", "workspace directory"), ("budget", "compute budget")):
        if getattr(ctx, field) is None:
            return {"ok": False, "tool": "run_gpu", "error": f"No {label} bound for this episode."}

    command = str(arguments.get("command") or "").strip()
    release_after = bool(arguments.get("release"))
    if not command:
        if release_after:
            return _release_only(ctx)
        return {"ok": False, "tool": "run_gpu", "error": "Missing GPU command to run."}

    cap = ctx.cluster.gpus_per_node
    gpus = bounded(arguments.get("gpus"), DEFAULT_GPUS, cap)
    minutes = bounded(arguments.get("minutes"), DEFAULT_MINUTES, MAX_MINUTES)
    note = clamp_note(arguments.get("gpus"), gpus, cap)

    # Acquire the session if none is held; pre-authorize its worst-case hold first.
    if ctx.session is None:
        affordable, reason = budget_mod.affordable(ctx.budget, gpus, minutes, ctx.cluster.hw)
        if not affordable:
            _record(ctx, command, gpus, minutes, ctx.cluster.hw, step=None, cost=0.0, refused=reason)
            return _refused(ctx, command, reason)
        # partition picks the pool for THIS allocation (default = the cluster profile's);
        # discover the choices with list_partitions. Fixed until the session is released.
        partition = str(arguments.get("partition") or "").strip() or None
        session, err = gpu_session.ensure_session(
            ctx, gpus=gpus, minutes=minutes, partition=partition,
            timeout=minutes * 60 + QUEUE_GRACE_SECONDS,
        )
        if session is None:
            return {"ok": False, "tool": "run_gpu", "command": command, "error": f"could not acquire GPU allocation: {err}"}
    else:
        session = ctx.session
        # Deterministic pre-launch staleness guard: a command started this close to
        # the --time wall can only be killed, so refuse instead of wasting it.
        stale_remaining = session.minutes * 60 - gpu_session.held_seconds(session)
        if stale_remaining < STALE_LAUNCH_SECONDS:
            cost = gpu_session.charge_accrued(ctx)
            reason = stale_refusal(session, max(0.0, stale_remaining))
            _record(ctx, command, session.gpus, session.minutes, session.hw, step=None, cost=cost, refused=reason)
            return _refused(ctx, command, reason)
        note = reuse_note(arguments, session) or note

    log_path = evidence_mod.next_gpu_log(ctx.evidence) if ctx.evidence is not None else None
    step = slurm.run_in_session(
        ctx.cluster, ctx.workspace, command, jobid=session.jobid,
        timeout=session.minutes * 60 + 600, sandbox=ctx.sandbox, log_path=log_path,
    )
    log_ref = _log_ref(ctx, log_path)
    if slurm.session_lost(step):
        gpu_session.drop_lost(ctx)
        return {
            "ok": False,
            "tool": "run_gpu",
            "command": command,
            "error": "GPU session expired or was cancelled (hit --time or scancel); "
            "the next run_gpu call will start a fresh allocation.",
            "output_log": log_ref,
            "stdout_tail": output_mod.tail(step.stdout, KILL_TAIL_CHARS),
            "stderr": output_mod.tail(step.stderr, KILL_TAIL_CHARS),
            "remaining_h100_hours": round(ctx.budget.remaining(), 4),
        }

    cost = gpu_session.charge_accrued(ctx)
    held = gpu_session.held_seconds(session)
    session_remaining = max(0.0, session.minutes * 60 - held)
    _record(ctx, command, session.gpus, session.minutes, session.hw, step=step, cost=cost, held=held)
    if release_after:
        gpu_session.release(ctx, "agent")

    elide_note = f" — full output in {log_ref}" if log_ref else ""
    stdout, t_out = output_mod.shape(step.stdout, RUN_FILE_DEFAULT_CHARS, note=elide_note)
    stderr, t_err = output_mod.shape(step.stderr, RUN_FILE_DEFAULT_CHARS, note=elide_note)
    result = {
        "ok": step.ok,
        "tool": "run_gpu",
        "command": command,
        "gpus": session.gpus,
        "minutes": session.minutes,
        "hw": session.hw,
        "partition": session.partition,
        "returncode": step.returncode,
        "run_seconds": round(step.elapsed_s, 1),
        "held_seconds": round(held, 1),
        "session_remaining_seconds": 0.0 if release_after else round(session_remaining, 1),
        "cost_h100_hours": round(cost, 4),
        "remaining_h100_hours": round(ctx.budget.remaining(), 4),
        "budget_exhausted": ctx.budget.exhausted(),
        "session_released": release_after,
        "session_jobid": None if release_after else session.jobid,
        "output_log": log_ref,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": t_out or t_err,
    }
    warning = None if release_after else expiry_warning(session, session_remaining)
    if warning:
        result["session_expiry_warning"] = warning
    if note:
        result["note"] = note
    return result


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _refused(ctx: ExecutionContext, command: str, reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "tool": "run_gpu",
        "command": command,
        "error": f"run_gpu refused: {reason}",
        "remaining_h100_hours": round(ctx.budget.remaining(), 4),
    }


def _log_ref(ctx: ExecutionContext, log_path: Path | None) -> str | None:
    """The step log's path *as the agent can reach it* (container path when sandboxed)."""
    if log_path is None:
        return None
    if ctx.sandbox is not None:
        return f"{CONTAINER_EVIDENCE}/{log_path.name}"
    return str(log_path)


def _release_only(ctx: ExecutionContext) -> dict[str, Any]:
    """Honor ``release=true`` with no command: free the held allocation, if any."""
    record = gpu_session.release(ctx, "agent")
    if record is None:
        return {"ok": True, "tool": "run_gpu", "note": "no GPU session was held.", "session_released": False}
    return {
        "ok": True,
        "tool": "run_gpu",
        "session_released": True,
        "held_seconds": record["held_seconds"],
        "cost_h100_hours": record["final_charge_h100_hours"],
        "remaining_h100_hours": round(ctx.budget.remaining(), 4) if ctx.budget else None,
    }


def _record(
    ctx: ExecutionContext,
    command: str,
    gpus: int,
    minutes: int,
    hw: str,
    *,
    step: slurm.StepResult | None,
    cost: float,
    held: float = 0.0,
    refused: str | None = None,
) -> None:
    """Append one trajectory row + a commands.log line for this step."""
    if ctx.evidence is None:
        return
    returncode = None if step is None else step.returncode
    row: dict[str, Any] = {
        "type": "run_gpu",
        "command": command,
        "gpus": gpus,
        "minutes": minutes,
        "hw": hw,
        "returncode": returncode,
        "run_seconds": None if step is None else round(step.elapsed_s, 1),
        "held_seconds": round(held, 1),
        "cost_h100_hours": round(cost, 4),
        "remaining_h100_hours": round(ctx.budget.remaining(), 4) if ctx.budget else None,
    }
    if refused is not None:
        row["refused"] = refused
    if step is not None:
        row["argv"] = " ".join(shlex.quote(a) for a in step.command)
    evidence_mod.append_trajectory(ctx.evidence, row)
    evidence_mod.log_command(
        ctx.evidence,
        f"run_gpu ({gpus} gpu x {minutes} min {hw}): {command}",
        returncode=returncode,
        cwd=ctx.workspace,
        duration_s=None if step is None else step.elapsed_s,
    )


RUN_GPU_HANDLERS = {"run_gpu": run_gpu}

# The ``run_gpu`` JSON schema (``run_gpu_tool``) lives in ``run_gpu_schema.py``; the
# model-facing notes/warnings/refusal strings live in ``run_gpu_notes.py``.
