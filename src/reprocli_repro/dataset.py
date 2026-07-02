"""Lockfile loading + per-row field accessors for the reproduce episodes.

Source of truth is a **Hugging Face dataset** (default ``Mithilss/reprobench-splits``),
not a local JSON file. That dataset publishes two named splits: ``test`` (the 100-paper
frozen benchmark, ``split="eval"`` in-row) and ``validation`` (the disjoint 14-paper
``dev`` split); there is no ``train`` split, so the loader defaults to ``test`` and
accepts the friendly aliases ``eval``/``dev``. ``load_lockfile_rows`` accepts, in
priority order:

* a bare HF dataset repo id (``owner/name``) loaded with ``datasets.load_dataset``
  at the requested ``split``;
* an ``hf://datasets/<owner>/<name>/<file>`` reference (a loose file on the Hub);
* a local ``.jsonl`` path (offline development and the Phase-1 gate test).

The ``split`` selector applies only to the bare-repo path; a loose file or local
``.jsonl`` is read whole. Everything here is pure row plumbing — no episode state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reprocli_vllm.runtime.mre_records import load_mre_records

DEFAULT_LOCKFILE_DATASET = "Mithilss/reprobench-splits"
# The reproduction agent reproduces the frozen benchmark by default; "validation"
# (the 14-paper dev split) is for development. "train" does not exist here.
DEFAULT_LOCKFILE_SPLIT = "test"
_SPLIT_ALIASES = {"eval": "test", "eval100": "test", "dev": "validation", "dev15": "validation"}


def normalize_split(name: str | None) -> str:
    """Map friendly split aliases (eval/dev) to the dataset's real split names."""
    key = str(name or "").strip().lower()
    return _SPLIT_ALIASES.get(key, key) or DEFAULT_LOCKFILE_SPLIT


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #
def load_lockfile_rows(
    source: str | None, *, split: str = DEFAULT_LOCKFILE_SPLIT
) -> dict[str, dict]:
    """Return ``{arxiv_id: row}`` from an HF dataset, an hf:// file, or local JSONL."""
    spec = str(source or DEFAULT_LOCKFILE_DATASET)
    if _looks_like_dataset_repo(spec):
        return _index_rows(_iter_hf_dataset(spec, normalize_split(split)))
    # Local .jsonl path or hf://datasets/<owner>/<name>/<file> — reuse the tested
    # file loader the classifier/auditor already share.
    return load_mre_records(spec)


def _looks_like_dataset_repo(spec: str) -> bool:
    if spec.startswith("hf://") or Path(spec).exists():
        return False
    if spec.endswith((".jsonl", ".json")):
        return False
    return "/" in spec


def _iter_hf_dataset(repo_id: str, split: str) -> Iterable[dict]:
    from datasets import load_dataset

    return iter(load_dataset(repo_id, split=split))


def _index_rows(rows: Iterable[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        arxiv_id = arxiv_id_of(row)
        if arxiv_id:
            indexed[arxiv_id] = dict(row)
    if not indexed:
        raise SystemExit("No lockfile rows found (every row lacked an arXiv id).")
    return indexed


# --------------------------------------------------------------------------- #
# Field accessors                                                              #
# --------------------------------------------------------------------------- #
def arxiv_id_of(row: dict) -> str:
    for key in ("custom_id", "paper_id", "arxiv_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def band_of(row: dict) -> str:
    for key in ("selection_band", "h100_band"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "(unspecified)"


def band_max_hours(row: dict) -> float | None:
    """Upper edge of the row's compute band in H100-h (e.g. ``'96-192'`` -> 192.0,
    ``'0-8'`` -> 8.0). Returns ``None`` when the band is unspecified/unparseable."""
    try:
        return float(band_of(row).split("-")[-1])
    except (ValueError, IndexError):
        return None


def format_hours(hours: float) -> str:
    return f"{float(hours):g}"
