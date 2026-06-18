"""Per-episode execution state for the reproduction agent.

``ExecutionContext`` is the repro analog of the classifier's ``Paper``: one
instance per paper/episode, keyed by ``custom_id`` (the arXiv id) in the tool
loop. Where the classifier threads ``execute_tool_call(call, paper=paper)``, the
repro loop threads ``execute_repro_tool_call(call, ctx)`` so every tool acts on
*this* episode's mutable workspace, budget meter, allocation, and evidence dir.

Phase 0 ships the dataclass plus the minimal ``Budget`` surface the loop's
compute-budget guardrail needs (``remaining`` / ``exhausted`` / ``consume``).
Later phases populate the fields: ``workspace`` + ``evidence`` (Phase 2),
``budget`` metering with the hw-multiplier table and ``allocation`` (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Budget:
    """Per-episode compute budget, denominated in H100-equivalent hours.

    Phase 0 ships only the guardrail surface the loop reads. Phase 3's
    ``budget.py`` adds the ``hw_multiplier`` table (GH200/H200 → H100-equiv) and
    the ``gpus x wallclock x hw_multiplier`` accounting that calls ``consume``.
    """

    total_h100_hours: float
    spent_h100_hours: float = 0.0

    def remaining(self) -> float:
        return self.total_h100_hours - self.spent_h100_hours

    def exhausted(self) -> bool:
        return self.remaining() <= 0

    def consume(self, h100_hours: float) -> float:
        """Charge ``h100_hours`` against the budget; return what remains."""
        self.spent_h100_hours += max(0.0, h100_hours)
        return self.remaining()


@dataclass
class ExecutionContext:
    """Mutable per-episode state the repro tool loop dispatches against."""

    arxiv_id: str
    lockfile_row: dict[str, Any] = field(default_factory=dict)
    workspace: Path | None = None        # Phase 2: editable code clone + venv (rw)
    reference: Path | None = None        # Phase 2: read-only paper LaTeX + supplement (ro)
    budget: Budget | None = None         # Phase 3: metered compute budget
    allocation: str | None = None        # Phase 3: SLURM allocation jobid / executor
    evidence: Path | None = None         # Phase 2: commands.log / trajectory.jsonl / ...
