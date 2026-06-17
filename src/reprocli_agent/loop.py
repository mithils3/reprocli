from __future__ import annotations

import json
import re
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from typing import Any

from openai import OpenAI, RateLimitError

from .prompt import BenchmarkEntry, build_prompt, SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .output import ReproResult, parse_output

MAX_ROUNDS = 30
MAX_BASH_NUDGES = 3
_PREVIEW_CHARS = 400

# Patterns that signal setup / experiment phases
_SETUP_RE = re.compile(r"git\s+clone|apptainer\s+build|pip\s+install|apt[- ]|wget\b")
_RUN_RE = re.compile(r"\bsbatch\b|\bsrun\b|apptainer\s+exec.*--nv")

_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)
_MAX_RETRIES = 6


# ---------------------------------------------------------------------------
# Logger: tees to stderr + repro.log
# ---------------------------------------------------------------------------

class _Logger:
    def __init__(self, id_: str, log_path: Path) -> None:
        self.id_ = id_
        self._f: TextIOWrapper = log_path.open("a", encoding="utf-8")

    def __call__(self, msg: str) -> None:
        line = f"[{self.id_}] {msg}"
        print(line, file=sys.stderr, flush=True)
        self._f.write(line + "\n")
        self._f.flush()

    def full(self, header: str, content: str) -> None:
        """Write full content to the log file; only a preview goes to stderr."""
        self._f.write(f"=== {header} ===\n{content}\n=== END {header} ===\n\n")
        self._f.flush()

    def close(self) -> None:
        self._f.close()


# ---------------------------------------------------------------------------
# Tool-call logging
# ---------------------------------------------------------------------------

def _log_call(log: _Logger, name: str, args: dict) -> None:
    if name == "bash":
        cmd = args.get("command", "")
        timeout_note = f"  [timeout={args['timeout']}s]" if "timeout" in args else ""
        log(f"  ┌─ bash{timeout_note}")
        for line in cmd.splitlines():
            log(f"  │  {line}")
        log("  └─")
    elif name == "github_browse":
        log(f"  → github_browse  repo={args.get('repo', '')}  path={args.get('path', '(README)')}")
    elif name == "hf_browse":
        log(f"  → hf_browse  repo={args.get('repo', '')}  type={args.get('repo_type', 'model')}")
    elif name == "fetch_url":
        log(f"  → fetch_url  {args.get('url', '')}")
    elif name == "list_files":
        log(f"  → list_files  path={args.get('path', '.')}  depth={args.get('max_depth', 4)}")
    elif name in ("read_file", "write_file"):
        log(f"  → {name}  path={args.get('path', '')}")
    else:
        log(f"  → {name}")


def _log_result(log: _Logger, name: str, result: str) -> None:
    failed = result.startswith("[exit ") and not result.startswith("[exit 0]")
    status = "FAILED" if failed else "ok"
    log(f"  ← {name}  {status}  ({len(result)} chars)")
    # preview to stderr via log()
    for line in result[:_PREVIEW_CHARS].splitlines():
        log(f"  │  {line}")
    if len(result) > _PREVIEW_CHARS:
        log(f"  │  ... ({len(result) - _PREVIEW_CHARS} more chars — see repro.log)")
    # full output to file
    log.full(f"{name} output", result)


# ---------------------------------------------------------------------------
# API call with rate-limit retry
# ---------------------------------------------------------------------------

def _chat_with_retry(log: _Logger, client: OpenAI, model: str, messages: list[dict]) -> Any:
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except RateLimitError as exc:
            if attempt == _MAX_RETRIES:
                log(f"API error (gave up after {_MAX_RETRIES} retries): {exc}")
                raise
            m = _RETRY_AFTER_RE.search(str(exc))
            wait = float(m.group(1)) + 1.0 if m else 2 ** (attempt + 1) * 5.0
            log(f"rate limited — waiting {wait:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
            time.sleep(wait)
        except Exception as exc:
            log(f"API error: {type(exc).__name__}: {exc}")
            raise


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run_session(
    entry: BenchmarkEntry,
    workdir: str,
    client: OpenAI,
    model: str,
    max_rounds: int = MAX_ROUNDS,
) -> ReproResult:
    id_ = entry.custom_id
    log = _Logger(id_, Path(workdir) / "repro.log")
    try:
        return _run(entry, workdir, client, model, max_rounds, log)
    finally:
        log.close()


def _run(
    entry: BenchmarkEntry,
    workdir: str,
    client: OpenAI,
    model: str,
    max_rounds: int,
    log: _Logger,
) -> ReproResult:
    id_ = entry.custom_id
    log(f"starting  model={model}  workdir={workdir}")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(entry)},
    ]

    bash_run = False
    browse_count = 0
    browse_nudge_sent = False
    bash_nudges = 0
    tool_rounds = 0
    run_steer_sent = False

    for round_i in range(max_rounds):
        log(f"round {round_i + 1}/{max_rounds}  bash_run={bash_run}")
        response = _chat_with_retry(log, client, model, messages)
        msg = response.choices[0].message
        log(f"  finish_reason={response.choices[0].finish_reason}  tool_calls={len(msg.tool_calls or [])}")

        assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if not msg.tool_calls:
            if not bash_run and bash_nudges < MAX_BASH_NUDGES:
                bash_nudges += 1
                log(f"bash not run — nudge {bash_nudges}/{MAX_BASH_NUDGES}")
                messages.append({
                    "role": "user",
                    "content": (
                        "You have not run bash yet. Proceed to Step 1: "
                        "inspect the host, then Step 2: clone the repo."
                    ),
                })
                continue
            log("agent finished")
            break

        tool_rounds += 1
        run_steer_needed = False

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            _log_call(log, name, args)
            result = dispatch(name, args, workdir)
            _log_result(log, name, result)

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            if name == "bash":
                bash_run = True
                if _RUN_RE.search(str(args.get("command", ""))) and not run_steer_sent:
                    run_steer_needed = True
            elif name in ("fetch_url", "github_browse", "hf_browse"):
                browse_count += 1

        if run_steer_needed and not run_steer_sent:
            run_steer_sent = True
            messages.append({
                "role": "user",
                "content": (
                    "The experiment has been submitted or run. "
                    "If you used sbatch, poll with squeue until the job finishes, "
                    "then read slurm-<jobid>.out for metric values. "
                    "Once you have the results, emit the final JSON object — no prose, no fences."
                ),
            })
        elif not bash_run and not browse_nudge_sent and browse_count >= 3:
            browse_nudge_sent = True
            messages.append({
                "role": "user",
                "content": (
                    "You have browsed enough. Proceed to Step 2: "
                    "clone the repository and inspect its structure."
                ),
            })

    return parse_output(entry.custom_id, messages, tool_rounds_used=tool_rounds)
