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
from dataclasses import dataclass
from typing import Any

from reprocli_repro import postgrest  # shared PostgREST transport (repro pkg on PYTHONPATH)
from reprocli_vllm.runtime import live_events

QUEUE_MAX = 4000
BATCH_MAX = 50
HTTP_TIMEOUT = 8.0
STDOUT_CAP = 8000  # chars per stdout/stderr/text cell


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---- pure PostgREST row builders ---------------------------------------------
# Mirrors ``reprocli_repro.supabase_rows`` (the reproduce-run version) so the
# audit transcript lands in ``audit_events`` with the SAME column shape the
# viewer's ``rowsToRounds`` already understands — the dashboard renders an audit
# exactly like a run. Pure: an event payload in, a row ``dict`` out. The sink
# supplies ``base`` (``audit_run_id`` / ``seq`` / ``kind`` / ``round_index``).


def cap(text: Any, limit: int = STDOUT_CAP) -> tuple[str, bool]:
    s = "" if text is None else str(text)
    if len(s) <= limit:
        return s, False
    return s[:limit] + f"\n…(+{len(s) - limit} chars truncated)", True


def arguments(call: dict[str, Any]) -> dict[str, Any]:
    fn = call.get("function") or {}
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            return {"_raw": args}
    return args if isinstance(args, dict) else {}


def message_row(base: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    msg = payload.get("message") or {}
    reasoning, _ = cap(msg.get("reasoning") or msg.get("reasoning_content"), STDOUT_CAP * 2)
    content, _ = cap(msg.get("content"), STDOUT_CAP * 2)
    base.update({"role": "assistant", "reasoning": reasoning or None, "content": content or None})
    if base.get("kind") == "final":
        base["exit_reason"] = payload.get("exit_reason") or None
    return base


def call_row(base: dict[str, Any], call: dict[str, Any]) -> dict[str, Any]:
    args = arguments(call)
    base["tool_name"] = str((call.get("function") or {}).get("name") or "?")
    if "command" in args:
        base.update(detail_kind="command", command=str(args["command"]))
    elif "path" in args:
        base.update(detail_kind="path", command=str(args["path"]))
    elif args:
        base.update(detail_kind="json", args=args)
    return base


def result_row(base: dict[str, Any], res: dict[str, Any]) -> dict[str, Any]:
    out, t1 = cap(res.get("stdout"))
    err, t2 = cap(res.get("stderr"))
    base.update({
        "ok": res.get("ok"), "rc": res.get("returncode"), "duration_s": res.get("duration_s"),
        "error": (str(res["error"]).splitlines()[0] if res.get("error") else None),
        "path": res.get("path"), "stdout": out or None, "stderr": err or None,
        "truncated": bool(t1 or t2),
    })
    return base


@dataclass
class SinkConfig:
    url: str
    service_key: str
    graded_run_id: str | None
    model: str | None
    host: str
    # Discriminator for the audit's identity. The id is otherwise derived from the
    # graded run alone, so a SECOND grader of the same run (a different model, or a
    # re-grade) lands on the first audit's row: it overwrites the run row's model
    # and status while inheriting the old verdict, and every event insert collides
    # with the existing (audit_run_id, seq) rows and is dropped -- an audit that
    # appears finished with someone else's score and no transcript. Set this per
    # grading attempt to give each audit its own row.
    attempt: str | None = None

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
        attempt = f"-{self.cfg.attempt}" if self.cfg.attempt else ""
        return f"{base}-{custom_id}{attempt}-audit"

    def _ensure_run(self, custom_id: str) -> str:
        aid = self._audit_run_id(custom_id)
        if aid not in self._seen:
            self._seen.add(aid)
            # The verdict columns are cleared on start: re-grading into an existing
            # row must not display the previous run's score while this one works.
            self._put("run_upsert", {
                "audit_run_id": aid, "graded_run_id": self.cfg.graded_run_id,
                "arxiv_id": custom_id, "model": self.cfg.model, "status": "running",
                "host": self.cfg.host, "started_at": _now_iso(), "updated_at": _now_iso(),
                "score": None, "verdict": None, "reproduced": None,
                "has_high_cheat_flag": None, "exit_reason": None, "finished_at": None,
                "tool_rounds_used": 0,
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
            self._put("events", message_row(self._row_base(aid, kind, idx), payload))
            if kind == "final":
                self._finish(aid, payload)
        elif kind == "call_start":
            self._put("events", call_row(self._row_base(aid, "call_start", self._round.get(aid)), payload["call"]))
        elif kind == "call_result":
            self._put("events", result_row(self._row_base(aid, "call_result", self._round.get(aid)), payload["result"]))

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

    def _post(self, method: str, path: str, body: Any, *, prefer: str | None = None) -> None:
        try:
            code, text = postgrest.request(
                self.cfg.url + path, service_key=self.cfg.service_key, method=method,
                body=body, prefer=prefer, timeout=HTTP_TIMEOUT)
        except Exception as exc:  # noqa: BLE001 — best-effort; never propagate
            self._note_failure(f"{type(exc).__name__}: {exc}")
            return
        if not code or code >= 300:
            self._note_failure(f"HTTP {code} {text[:200]}")

    def _note_failure(self, detail: str) -> None:
        """Count a failed write, and say so the FIRST time.

        Silence here reads as a working stream: a rejected insert (a colliding
        audit id, a schema drift) would otherwise leave the dashboard quietly
        empty while the audit runs to completion.
        """
        self.failed += 1
        if self.failed == 1:
            print(f"audit_sink: write rejected ({detail}); the Audits page will be incomplete",
                  flush=True)

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
