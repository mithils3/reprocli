"""Filesystem sandbox for the reproduction agent's shell steps (Apptainer).

The agent runs *arbitrary* shell — it ``git clone``s an unknown repo and executes
its code (``workspace_bash`` on the orchestrator, ``run_gpu`` on a GPU node). The
file tools (``tools/files.py``) confine their *path arguments*, but a shell command
can write anywhere the user can, so confinement has to happen at the OS, not by
inspecting command strings. This module wraps each step in an **Apptainer** container
(DeltaAI's supported runtime — it has no bubblewrap and no Docker) so the step runs
inside a read-only image and can only *write* the episode's own dirs.

Apptainer confines differently from bubblewrap. There is no ``--ro-bind / /``: the
container **image** is the read-only root (``/``), so the agent's toolchain — git,
Python, the CUDA stack, and a prebuilt GPU ``torch`` — comes from the image (an NGC
PyTorch ``.sif`` on DeltaAI) rather than the host, and host ``module load`` is gone.
Only the paths we *bind* are visible at all:

* **read-write** binds over the episode's ``workspace``/``evidence``, the node-local
  ``/tmp`` (the agent's bulk scratch — a real bind, **not** a tmpfs, so weights and
  datasets land on the node's fast local disk), and the shared package caches
  (``~/.cache`` incl. HF/uv/pip) so a download or wheel build is reused across papers;
* a **read-only** bind over the episode's ``reference`` (the paper copy);
* everything else on the host — ``$HOME`` and the secrets ``~/.bashrc`` exports, other
  ``/projects``/``/work`` paths — is simply *not mounted*, so it can be neither read
  nor written.

``--cleanenv`` stops the orchestrator's ``LD_LIBRARY_PATH``/``PYTHONPATH`` leaking into
the container (host libs would shadow the image's own and crash ``git``/``torch``), and
``--no-home`` keeps the host home — and any keys ``~/.bashrc`` would export into a
``bash -lc`` login shell — out of the sandbox. The env vars the agent legitimately needs
(``HF_TOKEN`` and friends, the proxy vars) are forwarded explicitly via ``APPTAINERENV_*``
(see :func:`forward_env`) so gated Hugging Face downloads keep working without putting a
token on the command line. ``--nv`` is added on GPU steps to pass the device + CUDA driver
through.

The sandbox is **mandatory**: every agent shell step is wrapped, with no opt-out.
:func:`require_apptainer` **hard-fails the run** if Apptainer cannot execute the image on
this host (or no image is configured) rather than letting a step run unconfined.
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

# Host env vars forwarded into the ``--cleanenv`` container (mirrored to ``APPTAINERENV_*``
# in :func:`forward_env`) so HF auth, cache locations, and proxies survive the env scrub
# without ever appearing on the command line.
FORWARD_ENV = (
    "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN",
    "HF_HOME", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HUB_ENABLE_HF_TRANSFER",
    "UV_CACHE_DIR", "PIP_CACHE_DIR",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
)

# One-time, cached result of the runtime Apptainer probe, keyed by image (so tests can
# reset it and distinct images probe independently).
_PROBE: dict[str, bool] = {}


def apptainer_usable(image: str) -> bool:
    """True iff ``apptainer`` can actually ``exec`` *this image* on this host.

    ``shutil.which`` alone is not enough — the image must exist and be runnable here
    (a bad path or a node without unprivileged container support both fail). We run a
    trivial ``apptainer exec <image> true`` once per image and cache the verdict.
    """
    if image not in _PROBE:
        _PROBE[image] = _probe_apptainer(image)
    return _PROBE[image]


def _probe_apptainer(image: str) -> bool:
    if not image or not shutil.which("apptainer") or not Path(image).exists():
        return False
    try:
        proc = subprocess.run(
            ["apptainer", "exec", "--cleanenv", image, "true"],
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def require_apptainer(image: str | None) -> None:
    """Hard-fail the run unless Apptainer can sandbox here — the sandbox is mandatory.

    Called once before any agent step runs. Refusing here is the point: a step must
    never run unconfined, so a missing image or an unusable Apptainer aborts the run.
    """
    if not image:
        raise SystemExit(
            "the Apptainer sandbox is mandatory but no image is configured: pass "
            "--apptainer-image (or set $REPRO_APPTAINER_SIF), or pick a cluster profile "
            "that pins one (deltaai does). The reproduction agent refuses to run shell "
            "steps unconfined."
        )
    if apptainer_usable(image):
        return
    raise SystemExit(
        f"the Apptainer sandbox is mandatory but unusable here: `apptainer exec {image} "
        "true` failed — check that `apptainer` is on PATH and the image exists and is "
        "readable on this node (set $APPTAINER_CACHEDIR to /scratch or NVMe if you hit a "
        "~/.apptainer quota error)."
    )


def forward_env() -> None:
    """Mirror the :data:`FORWARD_ENV` allowlist into ``APPTAINERENV_*`` for ``--cleanenv``.

    Apptainer imports ``APPTAINERENV_FOO`` as ``FOO`` inside the container even under
    ``--cleanenv``. Setting it in *our* process environment (never on argv) forwards HF
    auth and cache/proxy settings without exposing a token via ``ps``. Idempotent — an
    explicit ``APPTAINERENV_*`` already in the environment wins.
    """
    for var in FORWARD_ENV:
        value = os.environ.get(var)
        if value is not None:
            os.environ.setdefault(f"APPTAINERENV_{var}", value)


@dataclass(frozen=True)
class Sandbox:
    """How to wrap one step's ``bash -lc`` body in the episode's Apptainer container.

    ``image`` is the read-only ``.sif`` that becomes ``/``; ``writable`` are the
    *episode/cache* read-write bind roots (workspace, evidence, caches); ``readonly``
    are the read-only binds (the paper ``reference``). The node-local ``/tmp`` is always
    bound read-write (the agent's bulk scratch). The wrap is unconditional — there is no
    opt-out (see module docstring).
    """

    image: str
    writable: tuple[Path, ...] = ()
    readonly: tuple[Path, ...] = ()

    def wrap_argv(self, body: str, *, nv: bool = False) -> list[str]:
        """``["apptainer", "exec", <flags...>, <image>, "bash", "-lc", <body>]``.

        ``nv`` adds ``--nv`` so a GPU step sees the device + CUDA driver; CPU-setup
        steps on the login node omit it (there is no GPU there to pass through).
        """
        return [*self._apptainer_prefix(nv=nv), "bash", "-lc", body]

    def status(self) -> str:
        """Human-readable effective state for the setup summary / evidence."""
        rw = ", ".join(str(p) for p in self.writable) or "(none)"
        ro = ", ".join(str(p) for p in self.readonly) or "(none)"
        return f"apptainer (mandatory) {self.image}; rw: /tmp, {rw}; ro: {ro}"

    def _apptainer_prefix(self, *, nv: bool) -> list[str]:
        argv = ["apptainer", "exec", "--cleanenv", "--no-home"]
        if nv:
            argv.append("--nv")
        # node-local /tmp stays a real rw bind (NOT a tmpfs) — bulk weights/datasets.
        argv += ["--bind", "/tmp"]
        for path in self.writable:
            argv += ["--bind", str(path)]
        for path in self.readonly:
            argv += ["--bind", f"{path}:{path}:ro"]
        # NGC images ship `pip` but not `uv`, and the prompt installs with `uv pip`;
        # bind the host `uv` (aarch64, runs fine in the container) onto the default PATH.
        uv = shutil.which("uv")
        if uv:
            argv += ["--bind", f"{uv}:/usr/local/bin/uv"]
        argv.append(self.image)
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
    image: str,
    caches: Iterable[Path] | None = None,
) -> Sandbox:
    """Build the episode's sandbox: rw binds for its dirs + caches, ro bind for reference.

    Every bind source must exist before ``apptainer`` runs, so we create the episode
    dirs and cache roots up front (idempotent) and drop any that can't be created.
    ``/tmp`` is bound unconditionally by :class:`Sandbox`; cache roots default to
    :func:`default_cache_dirs`.
    """
    candidates = [run_paths.workspace, run_paths.evidence]
    candidates += list(caches if caches is not None else default_cache_dirs())
    writable: list[Path] = []
    for path in candidates:
        resolved = _ensure_dir(path)
        if resolved is not None and resolved not in writable:
            writable.append(resolved)
    readonly: list[Path] = []
    reference = _ensure_dir(run_paths.reference)
    if reference is not None:
        readonly.append(reference)
    return Sandbox(image=image, writable=tuple(writable), readonly=tuple(readonly))


def _ensure_dir(path: Path | None) -> Path | None:
    if path is None:
        return None
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return Path(path).resolve()
    except OSError:
        return None
