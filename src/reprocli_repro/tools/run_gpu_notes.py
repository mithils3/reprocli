"""The model-facing notes/warnings/refusals for ``run_gpu`` (split for file size).

``run_gpu.py`` holds the handler; this module builds every advisory string it
returns — clamp notes, session-expiry warnings, the reuse note, and the pre-launch
staleness refusal. Message quality is load-bearing here: the 06-29 batch showed
agents burning sessions on exactly the semantics these spell out (``minutes`` on a
reuse call does NOT extend the hold), so each message states the semantics and the
recovery action, not just the failure.
"""

from __future__ import annotations

from typing import Any

# Warn the model when the held allocation is within this many seconds of its --time
# wall: past it SLURM reclaims the node mid-step and any unsaved state is lost.
SESSION_WARN_SECONDS = 120
# Refuse to LAUNCH a new command on a session with less than this left on its
# --time. Three 06-29 runs started multi-minute jobs into a <2-min hold and lost
# them; a launch that near the wall can only be killed, so this is a deterministic
# guard, not a heuristic.
STALE_LAUNCH_SECONDS = 120


def bounded(value: Any, default: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def clamp_note(requested: Any, effective: int, cap: int) -> str | None:
    """Tell the agent when its requested GPU count was clamped to the node cap."""
    if requested in (None, ""):
        return None
    asked = _safe_int(requested)
    if asked is not None and asked != effective:
        return f"requested gpus={asked} clamped to {effective} (node capacity is {cap})."
    return None


def expiry_warning(session: Any, remaining_seconds: float) -> str | None:
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


def stale_refusal(session: Any, remaining_seconds: float) -> str:
    """Why a launch on a nearly-expired held session was refused, and the way out.

    States the reuse semantics explicitly: ``minutes`` is fixed at acquire, so passing
    a bigger value on a reuse call cannot extend the hold — the fix is always
    release + re-acquire.
    """
    return (
        f"the held session (jobid {session.jobid}) has only ~{remaining_seconds:.0f}s of its "
        f"{session.minutes}-min --time left; SLURM would kill this command almost immediately "
        "and its work would be lost. Note that minutes= is fixed when a session is ACQUIRED — "
        "passing minutes= on a reuse call does NOT extend the hold. Release this session "
        "(run_gpu release=true) and start a fresh one with minutes= sized to the job."
    )


def reuse_note(arguments: dict[str, Any], session: Any) -> str | None:
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
