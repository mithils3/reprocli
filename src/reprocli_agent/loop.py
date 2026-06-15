from __future__ import annotations

import json
import re
import sys
from typing import Any

from openai import OpenAI

from .prompt import BenchmarkEntry, build_prompt, SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .output import ReproResult, parse_output

MAX_ROUNDS = 30
MAX_BROWSE_NUDGES = 1  # steering messages to hurry browsing along
MAX_BASH_NUDGES = 3  # nudges when bash never runs

_SETUP_RE = re.compile(
    r"git\s+clone|pip\s+install|conda\s+install|npm\s+install|apt[- ]|wget\b|curl\b"
)
_RUN_RE = re.compile(r"\bpython\b|\bpytest\b|\bbash\b|\bsh\b|\.\/|train|eval|inference")

_log = lambda id_, msg: print(f"[{id_}] {msg}", file=sys.stderr, flush=True)


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
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except Exception as exc:
            _log(id_, f"API error: {type(exc).__name__}: {exc}")
            raise
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

            _log(id_, f"  → {name}")
            result = dispatch(name, args, workdir)
            _log(id_, f"  ← {name}  ({len(result)} chars)")

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
                        "The experiment has run. Now emit the final JSON result. "
                        "Extract every metric value from the command output above. "
                        "Your entire response must be a single JSON object — no prose, no fences."
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
