from __future__ import annotations

import json
import re
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from typing import Any

from openai import OpenAI, RateLimitError

from .phases import Phase, get_phases
from .prompt import BenchmarkEntry, build_phase_messages
from .repair import MAX_REPAIRS
from .schemas import get_tool_schemas, filter_schemas
from .state import ReproState
from .tools import dispatch
from .output import ReproResult, looks_like_final_json, parse_output

_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)
_MAX_RETRIES = 6
_PREVIEW_CHARS = 400
MAX_BASH_NUDGES = 3


# ---------------------------------------------------------------------------
# Logger
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
        self._f.write(f"=== {header} ===\n{content}\n=== END {header} ===\n\n")
        self._f.flush()

    def close(self) -> None:
        self._f.close()


# ---------------------------------------------------------------------------
# Tool-call logging
# ---------------------------------------------------------------------------

def _log_call(log: _Logger, name: str, args: dict) -> None:
    if name == "bash":
        env = f"  [conda_env={args['conda_env']}]" if "conda_env" in args else ""
        timeout = f"  [timeout={args['timeout']}s]" if "timeout" in args else ""
        log(f"  ┌─ bash{env}{timeout}")
        for line in args.get("command", "").splitlines():
            log(f"  │  {line}")
        log("  └─")
    elif name in ("github_browse", "hf_browse", "fetch_url"):
        key = args.get("repo") or args.get("url", "")
        log(f"  → {name}  {key}")
    elif name in ("read_file", "write_file", "list_files"):
        log(f"  → {name}  path={args.get('path', '.')}")
    else:
        log(f"  → {name}")


def _log_result(log: _Logger, name: str, result: str) -> None:
    failed = result.startswith("[exit ") and not result.startswith("[exit 0]")
    status = "FAILED" if failed else "ok"
    log(f"  ← {name}  {status}  ({len(result)} chars)")
    for line in result[:_PREVIEW_CHARS].splitlines():
        log(f"  │  {line}")
    if len(result) > _PREVIEW_CHARS:
        log(f"  │  ... ({len(result) - _PREVIEW_CHARS} more chars — see repro.log)")
    log.full(f"{name} output", result)


# ---------------------------------------------------------------------------
# API call with retry
# ---------------------------------------------------------------------------

def _chat(
    log: _Logger, client: OpenAI, model: str,
    messages: list[dict], tool_schemas: list[dict],
) -> Any:
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=model, messages=messages,
                tools=tool_schemas, tool_choice="auto",
            )
        except RateLimitError as exc:
            if attempt == _MAX_RETRIES:
                log(f"rate limit — gave up after {_MAX_RETRIES} retries: {exc}")
                raise
            m = _RETRY_AFTER_RE.search(str(exc))
            wait = float(m.group(1)) + 1.0 if m else 2 ** (attempt + 1) * 5.0
            log(f"rate limited — waiting {wait:.1f}s (attempt {attempt + 1})")
            time.sleep(wait)
        except Exception as exc:
            log(f"API error: {type(exc).__name__}: {exc}")
            raise


# ---------------------------------------------------------------------------
# Single-phase mini-loop
# ---------------------------------------------------------------------------

def _run_phase(
    phase: Phase,
    entry: BenchmarkEntry,
    state: ReproState,
    workdir: str,
    client: OpenAI,
    model: str,
    use_container: bool,
    use_slurm: bool,
    log: _Logger,
) -> None:
    """Run one phase to completion (mutates state in place)."""
    all_schemas = get_tool_schemas(use_container)
    tool_schemas = filter_schemas(all_schemas, phase.allowed_tools)

    messages = build_phase_messages(entry, state, phase)
    bash_nudges = 0
    tool_rounds = 0
    phase_names = [p.name for p in get_phases(use_container, use_slurm)]

    log(f"phase={phase.name}  max_rounds={phase.max_rounds}  tools={phase.allowed_tools}")

    for round_i in range(phase.max_rounds):
        vr = phase.verifier(workdir, state)
        if vr.status == "success":
            log(f"  verifier: success — {vr.message}")
            state.mark_done(phase.name)
            state.save()
            return
        if vr.status == "repair":
            target = vr.repair_phase or phase.name
            log(f"  verifier: repair → {target} — {vr.message}")
            state.repair_to(target, phase_names, failure_message=vr.message, failed_phase=phase.name)
            if state.repair_count >= MAX_REPAIRS:
                state.blockers.append(f"{phase.name}: exceeded repair budget ({MAX_REPAIRS}) — last failure: {vr.message}")
                state.phase = "blocked"
                state.save()
                raise RuntimeError(f"exceeded repair budget in {phase.name}: {vr.message}")
            state.save()
            return
        if vr.status == "blocked":
            state.blockers.append(f"{phase.name}: {vr.message}")
            state.save()
            raise RuntimeError(f"blocked in {phase.name}: {vr.message}")

        log(f"  round {round_i + 1}/{phase.max_rounds}  verifier=continue ({vr.message})")
        response = _chat(log, client, model, messages, tool_schemas)
        msg = response.choices[0].message
        log(f"  finish_reason={response.choices[0].finish_reason}  tool_calls={len(msg.tool_calls or [])}")

        if phase.name != "finalize" and looks_like_final_json(msg.content):
            log("  rejected: final reproduction JSON emitted outside finalize phase")
            messages.append({"role": "assistant", "content": msg.content})
            messages.append({"role": "user", "content": (
                "Final JSON is not allowed yet — you are still in phase "
                f"{phase.name}. Continue working on this phase's artifacts."
            )})
            continue

        assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if not msg.tool_calls:
            if bash_nudges < MAX_BASH_NUDGES:
                bash_nudges += 1
                messages.append({"role": "user", "content": (
                    f"You have not completed {phase.name} yet. "
                    "Check the required artifacts in your phase instructions and continue."
                )})
                continue
            log(f"  model stopped without completing phase — giving up on {phase.name}")
            break

        tool_rounds += 1
        state.total_tool_rounds += 1

        for tc in msg.tool_calls:
            name = tc.function.name
            if name not in phase.allowed_tools:
                result = f"Tool '{name}' is not allowed in phase {phase.name}. Allowed: {phase.allowed_tools}"
            else:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                _log_call(log, name, args)
                result = dispatch(name, args, workdir)
                _log_result(log, name, result)

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    # Final verifier check after exhausting rounds
    vr = phase.verifier(workdir, state)
    if vr.status == "success":
        state.mark_done(phase.name)
        state.save()
    else:
        log(f"  phase {phase.name} exhausted rounds without success: {vr.message}")


# ---------------------------------------------------------------------------
# Top-level session
# ---------------------------------------------------------------------------

def run_session(
    entry: BenchmarkEntry,
    workdir: str,
    client: OpenAI,
    model: str,
    use_container: bool = False,
    use_slurm: bool = True,
) -> ReproResult:
    id_ = entry.custom_id
    log = _Logger(id_, Path(workdir) / "repro.log")
    try:
        return _run(entry, workdir, client, model, use_container, use_slurm, log)
    finally:
        log.close()


def _run(
    entry: BenchmarkEntry,
    workdir: str,
    client: OpenAI,
    model: str,
    use_container: bool,
    use_slurm: bool,
    log: _Logger,
) -> ReproResult:
    phases = get_phases(use_container, use_slurm)
    phase_names = [p.name for p in phases]

    state = ReproState.load(workdir) or ReproState.new(
        paper_id=entry.custom_id,
        workdir=workdir,
        env_mode="apptainer" if use_container else "conda",
        first_phase=phase_names[0],
    )
    state.verification_targets = [
        {"metric": t.metric, "expected_value": t.expected_value} for t in entry.verification_targets
    ]
    log(f"starting  pipeline={'container' if use_container else 'conda'}  "
        f"slurm={use_slurm if use_container else 'n/a'}  phase={state.phase}")

    # Build a lookup so we can resume from the right position
    phase_by_name = {p.name: p for p in phases}

    while state.phase in phase_by_name:
        phase = phase_by_name[state.phase]
        if phase.name in state.phases_completed:
            # advance to next
            idx = phase_names.index(phase.name)
            if idx + 1 < len(phase_names):
                state.phase = phase_names[idx + 1]
                state.save()
            else:
                break
            continue

        try:
            _run_phase(phase, entry, state, workdir, client, model, use_container, use_slurm, log)
        except RuntimeError as exc:
            return ReproResult(
                custom_id=entry.custom_id,
                reproduction_status="failed",
                metric_results=[],
                claim_supported=None,
                claim_assessment="",
                failure_reason=str(exc),
                tool_rounds_used=state.total_tool_rounds,
            )

        # After _run_phase, state.phase may have been rewound (repair) or is still this phase
        if phase.name in state.phases_completed:
            idx = phase_names.index(phase.name)
            if idx + 1 < len(phase_names):
                state.phase = phase_names[idx + 1]
                state.save()
            else:
                break

    # Collect any messages for parse_output (just use finalize phase messages as proxy)
    return parse_output(entry.custom_id, [], tool_rounds_used=state.total_tool_rounds, workdir=workdir)
