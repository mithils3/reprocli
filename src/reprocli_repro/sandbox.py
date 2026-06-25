"""Filesystem sandbox for the reproduction agent's shell steps.

The agent runs *arbitrary* shell — it ``git clone``s an unknown repo and executes
its code (``workspace_bash`` on the orchestrator, ``run_gpu`` on a GPU node). The
file tools (``tools/files.py``) confine their *path arguments*, but a shell command
can write anywhere the user can, so confinement has to happen at the OS, not by
inspecting command strings. This module wraps each step in **bubblewrap**
(``bwrap``) so writes are confined to the episode's own dirs while the rest of the
filesystem stays readable.

The policy is **writes-only confinement** (per the operator's choice):

* ``--ro-bind / /`` — the whole system stays *readable*, so ``module load``, the
  system ``git``, compilers, and CUDA libraries keep working;
* ``--bind`` (read-write) only over the episode's ``workspace``/``evidence``, the
  node-local ``/tmp``, and the shared caches (``~/.cache`` etc.) — everything else,
  including ``$HOME`` config and any API keys exported from ``~/.bashrc``, is
  read-only;
* ``/tmp`` stays the real node-local disk (a read-write bind, **not** a tmpfs): the
  reproduce prompt sends bulk scratch — model weights, datasets — there because it
  is the node's fast local disk and is wiped with the allocation, so it must not be
  shrunk to a RAM-backed tmpfs or redirected onto the quota'd workspace;
* ``--dev-bind /dev /dev`` so the GPU device nodes and ``/dev/shm`` (CUDA/NCCL IPC)
  pass through.

bwrap sandboxes the **filesystem, not the environment**: we do *not* ``--clearenv``,
so ``HF_TOKEN`` (and the network) pass straight through and gated Hugging Face
downloads keep working. Keeping the shared HF/uv/pip/torch caches writable means a
download or wheel build happens once and is reused across papers, not re-fetched on
GPU time.

The sandbox is **mandatory**: every agent shell step is wrapped, with no opt-out and
no other mechanism. ``bwrap`` can be on ``PATH`` yet fail when unprivileged user
namespaces are disabled (some HPC login/compute nodes), so we probe it once and
:func:`require_bwrap` **hard-fails the run** if it is unusable rather than letting a
step run unconfined. The Apptainer execution path is incompatible with the
mandatory bwrap wrap and is rejected up front in the CLI.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from reprocli_repro.inputs import RunPaths

# One-time, cached result of the runtime bwrap probe (keyed so tests can reset it).
_PROBE: dict[str, bool] = {}


def bwrap_usable() -> bool:
    """True iff ``bwrap`` is installed *and* can create a namespace on this host.

    ``shutil.which`` alone lies: ``bwrap`` is frequently present but refuses at
    runtime where unprivileged user namespaces are disabled. We run a trivial
    sandbox once and cache the verdict for the process.
    """
    if "ok" not in _PROBE:
        _PROBE["ok"] = _probe_bwrap()
    return _PROBE["ok"]


def _probe_bwrap() -> bool:
    if not shutil.which("bwrap"):
        return False
    try:
        proc = subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "true"],
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def require_bwrap() -> None:
    """Hard-fail the run unless bwrap can sandbox here — the sandbox is mandatory.

    Called once before any agent step runs. Refusing here is the point: a step must
    never run unconfined, so an unusable ``bwrap`` aborts the run rather than
    silently dropping the boundary.
    """
    if bwrap_usable():
        return
    raise SystemExit(
        "bwrap sandbox is mandatory but unusable on this host: either `bwrap` is not "
        "installed (install bubblewrap) or unprivileged user namespaces are disabled "
        "(check `sysctl kernel.unprivileged_userns_clone` / "
        "`kernel.apparmor_restrict_unprivileged_userns`). The reproduction agent "
        "refuses to run shell steps unconfined."
    )


@dataclass(frozen=True)
class Sandbox:
    """How to wrap one step's ``bash -lc`` body for filesystem confinement.

    ``writable`` are the *episode/cache* read-write bind roots (workspace, evidence,
    caches); everything else is readable but not writable. The node-local ``/tmp`` is
    always bound read-write on top (the agent's bulk scratch), and is added here too
    so it can't be dropped silently. The wrap is unconditional — there is no opt-out
    (see module docstring).
    """

    writable: tuple[Path, ...] = ()

    def wrap_argv(self, body: str) -> list[str]:
        """``["bwrap", <flags...>, "bash", "-lc", <body>]`` — the confined step argv."""
        return [*self._bwrap_prefix(), "bash", "-lc", body]

    def status(self) -> str:
        """Human-readable effective state for the setup summary / evidence."""
        roots = ", ".join(str(p) for p in self.writable) or "(none)"
        return f"bwrap (mandatory); writable: /tmp, {roots}"

    def _bwrap_prefix(self) -> list[str]:
        # Order matters: `--ro-bind / /` lays the whole tree read-only first, then the
        # later overlays win — a fresh /proc, a real /dev (GPU nodes + /dev/shm), the
        # node-local /tmp re-made writable, and the read-write episode/cache binds on
        # top of the ro base.
        argv = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--dev-bind", "/dev", "/dev",
            "--proc", "/proc",
            "--bind", "/tmp", "/tmp",
            "--die-with-parent",
        ]
        for path in self.writable:
            sp = str(path)
            argv += ["--bind", sp, sp]
        return argv


def default_cache_dirs() -> list[Path]:
    """Shared caches that stay writable so HF/uv/pip/torch don't re-fetch per paper.

    ``~/.cache`` covers the default HF hub cache, uv, pip, torch hub, and triton; a
    custom ``HF_HOME``/``UV_CACHE_DIR`` (and the legacy ``~/.huggingface`` token dir)
    are added when set/present so the HF token stays both readable and refreshable.
    """
    home = Path.home()
    dirs = [home / ".cache"]
    for var in ("HF_HOME", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "UV_CACHE_DIR"):
        value = os.environ.get(var)
        if value:
            dirs.append(Path(value).expanduser())
    legacy = home / ".huggingface"
    if legacy.exists():
        dirs.append(legacy)
    return dirs


def from_run_paths(
    run_paths: "RunPaths",
    *,
    caches: Iterable[Path] | None = None,
) -> Sandbox:
    """Build the episode's sandbox: rw binds for its dirs + the shared caches.

    Every read-write bind source must exist before ``bwrap`` runs, so we create the
    episode dirs and the cache roots up front (idempotent) and drop any that can't be
    created. ``/tmp`` is bound unconditionally by :class:`Sandbox`; cache roots
    default to :func:`default_cache_dirs`.
    """
    candidates = [run_paths.workspace, run_paths.evidence]
    candidates += list(caches if caches is not None else default_cache_dirs())
    writable: list[Path] = []
    for path in candidates:
        resolved = _ensure_dir(path)
        if resolved is not None and resolved not in writable:
            writable.append(resolved)
    return Sandbox(writable=tuple(writable))


def _ensure_dir(path: Path | None) -> Path | None:
    if path is None:
        return None
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return Path(path).resolve()
    except OSError:
        return None
