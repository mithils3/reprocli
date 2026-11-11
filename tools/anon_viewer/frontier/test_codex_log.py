"""Mechanical checks for codex_log.events() over every codex-gpt run folder."""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import codex_log  # noqa: E402

ROOT = HERE.parents[2]
RUNS = ROOT / "tools/anon_viewer/.scratch/frontier_src/runs"
KINDS = {"round_open", "call_start", "call_result", "final"}


def _has_none(value):
    if value is None:
        return True
    if isinstance(value, dict):
        return any(_has_none(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_none(v) for v in value)
    return False


def _raw_counts(path):
    counts = collections.Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        item = rec.get("item") if isinstance(rec.get("item"), dict) else {}
        counts[(rec.get("type"), item.get("type"))] += 1
    return counts


def main():
    folders = sorted(p for p in RUNS.glob("*/*/codex-gpt-*") if p.is_dir())
    assert folders, "no run folders found"
    all_pairs = collections.Counter()

    for folder in folders:
        raw = _raw_counts(folder / "codex_events.jsonl")
        all_pairs.update(raw)
        cmd_done = raw[("item.completed", "command_execution")]
        msg_done = raw[("item.completed", "agent_message")]
        reas_done = raw[("item.completed", "reasoning")]

        evs = codex_log.events(folder)
        json.dumps(evs)

        assert [e["seq"] for e in evs] == list(range(len(evs))), "seq not 0..n-1"
        assert all(e["kind"] in KINDS for e in evs), "unexpected kind"
        assert not _has_none(evs), "None value present"
        assert evs[-1]["kind"] == "final", "last event is not final"
        assert evs[-1]["content"] == (folder / "report.json").read_text(encoding="utf-8")

        rounds = 0
        calls = 0
        for i, e in enumerate(evs):
            if e["kind"] == "round_open":
                rounds += 1
                assert e["round_index"] == rounds - 1, "round_index mismatch"
            if e["kind"] == "call_start":
                calls += 1
                assert i + 1 < len(evs) and evs[i + 1]["kind"] == "call_result", "call_start not followed by call_result"
                assert evs[i + 1]["round_index"] == e["round_index"]

        shell_starts = sum(1 for e in evs if e["kind"] == "call_start" and e.get("tool_name") == "shell")
        assert shell_starts == cmd_done, f"shell call_start {shell_starts} != command_execution {cmd_done}"
        assert msg_done <= rounds <= msg_done + reas_done + 1, f"rounds {rounds} outside bounds"

        print(f"{folder.name} rounds={rounds} calls={calls} ok")

    print("Counter of (type, item.type) over all files:")
    for pair, n in all_pairs.most_common():
        print(f"  {n} {pair}")
    print(f"ALL OK {len(folders)}")


if __name__ == "__main__":
    main()
