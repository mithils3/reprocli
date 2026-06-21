from __future__ import annotations

MAX_REPAIRS = 3

_CLASSIFIERS: list[tuple[str, str]] = [
    ("ModuleNotFoundError", "missing_python_package"),
    ("No module named", "missing_python_package"),
    ("ImportError", "missing_python_package"),
    ("error while loading shared libraries", "missing_system_library"),
    ("CUDA error", "cuda_mismatch"),
    ("CUDA out of memory", "cuda_mismatch"),
    ("FATAL:", "container_exec_failed"),
    ("FATAL ERROR", "container_exec_failed"),
    ("checkpoint", "checkpoint_corrupt"),
    ("PytorchStreamReader failed", "checkpoint_corrupt"),
    ("No such file or directory", "dataset_missing"),
    ("FileNotFoundError", "dataset_missing"),
    ("slurmstepd", "slurm_resource_error"),
    ("Requested node configuration is not available", "slurm_resource_error"),
    ("Traceback (most recent", "repo_command_error"),
]


def classify_failure(text: str) -> str:
    for needle, kind in _CLASSIFIERS:
        if needle in text:
            return kind
    return "unknown"


def route_repair(failure_kind: str, default_phase: str) -> str:
    if failure_kind in {
        "missing_python_package",
        "missing_system_library",
        "cuda_mismatch",
        "container_exec_failed",
    }:
        return "build_environment"
    if failure_kind in {"dataset_missing", "checkpoint_missing", "checkpoint_corrupt"}:
        return "run_experiment"
    if failure_kind == "slurm_resource_error":
        return "generate_launchers"
    if failure_kind == "repo_command_error":
        return "inspect_repo"
    return default_phase
