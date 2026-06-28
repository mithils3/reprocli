"""The GPU step — the reproduction agent's interactive GPU shell.

Everything else the agent does (clone, venv, installs, edits, inspecting data) is
cheap CPU work in ``workspace_bash``; ``run_gpu`` is the one tool that provisions a
GPU. The first call ACQUIRES one ``salloc`` allocation that **stays held**; every
later call runs into the same node (``slurm.run_in_session``) with no new queue
wait, so the agent installs torch, verifies CUDA, and runs the experiment as
successive ``run_gpu`` calls on one allocation instead of re-queueing each time.
The agent frees it with ``release=true`` the moment it is done; ``gpu_session``
also releases it at episode teardown.

The tool is the budget meter's enforcement point. The held node is billed by
**wall clock** — ``gpus x (held seconds) x hw`` — because the GPU is reserved across
the agent's reasoning/install gaps, not only while a command runs:

* **before acquiring** -- ``budget.affordable`` refuses to start a session whose
  worst case (``gpus x minutes x hw``, the ``--time`` pre-authorization) would
  overspend the remaining H100-hour budget;
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
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_DEFAULT_CHARS, function_tool

from reprocli_repro import budget as budget_mod
from reprocli_repro import evidence as evidence_mod
from reprocli_repro import gpu_session, slurm
from reprocli_repro.context import ExecutionContext

# Defaults/bounds for the model-set knobs, applied on the call that *starts* a
# session. ``gpus`` is capped to the node by ``slurm.build_acquire``; ``minutes`` is
# the SLURM ``--time`` (the hold's lifetime and the budget pre-authorization).
DEFAULT_GPUS = 1
DEFAULT_MINUTES = 30
MAX_MINUTES = 24 * 60
# Bound an acquire that never returns (wedged in queue) without killing a legitimate
# long queue wait: wait the hold's own wall cap plus this grace before giving up.
QUEUE_GRACE_SECONDS = 4 * 3600
# Warn the model when the held allocation is within this many seconds of its --time
# wall: past it SLURM reclaims the node mid-step and any unsaved state is lost.
SESSION_WARN_SECONDS = 120


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
    gpus = _bounded(arguments.get("gpus"), DEFAULT_GPUS, cap)
    minutes = _bounded(arguments.get("minutes"), DEFAULT_MINUTES, MAX_MINUTES)
    note = _clamp_note(arguments.get("gpus"), gpus, cap)

    # Acquire the session if none is held; pre-authorize its worst-case hold first.
    if ctx.session is None:
        affordable, reason = budget_mod.affordable(ctx.budget, gpus, minutes, ctx.cluster.hw)
        if not affordable:
            _record(ctx, command, gpus, minutes, ctx.cluster.hw, step=None, cost=0.0, refused=reason)
            return {
                "ok": False,
                "tool": "run_gpu",
                "command": command,
                "error": f"run_gpu refused: {reason}",
                "remaining_h100_hours": round(ctx.budget.remaining(), 4),
            }
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
        note = _reuse_note(arguments, session) or note

    step = slurm.run_in_session(
        ctx.cluster, ctx.workspace, command, jobid=session.jobid,
        timeout=session.minutes * 60 + 600, sandbox=ctx.sandbox,
    )
    if slurm.session_lost(step):
        gpu_session.drop_lost(ctx)
        return {
            "ok": False,
            "tool": "run_gpu",
            "command": command,
            "error": "GPU session expired or was cancelled (hit --time or scancel); "
            "the next run_gpu call will start a fresh allocation.",
            "stderr": step.stderr[:RUN_FILE_DEFAULT_CHARS],
            "remaining_h100_hours": round(ctx.budget.remaining(), 4),
        }

    cost = gpu_session.charge_accrued(ctx)
    held = gpu_session.held_seconds(session)
    session_remaining = max(0.0, session.minutes * 60 - held)
    _record(ctx, command, session.gpus, session.minutes, session.hw, step=step, cost=cost, held=held)
    if release_after:
        gpu_session.release(ctx, "agent")

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
        "stdout": step.stdout[:RUN_FILE_DEFAULT_CHARS],
        "stderr": step.stderr[:RUN_FILE_DEFAULT_CHARS],
        "truncated": len(step.stdout) > RUN_FILE_DEFAULT_CHARS or len(step.stderr) > RUN_FILE_DEFAULT_CHARS,
    }
    warning = None if release_after else _expiry_warning(session, session_remaining)
    if warning:
        result["session_expiry_warning"] = warning
    if note:
        result["note"] = note
    return result


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
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


def _bounded(value: Any, default: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def _clamp_note(requested: Any, effective: int, cap: int) -> str | None:
    """Tell the agent when its requested GPU count was clamped to the node cap."""
    if requested in (None, ""):
        return None
    try:
        asked = int(requested)
    except (TypeError, ValueError):
        return None
    if asked != effective:
        return f"requested gpus={asked} clamped to {effective} (node capacity is {cap})."
    return None


def _expiry_warning(session: Any, remaining_seconds: float) -> str | None:
    """Loud heads-up when the held allocation is about to hit its --time wall.

    Past the wall SLURM reclaims the node mid-step, so anything not written to disk
    (training state, in-memory results) is gone. Surfaced so the model checkpoints and
    re-acquires a fresh/longer hold *before* it loses the node, not after.
    """
    if remaining_seconds > SESSION_WARN_SECONDS:
        return None
    return (
        f"SESSION ENDING: ~{remaining_seconds / 60:.1f} min left on this {session.minutes}-min "
        f"allocation (jobid {session.jobid}) before SLURM reclaims the node and loses any unsaved "
        "state. Save results/checkpoints to disk now. Long work left? release=true and start a "
        "fresh session with a larger minutes= (or finish what fits in the time remaining)."
    )


def _reuse_note(arguments: dict[str, Any], session: Any) -> str | None:
    """Warn when gpus/minutes are passed to a call that reuses a live session."""
    asked_gpus = arguments.get("gpus")
    if asked_gpus not in (None, "") and _safe_int(asked_gpus) not in (None, session.gpus):
        return (
            f"a GPU session is already held ({session.gpus} gpu, jobid {session.jobid}); "
            "gpus/minutes are fixed until you release it (run_gpu release=true) and start a new one."
        )
    return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def run_gpu_tool(gpus_per_node: int) -> dict:
    """Build the ``run_gpu`` schema, advertising this cluster's per-node GPU cap."""
    return function_tool(
        "run_gpu",
        "Run ONE command on a real GPU (training, evaluation, scoring, verifying the "
        "container's torch.cuda, nvidia-smi). The GPU allocation is HELD across calls: the "
        "first run_gpu acquires it (you may wait in the queue once) and every later "
        "run_gpu runs on the SAME node with NO new queue wait, so install → verify → "
        "run as successive calls. You are billed WALL-CLOCK for the whole time the "
        "allocation is held — gpus x held-time x hw, including while you reason or "
        "install between commands — so set release=true the moment you are done with "
        "the GPU to stop the meter (re-acquire later if you need it again). The command "
        "runs with the workspace as its cwd; cost and remaining budget are returned and "
        "recorded to evidence/. Each result also reports session_remaining_seconds — the "
        "wall left before this allocation hits its `minutes` (--time) cap and SLURM reclaims "
        "the node (losing any unsaved state); when it runs low a session_expiry_warning tells "
        "you to checkpoint to disk and, if you need more time, release and re-acquire.",
        {
            "command": {
                "type": "string",
                "description": "The GPU command to run (e.g. `python train.py ...`). Omit only with release=true to just free the session.",
            },
            "gpus": {
                "type": "integer",
                "default": DEFAULT_GPUS,
                "minimum": 1,
                "maximum": gpus_per_node,
                "description": (
                    f"GPUs to hold (1-{gpus_per_node}, one node); set only on the call that STARTS "
                    "the session. Default 1 is for smoke tests — take more to fit a model/batch too "
                    "big for one GPU or to finish sooner; throughput scales with gpus (wall budget ~same)."
                ),
            },
            "minutes": {
                "type": "integer",
                "default": DEFAULT_MINUTES,
                "minimum": 1,
                "maximum": MAX_MINUTES,
                "description": "Max lifetime of the held allocation (SLURM --time) and the budget "
                "pre-authorization; set on the call that starts the session. Pick ~ how long you will hold it.",
            },
            "release": {
                "type": "boolean",
                "default": False,
                "description": "Set true when you are done with the GPU: frees the allocation after "
                "this command (or immediately if no command) so wall-clock billing stops.",
            },
            "partition": {
                "type": "string",
                "description": "SLURM partition (node pool) to allocate on. Omit to use this "
                "cluster's default; call list_partitions to see the alternatives (e.g. a "
                "faster-queueing interactive pool). Takes effect only on the call that STARTS "
                "the session; fixed until you release it.",
            },
        },
        [],  # command is enforced by the handler (it is optional only with release=true)
    )


RUN_GPU_HANDLERS = {"run_gpu": run_gpu}
