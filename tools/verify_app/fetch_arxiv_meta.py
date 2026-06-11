#!/usr/bin/env python3
"""Patch public/papers.json with authoritative metadata from the arXiv API.

Why: the titles in papers.json were originally scraped out of the model's
conversation traces, and ~25% of them belong to a *different* paper than the
custom_id says (the trace rows are misaligned). Reviewers were shown the wrong
title next to the right claim. This script fetches the real title — plus
authors, year, and abstract — straight from the arXiv API, keyed by arXiv id,
and rewrites papers.json.

Results are cached in arxiv_meta.json so re-runs (and build_data.py) don't
re-hit the API.

The Semantic Scholar batch endpoint is tried first (450 ids per request, no
practical rate limit); the arXiv API is the fallback for ids Semantic Scholar
doesn't know, since arXiv aggressively rate-limits batch queries.

Usage::

    python3 tools/verify_app/fetch_arxiv_meta.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPERS = HERE / "public" / "papers.json"
CACHE = HERE / "arxiv_meta.json"

API = "http://export.arxiv.org/api/query?id_list={ids}&max_results={n}"
ATOM = "{http://www.w3.org/2005/Atom}"
BATCH = 100
ABSTRACT_CLIP = 1600

S2_API = ("https://api.semanticscholar.org/graph/v1/paper/batch"
          "?fields=title,authors,year,abstract")
S2_BATCH = 450


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def clip_abstract(text: str) -> str:
    text = norm_ws(text)
    if len(text) > ABSTRACT_CLIP:
        text = text[:ABSTRACT_CLIP].rsplit(" ", 1)[0] + " …"
    return text


def fetch_s2_batch(ids: list[str]) -> dict[str, dict]:
    """Semantic Scholar paper batch lookup; returns only the ids it resolves."""
    req = urllib.request.Request(
        S2_API,
        data=json.dumps({"ids": [f"ARXIV:{i}" for i in ids]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                records = json.loads(resp.read())
            break
        except Exception as exc:  # 429s are routine; back off and retry
            if attempt == 3:
                print(f"  ! Semantic Scholar batch failed: {exc}", file=sys.stderr)
                return {}
            time.sleep(5 * (attempt + 1))
    out: dict[str, dict] = {}
    for cid, rec in zip(ids, records):
        if not isinstance(rec, dict) or not rec.get("title"):
            continue
        out[cid] = {
            "title": norm_ws(rec["title"]),
            "authors": [norm_ws(a.get("name") or "") for a in rec.get("authors") or []],
            "year": rec.get("year"),
            "abstract": clip_abstract(rec.get("abstract") or ""),
        }
    return out


def fetch_batch(ids: list[str]) -> dict[str, dict]:
    url = API.format(ids=",".join(ids), n=len(ids))
    with urllib.request.urlopen(url, timeout=60) as resp:
        root = ET.fromstring(resp.read())
    out: dict[str, dict] = {}
    for entry in root.iter(f"{ATOM}entry"):
        raw_id = entry.findtext(f"{ATOM}id") or ""
        # http://arxiv.org/abs/2112.02604v2 -> 2112.02604
        m = re.search(r"abs/([^v]+?)(v\d+)?$", raw_id)
        if not m:
            continue
        cid = m.group(1)
        authors = [norm_ws(a.findtext(f"{ATOM}name") or "")
                   for a in entry.iter(f"{ATOM}author")]
        published = entry.findtext(f"{ATOM}published") or ""
        abstract = clip_abstract(entry.findtext(f"{ATOM}summary") or "")
        out[cid] = {
            "title": norm_ws(entry.findtext(f"{ATOM}title") or ""),
            "authors": authors,
            "year": int(published[:4]) if published[:4].isdigit() else None,
            "abstract": abstract,
        }
    return out


def main() -> None:
    papers = json.loads(PAPERS.read_text(encoding="utf-8"))
    ids = [p["custom_id"] for p in papers]

    meta: dict[str, dict] = {}
    if CACHE.exists():
        meta = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"Loaded {len(meta)} cached records from {CACHE.name}")

    missing = [i for i in ids if i not in meta]
    for start in range(0, len(missing), S2_BATCH):
        batch = missing[start:start + S2_BATCH]
        print(f"Semantic Scholar {start + 1}-{start + len(batch)} of {len(missing)} ...")
        meta.update(fetch_s2_batch(batch))
        CACHE.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    # arXiv fallback: ids Semantic Scholar doesn't know, or knows without abstract
    fallback = [i for i in ids if i not in meta or not meta[i].get("abstract")]
    for start in range(0, len(fallback), BATCH):
        batch = fallback[start:start + BATCH]
        print(f"arXiv fallback {start + 1}-{start + len(batch)} of {len(fallback)} ...")
        for cid, rec in fetch_batch(batch).items():
            if cid not in meta:
                meta[cid] = rec
            elif not meta[cid].get("abstract"):
                meta[cid]["abstract"] = rec["abstract"]
        CACHE.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        if start + BATCH < len(fallback):
            time.sleep(3)  # arXiv API rate-limit courtesy

    still_missing = [i for i in ids if i not in meta]
    if still_missing:
        print(f"  ! no arXiv record for: {', '.join(still_missing)}", file=sys.stderr)

    changed_titles = 0
    for p in papers:
        m = meta.get(p["custom_id"])
        if not m:
            continue
        if m["title"] and norm_ws(p.get("title") or "") != m["title"]:
            changed_titles += 1
        p["title"] = m["title"] or p.get("title")
        p["authors"] = m["authors"]
        p["year"] = m["year"]
        p["abstract"] = m["abstract"]

    PAPERS.write_text(json.dumps(papers, ensure_ascii=False), encoding="utf-8")
    size_kb = PAPERS.stat().st_size / 1024
    print(f"Patched {len(papers)} papers ({changed_titles} titles corrected) -> "
          f"{PAPERS} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
