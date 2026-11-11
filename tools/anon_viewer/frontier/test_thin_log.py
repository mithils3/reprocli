"""Mechanical checks for thin_log.events on every core-a and astra-a run folder."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import thin_log  # noqa: E402

REPO = HERE.parents[2]
RUNS = REPO / "tools/anon_viewer/.scratch/frontier_src/runs"
KINDS = {"round_open", "call_start", "call_result", "final"}
HEADER_RE = re.compile(r"^ round \d+ · ")


def _no_none(value):
    assert value is not None
    if isinstance(value, dict):
        for v in value.values():
            _no_none(v)
    elif isinstance(value, list):
        for v in value:
            _no_none(v)


def _check(folder):
    lines = (folder / "agent.full.log").read_text(encoding="utf-8", errors="replace").split("\n")
    headers = sum(1 for ln in lines if HEADER_RE.match(ln))
    calls = sum(1 for ln in lines if ln.startswith(" ⏺ "))
    stdout_lines = sum(1 for ln in lines if ln.startswith("   │"))
    stderr_lines = sum(1 for ln in lines if ln.startswith("   ┊"))

    evs = thin_log.events(folder)
    json.dumps(evs)
    _no_none(evs)
    assert [e["seq"] for e in evs] == list(range(len(evs)))
    assert {e["kind"] for e in evs} <= KINDS
    assert evs[-1]["kind"] == "final"

    opens = [e for e in evs if e["kind"] == "round_open"]
    assert len(opens) == headers, (len(opens), headers)
    assert [e["round_index"] for e in opens] == list(range(headers))

    starts = [i for i, e in enumerate(evs) if e["kind"] == "call_start"]
    assert len(starts) == calls, (len(starts), calls)
    for i in starts:
        nxt = evs[i + 1]
        assert nxt["kind"] == "call_result" and nxt["round_index"] == evs[i]["round_index"]
    results = [e for e in evs if e["kind"] == "call_result"]
    assert len(results) == calls

    out_stdout = sum(len(e["stdout"].split("\n")) for e in results if "stdout" in e)
    out_stderr = sum(len(e["stderr"].split("\n")) for e in results if "stderr" in e)
    assert out_stdout == stdout_lines, (out_stdout, stdout_lines)
    assert out_stderr == stderr_lines, (out_stderr, stderr_lines)

    report = (folder / "report.json").read_text(encoding="utf-8", errors="replace")
    assert evs[-1]["content"] == report
    return len(opens), len(starts)


def main():
    folders = sorted(
        p for pat in ("*/*/core-a-*", "*/*/astra-a-*") for p in RUNS.glob(pat) if p.is_dir()
    )
    assert len(folders) == 16, len(folders)
    for folder in folders:
        rounds, calls = _check(folder)
        print(f"{folder.name} rounds={rounds} calls={calls} ok")
    print(f"ALL OK {len(folders)}")


if __name__ == "__main__":
    main()
