from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

TERMINAL_BATCH_STATUSES = {"completed", "failed", "expired", "cancelled"}
RESPONSES_ENDPOINT = "/v1/responses"


def create_responses_batch(
    client: Any,
    input_path: Path,
    *,
    metadata: dict[str, str] | None = None,
) -> Any:
    with input_path.open("rb") as handle:
        file_obj = client.files.create(file=handle, purpose="batch")
    return client.batches.create(
        input_file_id=file_obj.id,
        endpoint=RESPONSES_ENDPOINT,
        completion_window="24h",
        metadata=metadata or {},
    )


def wait_for_terminal_batch(client: Any, batch_id: str, poll_seconds: float) -> Any:
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be positive")

    last_summary = ""
    while True:
        batch = client.batches.retrieve(batch_id)
        summary = batch_summary(batch)
        if summary != last_summary:
            print(summary, file=sys.stderr)
            last_summary = summary
        if batch_status(batch) in TERMINAL_BATCH_STATUSES:
            return batch
        time.sleep(poll_seconds)


def write_batch_info(path: Path, batch: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(dump_openai_object(batch), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def download_batch_files(
    client: Any,
    batch: Any,
    *,
    output_path: Path,
    error_path: Path,
) -> None:
    output_file_id = object_attr(batch, "output_file_id")
    error_file_id = object_attr(batch, "error_file_id")
    if output_file_id:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(download_file_text(client, output_file_id), encoding="utf-8")
    if error_file_id:
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text(download_file_text(client, error_file_id), encoding="utf-8")


def download_file_text(client: Any, file_id: str) -> str:
    response = client.files.content(file_id)
    if hasattr(response, "text"):
        return response.text
    content = response.read()
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return str(content)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            json.dump(row, handle, ensure_ascii=False)
            handle.write("\n")


def read_batch_registry(path: Path) -> list[dict[str, Any]]:
    records = load_jsonl(path)
    for record in records:
        if "batch_id" not in record:
            raise ValueError(f"{path}: registry row is missing batch_id")
    return records


def append_batch_registry(path: Path, record: dict[str, Any]) -> None:
    records = [
        existing
        for existing in read_batch_registry(path)
        if existing.get("batch_id") != record.get("batch_id")
    ]
    records.append(record)
    write_jsonl(path, records)


def rewrite_batch_registry(path: Path, records: list[dict[str, Any]]) -> None:
    if records:
        write_jsonl(path, records)
    elif path.exists():
        path.unlink()


def batch_specific_path(path: Path, batch_id: str) -> Path:
    return path.with_name(f"{path.stem}_{batch_id}{path.suffix}")


def batch_status(batch: Any) -> str:
    return str(object_attr(batch, "status") or "")


def batch_summary(batch: Any) -> str:
    counts = object_attr(batch, "request_counts")
    count_text = ""
    if counts:
        total = object_attr(counts, "total")
        completed = object_attr(counts, "completed")
        failed = object_attr(counts, "failed")
        count_text = f" requests={completed}/{total} failed={failed}"
    return f"Batch {object_attr(batch, 'id')} status={batch_status(batch)}{count_text}"


def dump_openai_object(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return json.loads(json.dumps(value, default=str))


def responses_output_text(response_body: dict[str, Any]) -> str:
    output_text = response_body.get("output_text")
    if isinstance(output_text, str):
        return output_text

    chunks = []
    for item in response_body.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def batch_response_body(batch_row: dict[str, Any]) -> dict[str, Any]:
    response = batch_row.get("response") or {}
    if response.get("status_code") != 200:
        return {}
    body = response.get("body")
    return body if isinstance(body, dict) else {}


def object_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
