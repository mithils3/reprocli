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


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


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
        abstract = norm_ws(entry.findtext(f"{ATOM}summary") or "")
        if len(abstract) > ABSTRACT_CLIP:
            abstract = abstract[:ABSTRACT_CLIP].rsplit(" ", 1)[0] + " …"
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
    for start in range(0, len(missing), BATCH):
        batch = missing[start:start + BATCH]
        print(f"Fetching {start + 1}-{start + len(batch)} of {len(missing)} ...")
        meta.update(fetch_batch(batch))
        CACHE.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        if start + BATCH < len(missing):
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
