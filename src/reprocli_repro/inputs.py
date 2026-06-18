"""Phase 1: one lockfile row -> one fully-rendered reproduction episode.

Turns the audited lockfile (the selected-paper audit pool) into the inputs the
forked tool loop needs: the opening prompt and the per-episode run directory.

Source of truth is a **Hugging Face dataset** (default
``Mithilss/neurips-2025-audit-pool``), not a local JSON file. ``load_lockfile_rows``
accepts, in priority order:

* a bare HF dataset repo id (``owner/name``) loaded with ``datasets.load_dataset``;
* an ``hf://datasets/<owner>/<name>/<file>`` reference (a loose file on the Hub);
* a local ``.jsonl`` path (offline development and the Phase-1 gate test).

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

from reprocli_repro.context import Budget, ExecutionContext
from reprocli_repro.reference import safe_component

DEFAULT_LOCKFILE_DATASET = "Mithilss/neurips-2025-audit-pool"

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
def load_lockfile_rows(source: str | None, *, split: str = "train") -> dict[str, dict]:
    """Return ``{arxiv_id: row}`` from an HF dataset, an hf:// file, or local JSONL."""
    spec = str(source or DEFAULT_LOCKFILE_DATASET)
    if _looks_like_dataset_repo(spec):
        return _index_rows(_iter_hf_dataset(spec, split))
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
def select_episode_rows(
    rows: dict[str, dict],
    *,
    paper_id: str | None,
    num_prompts: int | None,
    seed: int = 0,
) -> list[dict]:
    if paper_id:
        row = rows.get(paper_id) or rows.get(paper_id.split("v")[0])
        if row is None:
            sample = ", ".join(sorted(rows)[:8])
            raise SystemExit(f"paper-id {paper_id!r} not in lockfile (e.g. {sample} ...).")
        return [row]
    ordered = list(rows.values())
    if num_prompts is None:
        raise SystemExit("Pass --paper-id <arxiv_id> or --num-prompts <N> to select episode(s).")
    if num_prompts >= len(ordered):
        return ordered
    import random

    return random.Random(seed).sample(ordered, num_prompts)


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
        "{MRE_CONFIG}": _text_or(row.get("mre_config"), "(no MRE configuration recorded)"),
        "{AGENT_TASK}": _text_or(row.get("agent_task"), "(no step-by-step task recorded)"),
        "{VERIFIED_LINKS}": _verified_links_block(row),
        "{WORKSPACE_DIR}": str(run_paths.workspace),
        "{REFERENCE_DIR}": str(run_paths.reference),
        "{EVIDENCE_DIR}": str(run_paths.evidence),
        "{RUN_DIR}": str(run_paths.run_dir),
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


# --------------------------------------------------------------------------- #
# Top-level entry                                                              #
# --------------------------------------------------------------------------- #
def prepare_episodes(args: argparse.Namespace) -> list[EpisodeInput]:
    template = Path(args.prompt_file).read_text(encoding="utf-8")
    rows = load_lockfile_rows(getattr(args, "lockfile", None))
    selected = select_episode_rows(
        rows,
        paper_id=args.paper_id,
        num_prompts=args.num_prompts,
        seed=getattr(args, "seed", 0),
    )
    budget = float(args.budget_h100_hours)
    pinned_run_id = getattr(args, "run_id", None)
    episodes: list[EpisodeInput] = []
    for row in selected:
        arxiv_id = arxiv_id_of(row)
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
        evidence=ep.run_paths.evidence,
        budget=Budget(total_h100_hours=ep.budget),
        allocation=allocation,
    )
