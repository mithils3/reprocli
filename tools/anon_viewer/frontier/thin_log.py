"""Turn one agent.full.log run folder into viewer events.

Output kinds: round_open, call_start, call_result, final. The shape follows the
existing bundle in tools/anon_viewer/public/data/runs/. Log line prefixes handled:

    " round 3 · <paper id> · 2026-01-02T03:04:05Z"   round header (after a rule line)
    " ⏺ <tool_name>"                                  tool call start
    "   $ <command>"                                  shell command (may continue)
    "   ✓ ok=True rc=0 12.3s"  /  "   ✗ ok=False ..."  call status
    "   ┊ <text>"                                      stderr line
    "   │ <text>"                                      stdout line
    "   ! <text>"                                      error message
    "   · cost_h100_hours=0.0166"                     GPU cost (other "· " lines are dropped)
    " 🗒  assistant" + 4-space lines                  model text for the open round
    " ✅ FINAL (round 7) · <paper id> · exit=natural · <timestamp>"
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROUND_RE = re.compile(r"^ round (\d+) · (\S+) · (\S+)$")
FINAL_RE = re.compile(r"^ ✅ FINAL \(round (\d+)\) · (\S+) · exit=(\S+) · (\S+)$")
STATUS_RE = re.compile(r"^   ([✓✗]) ok=(True|False)(.*)$")
COST_RE = re.compile(r"^   · (cost|remaining)_h100_hours=(\S+)$")
RC_RE = re.compile(r"\brc=(-?\d+)")
DUR_RE = re.compile(r"\s(\d+(?:\.\d+)?)s\b")
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"
COST_KEYS = {"cost": "cost_h100", "remaining": "remaining_h100"}


def _ts(text):
    return datetime.strptime(text, TS_FMT).replace(tzinfo=timezone.utc).timestamp()


def _new_call(name):
    return {
        "name": name, "command": None, "args": [], "status": None,
        "stdout": [], "stderr": [], "error": [], "cost": {},
    }


class _Builder:
    def __init__(self):
        self.out = []
        self.round_idx = -1
        self.t0 = None
        self.round_t = None
        self.open_event = None
        self.call = None
        self.text = None
        self.final_t = None
        self.done = False

    def _emit(self, kind, **fields):
        ev = {"kind": kind, "round_index": self.round_idx}
        if self.round_t is not None:
            ev["t_rel_s"] = self.round_t
        ev.update(fields)
        self.out.append(ev)
        return ev

    def open_round(self, m):
        self.close()
        ts = _ts(m.group(3))
        if self.t0 is None:
            self.t0 = ts
        self.round_t = ts - self.t0
        self.round_idx += 1
        self.open_event = self._emit("round_open", role="assistant")

    def close(self):
        self.close_call()
        self.close_text()

    def close_text(self):
        if self.text is not None and self.open_event is not None:
            body = "\n".join(self.text).strip("\n")
            if body:
                self.open_event["reasoning"] = body
        self.text = None

    def close_call(self):
        c, self.call = self.call, None
        if c is None:
            return
        if c["command"] is not None:
            start = {"command": "\n".join(c["command"]).rstrip(), "detail_kind": "bash"}
        else:
            text = "\n".join(c["args"]).strip()
            start = {"args": {"text": text} if text else {}, "detail_kind": "json"}
        self._emit("call_start", tool_name=c["name"], **start)
        self._emit("call_result", **self._result(c))

    @staticmethod
    def _result(c):
        st = c["status"]
        if st is None:
            res = {"ok": False, "error": "no status line in log"}
        else:
            res = {"ok": st["ok"]}
            if st["rc"] is not None:
                res["rc"] = st["rc"]
            if st["duration"] is not None:
                res["duration_s"] = st["duration"]
        if c["stdout"]:
            res["stdout"] = "\n".join(c["stdout"])
        if c["stderr"]:
            res["stderr"] = "\n".join(c["stderr"])
        if c["error"]:
            res["error"] = "\n".join(c["error"])
        res.update(c["cost"])
        res["truncated"] = False
        return res

    def call_line(self, line):
        c = self.call
        if c["status"] is not None:
            if line.startswith("   ┊"):
                c["stderr"].append(line[5:])
            elif line.startswith("   │"):
                c["stdout"].append(line[5:])
            elif line.startswith("   ! "):
                c["error"].append(line[5:])
            else:
                m = COST_RE.match(line)
                if m:
                    c["cost"][COST_KEYS[m.group(1)]] = float(m.group(2))
            return
        m = STATUS_RE.match(line)
        if m:
            rest = m.group(3)
            rc = RC_RE.search(rest)
            dur = DUR_RE.search(rest)
            c["status"] = {
                "ok": m.group(2) == "True",
                "rc": int(rc.group(1)) if rc else None,
                "duration": float(dur.group(1)) if dur else None,
            }
        elif line.startswith("   $ ") and c["command"] is None:
            c["command"] = [line[5:]]
        elif c["command"] is not None:
            c["command"].append(line)
        else:
            c["args"].append(line[3:] if line.startswith("   ") else line)

    def feed(self, line):
        if self.done:
            return
        if line.startswith("─"):
            self.close()
            return
        if self.text is not None:
            if line.startswith("    ") or not line.strip():
                self.text.append(line[4:])
                return
            self.close_text()
        m = ROUND_RE.match(line)
        if m:
            self.open_round(m)
            return
        m = FINAL_RE.match(line)
        if m:
            self.close()
            self.final_t = _ts(m.group(4)) - self.t0
            self.done = True
            return
        if line.startswith(" 🗒"):
            self.close_call()
            self.text = []
            return
        if line.startswith(" ⏺ "):
            self.close_call()
            self.call = _new_call(line[3:].split()[0])
            return
        if self.call is not None:
            self.call_line(line)


def _exit_reason(report_text):
    try:
        value = json.loads(report_text).get("exit_reason")
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def events(run_dir):
    run = Path(run_dir)
    log = (run / "agent.full.log").read_text(encoding="utf-8", errors="replace")
    b = _Builder()
    for line in log.split("\n"):
        b.feed(line)
    b.close()
    report = (run / "report.json").read_text(encoding="utf-8", errors="replace")
    final = {"kind": "final", "round_index": max(b.round_idx, 0),
             "role": "assistant", "content": report}
    reason = _exit_reason(report)
    if reason is not None:
        final["exit_reason"] = reason
    if b.final_t is not None:
        final["t_rel_s"] = b.final_t
    b.out.append(final)
    for i, ev in enumerate(b.out):
        ev["seq"] = i
    return b.out
