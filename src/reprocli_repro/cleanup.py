"""Post-episode workspace pruning: reclaim accidental large downloads.

The agent's ``workspace/`` (bound to ``/repro/workspace`` in the sandbox) is NVMe
scratch it clones code and builds a venv into. It is also where a mis-issued
``load_dataset`` / ``wget`` / ``git clone`` of a full dataset lands, and those can
be tens of GB. Nothing downstream needs them: the S6->S7 auditor grades
``report.json`` plus the durable ``evidence/`` trajectory, never the workspace
scratch, and the Supabase sink only uploads ``stats.json`` + ``agent.full.log``
from ``evidence/``. So once an episode reaches a terminal state we prune the
workspace's big artifacts to keep the run root (and the shared filesystem) small.

Two passes, both confined to ``workspace/`` (``reference/`` and ``evidence/`` are
never touched) and both skipping symlinks so we only ever delete a link, never the
thing it points at:

  1. delete any single regular file larger than the threshold, then
  2. delete the *tightest* subdirectory whose total still exceeds the threshold —
     the deepest qualifying dir, so a sharded dataset dir (many sub-threshold
     shards) is removed whole while the enclosing cloned code repo survives.

Deletion is best-effort and logged with a path + size line each; a filesystem
error on one entry is reported and skipped, never raised, so pruning can never
strand an otherwise-finalized run.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import TextIO

# Files/dirs at or above this many MB are pruned from the workspace after an
# episode finishes. Tunable per run via --prune-workspace-threshold-mb (0 = off).
DEFAULT_PRUNE_THRESHOLD_MB = 500


def _human(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TiB"


def _dir_sizes(workspace: Path) -> dict[str, int]:
    """Recursive byte size of every directory under (and including) ``workspace``.

    Bottom-up accumulation (``topdown=False`` visits children first) so each dir's
    total is its own regular files plus its already-summed immediate subdirs.
    Symlinks — files and dirs — are skipped, never followed.
    """
    sizes: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(workspace, topdown=False, followlinks=False):
        total = 0
        for name in filenames:
            fp = os.path.join(dirpath, name)
            if os.path.islink(fp):
                continue
            try:
                total += os.path.getsize(fp)
            except OSError:
                continue
        for name in dirnames:
            sub = os.path.join(dirpath, name)
            if os.path.islink(sub):
                continue
            total += sizes.get(sub, 0)
        sizes[dirpath] = total
    return sizes


def _deepest_big_dirs(workspace: Path, threshold: int) -> list[tuple[Path, int]]:
    """Subdirectories whose total exceeds ``threshold`` and that contain no such
    subdirectory themselves — the tightest big subtree along each path.

    Excludes ``workspace`` itself: we prune its contents, never the root.
    """
    sizes = _dir_sizes(workspace)
    root = str(workspace)
    qualifying = [d for d, size in sizes.items() if d != root and size > threshold]
    quals = set(qualifying)
    targets = []
    for d in qualifying:
        prefix = d + os.sep
        if not any(other != d and other.startswith(prefix) for other in quals):
            targets.append((Path(d), sizes[d]))
    return targets


def prune_workspace(
    workspace: Path | str | None,
    threshold_mb: float,
    *,
    log: TextIO = sys.stderr,
    label: str = "",
) -> int:
    """Delete big files and big subdirs from ``workspace``; return bytes freed.

    A ``threshold_mb`` of 0 (or a missing/non-directory workspace) is a no-op.
    """
    if not workspace or threshold_mb <= 0:
        return 0
    root = Path(workspace)
    if not root.is_dir():
        return 0
    threshold = int(threshold_mb * 1024 * 1024)
    tag = f"prune {label}: " if label else "prune: "
    deleted: list[tuple[Path, int]] = []

    # Pass 1: individual oversized files (anywhere in the tree, symlinks skipped).
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                if fp.is_symlink():
                    continue
                size = fp.stat().st_size
            except OSError:
                continue
            if size > threshold:
                if _remove(fp, is_dir=False, tag=tag, log=log):
                    deleted.append((fp, size))

    # Pass 2: tightest subdirs still over threshold once big files are gone.
    for path, size in _deepest_big_dirs(root, threshold):
        if _remove(path, is_dir=True, tag=tag, log=log):
            deleted.append((path, size))

    freed = sum(size for _, size in deleted)
    for path, size in deleted:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        print(f"{tag}deleted {rel} ({_human(size)})", file=log)
    if deleted:
        print(f"{tag}reclaimed {_human(freed)} across {len(deleted)} item(s)", file=log)
    return freed


def _remove(path: Path, *, is_dir: bool, tag: str, log: TextIO) -> bool:
    try:
        if is_dir:
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as exc:
        print(f"{tag}could not delete {path} ({exc}); skipping", file=log)
        return False
    return True


__all__ = ["DEFAULT_PRUNE_THRESHOLD_MB", "prune_workspace"]
