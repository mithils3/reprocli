#!/usr/bin/env python3
"""Build static data for the verification app.

Reads the v4 output family and produces:

  public/papers.json             -- one compact record per paper (shipped with the site)
  traces_out/<custom_id>.json    -- per-paper conversation trace (uploaded on demand)

The 220 MB ``*_trace.jsonl`` is read once, streaming, to (a) pull the paper
title / source_url out of the first user message and (b) split each trace into
its own small file. ``papers.json`` is everything a reviewer needs to verify a
paper without loading the trace; the trace is fetched lazily from cloud storage.

Usage::

    python3 tools/verify_app/build_data.py
    python3 tools/verify_app/build_data.py --run outputs/v4/neurips_2025_minimax_m2_trial
    python3 tools/verify_app/build_data.py --upload      # also push traces to Supabase Storage
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_BASE = REPO / "outputs/v4/neurips_2025_minimax_m2_trial"

TITLE_RE = re.compile(r"^title:\s*(.+)$", re.MULTILINE)
SOURCE_RE = re.compile(r"^source_url:\s*(.+)$", re.MULTILINE)
ARXIV_RE = re.compile(r"^arxiv_id:\s*(.+)$", re.MULTILINE)

# Trim huge tool payloads so per-trace files stay small and load fast.
CONTENT_CLIP = 16000
ARG_CLIP = 6000


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        print(f"  ! missing {path}", file=sys.stderr)
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  ! {path.name}:{line_no} bad json: {exc.msg}", file=sys.stderr)


def clip(value: Any, limit: int) -> Any:
    if not isinstance(value, str) or len(value) <= limit:
        return value
    return f"{value[:limit]}\n\n[... trimmed {len(value) - limit} chars ...]"


def compact_message(message: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(message, dict):
        return {"role": "unknown", "content": repr(message)}
    out: dict[str, Any] = {
        "role": message.get("role"),
        "name": message.get("name"),
        "content": clip(message.get("content"), CONTENT_CLIP),
    }
    calls = message.get("tool_calls")
    if calls:
        out["tool_calls"] = [
            {
                "name": (c.get("function") or {}).get("name"),
                "arguments": clip((c.get("function") or {}).get("arguments"), ARG_CLIP),
            }
            for c in calls
            if isinstance(c, dict)
        ]
    return out


def extract_meta(messages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Pull title + source_url out of the first user message that has them."""
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if not isinstance(content, str) or "title:" not in content:
            continue
        title = TITLE_RE.search(content)
        source = SOURCE_RE.search(content)
        if title:
            return (
                title.group(1).strip(),
                source.group(1).strip() if source else None,
            )
    return None, None


def build(base: Path, out_dir: Path, traces_dir: Path) -> dict[str, dict[str, Any]]:
    extracted_path = Path(f"{base}_extracted.jsonl")
    trace_path = Path(f"{base}_trace.jsonl")

    papers: dict[str, dict[str, Any]] = {}

    print(f"Reading {extracted_path.name} ...")
    for row in iter_jsonl(extracted_path):
        cid = str(row.get("custom_id") or "").strip()
        if not cid:
            continue
        signals = row.get("signals") or {}
        papers[cid] = {
            "custom_id": cid,
            "title": None,
            "source_url": f"https://arxiv.org/abs/{cid}",
            "central_claim": row.get("central_claim"),
            "claim_evidence": row.get("claim_evidence"),
            "mre_config": row.get("mre_config"),
            "agent_task": row.get("agent_task"),
            "web_verification": row.get("web_verification"),
            "verified_links": row.get("verified_links") or {},
            "signals": signals,
            "score": row.get("score"),
            "tier": row.get("tier"),
            "h100_hours_estimate": row.get("h100_hours_estimate"),
            "h100_estimate_basis": row.get("h100_estimate_basis"),
            "has_trace": False,
        }

    traces_dir.mkdir(parents=True, exist_ok=True)
    print(f"Streaming {trace_path.name} (large) and splitting traces ...")
    n_trace = 0
    for row in iter_jsonl(trace_path):
        cid = str(row.get("custom_id") or "").strip()
        if not cid:
            continue
        messages = row.get("messages") or []
        title, source = extract_meta(messages)
        rec = papers.setdefault(cid, {"custom_id": cid, "signals": {}, "verified_links": {}})
        if title:
            rec["title"] = title
        if source:
            rec["source_url"] = source
        rec["has_trace"] = True

        trace_doc = {
            "custom_id": cid,
            "messages": [compact_message(m) for m in messages],
            "tool_loop": row.get("tool_loop"),
        }
        (traces_dir / f"{cid}.json").write_text(
            json.dumps(trace_doc, ensure_ascii=False), encoding="utf-8"
        )
        n_trace += 1
        if n_trace % 100 == 0:
            print(f"  ... {n_trace} traces")
    print(f"  wrote {n_trace} trace files to {traces_dir}")

    # Trace-derived titles are unreliable (the trace rows can be misaligned
    # with custom_id) — override with authoritative arXiv metadata when the
    # fetch_arxiv_meta.py cache is available.
    meta_path = HERE / "arxiv_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        patched = 0
        for cid, rec in papers.items():
            m = meta.get(cid)
            if not m:
                continue
            if m.get("title"):
                rec["title"] = m["title"]
            rec["authors"] = m.get("authors") or []
            rec["year"] = m.get("year")
            rec["abstract"] = m.get("abstract")
            patched += 1
        print(f"Merged arXiv metadata for {patched} papers from {meta_path.name}")
    else:
        print("  ! no arxiv_meta.json — run fetch_arxiv_meta.py to fix titles "
              "and add authors/abstracts", file=sys.stderr)

    for cid, rec in papers.items():
        if not rec.get("title"):
            rec["title"] = f"(title unavailable) {cid}"

    out_dir.mkdir(parents=True, exist_ok=True)
    papers_list = sorted(papers.values(), key=lambda r: r["custom_id"])
    (out_dir / "papers.json").write_text(
        json.dumps(papers_list, ensure_ascii=False), encoding="utf-8"
    )
    size_kb = (out_dir / "papers.json").stat().st_size / 1024
    print(f"Wrote {len(papers_list)} papers to {out_dir / 'papers.json'} ({size_kb:.0f} KB)")
    return papers


def upload_traces(traces_dir: Path) -> None:
    """Optional: push split traces to a public Supabase Storage bucket named 'traces'."""
    try:
        import requests  # noqa
    except ImportError:
        sys.exit("`pip install requests` to use --upload")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    bucket = os.environ.get("SUPABASE_TRACE_BUCKET", "traces")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars to upload.")
    import requests

    files = sorted(traces_dir.glob("*.json"))
    print(f"Uploading {len(files)} traces to bucket '{bucket}' ...")
    for i, f in enumerate(files, 1):
        endpoint = f"{url}/storage/v1/object/{bucket}/{f.name}"
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "x-upsert": "true",
            },
            data=f.read_bytes(),
            timeout=60,
        )
        if resp.status_code not in (200, 201):
            print(f"  ! {f.name}: {resp.status_code} {resp.text[:120]}", file=sys.stderr)
        if i % 100 == 0:
            print(f"  ... {i}/{len(files)}")
    print("Upload complete.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, default=DEFAULT_BASE, help="output basename (no suffix)")
    p.add_argument("--out", type=Path, default=HERE / "public", help="where papers.json goes")
    p.add_argument("--traces", type=Path, default=HERE / "traces_out", help="per-trace output dir")
    p.add_argument("--upload", action="store_true", help="upload split traces to Supabase Storage")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    build(args.run, args.out, args.traces)
    if args.upload:
        upload_traces(args.traces)


if __name__ == "__main__":
    main()
