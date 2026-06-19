"""Materialize paper-bundle rows into per-paper reference directories.

Streams the paper-bundle dataset (so it never loads every shard into memory) and
writes each row to::

    <out-dir>/<arxiv_id>/latex/<relative_path>        # paper .tex sources
    <out-dir>/<arxiv_id>/supplement/<relative_path>   # OpenReview supplement
    <out-dir>/<arxiv_id>/info.json                     # ids, urls, statuses

Supplement files are written from their raw ``content`` bytes, NOT from the
``text`` field: the bundle builder only fills ``text`` for a narrow extension set
(``.py`` and most code files are excluded), but ``content`` holds the bytes for
every file. LaTeX files only carry ``text`` (always decodable), so those are
written as UTF-8.

Run it::

    PYTHONPATH=src python3 -m reprocli_repro.reference --out-dir refs \
        --arxiv-id 2110.03155
    PYTHONPATH=src python3 -m reprocli_repro.reference --out-dir refs --limit 50
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_DATASET = "Mithilss/neurips-2025-paper-bundles"


def main() -> int:
    args = parse_args()
    wanted = load_wanted_ids(args)
    written = materialize(
        dataset=args.dataset,
        out_dir=args.out_dir,
        wanted=wanted,
        limit=args.limit,
        overwrite=args.overwrite,
    )
    print(f"Wrote {written} paper reference dir(s) under {args.out_dir}", file=sys.stderr)
    return 0


def stream_bundle(dataset: str):
    """Open the paper-bundle as a streaming dataset (never loads all shards)."""
    from datasets import load_dataset

    return load_dataset(dataset, split="train", streaming=True)


def arxiv_matches(row_id: str, wanted: str) -> bool:
    """True if ``row_id`` is ``wanted``, ignoring any trailing version (``v2``)."""
    row_id = str(row_id or "").strip()
    wanted = str(wanted or "").strip()
    return bool(row_id) and (row_id == wanted or row_id.split("v")[0] == wanted.split("v")[0])


def materialize(
    *,
    dataset: str,
    out_dir: Path,
    wanted: set[str] | None,
    limit: int | None,
    overwrite: bool,
) -> int:
    written = 0
    for row in stream_bundle(dataset):
        arxiv_id = str(row.get("arxiv_id") or "").strip()
        if not arxiv_id:
            continue
        if wanted is not None and arxiv_id not in wanted:
            continue
        paper_dir = out_dir / safe_component(arxiv_id)
        if paper_dir.exists() and not overwrite:
            print(f"skip {arxiv_id}: already exists (use --overwrite)", file=sys.stderr)
        else:
            write_paper(row, paper_dir)
            written += 1
            print(f"[{written}] wrote {arxiv_id}", file=sys.stderr)
        if wanted is not None:
            wanted.discard(arxiv_id)
            if not wanted:
                break
        if limit is not None and written >= limit:
            break
    if wanted:
        print(
            f"Warning: {len(wanted)} requested id(s) not found in stream: "
            f"{', '.join(sorted(wanted)[:10])}",
            file=sys.stderr,
        )
    return written


def write_paper(row: dict, paper_dir: Path) -> dict:
    """Materialize one bundle row into ``paper_dir`` and return its counts."""
    latex_dir = paper_dir / "latex"
    supp_dir = paper_dir / "supplement"
    n_tex = write_tex_files(row.get("paper_tex_files") or [], latex_dir)
    n_supp = write_supplement_files(row.get("supplement_files") or [], supp_dir)
    write_info(row, paper_dir, n_tex, n_supp)
    write_manifest(paper_dir)
    return {"arxiv_id": row.get("arxiv_id"), "latex_files": n_tex, "supplement_files": n_supp}


def write_tex_files(items: list, latex_dir: Path) -> int:
    count = 0
    for item in items:
        rel = item.get("relative_path") or item.get("filename")
        target = safe_target(latex_dir, rel)
        if target is None:
            continue
        text = item.get("text")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text if isinstance(text, str) else "", encoding="utf-8")
        count += 1
    return count


def write_supplement_files(items: list, supp_dir: Path) -> int:
    count = 0
    for item in items:
        rel = item.get("relative_path") or item.get("filename")
        target = safe_target(supp_dir, rel)
        if target is None:
            continue
        data = supplement_bytes(item)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        count += 1
    return count


def supplement_bytes(item: dict) -> bytes:
    content = item.get("content")
    if isinstance(content, (bytes, bytearray)):
        return bytes(content)
    text = item.get("text")
    if isinstance(text, str):
        return text.encode("utf-8")
    return b""


def write_info(row: dict, paper_dir: Path, n_tex: int, n_supp: int) -> None:
    info = {
        "arxiv_id": row.get("arxiv_id"),
        "title": row.get("title"),
        "openreview_id": row.get("openreview_id"),
        "paper_source_url": row.get("paper_source_url"),
        "paper_status": row.get("paper_status"),
        "supplement_source_url": row.get("supplement_source_url"),
        "supplement_status": row.get("supplement_status"),
        "latex_files": n_tex,
        "supplement_files": n_supp,
    }
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def write_manifest(paper_dir: Path) -> Path:
    """List every materialized reference file (latex/ + supplement/) with sizes."""
    lines = [f"REFERENCE MANIFEST for {paper_dir.name}", ""]
    total = 0
    for sub in ("latex", "supplement"):
        root = paper_dir / sub
        files = sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else []
        lines.append(f"{sub}/ ({len(files)} file(s)):")
        for path in files:
            size = path.stat().st_size
            total += size
            lines.append(f"  {path.relative_to(paper_dir)}  ({size} bytes)")
        lines.append("")
    lines.append(f"{total} bytes total across latex/ and supplement/.")
    manifest = paper_dir / "MANIFEST.txt"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def materialize_reference(
    arxiv_id: str,
    dest: Path,
    *,
    dataset: str = DEFAULT_DATASET,
    overwrite: bool = False,
    row: dict | None = None,
) -> dict:
    """Write one paper's read-only ``reference/`` dir (latex + supplement + manifest).

    ``row`` lets callers (and tests) skip the network; otherwise the bundle is
    streamed until ``arxiv_id`` is found. Returns the per-paper counts plus an
    ``ok`` flag so the workspace setup can report what landed.
    """
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()) and not overwrite:
        return {"ok": True, "skipped": True, "reason": "reference already materialized", "dest": str(dest)}
    if row is None:
        row = find_bundle_row(arxiv_id, dataset=dataset)
    if row is None:
        return {"ok": False, "error": f"arxiv_id {arxiv_id!r} not found in bundle {dataset!r}", "dest": str(dest)}
    counts = write_paper(row, dest)
    return {"ok": True, "skipped": False, "dest": str(dest), **counts}


def find_bundle_row(arxiv_id: str, *, dataset: str = DEFAULT_DATASET) -> dict | None:
    """Stream the bundle and return the first row whose arXiv id matches."""
    for row in stream_bundle(dataset):
        if arxiv_matches(row.get("arxiv_id"), arxiv_id):
            return dict(row)
    return None


def safe_target(base: Path, rel: object) -> Path | None:
    """Join ``rel`` under ``base``, rejecting absolute paths and traversal."""
    raw = str(rel or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/"):
        return None
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    if not parts:
        return None
    return base.joinpath(*parts)


def safe_component(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").strip() or "unknown"


def load_wanted_ids(args: argparse.Namespace) -> set[str] | None:
    ids: set[str] = set(args.arxiv_id or [])
    if args.ids_file:
        ids.update(
            line.strip()
            for line in args.ids_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return ids or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Destination root; each paper goes to <out-dir>/<arxiv_id>/{latex,supplement}.",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Paper-bundle dataset (default: {DEFAULT_DATASET}).",
    )
    parser.add_argument(
        "--arxiv-id",
        action="append",
        help="Materialize only this arXiv id (repeatable). Stream stops once all are found.",
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        help="File of arXiv ids (one per line) to materialize.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Stop after writing this many papers (ignored when --arxiv-id/--ids-file given).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rewrite a paper dir that already exists (default: skip).",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    return args


if __name__ == "__main__":
    import os

    _rc = main()
    # Streaming the dataset pulls in torch/aiohttp background threads that can
    # crash during interpreter finalization (PyGILState_Release). The work is
    # already on disk, so flush and skip the teardown.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_rc)
