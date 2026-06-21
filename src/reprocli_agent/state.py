from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Literal


@dataclass
class ReproState:
    paper_id: str
    phase: str = "inspect_host"
    env_mode: Literal["apptainer", "conda"] = "conda"
    workdir: str = "."

    # Host profile — populated by inspect_host verifier
    host_arch: str | None = None
    has_apptainer: bool = False
    has_conda: bool = False
    cuda_visible: bool = False
    gpu_name: str | None = None
    slurm_available: bool = False

    # Repo — populated by clone_repo / inspect_repo verifiers
    repo_url: str | None = None
    repo_path: str | None = None
    repo_cloned: bool = False
    repo_inspected: bool = False
    main_scripts: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)
    candidate_commands: list[str] = field(default_factory=list)
    dataset_hints: list[str] = field(default_factory=list)
    checkpoint_hints: list[str] = field(default_factory=list)

    # Environment — populated by build_environment verifier
    container_path: str | None = None
    venv_path: str | None = None
    conda_env_name: str | None = None
    selected_command: str | None = None
    env_plan_written: bool = False
    env_ready: bool = False
    smoke_test_passed: bool = False
    gpu_test_passed: bool = False

    # Launchers (apptainer only)
    launchers_written: bool = False

    # Experiment — populated by run_experiment verifier
    experiment_submitted: bool = False
    slurm_job_id: str | None = None
    experiment_finished: bool = False
    run_log_path: str | None = None

    # Results — populated by collect_results verifier
    results_found: bool = False
    metric_results: list[dict[str, Any]] = field(default_factory=list)
    verification_targets: list[dict[str, Any]] = field(default_factory=list)

    # Diagnostics
    phases_completed: list[str] = field(default_factory=list)
    repair_count: int = 0
    blockers: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    total_tool_rounds: int = 0
    last_failure: str | None = None
    last_failure_phase: str | None = None
    last_failure_target: str | None = None

    # ------------------------------------------------------------------ #

    def save(self) -> None:
        (Path(self.workdir) / "state.json").write_text(
            json.dumps(asdict(self), indent=2)
        )

    @classmethod
    def load(cls, workdir: str) -> ReproState | None:
        p = Path(workdir) / "state.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    @classmethod
    def new(
        cls,
        paper_id: str,
        workdir: str,
        env_mode: str,
        first_phase: str,
    ) -> ReproState:
        return cls(
            paper_id=paper_id,
            workdir=workdir,
            env_mode=env_mode,  # type: ignore[arg-type]
            phase=first_phase,
        )

    def mark_done(self, phase: str) -> None:
        if phase not in self.phases_completed:
            self.phases_completed.append(phase)
        if phase == self.last_failure_target:
            self.last_failure = None
            self.last_failure_phase = None
            self.last_failure_target = None

    def repair_to(
        self,
        target: str,
        all_phases: list[str] | None = None,
        failure_message: str | None = None,
        failed_phase: str | None = None,
    ) -> None:
        self.repair_count += 1
        if failure_message is not None:
            self.last_failure = failure_message
            self.last_failure_phase = failed_phase
            self.last_failure_target = target
        if all_phases and target in all_phases:
            idx = all_phases.index(target)
            self.phases_completed = [
                p
                for p in self.phases_completed
                if p in all_phases and all_phases.index(p) < idx
            ]
        self.phase = target

    def state_summary(self) -> str:
        lines = ["## Pipeline State"]
        for p in self.phases_completed:
            lines.append(f"- {p}: DONE")
        lines.append(f"- {self.phase}: IN PROGRESS  ← current")
        if self.blockers:
            lines.append(f"\nBlockers: {'; '.join(self.blockers)}")
        if self.last_failure:
            lines.append(
                f"\nLast failure (in {self.last_failure_phase or '?'}, sent you back here): {self.last_failure}"
            )
        facts: list[str] = []
        if self.host_arch:
            facts.append(f"arch={self.host_arch}")
        if self.repo_path:
            facts.append(f"repo={self.repo_path}")
        if self.container_path:
            facts.append(f"sif={self.container_path}")
        if self.venv_path:
            facts.append(f"venv={self.venv_path}")
        if self.selected_command:
            facts.append(f"selected_command={self.selected_command}")
        if self.conda_env_name:
            facts.append(f"conda_env={self.conda_env_name}")
        if self.slurm_job_id:
            facts.append(f"job_id={self.slurm_job_id}")
        if facts:
            lines.append(f"\nDiscovered: {', '.join(facts)}")
        return "\n".join(lines)


def can_finalize(state: ReproState) -> bool:
    """Final reproduction JSON is only meaningful once we're in finalize with something to report."""
    return state.phase == "finalize" and (state.results_found or bool(state.blockers))
