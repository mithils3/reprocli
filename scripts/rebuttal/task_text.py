"""Task text for an agent that has only a bash shell (mini-SWE-agent) or a shell plus run_gpu (Codex).

``paper_task_text`` renders prompts/prompt_reproduce.txt for one lockfile row exactly as the thin harness does, then
swaps the passages that name the thin harness's tools (workspace_bash, run_gpu's tool-call form, list_partitions,
update_plan, write_file/edit_file, fetch_url), its compaction, and its round-counter status line. Every other
sentence stays verbatim. ``adapt`` raises if a passage is not found exactly once, so a changed template fails here
rather than shipping a stale instruction.
"""
from __future__ import annotations

from pathlib import Path

from reprocli_repro.prompt_render import render_reproduce_prompt

REPO = Path(__file__).resolve().parents[2]
PROMPT_TEMPLATE = REPO / "prompts" / "prompt_reproduce.txt"

SHELL_PASSAGE = """Tools:
- bash — a shell in the sandbox, starting in {WORKSPACE_DIR}. It runs on the shared CPU login node with NO GPU.
  Use it to clone, edit, install, inspect and organise evidence. Never compute a reported number there.
  Each command has a 900s timeout by default and 3600s at most. Curl is available for fetching documentation
  pages; there is no web search, so cite the URL for anything you take from a page.
- run_gpu <command> — runs one command on a real GPU on a metered SLURM allocation, in {WORKSPACE_DIR}, and
  prints a JSON result. Options before the command: --gpus N (default 1), --minutes M (default 30; the lifetime
  of the allocation, fixed when it starts), --partition P (optional). The GPU stays held across run_gpu calls until
  you run `run_gpu --release`. Every GPU-hour is charged to this paper's GPU budget. ALL real computation runs
  here, including CPU-bound scoring and data prep: if it produces a number the auditor reads, it runs here.

Batch independent shell commands into one turn where you can."""

# (old, new[, count]) triples: each old text must occur exactly count times (default once) in the rendered prompt.
REPLACEMENTS = [
    ("Write durable evidence to disk as you go: your in-context notes are\nperiodically compacted away; only files survive.",
     "Write durable evidence to disk as you go; only files survive."),
    ("`Tool round U/300 · N left` each turn. You can be cut off by rounds",
     "You have at most 300 turns, and you can be cut off by rounds"),
    ("verify target provenance; set\n   update_plan.",
     "verify target provenance; write your plan\n   to {EVIDENCE_DIR}/plan.md."),
    ("Your very last turn returns one structured JSON report (tools are gone):",
     "Your very last turn returns one structured JSON report (no commands run after it):"),
    ("(read it from list_partitions)", "(read it with `sinfo -p ghx4`)", 2),
]

# Codex has its own shell tool and apply_patch; only the tool names in the shell passage differ.
CODEX_SHELL_EDIT = (
    ("- bash — a shell in the sandbox, starting in",
     "- shell — a shell in the sandbox (edit files with apply_patch), starting in"),
)

_BLOCK_START = "Tools:\n"
_BLOCK_END = "=== GPU SESSIONS ==="


def adapt(rendered: str, *, workspace_dir: str, evidence_dir: str, harness: str = "bash") -> str:
    """Swap the tool passages of an already-rendered prompt. Pure text in, text out.

    ``harness="bash"`` (mini-SWE-agent) is the default; ``harness="codex"`` names Codex's shell and apply_patch.
    """
    if harness not in ("bash", "codex"):
        raise ValueError(f"unknown harness {harness!r}")
    start = rendered.count(_BLOCK_START)
    end = rendered.count(_BLOCK_END)
    if start != 1 or end != 1:
        raise ValueError(f"tool block markers found {start} and {end} times, expected 1 each")
    head, rest = rendered.split(_BLOCK_START, 1)
    _, tail = rest.split(_BLOCK_END, 1)
    shell = SHELL_PASSAGE
    if harness == "codex":
        for old, new in CODEX_SHELL_EDIT:
            shell = shell.replace(old, new)
    out = head + shell.replace("{WORKSPACE_DIR}", workspace_dir) + "\n\n" + _BLOCK_END + tail
    for old, new, *expected in REPLACEMENTS:
        want = expected[0] if expected else 1
        n = out.count(old)
        if n != want:
            raise ValueError(f"passage found {n} times, expected {want}: {old[:60]!r}")
        out = out.replace(old, new.replace("{EVIDENCE_DIR}", evidence_dir))
    return out


def paper_task_text(row: dict, *, budget: float, workspace_dir: str = "/repro/workspace",
                    evidence_dir: str = "/repro/evidence", harness: str = "bash") -> str:
    """The reproduce prompt for one lockfile row, rendered as the thin harness renders it, then adapted."""
    rendered = render_reproduce_prompt(PROMPT_TEMPLATE.read_text(encoding="utf-8"), row, budget=budget)
    return adapt(rendered, workspace_dir=workspace_dir, evidence_dir=evidence_dir, harness=harness).strip()
