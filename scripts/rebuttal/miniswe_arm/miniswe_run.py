#!/usr/bin/env python3
"""mini-SWE-agent 2.4.6 on one paper, inside the thin harness's sandbox, with its run_gpu, budget and evidence.

Run on DeltaAI from the repo checkout with the arm's venv (see env.sh):
  python miniswe_run.py --paper-id 2510.20725 --run-dir DIR --paper-row ROW.json --paper-budget-h100 H --gpu-budget-h100 H

The bundle under --run-dir has the thin harness's layout: workspace/, reference/, evidence/ (commands.log,
trajectory.jsonl, env.lock, patches/, gpu_step_*.log), report.json, plus agent.full.log, mini_trajectory.json
and usage.json.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

from minisweagent.agents.default import DefaultAgent
from minisweagent.exceptions import LimitsExceeded

from reprocli_repro import evidence as evidence_mod
from reprocli_repro import gpu_session
from reprocli_repro import report as report_mod
from reprocli_repro import sandbox as sandbox_mod
from reprocli_repro.cluster import DEFAULT_APPTAINER_SIF, resolve_cluster
from reprocli_repro.context import Budget, ExecutionContext
from reprocli_repro.prompt_render import render_reproduce_prompt
from reprocli_repro.tools.run_gpu import MAX_MINUTES, queue_grace_seconds, run_gpu
from reprocli_repro.tools.workspace_bash import WORKSPACE_BASH_TIMEOUT

from miniswe_apptainer import ApptainerExecEnvironment
from miniswe_model import MuseWonderModel

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROMPT_TEMPLATE = REPO / "prompts" / "prompt_reproduce.txt"
SHIM = HERE / "run_gpu_shim.sh"
ACCOUNT = "betw-dtai-gh"
DEFAULT_LEDGER = "/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl"
META_CAP_USD = 480.0
DEFAULT_COST_CAP = 60.0

# mini 2.4.6's stock mini.yaml text for the system message, the observation and the format error. The task text
# and the submission line replace its instance template; the task is passed as a variable, so Jinja never parses it.
SYSTEM_TEMPLATE = "You are a helpful assistant that can interact with a computer.\n"
SUBMIT_LINE = ("Submit your changes and finish your work by issuing the following command: "
               "`echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`.\nDo not combine it with any other command. "
               "<important>After this command, you cannot continue working on this task.</important>")
INSTANCE_TEMPLATE = "{{task}}\n\n" + SUBMIT_LINE + "\n"
OBSERVATION_TEMPLATE = """{%- if output.output | length < 10000 -%}
{
  "returncode": {{ output.returncode }},
  "output": {{ output.output | tojson }}
  {%- if output.exception_info %}, "exception_info": {{ output.exception_info | tojson }}{% endif %}
}
{%- else -%}
{
  "returncode": {{ output.returncode }},
  "output_head": {{ output.output[:5000] | tojson }},
  "output_tail": {{ output.output[-5000:] | tojson }},
  "elided_chars": {{ output.output | length - 10000 }},
  "warning": "Output too long."
  {%- if output.exception_info %}, "exception_info": {{ output.exception_info | tojson }}{% endif %}
}
{%- endif -%}
"""
FORMAT_ERROR_TEMPLATE = """{% if finish_reason is defined and (finish_reason == "length" or (finish_reason == "tool_calls" and not has_tool_calls)) -%}
Your previous response reached the output token limit (finish_reason={{ finish_reason }}) before you produced a tool call, so it was cut off. Respond more concisely and finish with exactly one bash tool call. If you need to think more, do so briefly.
{%- else -%}
Tool call error:

<error>
{{error}}
</error>

Here is general guidance on how to submit correct toolcalls:

Every response needs to use the 'bash' tool at least once to execute commands.

Call the bash tool with your command as the argument:
- Tool: bash
- Arguments: {"command": "your_command_here"}

If you want to end the task, please issue the following command: `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`
without any other command.
{%- endif %}
"""
FINAL_PROMPT = ("The run is over. Do not call any tool. Write the report for this run now as one JSON object that "
                "matches the response schema: what you ran, the measured values with their evidence files, your "
                "assessment, what you changed, and what blocked you.")


def stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp()}]\n{text.rstrip()}\n")


class Mailbox:
    """Serves the sandbox's run_gpu requests on the host. Each request is a directory the shim renames into place."""

    def __init__(self, root: Path, ctx: ExecutionContext, full_log: Path):
        self.root, self.ctx, self.full_log = root, ctx, full_log
        self.seen: set[str] = set()

    def __call__(self) -> None:
        for req in sorted(self.root.iterdir()):
            if req.name.endswith(".tmp") or req.name in self.seen:
                continue
            self.seen.add(req.name)
            self._handle(req)

    def _handle(self, req: Path) -> None:
        args = dict(line.split("=", 1) for line in (req / "args").read_text().splitlines() if "=" in line)
        command = (req / "command").read_text()
        arguments: dict = {"gpus": int(args["gpus"]), "minutes": int(args["minutes"]),
                           "release": args["release"] == "true"}
        if command.strip():
            arguments["command"] = command
        if args.get("partition"):
            arguments["partition"] = args["partition"]
        try:
            result = run_gpu(arguments, self.ctx)
        except Exception as e:
            result = {"ok": False, "tool": "run_gpu", "error": f"{type(e).__name__}: {e}"}
        text = json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n"
        write_log(self.full_log, f"run_gpu {json.dumps(arguments)}\n{text}")
        code = result.get("returncode", 0 if result.get("ok") else 1)
        (req / "out").write_text(text, encoding="utf-8")
        (req / "rc").write_text(str(code if code is not None else 1), encoding="utf-8")
        (req / "done").write_text("", encoding="utf-8")


class ArmAgent(DefaultAgent):
    """mini's stock loop, with the thin harness's budget guardrail before each model call."""

    def __init__(self, *, model, env, ctx: ExecutionContext, full_log: Path, **kwargs):
        super().__init__(model, env, **kwargs)
        self.ctx, self.full_log = ctx, full_log

    def query(self) -> dict:
        if self.ctx.session is not None:
            gpu_session.charge_accrued(self.ctx)
        if self.ctx.budget.exhausted():
            gpu_session.release(self.ctx, "budget_exhausted")
            raise LimitsExceeded({"role": "exit", "content": "budget_exhausted",
                                  "extra": {"exit_status": "budget_exhausted", "submission": ""}})
        message = super().query()
        calls = "".join(f"tool call: {a['command']}\n" for a in message.get("extra", {}).get("actions", []))
        write_log(self.full_log, f"round {self.n_calls} assistant\n{message.get('content') or ''}\n{calls}")
        return message


def exit_reason(status: str, cost: float, cost_cap: float) -> str:
    if status == "Submitted":
        return "submitted"
    if status == "LimitsExceeded":
        return "cost_limit" if cost >= cost_cap else "round_limit"
    if status == "budget_exhausted":
        return status
    if status == "RepeatedFormatError":
        return "format_errors"
    return "error"


def task_text(args: argparse.Namespace) -> str:
    if args.task_file:
        return Path(args.task_file).read_text(encoding="utf-8").strip()
    row = json.loads(Path(args.paper_row).read_text(encoding="utf-8"))
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return render_reproduce_prompt(template, row, budget=args.paper_budget_h100).strip()


def close_tool_calls(messages: list[dict]) -> list[dict]:
    """Answer each tool call that has no result yet. A submission ends the run before its result is added, and the API
    rejects a history whose tool calls have no matching tool message."""
    answered = {m.get("tool_call_id") for m in messages if m.get("role") == "tool"}
    out = []
    for m in messages:
        out.append(m)
        for call in (m.get("tool_calls") or []) if m.get("role") == "assistant" else []:
            if call.get("id") not in answered:
                out.append({"role": "tool", "tool_call_id": call.get("id"),
                            "content": "The run ended before this command was executed."})
    return out


def probe_path(image: str) -> str:
    """PATH the image gives a login shell, so /repro/bin can go in front of it without dropping the image's tools."""
    done = subprocess.run(["apptainer", "exec", "--cleanenv", "--no-home", image, "bash", "-lc", 'printf %s "$PATH"'],
                          capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not done.stdout.strip():
        raise SystemExit(f"could not read PATH from the image: {done.stderr[-300:]}")
    return done.stdout.strip()


def ledger_meta_total(path: Path) -> float:
    if not path.exists():
        return 0.0
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sum(float(r.get("usd", 0.0)) for r in rows if r.get("provider") == "meta")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--paper-id", required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--task-file", help="exact task text (toy runs)")
    p.add_argument("--paper-row", help="lockfile row JSON; the task is prompt_reproduce.txt rendered from it")
    p.add_argument("--paper-budget-h100", type=float, default=0.0)
    p.add_argument("--gpu-budget-h100", type=float, required=True)
    p.add_argument("--tool-rounds", type=int, default=int(os.environ.get("TOOL_ROUNDS", "300")))
    p.add_argument("--cost-cap", type=float, default=DEFAULT_COST_CAP)
    p.add_argument("--image", default=DEFAULT_APPTAINER_SIF)
    p.add_argument("--item", default="E2")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    args = p.parse_args(argv)
    if bool(args.task_file) == bool(args.paper_row):
        p.error("give exactly one of --task-file and --paper-row")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    ws, ref, ev = run_dir / "workspace", run_dir / "reference", run_dir / "evidence"
    for d in (ws, ref, ev):
        d.mkdir(parents=True, exist_ok=True)
    evidence_mod.init_evidence(ev)
    full_log = run_dir / "agent.full.log"

    os.environ.setdefault("REPROCLI_SLURM_ACCOUNT", ACCOUNT)
    cluster = resolve_cluster()
    if cluster.account != ACCOUNT:
        raise SystemExit(f"Slurm account is {cluster.account!r}, expected {ACCOUNT!r}")
    key = os.environ.get("META_MODEL_KEY", "")
    if not key:
        raise SystemExit("META_MODEL_KEY is not set (source it from ~/.bashrc by pointer)")
    os.environ["OPENAI_API_KEY"] = key  # litellm reads it here; nothing writes it
    spent = ledger_meta_total(Path(args.ledger))
    if spent + args.cost_cap > META_CAP_USD:
        raise SystemExit(f"Meta ledger at ${spent:.2f}; a run capped at ${args.cost_cap:.0f} would pass ${META_CAP_USD:.0f}")

    task = task_text(args)
    sandbox_mod.require_apptainer(args.image)
    sandbox_mod.forward_env()
    base_sb = sandbox_mod.from_run_paths(SimpleNamespace(workspace=ws, evidence=ev, reference=ref), image=args.image)
    ctx = ExecutionContext(arxiv_id=args.paper_id, workspace=ws, reference=ref,
                           budget=Budget(total_h100_hours=args.gpu_budget_h100), evidence=ev, run_dir=run_dir,
                           cluster=cluster, sandbox=base_sb)

    scratch = Path(os.environ.get("TMPDIR", "/tmp")) / "miniswe-arm" / run_dir.name
    mail, bin_dir = scratch / "mail", scratch / "bin"
    mail.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(SHIM, bin_dir / "run_gpu")
    (bin_dir / "run_gpu").chmod(0o755)
    exec_sb = dataclasses.replace(base_sb, binds=(*base_sb.binds,
                                                  sandbox_mod.Bind(str(mail), "/repro/mail"),
                                                  sandbox_mod.Bind(str(bin_dir), "/repro/bin", ro=True)))

    def on_result(command: str, output: dict, seconds: float) -> None:
        evidence_mod.log_command(ev, command, returncode=output["returncode"], cwd=ws, duration_s=seconds)
        write_log(full_log, f"bash rc={output['returncode']} {seconds:.1f}s: {command}\n{output['output']}")

    env = ApptainerExecEnvironment(
        sandbox=exec_sb, cwd=sandbox_mod.CONTAINER_WORKSPACE, timeout=WORKSPACE_BASH_TIMEOUT,
        path_inside=probe_path(args.image), on_result=on_result, service=Mailbox(mail, ctx, full_log),
        gpu_timeout=MAX_MINUTES * 60 + int(queue_grace_seconds()) + 600)
    model = MuseWonderModel(observation_template=OBSERVATION_TEMPLATE, format_error_template=FORMAT_ERROR_TEMPLATE)
    agent = ArmAgent(model=model, env=env, ctx=ctx, full_log=full_log, system_template=SYSTEM_TEMPLATE,
                     instance_template=INSTANCE_TEMPLATE, step_limit=args.tool_rounds, cost_limit=args.cost_cap,
                     output_path=run_dir / "mini_trajectory.json")

    status = "error"
    try:
        status = agent.run(task=task).get("exit_status") or "error"
    except Exception:
        write_log(full_log, "agent crashed\n" + traceback.format_exc())
    reason = exit_reason(status, agent.cost, args.cost_cap)

    content = ""
    try:
        messages = close_tool_calls([m for m in agent.messages if m.get("role") != "exit"])
        messages.append({"role": "user", "content": FINAL_PROMPT})
        content = model.final_report(messages, report_mod.REPORT_RESPONSE_FORMAT)
    except Exception:
        write_log(full_log, "final report call failed\n" + traceback.format_exc())
    if ctx.session is not None:
        gpu_session.release(ctx, "teardown")
    report_mod.write_episode_report(ctx, content, reason)

    totals = model.totals()
    (run_dir / "usage.json").write_text(json.dumps({
        "item": args.item, "model": "muse-wonder-1.0", "exit_status": status, "exit_reason": reason,
        "calls": model.calls, "totals": totals, "remaining_h100_hours": round(ctx.budget.remaining(), 4),
        "usd_cap": args.cost_cap}, indent=2) + "\n", encoding="utf-8")
    ledger = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "item": args.item, "provider": "meta",
              "model": "muse-wonder-1.0", "in": totals["prompt_tokens"], "cached": totals["cached_tokens"],
              "out": totals["completion_tokens"], "usd": totals["usd"], "run_dir": str(run_dir)}
    with Path(args.ledger).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(ledger) + "\n")
    shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps({"run_dir": str(run_dir), "exit_reason": reason, "totals": totals,
                      "report": str(run_dir / "report.json")}, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
