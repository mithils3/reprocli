"""Run miniswe_log.events() on every mini-swe-agent run folder and check it."""
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import miniswe_log  # noqa: E402

REPO = HERE.parents[2]
GLOB = str(REPO / "tools/anon_viewer/.scratch/frontier_src/runs/*/*/miniswe-*")
KINDS = {"round_open", "call_start", "call_result", "final"}


def check_run(run_dir):
    traj = json.loads((run_dir / "mini_trajectory.json").read_text(encoding="utf-8"))
    msgs = traj["messages"]
    assistants = [m for m in msgs if m["role"] == "assistant"]
    tools = [m for m in msgs if m["role"] == "tool"]
    tool_calls = [c for m in assistants for c in (m.get("tool_calls") or [])]
    answered_ids = {m["tool_call_id"] for m in tools}
    unanswered = sum(1 for c in tool_calls if c["id"] not in answered_ids)

    evs = miniswe_log.events(run_dir)
    json.dumps(evs)

    assert [e["seq"] for e in evs] == list(range(len(evs))), "seq"
    assert all(e["kind"] in KINDS for e in evs), "kinds"
    assert all(v is not None for e in evs for v in e.values()), "None value"
    assert evs[-1]["kind"] == "final", "last is final"
    assert evs[-1]["content"] == (run_dir / "report.json").read_text(encoding="utf-8"), "final text"

    rounds = [e for e in evs if e["kind"] == "round_open"]
    starts = [e for e in evs if e["kind"] == "call_start"]
    results = [e for e in evs if e["kind"] == "call_result"]
    assert len(rounds) == len(assistants), "round_open count"
    assert len(starts) == len(tool_calls), "call_start count"
    assert len(results) - unanswered == len(tools), "call_result from tool messages"
    assert len(results) == len(starts), "one result per call"

    for i, e in enumerate(evs):
        if e["kind"] == "call_start":
            assert evs[i + 1]["kind"] == "call_result", "call_start not followed by result"
            assert evs[i + 1]["round_index"] == e["round_index"], "round_index mismatch"
    rounds_seen = [e["round_index"] for e in evs]
    assert rounds_seen == sorted(rounds_seen), "round_index order"
    assert [r["round_index"] for r in rounds] == list(range(len(rounds))), "round_index step"
    return len(rounds), len(starts)


def main():
    runs = sorted(Path(p) for p in glob.glob(GLOB))
    assert runs, "no run folders found"
    for run in runs:
        rounds, calls = check_run(run)
        print(f"{run.name} rounds={rounds} calls={calls} ok")
    print(f"ALL OK {len(runs)}")


if __name__ == "__main__":
    main()
