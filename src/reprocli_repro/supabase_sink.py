"""Best-effort live upload of the reproduce transcript to Supabase (opt-in).

Disabled unless ``SUPABASE_URL`` + ``SUPABASE_SERVICE_KEY`` are set (default runs
unchanged). When enabled, a background worker drains a bounded queue and batches
PostgREST writes (a full queue drops, never blocks). Mirrors ``live_log``'s
swallow-all discipline: no network failure may slow or crash the loop — the
on-disk ``agent.full.log`` stays the source of truth. Fed via
``live_log.register_sink(sink.on_event)``: each round becomes ``repro_events`` rows
(plus throttled ``repro_runs`` meter patches); the model's per-response token
``usage`` is summed onto the run row; on ``final`` the full log and a detailed
``stats.json`` are optionally pushed to Storage.

Pure row construction lives in ``supabase_rows``; per-run token bookkeeping in
``run_stats`` — this module is the queue + worker + HTTP plumbing.
"""

from __future__ import annotations

import json
import os
import queue
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reprocli_repro import live_log, supabase_rows as rows
from reprocli_repro.run_stats import RunStats
from reprocli_repro.supabase_rows import budget_of, run_id_of

try:  # already importable transitively (datasets/hf_hub); urllib is the fallback
    import requests
except ImportError:  # pragma: no cover
    requests = None
import urllib.request

QUEUE_MAX = 4000           # events; beyond this we drop rather than block the loop
BATCH_MAX = 50
HTTP_TIMEOUT = 8.0
BUCKET = "repro-logs"
GOOD_EXIT = {"natural", "completed"}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class SinkConfig:
    url: str
    service_key: str
    host: str
    upload_full_log: bool
    upload_stats: bool

    @classmethod
    def from_env(cls) -> "SinkConfig | None":
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return None
        full = os.environ.get("REPRO_UPLOAD_FULL_LOG", "").lower() in ("1", "true", "yes")
        # stats.json is tiny and the whole point of enabling the sink, so it's on
        # by default whenever the sink is active; set REPRO_UPLOAD_STATS=0 to skip.
        stats = os.environ.get("REPRO_UPLOAD_STATS", "1").lower() not in ("0", "false", "no")
        return cls(url=url.rstrip("/"), service_key=key, host=socket.gethostname(),
                   upload_full_log=full, upload_stats=stats)


class SupabaseSink:
    def __init__(self, cfg: SinkConfig) -> None:
        self.cfg = cfg
        self.q: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=QUEUE_MAX)
        self._lock = threading.Lock()
        self._seq: dict[str, int] = {}
        self._round: dict[str, int | None] = {}
        self._rounds_seen: dict[str, int] = {}
        self._total: dict[str, float | None] = {}
        self._lastpatch: dict[str, tuple] = {}
        self._stats: dict[str, RunStats] = {}
        self.dropped = 0
        self.failed = 0
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, name="supabase-sink", daemon=True)
        self._worker.start()

    # ---- enqueue (called from the loop / tool threads; never blocks) ----------
    def _put(self, kind: str, payload: Any) -> None:
        try:
            self.q.put_nowait((kind, payload))
        except queue.Full:
            self.dropped += 1

    def _next_seq(self, run_id: str) -> int:
        with self._lock:
            n = self._seq.get(run_id, 0)
            self._seq[run_id] = n + 1
            return n

    def _row_base(self, run_id: str, kind: str, idx: int | None) -> dict[str, Any]:
        return {"run_id": run_id, "seq": self._next_seq(run_id), "kind": kind, "round_index": idx}

    def _stats_for(self, run_id: str) -> RunStats:
        s = self._stats.get(run_id)
        if s is None:
            s = self._stats[run_id] = RunStats()
        return s

    def upsert_run(self, ctx, *, model: str | None, status: str = "running") -> None:
        run_id = run_id_of(ctx)
        if not run_id:
            return
        total, remaining = budget_of(ctx)
        self._total[run_id] = total
        self._put("run_upsert", {
            "run_id": run_id, "arxiv_id": getattr(ctx, "arxiv_id", None), "model": model,
            "status": status, "host": self.cfg.host, "budget": total,
            "total_h100": total, "remaining_h100": remaining, "spent_h100": 0,
            "tool_rounds_used": 0, "started_at": _now_iso(), "updated_at": _now_iso(),
        })

    def on_event(self, kind: str, ctx, payload: dict[str, Any]) -> None:
        run_id = run_id_of(ctx)
        if not run_id:
            return
        if kind == "round_open" or kind == "final":
            idx = payload.get("round_index")
            self._round[run_id] = idx
            if isinstance(idx, int):
                self._rounds_seen[run_id] = max(self._rounds_seen.get(run_id, 0), idx + 1)
            self._put("events", rows.message_row(self._row_base(run_id, kind, idx), payload))
            if kind == "final":
                self._finish(ctx, run_id, payload.get("exit_reason") or "")
        elif kind == "usage":
            self._stats_for(run_id).add_usage(
                payload.get("round_index"), payload.get("kind"), payload.get("usage"))
            self._put("run_patch", (run_id, {**self._stats_for(run_id).run_fields(), "updated_at": _now_iso()}))
        elif kind == "call_start":
            self._stats_for(run_id).add_tool_call()
            self._put("events", rows.call_row(self._row_base(run_id, "call_start", self._round.get(run_id)), payload["call"]))
        elif kind == "call_result":
            self._put("events", rows.result_row(self._row_base(run_id, "call_result", self._round.get(run_id)), payload["result"]))
            self._patch_meters(run_id, payload["result"])

    # ---- run-row meter / finalize --------------------------------------------
    def _patch_meters(self, run_id, res):
        rem = res.get("remaining_h100_hours")
        if rem is None:
            return
        rounds = self._rounds_seen.get(run_id, 0)
        key = (round(rem, 4), rounds)
        if self._lastpatch.get(run_id) == key:
            return
        self._lastpatch[run_id] = key
        fields = {"remaining_h100": round(rem, 4), "tool_rounds_used": rounds, "updated_at": _now_iso()}
        total = self._total.get(run_id)
        if total is not None:
            fields["spent_h100"] = round(total - rem, 4)
        self._put("run_patch", (run_id, fields))

    def _finish(self, ctx, run_id, exit_reason):
        total, remaining = budget_of(ctx)
        fields = {"status": "finished", "exit_reason": exit_reason or None,
                  "finished_at": _now_iso(), "updated_at": _now_iso(),
                  "tool_rounds_used": self._rounds_seen.get(run_id, 0)}
        fields.update(self._stats_for(run_id).run_fields())
        if total is not None and remaining is not None:
            fields["spent_h100"] = round(total - remaining, 4)
            fields["remaining_h100"] = round(remaining, 4)
        self._put("run_patch", (run_id, fields))
        if self.cfg.upload_full_log:
            ev = getattr(ctx, "evidence", None)
            if ev:
                self._put("full_log", (run_id, str(Path(ev).parent / "agent.full.log")))
        if self.cfg.upload_stats:
            self._queue_stats(ctx, run_id, exit_reason)

    def _queue_stats(self, ctx, run_id, exit_reason):
        ev = getattr(ctx, "evidence", None)
        if not ev:
            return
        total, remaining = budget_of(ctx)
        meta = {
            "run_id": run_id, "arxiv_id": getattr(ctx, "arxiv_id", None), "host": self.cfg.host,
            "exit_reason": exit_reason or None, "generated_at": _now_iso(),
            "budget_h100": total, "remaining_h100": remaining,
            "spent_h100": (round(total - remaining, 4) if total is not None and remaining is not None else None),
            "tool_rounds_used": self._rounds_seen.get(run_id, 0),
        }
        path = Path(ev).parent / "stats.json"
        if self._stats_for(run_id).write_doc(path, meta):
            self._put("stats", (run_id, str(path)))

    # ---- worker / HTTP -------------------------------------------------------
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

    def _flush(self, batch):
        events = []
        for kind, payload in batch:
            if kind == "events":
                events.append(payload)
            elif kind == "run_upsert":
                self._upsert_run(payload)
            elif kind == "run_patch":
                self._patch_run(payload[0], payload[1])
            elif kind == "full_log":
                self._do_storage(payload[0], payload[1], f"{payload[0]}.log", "text/plain", "full_log_url")
            elif kind == "stats":
                self._do_storage(payload[0], payload[1], f"{payload[0]}-stats.json", "application/json", "stats_url")
        if events:  # PostgREST bulk insert needs identical keys per row -> pad to union
            ks = set().union(*(e.keys() for e in events))
            self._post("POST", "/rest/v1/repro_events", [{k: e.get(k) for k in ks} for e in events], prefer="return=minimal")

    def _headers(self, prefer=None, content="application/json"):
        h = {"apikey": self.cfg.service_key, "Authorization": f"Bearer {self.cfg.service_key}", "Content-Type": content}
        if prefer:
            h["Prefer"] = prefer
        return h

    def _post(self, method, path, body, *, prefer=None, raw=None, content="application/json"):
        url = self.cfg.url + path
        data = raw if raw is not None else json.dumps(body).encode()
        try:
            if requests is not None:
                r = requests.request(method, url, headers=self._headers(prefer, content),
                                     data=data, timeout=HTTP_TIMEOUT)
                code = r.status_code
            else:
                req = urllib.request.Request(url, data=data, headers=self._headers(prefer, content), method=method)
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                    code = resp.status
            if code >= 300:
                self.failed += 1
        except Exception:  # noqa: BLE001 — best-effort; never propagate
            self.failed += 1

    def _upsert_run(self, row):
        self._post("POST", "/rest/v1/repro_runs?on_conflict=run_id", [row],
                   prefer="resolution=merge-duplicates,return=minimal")

    def _patch_run(self, run_id, fields):
        self._post("PATCH", f"/rest/v1/repro_runs?run_id=eq.{run_id}", fields, prefer="return=minimal")

    def _do_storage(self, run_id, path, object_name, content, url_field):
        """Upload a run artifact to the public bucket, then record its URL on the run."""
        try:
            data = Path(path).read_bytes()
        except OSError:
            return
        self._post("POST", f"/storage/v1/object/{BUCKET}/{object_name}", None, raw=data,
                   content=content, prefer=None)
        url = f"{self.cfg.url}/storage/v1/object/public/{BUCKET}/{object_name}"
        self._patch_run(run_id, {url_field: url})

    def close(self, timeout: float = 12.0) -> None:
        self._stop.set()
        self._worker.join(timeout=timeout)
        if self.dropped or self.failed:
            print(f"supabase_sink: {self.dropped} dropped, {self.failed} failed POSTs "
                  f"(local agent.full.log is the complete record)", flush=True)


def install(cfg: SinkConfig | None) -> "SupabaseSink | None":
    """Start the sink and wire it into the live_log seam. ``None`` cfg -> disabled."""
    if cfg is None:
        return None
    sink = SupabaseSink(cfg)
    live_log.register_sink(sink.on_event)
    return sink
