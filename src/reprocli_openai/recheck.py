"""Re-check the audit-pool Hard-tier no-code papers on gpt-5.5.

Synchronous Responses API runner (the Batch API queue was too slow). Each
paper is its own request with web search and strict structured outputs; a
small worker pool keeps requests in flight and retries rate limits with
backoff. Raw responses are appended to ``results_raw.jsonl`` as they land, so
rerunning the command resumes where it stopped.

    PYTHONPATH=src python -m reprocli_openai.recheck           # run + extract
    PYTHONPATH=src python -m reprocli_openai.recheck --status  # progress view
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from collections import Counter
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import PLACEHOLDER
from reprocli_vllm.schema.output import FINAL_JSON_SCHEMA, normalize_score_and_tier
from reprocli_vllm.vllm.io import append_jsonl_row

MODEL = "gpt-5.5"
REASONING_EFFORT = "low"
MAX_OUTPUT_TOKENS = 32768
WORKERS = 4
MAX_RETRIES = 10
REQUEST_TIMEOUT = 900
PROMPT_FILE = Path("prompts/prompt_openai_websearch.txt")
POOL = Path("outputs/v5/audit_pool_extracted.jsonl")
TRACE = Path("outputs/v5/audit_pool_trace.jsonl")
OUT_DIR = Path("outputs/v5/openai_hard_recheck_gpt55_low")
RAW_NAME = "results_raw.jsonl"
EXTRACTED_NAME = "recheck_extracted.jsonl"
PAPER_START = "INPUT PAPER:\n\n"
PAPER_END = "\n\n" + "=" * 70 + "\nCORE OBJECTIVE"


def iter_jsonl(path: Path, *, on_error: str = "raise") -> Iterator[dict[str, Any]]:
    """Stream the JSON objects of a JSONL file, skipping blank lines.

    This is the one JSONL reader for the recheck pipeline and the tools built on
    it. ``on_error="raise"`` (the default) lets a missing file and a torn line
    both blow up, which is what the data-merging paths want. ``on_error="report"``
    notes each problem on stderr and keeps going, which is what the app builders
    want when a 200 MB dump has one bad line in it.
    """
    if on_error == "report" and not path.exists():
        print(f"  ! missing {path}", file=sys.stderr)
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as err:
                if on_error == "raise":
                    raise
                print(f"  ! {path.name}:{line_no} bad json: {err.msg}", file=sys.stderr)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    """Truncate ``path`` and write one JSON object per line. Returns the count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def client():
    from openai import OpenAI

    return OpenAI(timeout=REQUEST_TIMEOUT, max_retries=0)


def hard_no_code_ids(pool_path: Path) -> list[str]:
    ids = []
    for row in iter_jsonl(pool_path):
        code = (row.get("signals") or {}).get("code_available") or {}
        if row.get("tier") == "Hard" and not code.get("value"):
            ids.append(str(row["custom_id"]))
    return ids


def paper_texts_from_trace(trace_path: Path, wanted: set[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for row in iter_jsonl(trace_path):
        custom_id = str(row.get("custom_id"))
        if custom_id in wanted and custom_id not in texts:
            user = next(
                (m for m in row.get("messages") or [] if m.get("role") == "user"), None
            )
            content = (user or {}).get("content") or ""
            start = content.find(PAPER_START)
            end = content.find(PAPER_END, start)
            if start < 0 or end < 0:
                print(f"Warning: paper markers not found for {custom_id}", file=sys.stderr)
                continue
            texts[custom_id] = content[start + len(PAPER_START) : end]
    return texts


def request_kwargs(prompt: str) -> dict:
    return {
        "model": MODEL,
        "input": prompt,
        "tools": [{"type": "web_search"}],
        "tool_choice": "auto",
        "reasoning": {"effort": REASONING_EFFORT},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "repro_artifact_classification",
                "schema": FINAL_JSON_SCHEMA,
                "strict": True,
            }
        },
    }


def retry_after_seconds(err) -> float | None:
    try:
        value = err.response.headers.get("retry-after")
        return float(value) if value else None
    except (AttributeError, ValueError):
        return None


def call_with_retry(api, prompt: str):
    from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

    for attempt in range(MAX_RETRIES):
        try:
            return api.responses.create(**request_kwargs(prompt))
        except RateLimitError as err:
            delay = retry_after_seconds(err) or min(120, 10 * 2**attempt)
        except (APIConnectionError, APITimeoutError):
            delay = min(120, 10 * 2**attempt)
        except APIStatusError as err:
            if err.status_code < 500:
                raise
            delay = min(120, 10 * 2**attempt)
        time.sleep(delay + random.uniform(0, 3))
    raise RuntimeError(f"gave up after {MAX_RETRIES} attempts")


def raw_rows(raw_path: Path) -> dict[str, dict]:
    """Every recorded response body, keyed by custom_id. Empty until the run starts."""
    if not raw_path.exists():
        return {}
    return {str(row["custom_id"]): row["body"] for row in iter_jsonl(raw_path)}


def completed(rows: dict[str, dict]) -> dict[str, dict]:
    """The subset whose API call actually finished; the rest are retryable."""
    return {cid: body for cid, body in rows.items() if body.get("status") == "completed"}


def completed_raw_rows(raw_path: Path) -> dict[str, dict]:
    return completed(raw_rows(raw_path))


def run(api, directory: Path) -> None:
    template = PROMPT_FILE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"{PROMPT_FILE} must contain {PLACEHOLDER}.")
    ids = hard_no_code_ids(POOL)
    texts = paper_texts_from_trace(TRACE, set(ids))
    missing = [i for i in ids if i not in texts]
    if missing:
        raise SystemExit(f"{len(missing)} id(s) missing from trace: {missing}")

    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / RAW_NAME
    done = set(completed_raw_rows(raw_path))
    todo = [i for i in ids if i not in done]
    print(f"{len(ids)} papers total, {len(done)} already done, {len(todo)} to go", flush=True)

    lock = threading.Lock()
    finished = [len(done)]

    def one(custom_id: str) -> None:
        response = call_with_retry(api, template.replace(PLACEHOLDER, texts[custom_id]))
        body = response.model_dump(mode="json")
        with lock:
            append_jsonl_row(raw_path, {"custom_id": custom_id, "body": body}, truncate=False)
            finished[0] += 1
            count = finished[0]
        searches = sum(1 for i in body.get("output") or [] if i.get("type") == "web_search_call")
        out_tokens = (body.get("usage") or {}).get("output_tokens")
        print(
            f"{custom_id}: {body.get('status')} ({searches} searches, "
            f"{out_tokens} output tokens) [{count}/{len(ids)}]",
            flush=True,
        )

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(one, cid): cid for cid in todo}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as err:
                print(f"{futures[future]}: FAILED {err}", flush=True)


def output_text(body: dict) -> str:
    return "".join(
        content.get("text") or ""
        for item in body.get("output") or []
        if item.get("type") == "message"
        for content in item.get("content") or []
        if content.get("type") == "output_text"
    )


def parse_result(custom_id: str, body: dict) -> dict:
    row = {
        "custom_id": custom_id,
        "model": body.get("model"),
        "response_status": body.get("status"),
        "web_search_calls": sum(
            1 for i in body.get("output") or [] if i.get("type") == "web_search_call"
        ),
        "usage": body.get("usage"),
    }
    if body.get("status") != "completed":
        return {**row, "error": f"response status {body.get('status')}"}
    text = output_text(body)
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {**row, "error": "unparseable output", "raw_text": text[:2000]}
    return normalize_score_and_tier({**row, **parsed})


def collect(directory: Path) -> None:
    rows = [
        parse_result(cid, body)
        for cid, body in sorted(raw_rows(directory / RAW_NAME).items())
    ]
    out = directory / EXTRACTED_NAME
    write_jsonl(out, rows)
    parsed = [r for r in rows if "error" not in r]
    found = [
        r["custom_id"]
        for r in parsed
        if (r.get("signals") or {}).get("code_available", {}).get("value")
    ]
    tiers = dict(Counter(row.get("tier") or "?" for row in parsed))
    print(f"Wrote {len(rows)} rows to {out} ({len(rows) - len(parsed)} errors)", flush=True)
    print(f"code_available now true for {len(found)}: {found}", flush=True)
    print(f"Recomputed tiers: {tiers}", flush=True)


def status(directory: Path) -> int:
    total = len(hard_no_code_ids(POOL))
    rows = raw_rows(directory / RAW_NAME)
    done = len(completed(rows))
    print(f"{done}/{total} papers completed ({len(rows) - done} non-completed responses)")
    return 0 if done == total else 1


def add_recheck_args(parser: argparse.ArgumentParser) -> None:
    """The three flags every downstream recheck consumer shares."""
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")


def wait_for_recheck(directory: Path, poll_seconds: int) -> None:
    """Block until every hard/no-code paper has a completed response."""
    total = len(hard_no_code_ids(POOL))
    raw_path = directory / RAW_NAME
    while True:
        done = len(completed_raw_rows(raw_path))
        print(f"recheck progress: {done}/{total}", flush=True)
        if done >= total:
            return
        time.sleep(poll_seconds)


def collect_recheck(
    directory: Path,
    allow_partial: bool,
    *,
    incomplete: str = "recheck is incomplete: {done}/{total}",
    partial: str = "recheck is incomplete; reporting partial results: {done}/{total}",
    row_errors: str = "{count} recheck rows have extraction errors",
) -> Path:
    """Extract the raw responses and return the path to the extracted rows.

    Exits when the run is short of ``hard_no_code_ids`` without ``allow_partial``,
    or when any extracted row carries an error. The three messages are the
    caller's own wording so each operational script keeps the output its operator
    reads.
    """
    total = len(hard_no_code_ids(POOL))
    done = len(completed_raw_rows(directory / RAW_NAME))
    if done < total and not allow_partial:
        raise SystemExit(incomplete.format(done=done, total=total))
    if done < total:
        print(partial.format(done=done, total=total), flush=True)
    collect(directory)
    extracted = directory / EXTRACTED_NAME
    errors = [row for row in iter_jsonl(extracted) if "error" in row]
    if errors:
        raise SystemExit(row_errors.format(count=len(errors)))
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="print progress and exit")
    args = parser.parse_args()
    if args.status:
        return status(OUT_DIR)
    run(client(), OUT_DIR)
    collect(OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
