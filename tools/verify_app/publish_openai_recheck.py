#!/usr/bin/env python3
"""Wait for the OpenAI recheck, merge it into the label app, and deploy.

The recheck only covers the Hard/no-code slice. This script overlays those
rows onto the v5 audit pool, replaces the matching model traces with compact
OpenAI Responses traces, rebuilds ``public/papers.json``, bundles traces into
``public/traces/``, and can deploy the static app to Vercel.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from collections.abc import Iterable

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reprocli_openai import recheck  # noqa: E402
from reprocli_vllm.schema.output import normalize_score_and_tier  # noqa: E402
from build_data import build, upload_traces  # noqa: E402

BASE = REPO / "outputs/v5/audit_pool"
RECHECK_DIR = REPO / "outputs/v5/openai_hard_recheck_gpt55_low"
MERGED_BASE = REPO / "outputs/v5/audit_pool_gpt55_low"
PUBLIC = HERE / "public"
TRACE_BUNDLE = PUBLIC / "traces"
SELECTION_FIELDS = (
    "audited_h100_hours",
    "h100_hours_adjudicated",
    "selection_band",
)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def completed_raw_rows(raw_path: Path) -> dict[str, dict[str, Any]]:
    return {
        cid: body
        for cid, body in recheck.raw_rows(raw_path).items()
        if body.get("status") == "completed"
    }


def wait_for_recheck(directory: Path, poll_seconds: int) -> None:
    total = len(recheck.hard_no_code_ids(recheck.POOL))
    raw_path = directory / recheck.RAW_NAME
    while True:
        done = len(completed_raw_rows(raw_path)) if raw_path.exists() else 0
        print(f"recheck progress: {done}/{total}", flush=True)
        if done >= total:
            return
        time.sleep(poll_seconds)


def collect_recheck(directory: Path, allow_partial: bool) -> Path:
    total = len(recheck.hard_no_code_ids(recheck.POOL))
    done = len(completed_raw_rows(directory / recheck.RAW_NAME))
    if done < total and not allow_partial:
        raise SystemExit(f"recheck is incomplete: {done}/{total} completed")
    if done < total:
        print(f"recheck is incomplete; publishing partial replacements: {done}/{total}", flush=True)
    recheck.collect(directory)
    extracted = directory / "recheck_extracted.jsonl"
    rows = list(recheck.iter_jsonl(extracted))
    errors = [row for row in rows if "error" in row]
    if errors:
        raise SystemExit(f"{len(errors)} recheck rows have errors; refusing to publish")
    return extracted


def merge_extracted(base: Path, updates_path: Path, out_base: Path) -> set[str]:
    base_path = Path(f"{base}_extracted.jsonl")
    updates = {str(row["custom_id"]): row for row in recheck.iter_jsonl(updates_path)}
    replaced: set[str] = set()

    def rows() -> Iterable[dict[str, Any]]:
        for old in recheck.iter_jsonl(base_path):
            cid = str(old.get("custom_id"))
            new = updates.get(cid)
            if not new:
                yield old
                continue
            merged = merged_recheck_row(old, new)
            for field in SELECTION_FIELDS:
                if field in old and old[field] is not None:
                    merged[field] = old[field]
            replaced.add(cid)
            yield merged

    count = write_jsonl(Path(f"{out_base}_extracted.jsonl"), rows())
    missing = set(updates) - replaced
    if missing:
        raise SystemExit(f"{len(missing)} recheck rows were not in the v5 pool: {sorted(missing)}")
    print(f"wrote {count} merged extracted rows; replaced {len(replaced)}", flush=True)
    return replaced


def signal_value(row: dict[str, Any], name: str) -> bool | None:
    value = ((row.get("signals") or {}).get(name) or {}).get("value")
    return value if isinstance(value, bool) else None


def merged_recheck_row(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(new)
    if (new.get("tier") == "Artifact-Blocked"
            and signal_value(old, "dataset_available") is True
            and signal_value(new, "dataset_available") is False):
        signals = dict(merged.get("signals") or {})
        old_signals = old.get("signals") or {}
        for field in ("dataset_available", "dataset_is_standard"):
            if field in old_signals:
                signals[field] = old_signals[field]
        merged["signals"] = signals
        merged = normalize_score_and_tier(merged)
    return merged


def search_summary(item: dict[str, Any]) -> str:
    action = item.get("action") or {}
    if action.get("type") == "open_page":
        return f"open_page: {action.get('url')}\nstatus: {item.get('status')}"
    queries = action.get("queries") or ([action.get("query")] if action.get("query") else [])
    return "web_search:\n" + "\n".join(f"- {q}" for q in queries) + f"\nstatus: {item.get('status')}"


def openai_trace_row(custom_id: str, body: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "Replacement trace from OpenAI hard/no-code recheck "
                f"({body.get('model')}, reasoning={body.get('reasoning')})."
            ),
        }
    ]
    for item in body.get("output") or []:
        kind = item.get("type")
        if kind == "web_search_call":
            messages.append({"role": "tool", "name": "web_search", "content": search_summary(item)})
        elif kind == "message":
            text = recheck.output_text({"output": [item]})
            messages.append({"role": "assistant", "content": text})
    return {
        "custom_id": custom_id,
        "messages": messages,
        "tool_loop": {
            "source": "openai_hard_recheck_gpt55_low",
            "model": body.get("model"),
            "status": body.get("status"),
            "usage": body.get("usage"),
            "reasoning": body.get("reasoning"),
        },
    }


def merge_traces(base: Path, directory: Path, replaced: set[str], out_base: Path) -> None:
    raw = completed_raw_rows(directory / recheck.RAW_NAME)
    replacements = {
        cid: openai_trace_row(cid, raw[cid])
        for cid in replaced
        if cid in raw
    }
    if set(replacements) != replaced:
        raise SystemExit("missing completed raw responses for some replacement traces")
    base_path = Path(f"{base}_trace.jsonl")
    seen: set[str] = set()

    def rows() -> Iterable[dict[str, Any]]:
        for old in recheck.iter_jsonl(base_path):
            cid = str(old.get("custom_id"))
            if cid in replacements:
                seen.add(cid)
                yield replacements[cid]
            else:
                yield old

    count = write_jsonl(Path(f"{out_base}_trace.jsonl"), rows())
    missing = replaced - seen
    if missing:
        raise SystemExit(f"{len(missing)} trace rows were not in the v5 pool: {sorted(missing)}")
    print(f"wrote {count} merged trace rows; replaced {len(replaced)}", flush=True)


def bundle_traces() -> None:
    if TRACE_BUNDLE.exists():
        shutil.rmtree(TRACE_BUNDLE)
    shutil.copytree(HERE / "traces_out", TRACE_BUNDLE)
    set_trace_base("traces")
    print(f"bundled traces into {TRACE_BUNDLE}", flush=True)


def set_trace_base(value: str) -> None:
    config = PUBLIC / "config.js"
    text = config.read_text(encoding="utf-8")
    text = re.sub(r'TRACE_BASE_URL:\s*"[^"]*"', f'TRACE_BASE_URL: "{value}"', text)
    config.write_text(text, encoding="utf-8")


def supabase_trace_base() -> str:
    url = os.environ.get("SUPABASE_URL") or config_value("SUPABASE_URL") or ""
    return f"{url.rstrip('/')}/storage/v1/object/public/traces"


def config_value(name: str) -> str | None:
    config = (PUBLIC / "config.js").read_text(encoding="utf-8")
    match = re.search(rf'{name}:\s*"([^"]*)"', config)
    return match.group(1) if match else None


def shell_file_value(name: str) -> str | None:
    pattern = re.compile(rf"^\s*(?:export\s+)?{name}=(['\"]?)(.+?)\1\s*$")
    for path in (Path.home() / ".bashrc", Path.home() / ".profile"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = pattern.match(line)
            if match and not line.lstrip().startswith("#"):
                return re.sub(r"\s+", "", match.group(2))
    return None


def upload_supabase_traces() -> None:
    url = os.environ.get("SUPABASE_URL") or config_value("SUPABASE_URL")
    if url:
        os.environ["SUPABASE_URL"] = url
    if os.environ.get("SUPABASE_SERVICE_KEY"):
        os.environ["SUPABASE_SERVICE_KEY"] = re.sub(r"\s+", "", os.environ["SUPABASE_SERVICE_KEY"])
    else:
        key = shell_file_value("SUPABASE_SERVICE_KEY")
        if key:
            os.environ["SUPABASE_SERVICE_KEY"] = key
    if not os.environ.get("SUPABASE_TRACE_BUCKET"): os.environ["SUPABASE_TRACE_BUCKET"] = "traces"
    upload_traces(HERE / "traces_out")
    set_trace_base(supabase_trace_base())


def deploy() -> None:
    subprocess.run(["vercel", "--prod", "--yes"], cwd=PUBLIC, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--trace-target", choices=("bundle", "supabase", "none"), default="bundle")
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()

    if not args.no_wait:
        wait_for_recheck(RECHECK_DIR, args.poll_seconds)
    extracted = collect_recheck(RECHECK_DIR, args.allow_partial)
    replaced = merge_extracted(BASE, extracted, MERGED_BASE)
    merge_traces(BASE, RECHECK_DIR, replaced, MERGED_BASE)
    build(MERGED_BASE, PUBLIC, HERE / "traces_out")
    if args.trace_target == "bundle":
        bundle_traces()
    elif args.trace_target == "supabase":
        upload_supabase_traces()
    if args.deploy:
        deploy()
    print("publish complete", flush=True)


if __name__ == "__main__":
    main()
