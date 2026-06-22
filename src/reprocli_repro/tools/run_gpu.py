"""The metered GPU step — the reproduction agent's only path to a GPU.

Everything else the agent does (clone, venv, installs, edits, inspecting data)
is cheap CPU work in ``workspace_bash``; ``run_gpu`` is the one tool that actually
provisions a GPU. Each call is a just-in-time ``salloc`` (``slurm.run_step``) that
is released the instant the command exits, so idle GPU time is never charged.

The tool is the budget meter's enforcement point (Phase 4):

* **before launch** -- ``budget.affordable`` refuses a step whose *worst case*
  (``gpus x minutes x hw_multiplier``, the ``--time`` pre-authorization) would
  overspend the remaining H100-hour budget, so a step can never start a charge it
  cannot cover;
* **after the run** -- the step's *run* time (queue wait excluded, measured via
  markers injected around the command) is converted to H100-equivalent hours and
  charged with ``budget.charge``;
* **either way** -- one structured row is appended to ``evidence/trajectory.jsonl``
  and the command is recorded in ``evidence/commands.log`` so the auditor can
  re-trace exactly what ran and what it cost.

When the charge drives the budget to zero the loop's guardrail force-finals the
episode on the next round (``loop.apply_guardrails``); this tool only ever spends.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_DEFAULT_CHARS, function_tool

from reprocli_repro import budget as budget_mod
from reprocli_repro import evidence as evidence_mod
from reprocli_repro.context import ExecutionContext
from reprocli_repro.slurm import StepResult, run_step

# Defaults/bounds for the model-set knobs. ``gpus`` is capped per call to the
# node capacity by ``slurm.build_command``; ``minutes`` is the SLURM ``--time``
# wall cap (and the budget pre-authorization), so it is bounded here too.
DEFAULT_GPUS = 1
DEFAULT_MINUTES = 30
MAX_MINUTES = 24 * 60
# Bound a salloc that never returns (e.g. wedged in queue) without killing a
# legitimately long queue wait: the orchestrator waits the step's own wall cap
# plus this grace before giving up. SLURM's ``--time`` still hard-kills the
# compute at ``minutes`` regardless.
QUEUE_GRACE_SECONDS = 4 * 3600

# Epoch markers wrapped around the agent's command so the meter can bill the
# command's run time and exclude salloc queue wait. Emitted to stderr and
# stripped from what the agent sees.
_T0 = "__REPRO_GPU_T0__"
_T1 = "__REPRO_GPU_T1__"
_MARKER_RE = re.compile(rf"^(?:{_T0}|{_T1}):[0-9.]+$", re.MULTILINE)
_T0_RE = re.compile(rf"{_T0}:([0-9.]+)")
_T1_RE = re.compile(rf"{_T1}:([0-9.]+)")


def run_gpu(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    """Provision a JIT GPU allocation, run one command on it, meter the cost."""
    if ctx.cluster is None:
        return {"ok": False, "tool": "run_gpu", "error": "No cluster profile bound for this episode."}
    if ctx.workspace is None:
        return {"ok": False, "tool": "run_gpu", "error": "No workspace directory for this episode."}
    if ctx.budget is None:
        return {"ok": False, "tool": "run_gpu", "error": "No compute budget bound for this episode."}

    command = str(arguments.get("command") or "").strip()
    if not command:
        return {"ok": False, "tool": "run_gpu", "error": "Missing GPU command to run."}
    gpus = _bounded(arguments.get("gpus"), DEFAULT_GPUS, ctx.cluster.gpus_per_node)
    minutes = _bounded(arguments.get("minutes"), DEFAULT_MINUTES, MAX_MINUTES)
    hw = ctx.cluster.hw

    affordable, reason = budget_mod.affordable(ctx.budget, gpus, minutes, hw)
    if not affordable:
        result = {
            "ok": False,
            "tool": "run_gpu",
            "command": command,
            "error": f"run_gpu refused: {reason}",
            "remaining_h100_hours": round(ctx.budget.remaining(), 4),
        }
        _record(ctx, command, gpus, minutes, hw, step=None, run_seconds=0.0, cost=0.0, refused=reason)
        return result

    step = run_step(
        ctx.cluster,
        ctx.workspace,
        _wrap(command),
        gpus=gpus,
        minutes=minutes,
        timeout=minutes * 60 + QUEUE_GRACE_SECONDS,
    )
    run_seconds = _run_seconds(step)
    cost = budget_mod.step_cost_hours(gpus, run_seconds, hw)
    remaining = ctx.budget.consume(cost)
    _record(ctx, command, gpus, minutes, hw, step=step, run_seconds=run_seconds, cost=cost)

    return {
        "ok": step.ok,
        "tool": "run_gpu",
        "command": command,
        "gpus": gpus,
        "minutes": minutes,
        "hw": hw,
        "returncode": step.returncode,
        "run_seconds": round(run_seconds, 1),
        "cost_h100_hours": round(cost, 4),
        "remaining_h100_hours": round(remaining, 4),
        "budget_exhausted": ctx.budget.exhausted(),
        "stdout": step.stdout[:RUN_FILE_DEFAULT_CHARS],
        "stderr": _clean(step.stderr)[:RUN_FILE_DEFAULT_CHARS],
        "truncated": len(step.stdout) > RUN_FILE_DEFAULT_CHARS
        or len(_clean(step.stderr)) > RUN_FILE_DEFAULT_CHARS,
    }


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _wrap(command: str) -> str:
    """Brace-group the command with epoch markers so run time excludes queue wait.

    ``slurm._inner_script`` appends this as the final ``&&`` term after ``cd`` +
    ``module load``, so the group runs only once setup succeeds; ``$?`` is the
    agent command's own exit code and the markers bracket just its execution.
    """
    return (
        f'{{ echo {_T0}:$(date +%s.%N) >&2; {command}; __rc=$?; '
        f'echo {_T1}:$(date +%s.%N) >&2; exit $__rc; }}'
    )


def _run_seconds(step: StepResult) -> float:
    """Run time from the injected markers; fall back to total wall on absence."""
    t0 = _T0_RE.search(step.stderr)
    t1 = _T1_RE.search(step.stderr)
    if t0 and t1:
        try:
            delta = float(t1.group(1)) - float(t0.group(1))
            if delta >= 0:
                return delta
        except ValueError:
            pass
    return max(0.0, step.elapsed_s)


def _clean(stderr: str) -> str:
    """Drop the timing-marker lines so the agent only sees real step output."""
    return _MARKER_RE.sub("", stderr).strip()


def _record(
    ctx: ExecutionContext,
    command: str,
    gpus: int,
    minutes: int,
    hw: str,
    *,
    step: StepResult | None,
    run_seconds: float,
    cost: float,
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
        "run_seconds": round(run_seconds, 1),
        "cost_h100_hours": round(cost, 4),
        "remaining_h100_hours": round(ctx.budget.remaining(), 4) if ctx.budget else None,
    }
    if refused is not None:
        row["refused"] = refused
    if step is not None:
        row["elapsed_seconds"] = round(step.elapsed_s, 1)
        row["argv"] = " ".join(shlex.quote(a) for a in step.command)
    evidence_mod.append_trajectory(ctx.evidence, row)
    evidence_mod.log_command(
        ctx.evidence,
        f"run_gpu ({gpus} gpu x {minutes} min {hw}): {command}",
        returncode=returncode,
        cwd=ctx.workspace,
        duration_s=run_seconds,
    )


def _bounded(value: Any, default: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


RUN_GPU_TOOL = function_tool(
    "run_gpu",
    "Provision a just-in-time GPU allocation and run ONE command on it (training, "
    "evaluation, or scoring). GPUs are not held while you reason or install -- only "
    "for this command -- and every GPU-second is charged against the paper's "
    "H100-hour budget, so request the fewest gpus and minutes that suffice and do "
    "all CPU work (clone, venv, deps, edits) with workspace_bash first. The command "
    "runs with the workspace as its working directory; cost and remaining budget are "
    "returned and recorded to evidence/.",
    {
        "command": {
            "type": "string",
            "description": "The GPU command to run (e.g. `python train.py ...`).",
        },
        "gpus": {
            "type": "integer",
            "default": DEFAULT_GPUS,
            "minimum": 1,
            "description": "GPUs for this single step (bounded by the node's capacity).",
        },
        "minutes": {
            "type": "integer",
            "default": DEFAULT_MINUTES,
            "minimum": 1,
            "maximum": MAX_MINUTES,
            "description": "Wallclock cap (SLURM --time); also the budget pre-authorization.",
        },
    },
    ["command"],
)

RUN_GPU_HANDLERS = {"run_gpu": run_gpu}
