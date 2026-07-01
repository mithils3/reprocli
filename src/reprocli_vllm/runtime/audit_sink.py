"""Best-effort live upload of the auditor transcript to Supabase (opt-in).

The reproduce mirror of this is ``reprocli_repro.supabase_sink``; this is the same
machinery for the S7 auditor so its run streams to the dashboard's Audits page in
real time. Disabled unless ``SUPABASE_URL`` + ``SUPABASE_SERVICE_KEY`` are set. A
background worker drains a bounded queue and batches PostgREST writes; a full queue
drops rather than blocking, and every network failure is swallowed — the loop and
the on-disk trace stay the source of truth.

Fed via ``live_events.register_sink(sink.on_event)``: each round becomes
``audit_events`` rows under one ``audit_runs`` row per graded paper. The row links
back to the reproduce run it graded via ``graded_run_id`` (``$REPROCLI_GRADED_RUN_ID``,
set by the pipeline), so the app can pair the audit with its run.
"""

from __future__ import annotations

import json
import os
import queue
import socket
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from reprocli_vllm.runtime import audit_rows as rows
from reprocli_vllm.runtime import live_events

try:  # already importable transitively; urllib is the fallback
    import requests
except ImportError:  # pragma: no cover
    requests = None

QUEUE_MAX = 4000
BATCH_MAX = 50
HTTP_TIMEOUT = 8.0


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class SinkConfig:
    url: str
    service_key: str
    graded_run_id: str | None
    model: str | None
    host: str

    @classmethod
    def from_env(cls, model: str | None = None) -> "SinkConfig | None":
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return None
        return cls(url=url.rstrip("/"), service_key=key,
                   graded_run_id=os.environ.get("REPROCLI_GRADED_RUN_ID") or None,
                   model=model, host=socket.gethostname())


class AuditSink:
    def __init__(self, cfg: SinkConfig) -> None:
        self.cfg = cfg
        self.q: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=QUEUE_MAX)
        self._lock = threading.Lock()
        self._seq: dict[str, int] = {}
        self._round: dict[str, int | None] = {}
        self._rounds_seen: dict[str, int] = {}
        self._seen: set[str] = set()
        self._base = _now_iso()
        self.dropped = self.failed = 0
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, name="audit-sink", daemon=True)
        self._worker.start()

    # ---- identity -----------------------------------------------------------
    def _audit_run_id(self, custom_id: str) -> str:
        base = self.cfg.graded_run_id or self._base
        return f"{base}-{custom_id}-audit"

    def _ensure_run(self, custom_id: str) -> str:
        aid = self._audit_run_id(custom_id)
        if aid not in self._seen:
            self._seen.add(aid)
            self._put("run_upsert", {
                "audit_run_id": aid, "graded_run_id": self.cfg.graded_run_id,
                "arxiv_id": custom_id, "model": self.cfg.model, "status": "running",
                "host": self.cfg.host, "started_at": _now_iso(), "updated_at": _now_iso(),
            })
        return aid

    # ---- enqueue (called from loop / tool threads; never blocks) ------------
    def _put(self, kind: str, payload: Any) -> None:
        try:
            self.q.put_nowait((kind, payload))
        except queue.Full:
            self.dropped += 1

    def _next_seq(self, aid: str) -> int:
        with self._lock:
            n = self._seq.get(aid, 0)
            self._seq[aid] = n + 1
            return n

    def _row_base(self, aid: str, kind: str, idx: int | None) -> dict[str, Any]:
        return {"audit_run_id": aid, "seq": self._next_seq(aid), "kind": kind, "round_index": idx}

    def on_event(self, kind: str, meta: dict[str, Any], payload: dict[str, Any]) -> None:
        custom_id = meta.get("custom_id")
        if not custom_id:
            return
        aid = self._ensure_run(custom_id)
        idx = meta.get("round_index")
        if kind in ("round_open", "final"):
            self._round[aid] = idx
            if isinstance(idx, int):
                self._rounds_seen[aid] = max(self._rounds_seen.get(aid, 0), idx + 1)
            self._put("events", rows.message_row(self._row_base(aid, kind, idx), payload))
            if kind == "final":
                self._finish(aid, payload)
        elif kind == "call_start":
            self._put("events", rows.call_row(self._row_base(aid, "call_start", self._round.get(aid)), payload["call"]))
        elif kind == "call_result":
            self._put("events", rows.result_row(self._row_base(aid, "call_result", self._round.get(aid)), payload["result"]))

    def _finish(self, aid: str, payload: dict[str, Any]) -> None:
        v = payload.get("verdict") or {}
        self._put("run_patch", (aid, {
            "status": "finished", "exit_reason": payload.get("exit_reason") or None,
            "score": v.get("score"), "verdict": v.get("verdict"),
            "reproduced": v.get("reproduced"), "has_high_cheat_flag": v.get("has_high_cheat_flag"),
            "tool_rounds_used": self._rounds_seen.get(aid, 0),
            "finished_at": _now_iso(), "updated_at": _now_iso(),
        }))

    # ---- worker / HTTP ------------------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set() or not self.q.empty():
            try:
                item = self.q.get(timeout=0.3)
            except queue.Empty:
                continue
            batch = [item]
            while len(batch) < BATCH_MAX:
                try:
                    batch.append(self.q.get_nowait())
                except queue.Empty:
                    break
            self._flush(batch)
            for _ in batch:
                self.q.task_done()

    def _flush(self, batch: list[tuple[str, Any]]) -> None:
        events = []
        for kind, payload in batch:
            if kind == "events":
                events.append(payload)
            elif kind == "run_upsert":
                self._post("POST", "/rest/v1/audit_runs?on_conflict=audit_run_id", [payload],
                           prefer="resolution=merge-duplicates,return=minimal")
            elif kind == "run_patch":
                self._post("PATCH", f"/rest/v1/audit_runs?audit_run_id=eq.{payload[0]}", payload[1],
                           prefer="return=minimal")
        if events:  # bulk insert needs identical keys per row -> pad to the union
            ks = set().union(*(e.keys() for e in events))
            self._post("POST", "/rest/v1/audit_events", [{k: e.get(k) for k in ks} for e in events],
                       prefer="return=minimal")

    def _headers(self, prefer: str | None) -> dict[str, str]:
        h = {"apikey": self.cfg.service_key, "Authorization": f"Bearer {self.cfg.service_key}",
             "Content-Type": "application/json"}
        if prefer:
            h["Prefer"] = prefer
        return h

    def _post(self, method: str, path: str, body: Any, *, prefer: str | None = None) -> None:
        url = self.cfg.url + path
        data = json.dumps(body).encode()
        try:
            if requests is not None:
                r = requests.request(method, url, headers=self._headers(prefer), data=data, timeout=HTTP_TIMEOUT)
                code = r.status_code
            else:
                req = urllib.request.Request(url, data=data, headers=self._headers(prefer), method=method)
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                    code = resp.status
            if code >= 300:
                self.failed += 1
        except Exception:  # noqa: BLE001 — best-effort; never propagate
            self.failed += 1

    def close(self, timeout: float = 12.0) -> None:
        self._stop.set()
        self._worker.join(timeout=timeout)
        if self.dropped or self.failed:
            print(f"audit_sink: {self.dropped} dropped, {self.failed} failed POSTs", flush=True)


def install(cfg: SinkConfig | None) -> "AuditSink | None":
    """Start the sink and wire it into the live_events seam. ``None`` cfg -> disabled."""
    if cfg is None:
        return None
    sink = AuditSink(cfg)
    live_events.register_sink(sink.on_event)
    return sink
