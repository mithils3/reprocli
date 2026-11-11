"""Add the frontier runs (Section 5.1 of the paper) to the anonymous viewer.

The 372 runs of the four open agents come from the database through export.py.
The frontier runs live as run folders, in three log formats, so this script
converts each one with tools/anon_viewer/frontier/, scrubs it with scrub.py,
writes public/data/frontier/<id>.json.gz, and lists the runs, their agents and
their sweeps in public/data/frontier.json. index.json and runs/ stay exactly the
372 runs of the four agents, which other scripts read as that set; the page
loads frontier.json beside the index and shows it under its own tab.

    python3 add_frontier.py --src .scratch/frontier_src [--jobs 3] [--only ID]

--src holds runs/<paper>/<budget>/<run id>/, grading/grades.jsonl with
grading/out/*_extracted.jsonl, and jobids_*.txt. Exits 1 on any leak-gate hit.
"""
import argparse
import collections
import csv
import glob
import gzip
import json
import multiprocessing
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export  # noqa: E402
import facing  # noqa: E402
import scrub  # noqa: E402
from frontier import codex_log, miniswe_log, thin_log  # noqa: E402

REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
CELLS = os.path.join(REPO, "rebuttal", "results", "databook", "frontier_cells.csv")
MODES_CSV = os.path.join(REPO, "rebuttal", "results", "frontier", "failure_modes.csv")

# arm in the data book -> (key, display name, model id, harness, converter)
ARMS = collections.OrderedDict([
    ("thin-gpt-6.1-sol", ("sol-loop", "gpt-6.1-sol (our loop)", "gpt-6.1-sol", "our loop", thin_log)),
    ("codex-gpt-6.1-sol", ("sol-codex", "gpt-6.1-sol (Codex CLI)", "gpt-6.1-sol", "Codex CLI", codex_log)),
    ("codex-gpt-6-astra", ("astra-codex", "gpt-6-astra (Codex CLI)", "gpt-6-astra", "Codex CLI", codex_log)),
    ("thin-gpt-6-astra", ("astra-loop", "gpt-6-astra (our loop)", "gpt-6-astra", "our loop", thin_log)),
    ("miniswe", ("wonder-miniswe", "Muse Wonder (mini-SWE-agent)", "Muse Wonder", "mini-SWE-agent", miniswe_log)),
])
REUSE = False
FRONT_DIR = os.path.join(export.DATA, "frontier")
FRONT_INDEX = os.path.join(export.DATA, "frontier.json")
EXIT = dict(export.EXIT_LABELS, submitted="Finished")
# Slurm job numbers of the period, read as job numbers wherever they appear
JOB_RANGE = re.compile(r"(?<![0-9.])(?:3[45][0-9]{5}|23[5-9][0-9]{5})(?![0-9])")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def read_rows():
    with open(CELLS, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["arm"] in ARMS]


def anon_id(row):
    return "%s-%s-%s" % (ARMS[row["arm"]][0], row["orig_tier"], row["paper"])


def tokens_of(run_dir):
    stats = load_json(os.path.join(run_dir, "stats.json"), {})
    if isinstance(stats.get("tokens"), dict):
        t = stats["tokens"]
        return {k: int(t.get(k) or 0) for k in ("prompt", "completion", "total", "cached", "reasoning")}
    tot = (load_json(os.path.join(run_dir, "usage.json"), {}) or {}).get("totals") or {}
    if "input_tokens" in tot:
        p, c = int(tot.get("input_tokens") or 0), int(tot.get("output_tokens") or 0)
        return {"prompt": p, "completion": c, "total": p + c,
                "cached": int(tot.get("cached_input_tokens") or 0),
                "reasoning": int(tot.get("reasoning_output_tokens") or 0)}
    if "prompt_tokens" in tot:
        p, c = int(tot.get("prompt_tokens") or 0), int(tot.get("completion_tokens") or 0)
        return {"prompt": p, "completion": c, "total": p + c,
                "cached": int(tot.get("cached_tokens") or 0), "reasoning": 0}
    return None


CHUNK = 3000
_SOFT = re.compile(r"(\s+)")
_HARD = re.compile(r"([,;\"'{}\[\]()|]+)")


def _pieces(line):
    """Cut one long line into pieces of at most CHUNK characters, at whitespace
    where there is any, then at punctuation, then by length."""
    out, cur = [], ""
    for tok in _SOFT.split(line):
        if len(tok) > CHUNK:
            parts = []
            for sub in _HARD.split(tok):
                parts.extend(sub[i:i + CHUNK] for i in range(0, len(sub), CHUNK))
        else:
            parts = [tok]
        for part in parts:
            if len(cur) + len(part) > CHUNK and cur:
                out.append(cur)
                cur = ""
            cur += part
    if cur:
        out.append(cur)
    return out


_BLOB = re.compile(r"[A-Za-z0-9._%+-]{150,}")
_BLOB_SECRET = ("hf_", "sk-", "ghp_", "akia", "eyj", "org-")
_BLOB_IDENT = ("salunk", "mithil", "ncsa", "illinois", "bfvr", "betw", "dtai", "ghx4",
               "gh200", "reprocl", "gh-login", "dt-login", "rebuttal", "uiuc")
# an address whose name part has no letter, which the scrubber's email rule skips
_NUM_EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[0-9._%+-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# launcher scripts that sit beside the Codex bridge and show up when an agent
# lists that folder; they are no part of the harness the agent calls
_LAUNCHER = re.compile(r"\b(?:advance_sweeps\.sh|sequence_sweeps\.sh|codex_sweep\.sh|sweep_ctl\.sh|"
                       r"sequencer\.sh|find_queue_cancels\.py|reconcile_spend\.py|skip_list\.py|"
                       r"test_bridge_queue\.py)")
_MARK = "\ue000%d\ue001"
_MARK_RE = re.compile("\ue000(\\d+)\ue001")


def _scrub_bounded(text):
    if len(text) <= CHUNK * 4:
        return scrub.scrub_text(text)
    out, cur, size = [], [], 0
    for line in text.split("\n"):
        if len(line) > CHUNK:
            if cur:
                out.append(scrub.scrub_text("\n".join(cur)))
                cur, size = [], 0
            out.append("".join(scrub.scrub_text(p) for p in _pieces(line)))
            continue
        if size + len(line) > CHUNK * 4 and cur:
            out.append(scrub.scrub_text("\n".join(cur)))
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        out.append(scrub.scrub_text("\n".join(cur)))
    return "\n".join(out)


def scrub_text(text):
    """scrub.scrub_text with bounded input. Its email pattern is cubic on an
    unbroken run of name characters (encoded data, a 30,000-character token),
    so a run of 150 or more is set aside first: redacted whole when it holds a
    key prefix, scrubbed in short pieces when it holds an identifier, and put
    back untouched otherwise. The rest is scrubbed in blocks of bounded size."""
    if not text:
        return text
    kept = []

    def aside(m):
        blob = m.group(0)
        low = blob.lower()
        if any(k in low for k in _BLOB_SECRET):
            blob = "[redacted]"
        elif any(k in low for k in _BLOB_IDENT):
            blob = "".join(scrub.scrub_text(blob[i:i + 100]) for i in range(0, len(blob), 100))
        kept.append(blob)
        return _MARK % (len(kept) - 1)

    body = _BLOB.sub(aside, text) if len(text) >= 150 else text
    body = _scrub_bounded(body)
    body = _NUM_EMAIL.sub("[email]", body)
    body = _LAUNCHER.sub("[launcher file]", body)
    return _MARK_RE.sub(lambda m: kept[int(m.group(1))], body) if kept else body


def scrub_obj(obj):
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [scrub_obj(v) for v in obj]
    if isinstance(obj, dict):
        return {k: scrub_obj(v) for k, v in obj.items()}
    return obj


def build(job):
    """One run: convert, scrub, write the bundle, return the index entry."""
    row, run_dir, verdict, mode_row, paper = job
    key, _name, _mid, _harness, conv = ARMS[row["arm"]]
    rid = anon_id(row)
    out_path = os.path.join(FRONT_DIR, rid + ".json.gz")
    if REUSE and os.path.isfile(out_path):
        with gzip.open(out_path, "rt", encoding="utf-8") as fh:
            return json.load(fh)["run"]
    events = conv.events(run_dir)
    report = load_json(os.path.join(run_dir, "report.json"), {}) or {}
    facing_stats = {}
    rationale = facing.trim_tail(verdict.get("rationale") or "") or None
    reproduced = str(row["reproduced"]) == "True"
    if reproduced:
        mode, slug = "reproduced-clean", "reproduced-clean"
    else:
        mode, slug = export.norm_mode((mode_row or {}).get("primary"))
    audit = scrub_obj({
        "score": int(row["score"]), "verdict": row["verdict"], "reproduced": reproduced,
        "flags": export.norm_flags(verdict.get("cheat_flags")),
        "rationale": rationale, "has_transcript": False,
    })
    analysis = scrub_obj({
        "paper_gist": paper.get("gist"),
        "failure_mode_detail": (mode_row or {}).get("evidence") or None,
        "self_report": facing.self_report(report.get("agent_assessment")),
    })
    for field in ("rationale",):
        if audit.get(field):
            audit[field] = facing.facing_pass(audit[field], facing_stats)
    if analysis.get("failure_mode_detail"):
        analysis["failure_mode_detail"] = facing.facing_pass(analysis["failure_mode_detail"], facing_stats)
    analysis = {k: v for k, v in analysis.items() if v}
    scrubbed = scrub_obj(events)
    last_t = max((e.get("t_rel_s") or 0 for e in scrubbed), default=0)
    entry = {
        "id": rid, "arxiv_id": row["paper"], "model": key, "tier": row["orig_tier"],
        "sweep": "%s-%s" % (key, row["orig_tier"]),
        "exit_label": EXIT.get(row.get("exit_reason") or "", "Finished"),
        "rounds": sum(1 for e in scrubbed if e["kind"] == "round_open"),
        "tool_calls": sum(1 for e in scrubbed if e["kind"] == "call_start"),
        "budget_h100": float(row["budget_h100"]), "spent_h100": round(float(row["spent_h100"] or 0), 4),
        "audit": audit, "mode": mode, "mode_slug": scrub.scrub_text(slug or "") or None,
        "claim": paper.get("claim"), "self_report": analysis.get("self_report"),
        "target": paper.get("target"), "frontier": True,
    }
    if last_t:
        entry["duration_s"] = int(last_t)
    tokens = tokens_of(run_dir)
    if tokens:
        entry["tokens"] = tokens
    entry = {k: v for k, v in entry.items() if v is not None}
    bundle = {"run": entry, "events": scrubbed, "analysis": analysis, "audit_events": []}
    export.write_gz(out_path, bundle)
    return entry


def sweep_rows(entries):
    out = []
    for arm, (key, _n, _m, _h, _c) in ARMS.items():
        for tier in ("run", "retrain", "reimplement"):
            runs = [e for e in entries if e["model"] == key and e["tier"] == tier]
            if not runs:
                continue
            scores = [e["audit"]["score"] for e in runs]
            dist = {str(i): scores.count(i) for i in range(11)}
            out.append({
                "key": "%s-%s" % (key, tier), "model": key, "tier": tier, "n": len(runs),
                "mean_score": round(sum(scores) / len(scores), 2),
                "n_reproduced": sum(1 for e in runs if e["audit"]["reproduced"]),
                "verdicts": dict(collections.Counter(e["audit"]["verdict"] for e in runs)),
                "modes": dict(collections.Counter(e["mode"] for e in runs)),
                "score_distribution": dist,
                "spent_h100": round(sum(e["spent_h100"] for e in runs), 1),
                "budget_h100": round(sum(e["budget_h100"] for e in runs), 1),
                "frontier": True,
            })
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only")
    ap.add_argument("--reuse", action="store_true", help="keep run files that already exist")
    args = ap.parse_args(argv)
    global REUSE
    REUSE = args.reuse
    src = os.path.abspath(args.src)
    rows = read_rows()
    index_path = os.path.join(export.DATA, "index.json")
    index = load_json(index_path)
    papers = {p["arxiv_id"]: p for p in index["papers"]}

    grades = {}
    for line in open(os.path.join(src, "grading", "grades.jsonl"), encoding="utf-8"):
        rec = json.loads(line)
        grades[rec["run_id"]] = rec          # the latest line for a run wins
    modes = {r["run_id"]: r for r in csv.DictReader(open(MODES_CSV, encoding="utf-8"))}

    # raw run ids: an exported run maps to its public id, every other one to [run]
    id_map = {rid: "[run]" for rid in grades}
    for path in glob.glob(os.path.join(src, "runs", "*", "*", "*")):
        id_map[os.path.basename(path)] = "[run]"
    for row in rows:
        id_map[row["run_id"]] = anon_id(row)
    scrub.set_id_map(id_map)

    job_ids = set()
    for path in glob.glob(os.path.join(src, "jobids_*.txt")):
        job_ids.update(l.strip().split("_")[0].split(".")[0] for l in open(path) if l.strip())
    for path in glob.glob(os.path.join(src, "runs", "*", "*", "*", "*")):
        if os.path.isfile(path) and not path.endswith(".tar"):
            with open(path, encoding="utf-8", errors="replace") as fh:
                job_ids.update(JOB_RANGE.findall(fh.read()))
    scrub.add_job_ids(job_ids)
    export.GATE_PATS = scrub.gate_patterns()
    print("id map %d raw ids, %d job numbers" % (len(id_map), len(job_ids)))

    jobs = []
    for row in rows:
        rid = anon_id(row)
        if args.only and rid != args.only:
            continue
        run_dir = os.path.join(src, "runs", row["paper"], row["budget"], row["run_id"])
        if not os.path.isdir(run_dir):
            sys.exit("missing run folder for %s" % row["run_id"])
        g = grades.get(row["run_id"]) or {}
        vfile = os.path.join(src, "grading", "out", os.path.basename(g.get("verdicts") or "x"))
        verdict = {}
        if os.path.isfile(vfile):
            lines = [json.loads(l) for l in open(vfile, encoding="utf-8") if l.strip()]
            verdict = lines[-1] if lines else {}
        if verdict and int(verdict.get("score", -1)) != int(row["score"]):
            sys.exit("score mismatch for %s: verdict file %s, data book %s"
                     % (row["run_id"], verdict.get("score"), row["score"]))
        if row["paper"] not in papers:
            sys.exit("paper %s is not in the site index" % row["paper"])
        jobs.append((row, run_dir, verdict, modes.get(row["run_id"]), papers[row["paper"]]))

    jobs.sort(key=lambda j: -os.path.getsize(os.path.join(j[1], "agent.full.log")))
    with multiprocessing.Pool(args.jobs) as pool:
        entries = []
        for entry in pool.imap_unordered(build, jobs):
            entries.append(entry)
            print("wrote %s score=%s rounds=%s calls=%s" % (
                entry["id"], entry["audit"]["score"], entry["rounds"], entry["tool_calls"]), flush=True)
    if args.only:
        return 0

    order = {anon_id(r): i for i, r in enumerate(rows)}
    entries.sort(key=lambda e: order[e["id"]])
    front = {
        "generated": export.GENERATED,
        "models": [{"key": k, "name": n, "id": mid, "harness": h, "frontier": True}
                   for k, n, mid, h, _c in ARMS.values()],
        "sweeps": sweep_rows(entries),
        "runs": entries,
    }
    export.write_json(FRONT_INDEX, front)

    hits, n_files, _bytes, _allowed = scrub.gate_tree(export.OUT)
    total = sum(len(v) for v in hits.values()) if isinstance(hits, dict) else len(hits)
    print("%d frontier runs beside %d indexed runs; leak gate over %d files: %d hits"
          % (len(entries), len(index["runs"]), n_files, total))
    if total:
        for name, found in (hits.items() if isinstance(hits, dict) else []):
            for item in found[:5]:
                print("  GATE %s: %s" % (name, str(item)[:200]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
