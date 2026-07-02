"""Phase 1: one lockfile row -> one fully-rendered reproduction episode.

Turns the audited lockfile (the selected-paper audit pool) into the inputs the
forked tool loop needs: the opening prompt and the per-episode run directory.

Source of truth is a **Hugging Face dataset** (default
``Mithilss/reprobench-splits``), not a local JSON file. That dataset publishes two
named splits: ``test`` (the 100-paper frozen benchmark, ``split="eval"`` in-row)
and ``validation`` (the disjoint 14-paper ``dev`` split); there is no ``train``
split, so the loader defaults to ``test`` and accepts the friendly aliases
``eval``/``dev``. ``load_lockfile_rows`` accepts, in priority order:

* a bare HF dataset repo id (``owner/name``) loaded with ``datasets.load_dataset``
  at the requested ``split``;
* an ``hf://datasets/<owner>/<name>/<file>`` reference (a loose file on the Hub);
* a local ``.jsonl`` path (offline development and the Phase-1 gate test).

The ``split`` selector applies only to the bare-repo path; a loose file or local
``.jsonl`` is read whole.

The run directory is resolved to ``<runs-dir>/<arxiv_id>/<budget>h/<run_id>/`` —
the S6->S7 contract the existing ``reprocli_vllm`` auditor reads (it walks
``<runs-dir>/<arxiv_id>`` recursively). ``render_reproduce_prompt`` fills every
``{PLACEHOLDER}`` in ``prompts/prompt_reproduce.txt`` and refuses to return a
prompt with any placeholder left unfilled.
"""

from __future__ import annotations

import argparse
import re
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from reprocli_vllm.runtime.mre_records import load_mre_records

from reprocli_repro import sandbox
from reprocli_repro.context import Budget, ExecutionContext
from reprocli_repro.reference import safe_component

DEFAULT_LOCKFILE_DATASET = "Mithilss/reprobench-splits"
# The reproduction agent reproduces the frozen benchmark by default; "validation"
# (the 14-paper dev split) is for development. "train" does not exist here.
DEFAULT_LOCKFILE_SPLIT = "test"
_SPLIT_ALIASES = {"eval": "test", "eval100": "test", "dev": "validation", "dev15": "validation"}

# Compute ceiling for a row whose selection_band is missing/unparseable, used when
# the budget is derived per-paper from the band (the default) rather than pinned flat.
DEFAULT_UNBANDED_BUDGET_H100_HOURS = 8.0


def normalize_split(name: str | None) -> str:
    """Map friendly split aliases (eval/dev) to the dataset's real split names."""
    key = str(name or "").strip().lower()
    return _SPLIT_ALIASES.get(key, key) or DEFAULT_LOCKFILE_SPLIT

# Every uppercase {TOKEN} the template carries. Literal JSON shown to the agent is
# lowercase on purpose, so this regex only ever matches a real placeholder.
_PLACEHOLDER_RE = re.compile(r"\{[A-Z][A-Z0-9_]*\}")


@dataclass
class RunPaths:
    """The resolved bundle layout for one episode (created in Phase 2)."""

    run_dir: Path
    workspace: Path
    reference: Path
    evidence: Path


@dataclass
class EpisodeInput:
    """One lockfile row turned into a ready-to-run episode."""

    arxiv_id: str
    row: dict[str, Any]
    prompt: str
    run_paths: RunPaths
    budget: float


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
# Selection                                                                    #
# --------------------------------------------------------------------------- #
def select_episode_rows(rows: dict[str, dict], *, paper_id: str | None) -> list[dict]:
    if not paper_id:
        raise SystemExit("Pass --paper-id <arxiv_id> to select the episode to reproduce.")
    row = rows.get(paper_id) or rows.get(paper_id.split("v")[0])
    if row is None:
        sample = ", ".join(sorted(rows)[:8])
        raise SystemExit(f"paper-id {paper_id!r} not in lockfile (e.g. {sample} ...).")
    return [row]


# --------------------------------------------------------------------------- #
# Run-directory resolution (the S6->S7 contract)                               #
# --------------------------------------------------------------------------- #
def new_run_id() -> str:
    """Time-stamped, randomly-suffixed id so re-runs never collide in one dir."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{stamp}-{secrets.token_hex(3)}"


def format_hours(hours: float) -> str:
    return f"{float(hours):g}"


def resolve_run_paths(
    runs_dir: Path, arxiv_id: str, budget: float, run_id: str | None = None
) -> RunPaths:
    run_dir = (
        Path(runs_dir)
        / safe_component(arxiv_id)
        / f"{format_hours(budget)}h"
        / (run_id or new_run_id())
    )
    return RunPaths(
        run_dir=run_dir,
        workspace=run_dir / "workspace",
        reference=run_dir / "reference",
        evidence=run_dir / "evidence",
    )


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


# --------------------------------------------------------------------------- #
# Prompt rendering                                                             #
# --------------------------------------------------------------------------- #
def render_reproduce_prompt(
    template: str, row: dict, *, budget: float, run_paths: RunPaths
) -> str:
    rendered = template
    for token, value in _replacements(row, budget, run_paths).items():
        rendered = rendered.replace(token, value)
    leftover = sorted(set(_PLACEHOLDER_RE.findall(rendered)))
    if leftover:
        raise ValueError(f"reproduce prompt has unfilled placeholders: {', '.join(leftover)}")
    return rendered


def _replacements(row: dict, budget: float, run_paths: RunPaths) -> dict[str, str]:
    return {
        "{ARXIV_ID}": arxiv_id_of(row) or "(unknown)",
        "{PAPER_KIND}": _text_or(row.get("paper_kind"), "empirical"),
        "{TIER}": _text_or(row.get("tier"), "(untiered)"),
        "{BAND}": band_of(row),
        "{BUDGET_H100_HOURS}": format_hours(budget),
        "{CENTRAL_CLAIM}": _text_or(row.get("central_claim"), "(no central claim recorded)"),
        "{CLAIM_EVIDENCE}": _text_or(row.get("claim_evidence"), "(no reported numbers recorded)"),
        "{VERIFIED_LINKS}": _verified_links_block(row),
        "{SIGNALS}": _signals_block(row),
        "{MATCH_TARGET}": _match_target_block(row),
        # Short, stable in-container paths the agent actually sees (sandbox.py remaps the
        # long per-run host dirs onto these), so the prompt never hands it the long path.
        "{WORKSPACE_DIR}": sandbox.CONTAINER_WORKSPACE,
        "{REFERENCE_DIR}": sandbox.CONTAINER_REFERENCE,
        "{EVIDENCE_DIR}": sandbox.CONTAINER_EVIDENCE,
        "{RUN_DIR}": sandbox.CONTAINER_RUN,
    }


def _text_or(value: object, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _verified_links_block(row: dict) -> str:
    links = row.get("verified_links") or {}
    labels = (
        ("Code", "code"),
        ("Paper / project", "paper_or_project"),
        ("Dataset", "dataset"),
        ("Weights / checkpoints", "weights"),
    )
    lines: list[str] = []
    for label, key in labels:
        urls = [u for u in (links.get(key) or []) if isinstance(u, str) and u.strip()]
        if urls:
            lines.append(f"{label}:")
            lines.extend(f"  - {url}" for url in urls)
    if not lines:
        return (
            "(No released artifacts for this paper — locate the code yourself or "
            "re-implement the method from the paper.)"
        )
    return "\n".join(lines)


def _match_target_block(row: dict) -> str:
    """Render the classifier's anchor target MINUS its ``config``.

    Hands the agent the success bar to match — metric, reported value, scope, and bar
    shape — while still withholding ``match_target['config']`` (the exact runnable
    configuration), which the agent must derive from the paper. Degrades to a clear
    fallback when no target is recorded.
    """
    target = row.get("match_target") or {}
    fields = (
        ("Metric", "metric"),
        ("Target value", "value"),
        ("Scope", "scope"),
        ("Bar shape", "match_bar_kind"),
    )
    lines: list[str] = []
    for label, key in fields:
        text = _text_or(target.get(key), "")
        if text:
            lines.append(f"  - {label}: {text}")
    if not lines:
        return (
            "(No anchor target recorded — derive the metric, value, and scope from the "
            "paper yourself.)"
        )
    return "\n".join(lines)


def _signals_block(row: dict) -> str:
    """Render the classifier's pre-assessed artifact availability for the prompt.

    The lockfile carries the classifier's ``signals`` (code / dataset / weights /
    dataset-is-standard + a verification level and evidence). Surfacing it spares the
    agent the rounds it otherwise burns rediscovering, e.g., that a repo is a release
    stub — while the prompt still tells it to verify against its exact MRE. Degrades to
    a clear fallback when a row predates signals.
    """
    signals = row.get("signals") or {}
    labels = (
        ("Code", "code_available"),
        ("Dataset", "dataset_available"),
        ("Weights / checkpoints", "weights_available"),
        ("Dataset is a standard benchmark", "dataset_is_standard"),
    )
    lines: list[str] = []
    for label, key in labels:
        sig = signals.get(key)
        if not isinstance(sig, dict) or "value" not in sig:
            continue
        value = "yes" if sig.get("value") else "no"
        verification = _text_or(sig.get("verification"), "unverified")
        line = f"  - {label}: {value} (classifier verification: {verification})"
        evidence = _text_or(sig.get("evidence"), "")
        if evidence:
            line += f" — {evidence}"
        lines.append(line)
    if not lines:
        return (
            "(No pre-assessed availability recorded — determine code/dataset/weights "
            "availability yourself.)"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Top-level entry                                                              #
# --------------------------------------------------------------------------- #
def prepare_episodes(args: argparse.Namespace) -> list[EpisodeInput]:
    template = Path(args.prompt_file).read_text(encoding="utf-8")
    rows = load_lockfile_rows(
        getattr(args, "lockfile", None),
        split=getattr(args, "split", DEFAULT_LOCKFILE_SPLIT),
    )
    selected = select_episode_rows(rows, paper_id=args.paper_id)
    # Default: derive each paper's ceiling from its selection_band. A flat
    # --budget-h100-hours, when given, overrides the band for every paper.
    flat_override = getattr(args, "budget_h100_hours", None)
    pinned_run_id = getattr(args, "run_id", None)
    episodes: list[EpisodeInput] = []
    for row in selected:
        arxiv_id = arxiv_id_of(row)
        if flat_override is not None:
            budget = float(flat_override)
        else:
            band_budget = band_max_hours(row)
            budget = band_budget if band_budget is not None else DEFAULT_UNBANDED_BUDGET_H100_HOURS
        run_paths = resolve_run_paths(args.runs_dir, arxiv_id, budget, pinned_run_id)
        prompt = render_reproduce_prompt(template, row, budget=budget, run_paths=run_paths)
        episodes.append(
            EpisodeInput(arxiv_id=arxiv_id, row=row, prompt=prompt, run_paths=run_paths, budget=budget)
        )
    return episodes


def build_context(ep: EpisodeInput, *, allocation: str | None = None) -> ExecutionContext:
    """Construct the per-episode loop state from a prepared episode."""
    return ExecutionContext(
        arxiv_id=ep.arxiv_id,
        lockfile_row=ep.row,
        workspace=ep.run_paths.workspace,
        reference=ep.run_paths.reference,
        evidence=ep.run_paths.evidence,
        run_dir=ep.run_paths.run_dir,
        budget=Budget(total_h100_hours=ep.budget),
        allocation=allocation,
    )
