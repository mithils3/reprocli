from __future__ import annotations

import json
import re
import sys
import time
from typing import Any

from openai import OpenAI, RateLimitError

from .prompt import BenchmarkEntry, build_prompt, SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .output import ReproResult, parse_output

MAX_ROUNDS = 30
MAX_BROWSE_NUDGES = 1  # steering messages to hurry browsing along
MAX_BASH_NUDGES = 3  # nudges when bash never runs

# Patterns that signal the setup phase (cloning, building container)
_SETUP_RE = re.compile(r"git\s+clone|apptainer\s+build|pip\s+install|apt[- ]|wget\b")
# Patterns that signal the experiment has been submitted/run
_RUN_RE = re.compile(r"\bsbatch\b|\bsrun\b|apptainer\s+exec.*--nv")

_PREVIEW_CHARS = 400  # chars of tool output shown in log

_log = lambda id_, msg: print(f"[{id_}] {msg}", file=sys.stderr, flush=True)


def _log_tool_call(id_: str, name: str, args: dict) -> None:
    if name == "bash":
        cmd = args.get("command", "")
        env = f"  [timeout={args['timeout']}s]" if "timeout" in args else ""
        _log(id_, f"  ┌─ bash{env}")
        for line in cmd.splitlines():
            _log(id_, f"  │  {line}")
        _log(id_, "  └─")
    elif name == "github_browse":
        _log(id_, f"  → github_browse  repo={args.get('repo', '')}  path={args.get('path', '(README)')}")
    elif name == "hf_browse":
        _log(id_, f"  → hf_browse  repo={args.get('repo', '')}  type={args.get('repo_type', 'model')}")
    elif name == "fetch_url":
        _log(id_, f"  → fetch_url  {args.get('url', '')}")
    elif name == "list_files":
        _log(id_, f"  → list_files  path={args.get('path', '.')}  depth={args.get('max_depth', 4)}")
    elif name in ("read_file", "write_file"):
        _log(id_, f"  → {name}  path={args.get('path', '')}")
    else:
        _log(id_, f"  → {name}")


def _log_tool_result(id_: str, name: str, result: str) -> None:
    failed = result.startswith("[exit ") and not result.startswith("[exit 0]")
    status = "FAILED" if failed else "ok"
    _log(id_, f"  ← {name}  {status}  ({len(result)} chars)")
    for line in result[:_PREVIEW_CHARS].splitlines():
        _log(id_, f"  │  {line}")
    if len(result) > _PREVIEW_CHARS:
        _log(id_, f"  │  ... ({len(result) - _PREVIEW_CHARS} more chars truncated)")


_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)
_MAX_RETRIES = 6


def _chat_with_retry(
    id_: str,
    client: OpenAI,
    model: str,
    messages: list[dict],
) -> Any:
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
                _log(id_, f"API error (gave up after {_MAX_RETRIES} retries): {exc}")
                raise
            m = _RETRY_AFTER_RE.search(str(exc))
            wait = float(m.group(1)) + 1.0 if m else 2 ** (attempt + 1) * 5.0
            _log(id_, f"rate limited — waiting {wait:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
            time.sleep(wait)
        except Exception as exc:
            _log(id_, f"API error: {type(exc).__name__}: {exc}")
            raise


def run_session(
    entry: BenchmarkEntry,
    workdir: str,
    client: OpenAI,
    model: str,
    max_rounds: int = MAX_ROUNDS,
) -> ReproResult:
    id_ = entry.custom_id
    _log(id_, f"starting  model={model}")

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
        _log(id_, f"round {round_i + 1}/{max_rounds}  bash_run={bash_run}")
        response = _chat_with_retry(id_, client, model, messages)
        msg = response.choices[0].message
        _log(
            id_,
            f"  finish_reason={response.choices[0].finish_reason}  tool_calls={len(msg.tool_calls or [])}",
        )

        # Append assistant turn to history
        assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if not msg.tool_calls:
            # Model stopped generating tool calls
            if not bash_run and bash_nudges < MAX_BASH_NUDGES:
                bash_nudges += 1
                _log(id_, f"bash not run — nudge {bash_nudges}/{MAX_BASH_NUDGES}")
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You have not run bash yet. Proceed to Step 2: "
                            "clone the repository and install dependencies."
                        ),
                    }
                )
                continue
            _log(id_, "agent finished")
            break

        # Execute all tool calls in this turn
        tool_rounds += 1
        run_steer_needed = False

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            _log_tool_call(id_, name, args)
            result = dispatch(name, args, workdir)
            _log_tool_result(id_, name, result)

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            if name == "bash":
                cmd = str(args.get("command", ""))
                bash_run = True
                if _RUN_RE.search(cmd) and not run_steer_sent:
                    run_steer_needed = True
            elif name in ("fetch_url", "github_browse", "hf_browse"):
                browse_count += 1

        # Phase steering injected as user messages after tool results
        if run_steer_needed and not run_steer_sent:
            run_steer_sent = True
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The experiment has been submitted or run. "
                        "If you used sbatch, poll with squeue until the job finishes, "
                        "then read slurm-<jobid>.out for metric values. "
                        "Once you have the results, emit the final JSON object — "
                        "no prose, no fences."
                    ),
                }
            )
        elif not bash_run and not browse_nudge_sent and browse_count >= 3:
            browse_nudge_sent = True
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You have browsed enough. Proceed to Step 2: "
                        "call bash to clone the repository and install dependencies."
                    ),
                }
            )

    return parse_output(entry.custom_id, messages, tool_rounds_used=tool_rounds)
