"""Codex ``exec --json`` events -> the harness's run-bundle files.

One ``Recorder`` per run. It receives each JSONL event the Codex CLI prints and writes:

- ``agent.full.log``   untruncated, one line per event (host side, next to evidence/),
- ``evidence/commands.log`` and ``evidence/plan.md`` via ``evidence.py`` helpers,
- ``usage.json``       token counts per model turn and the USD cost at flex prices.

``run_gpu`` calls never reach Codex's events as GPU work: the bridge runs the harness's
own handler, which writes its own trajectory row and commands.log line. The shell item
that launched the shim is logged to the full log only, so each GPU step appears once in
commands.log.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from reprocli_repro import evidence as evidence_mod

# USD per million tokens at the flex tier (gpt-6.1-terra, rebuttal ops COMMON.md).
PRICES_PER_M = {"gpt-6.1-terra": {"in": 0.50, "cached": 0.025, "out": 2.50}}

_RUN_GPU_TOKEN = re.compile(r"(^|[\s/;&|])run_gpu(\s|$)")


def turn_usd(model: str, input_tokens: int, cached: int, output_tokens: int) -> float:
    """Cost of one turn. ``input_tokens`` includes the cached part, output includes reasoning."""
    price = PRICES_PER_M[model]
    uncached = max(0, input_tokens - cached)
    return (uncached * price["in"] + cached * price["cached"] + output_tokens * price["out"]) / 1e6


class Recorder:
    """Turns the event stream into the bundle files. Safe to call from two threads."""

    def __init__(self, run_dir: Path, evidence_dir: Path, model: str, workspace: Path) -> None:
        self.run_dir = Path(run_dir)
        self.evidence_dir = Path(evidence_dir)
        self.model = model
        self.workspace = workspace
        self.phase = "work"
        self.turns: list[dict[str, Any]] = []
        self.thread_id: str | None = None
        self._lock = threading.Lock()
        self.full_log = self.run_dir / "agent.full.log"

    # ------------------------------------------------------------------ #
    def _write(self, lines: list[str]) -> None:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock, self.full_log.open("a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(f"[{stamp}] {line}\n")

    def handle(self, event: dict[str, Any]) -> None:
        kind = event.get("type", "")
        if kind == "thread.started":
            self.thread_id = event.get("thread_id")
            self._write([f"session {self.thread_id} phase={self.phase} model={self.model}"])
        elif kind == "turn.completed":
            self._turn(event.get("usage") or {})
        elif kind in ("turn.failed", "error"):
            message = (event.get("error") or {}).get("message") or event.get("message") or ""
            self._write([f"ERROR {kind}: {message}"])
        elif kind in ("item.completed", "item.updated"):
            self._item(event.get("item") or {}, final=kind == "item.completed")

    def _turn(self, usage: dict[str, Any]) -> None:
        inp = int(usage.get("input_tokens") or 0)
        cached = int(usage.get("cached_input_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        reasoning = int(usage.get("reasoning_output_tokens") or 0)
        usd = turn_usd(self.model, inp, cached, out)
        self.turns.append({
            "phase": self.phase,
            "index": len(self.turns),
            "input_tokens": inp,
            "cached_input_tokens": cached,
            "output_tokens": out,
            "reasoning_output_tokens": reasoning,
            "usd": round(usd, 6),
        })
        self._write([f"turn {len(self.turns) - 1} ({self.phase}) in={inp} cached={cached} out={out} usd={usd:.6f}"])

    def _item(self, item: dict[str, Any], *, final: bool) -> None:
        itype = item.get("type", "")
        if itype == "agent_message" and final:
            self._write([f"assistant: {line}" for line in (item.get("text") or "").splitlines()] or ["assistant:"])
        elif itype == "reasoning" and final and item.get("text"):
            self._write([f"thinking: {line}" for line in str(item["text"]).splitlines()])
        elif itype == "command_execution" and final:
            self._command(item)
        elif itype == "file_change" and final:
            self._file_change(item)
        elif itype == "todo_list":
            self._plan(item)
        elif itype in ("mcp_tool_call", "web_search") and final:
            self._write([f"{itype}: {json.dumps(item, default=str)[:2000]}"])

    def _command(self, item: dict[str, Any]) -> None:
        command = str(item.get("command") or "")
        rc = item.get("exit_code")
        output = str(item.get("aggregated_output") or "").rstrip()
        self._write([f"exec rc={rc}: {command}"] + [f"    | {ln}" for ln in output.splitlines()])
        if _RUN_GPU_TOKEN.search(command):
            return  # the bridge logs every run_gpu step itself
        evidence_mod.log_command(
            self.evidence_dir, command, returncode=rc if isinstance(rc, int) else None, cwd=self.workspace,
        )

    def _file_change(self, item: dict[str, Any]) -> None:
        failed = item.get("status") == "failed"
        for change in item.get("changes") or []:
            path, kind = change.get("path"), change.get("kind")
            self._write([f"edit {kind} {path}{' (failed)' if failed else ''}"])
            evidence_mod.log_command(
                self.evidence_dir, f"edit_file {path} ({kind})", returncode=1 if failed else 0,
                cwd=self.workspace,
            )

    def _plan(self, item: dict[str, Any]) -> None:
        steps = item.get("items") or []
        rendered = "\n".join(
            f"- [{'x' if step.get('completed') else ' '}] {step.get('text', '')}" for step in steps
        )
        evidence_mod.save_plan(self.evidence_dir, rendered)

    def log_gpu(self, result: dict[str, Any]) -> None:
        """One line per run_gpu call the bridge served (the handler's own result dict)."""
        self._write([
            f"run_gpu ok={result.get('ok')} rc={result.get('returncode')} "
            f"cost_h100h={result.get('cost_h100_hours')} remaining_h100h={result.get('remaining_h100_hours')} "
            f"error={result.get('error', '')}",
            f"    cmd: {result.get('command', '')}",
        ])

    def log_line(self, text: str) -> None:
        self._write([text])

    # ------------------------------------------------------------------ #
    def totals(self) -> dict[str, Any]:
        keys = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
        sums = {k: sum(t[k] for t in self.turns) for k in keys}
        sums["usd"] = round(sum(t["usd"] for t in self.turns), 6)
        sums["turns"] = len(self.turns)
        return sums

    def write_usage(self) -> Path:
        price = PRICES_PER_M[self.model]
        payload = {
            "model": self.model,
            "service_tier": "flex",
            "prices_usd_per_million": price,
            "cost_formula": "(input - cached) * in + cached * cached_price + output * out, per turn; "
                            "output includes reasoning tokens",
            "turns": self.turns,
            "totals": self.totals(),
        }
        target = self.run_dir / "usage.json"
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return target


def request_usage(codex_home: Path) -> dict[str, Any]:
    """Per model request input tokens, from the rollout files Codex keeps under CODEX_HOME.

    ``turn.completed`` sums a turn's requests, so the per-request maximum (the flex 256k ceiling)
    has to come from ``token_count`` events in the session rollout.
    """
    requests: list[int] = []
    for rollout in sorted(Path(codex_home).glob("sessions/**/rollout-*.jsonl")):
        for line in rollout.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            payload = row.get("payload") or {}
            if row.get("type") == "event_msg" and payload.get("type") == "token_count":
                last = ((payload.get("info") or {}).get("last_token_usage") or {})
                if "input_tokens" in last:
                    requests.append(int(last["input_tokens"]))
    return {"requests": requests, "max_request_input_tokens": max(requests) if requests else 0}


def attach_requests(run_dir: Path, codex_home: Path) -> None:
    """Add the per-request input counts to usage.json."""
    target = Path(run_dir) / "usage.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload.update(request_usage(codex_home))
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
