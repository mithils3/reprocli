from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .state import ReproState


@dataclass
class VerifierResult:
    status: Literal["success", "continue", "repair", "blocked"]
    message: str
    repair_phase: str | None = None


def _missing(workdir: str, *paths: str) -> list[str]:
    return [p for p in paths if not (Path(workdir) / p).exists()]


def _log_contains(workdir: str, filename: str, *bad_strings: str) -> str | None:
    p = Path(workdir) / filename
    if not p.exists():
        return None
    text = p.read_text(errors="replace")
    for s in bad_strings:
        if s in text:
            return s
    return ""  # exists, no bad strings found


def _read_json(workdir: str, filename: str) -> dict | list | None:
    p = Path(workdir) / filename
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="replace"))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# One verifier per phase — each enriches `state` with discovered facts on success
# ---------------------------------------------------------------------------

def v_inspect_host(workdir: str, state: ReproState) -> VerifierResult:
    data = _read_json(workdir, "host_profile.json")
    if data is None:
        return VerifierResult("continue", "host_profile.json not yet written")
    if isinstance(data, dict):
        state.host_arch = data.get("arch") or state.host_arch
        state.has_conda = bool(data.get("has_conda", state.has_conda))
        state.has_apptainer = bool(data.get("has_apptainer", state.has_apptainer))
        state.cuda_visible = bool(data.get("has_gpu", state.cuda_visible))
        state.gpu_name = data.get("gpu_name") or state.gpu_name
        state.slurm_available = bool(data.get("slurm_available", state.slurm_available))
    return VerifierResult("success", "host_profile.json written")


def v_clone_repo(workdir: str, state: ReproState) -> VerifierResult:
    hits = list(Path(workdir).glob("*/.git"))
    if hits:
        state.repo_path = hits[0].parent.name
        state.repo_cloned = True
        return VerifierResult("success", f"repo: {hits[0].parent.name}")
    return VerifierResult("continue", "no .git directory found yet")


def v_inspect_repo(workdir: str, state: ReproState) -> VerifierResult:
    data = _read_json(workdir, "repo_profile.json")
    if data is None:
        return VerifierResult("continue", "repo_profile.json not yet written")
    if isinstance(data, dict):
        state.repo_inspected = True
        cmds = [c for c in (data.get("training_command"), data.get("eval_command")) if c]
        state.candidate_commands = cmds or state.candidate_commands
        dl = data.get("dataset_download_commands")
        if dl:
            state.dataset_hints = dl if isinstance(dl, list) else [dl]
        entries = data.get("entry_points")
        if entries:
            state.main_scripts = entries if isinstance(entries, list) else [entries]
    return VerifierResult("success", "repo_profile.json written")


CONTAINER_IMMUTABLE_PACKAGES = {"torch", "torchvision", "torchaudio", "triton", "numpy", "pillow", "pil"}


def _pip_package_names(pip_packages: object) -> set[str]:
    names: set[str] = set()
    for p in pip_packages or []:
        if isinstance(p, dict):
            name = p.get("name")
        else:
            name = p
        if isinstance(name, str):
            names.add(name.strip().lower().split("==")[0].split(">=")[0])
    return names


def v_plan_environment(workdir: str, state: ReproState) -> VerifierResult:
    data = _read_json(workdir, "env_plan.json")
    if data is None:
        return VerifierResult("continue", "env_plan.json not yet written")
    if isinstance(data, dict):
        state.selected_command = data.get("selected_command") or state.selected_command
    state.env_plan_written = True
    return VerifierResult("success", "env_plan.json written")


def v_build_env_container(workdir: str, state: ReproState) -> VerifierResult:
    data = _read_json(workdir, "env_ready.json")
    if data is None:
        return VerifierResult("continue", "env_ready.json not yet written")
    if isinstance(data, dict):
        hit = _pip_package_names(data.get("packages_installed")) & CONTAINER_IMMUTABLE_PACKAGES
        if hit:
            return VerifierResult(
                "repair",
                f"env_ready.json reports installing packages the container already "
                f"provides — this breaks the ABI: {', '.join(sorted(hit))}",
                repair_phase="build_environment",
            )
        state.container_path = data.get("container_path") or state.container_path
        state.venv_path = data.get("venv_path") or state.venv_path
        state.selected_command = data.get("selected_command") or state.selected_command
    state.env_ready = True
    return VerifierResult("success", "env_ready.json written")


def v_build_env_conda(workdir: str, state: ReproState) -> VerifierResult:
    data = _read_json(workdir, "env_ready.json")
    if data is None:
        return VerifierResult("continue", "env_ready.json not yet written")
    if isinstance(data, dict):
        state.conda_env_name = data.get("env_name") or state.conda_env_name
    state.env_ready = True
    return VerifierResult("success", "conda env ready")


def v_smoke_test(workdir: str, state: ReproState) -> VerifierResult:
    log = Path(workdir) / "smoke_test.log"
    if not log.exists():
        return VerifierResult("continue", "smoke_test.log not yet written")
    text = log.read_text(errors="replace")
    for bad in ("ImportError", "ModuleNotFoundError", "No module named", "FAILED"):
        if bad in text:
            # The verifier for build_environment short-circuits to "success" if
            # env_ready.json already exists, so a stale one would make the
            # repaired build_environment phase exit instantly without fixing
            # the missing module. Delete it so build_environment must rerun
            # the loop and write a fresh env_ready.json.
            env_ready = Path(workdir) / "env_ready.json"
            if env_ready.exists():
                env_ready.unlink()
            state.env_ready = False
            return VerifierResult("repair", f"smoke_test.log: '{bad}'", repair_phase="build_environment")
    if "SMOKE_OK" in text:
        state.smoke_test_passed = True
        return VerifierResult("success", "smoke test passed")
    return VerifierResult("continue", "SMOKE_OK not yet in smoke_test.log")


def v_generate_launchers(workdir: str, state: ReproState) -> VerifierResult:
    missing = _missing(workdir, "reproduce.sh", "slurm_run.sh")
    if not missing:
        state.launchers_written = True
        return VerifierResult("success", "reproduce.sh + slurm_run.sh written")
    return VerifierResult("continue", f"missing: {', '.join(missing)}")


def v_run_experiment(workdir: str, state: ReproState) -> VerifierResult:
    run_log = Path(workdir) / "run.log"
    if run_log.exists():
        text = run_log.read_text(errors="replace")
        if "Traceback (most recent" in text and "Error:" in text:
            return VerifierResult("repair", "fatal traceback in run.log", repair_phase="run_experiment")
        state.experiment_finished = True
        state.run_log_path = str(run_log)
        job_hits = sorted(Path(workdir).glob("slurm-*.out"))
        if job_hits:
            state.slurm_job_id = job_hits[-1].stem.removeprefix("slurm-")
        return VerifierResult("success", "run.log written")
    return VerifierResult("continue", "run.log not yet written")


def v_collect_results(workdir: str, state: ReproState) -> VerifierResult:
    data = _read_json(workdir, "results.json")
    if data is None:
        return VerifierResult("continue", "results.json not yet written")
    metrics = data if isinstance(data, list) else (data.get("metric_results") if isinstance(data, dict) else None)
    if metrics is None:
        return VerifierResult("continue", "results.json malformed")

    if state.verification_targets:
        run_log = Path(workdir) / "run.log"
        if run_log.exists():
            from .output import parse_metrics_from_log

            target_names = [t["metric"] for t in state.verification_targets if t.get("metric")]
            regex_results = {r["metric"]: r["actual_value"] for r in parse_metrics_from_log(
                run_log.read_text(errors="replace"), target_names
            )}
            for m in metrics:
                if isinstance(m, dict) and m.get("actual_value") is None:
                    fallback = regex_results.get(m.get("metric"))
                    if fallback is not None:
                        m["actual_value"] = fallback

        found_names = {m.get("metric") for m in metrics if isinstance(m, dict)}
        missing = [
            t["metric"] for t in state.verification_targets
            if t.get("metric") and t["metric"] not in found_names
        ]
        if missing:
            return VerifierResult(
                "repair",
                f"results.json is missing verification_targets: {', '.join(missing)}",
                repair_phase="collect_results",
            )

    state.results_found = True
    state.metric_results = [m for m in metrics if isinstance(m, dict)]
    return VerifierResult("success", "results.json written")


def v_finalize(workdir: str, state: ReproState) -> VerifierResult:
    reasoning = Path(workdir) / "REASONING.txt"
    if not reasoning.exists() or not reasoning.read_text(errors="replace").strip():
        return VerifierResult("continue", "REASONING.txt not yet written")

    data = _read_json(workdir, "final_result.json")
    if data is None:
        return VerifierResult("continue", "final_result.json not yet written")
    if not isinstance(data, dict) or "reproduction_status" not in data:
        return VerifierResult("continue", "final_result.json missing reproduction_status")

    return VerifierResult("success", "finalize complete")
