#!/usr/bin/env python3
"""E9: find checkpoint and result-file downloads in agent run transcripts.

Maps each run in index.json to its run dir under agent_runs/<arxiv>/<budget>/<run_dir>
(stats.json: spent_h100 and tool_rounds_used must match the index), then scans:
  command   executed commands (evidence/commands.log and "$" lines in agent.full.log)
  fetch_url URLs passed to the fetch_url tool
  written_file  code the agent wrote (write_file/edit_file paths in the transcript)
  executed_repo_code / executed_repo_dir  cloned-repo code that an executed command runs (by .py name or clone dir)
Weight files on disk (>= 1 MB) are listed separately in weights.csv.

Run on DeltaAI with nice:
  nice -n 19 /usr/bin/python3.12 e9_checkpoint_scan.py --index index.json --out DIR [--tiers run,retrain,reimplement] [--ids a,b]
"""
import argparse
import csv
import json
import os
import re
from collections import Counter
from multiprocessing import Pool
from multiprocessing import TimeoutError

RUNS_ROOT = "/work/nvme/bfvr/msalunkhe/reprocli/agent_runs"
WEIGHT_EXT = (".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".npz", ".pkl")
CODE_EXT = (".py", ".sh", ".bash", ".yaml", ".yml", ".toml", ".cfg", ".ini")
WRITTEN_EXT = CODE_EXT + (".json", ".txt", ".md", ".ipynb", ".js", ".ts", ".R", ".jl")
WALK_SKIP = {".venv", "venv", "__pycache__", "node_modules", ".git", "reference", "evidence"}
URL_RE = re.compile(r"https?://[^\s\"'`)<>]+")
FIRST_QUOTED = re.compile(r"[\"']([^\"'\s]{3,})[\"']")
PATTERNS = [
    ("hf_hub_download", re.compile(r"\bhf_hub_download\b")),
    ("snapshot_download", re.compile(r"\bsnapshot_download\b")),
    ("hf_cli_download", re.compile(r"\b(?:huggingface-cli|hf)\s+download\b")),
    ("from_pretrained_id", re.compile(r"from_pretrained\(\s*(?:[A-Za-z_]+\s*=\s*)?[\"']([A-Za-z0-9][A-Za-z0-9_.\-]*(?:/[A-Za-z0-9_.\-]+)?)[\"']")),
    ("torch_hub", re.compile(r"\btorch\.hub\.(?:load|load_state_dict_from_url)\b")),
    ("timm_pretrained", re.compile(r"create_model\([^)\n]*pretrained\s*=\s*True")),
    ("gdown", re.compile(r"\bgdown\b")),
    ("git_lfs", re.compile(r"\bgit\s+lfs\s+(?:pull|fetch|checkout)\b")),
    ("git_clone_hf", re.compile(r"\bgit\s+clone\b[^\n]*?(?:huggingface\.co|hf\.co)/")),
]
HDR = ("tier", "run_id", "arxiv_id", "model", "verdict", "score", "source", "pattern", "key", "command", "file", "line_no")


def load_index(path):
    with open(path) as f:
        return json.load(f)["runs"]


def load_stats(root):
    """Return (arxiv, run_dir, budget, spent, rounds) for every run dir with a stats.json."""
    out = []
    for arxiv in os.listdir(root):
        for budget in os.listdir(os.path.join(root, arxiv)):
            for rd in os.listdir(os.path.join(root, arxiv, budget)):
                p = os.path.join(root, arxiv, budget, rd, "stats.json")
                if os.path.isfile(p):
                    with open(p) as f:
                        s = json.load(f)
                    out.append((arxiv, os.path.dirname(p), s.get("budget_h100"), s.get("spent_h100"), s.get("tool_rounds_used")))
    return out


def map_runs(rows, stats):
    """Match each index row to one run dir by arxiv, spent, rounds and budget."""
    mapping = {}
    for r in rows:
        c = [s for s in stats if s[0] == r["arxiv_id"] and s[3] is not None
             and abs(s[3] - r["spent_h100"]) <= 6e-5 and s[4] == r["rounds"]]
        if len(c) > 1:
            c = [s for s in c if s[2] == r["budget_h100"]]
        if len(c) == 1:
            mapping[r["id"]] = (c[0][1], "ok")
        else:
            mapping[r["id"]] = ("", "ambiguous" if len(c) > 1 else "no_stats_match")
    return mapping


READ_CMDS = {"grep", "rg", "fd", "cat", "head", "tail", "sed", "awk", "less", "echo", "printf", "ls", "wc",
             "find", "tree", "nl", "cut", "sort", "uniq", "tr", "diff", "jq", "file", "stat", "du", "cd", "true"}
READ_GIT = {"show", "ls-tree", "log", "grep", "diff", "cat-file", "blame", "status"}


def exec_segments(text):
    """Keep the parts of a shell line that run something (drop grep, cat, echo, git show)."""
    keep = []
    for seg in re.split(r"&&|\|\||;|\|", text):
        w = seg.split()
        if not w:
            continue
        if w[0] in READ_CMDS:
            continue
        if w[0] == "git" and len(w) > 1 and w[1] in READ_GIT:
            continue
        keep.append(seg)
    return " ; ".join(keep)


def cut(s, n=300):
    s = " ".join(s.split())
    return s[:n]


def url_hits(text):
    """Yield (pattern, key) for weight, HF-resolve and result-file URLs in a line."""
    for u in URL_RE.findall(text):
        if "huggingface.co/" in u and "/resolve/" in u:
            m = re.search(r"huggingface\.co/([^/\s]+/[^/\s]+)/resolve/", u)
            yield ("hf_resolve_url", m.group(1) if m else u)
        if re.search(r"\.(?:pt|pth|ckpt|safetensors|bin|npz|pkl)(?:[?#]|$)", u):
            yield ("weight_url", u)
        if re.search(r"(?:releases/download|raw\.githubusercontent\.com|result)", u, re.I) and \
                re.search(r"\.(?:csv|json|txt)(?:[?#]|$)|releases/download", u):
            yield ("result_url", u)


PREFILTER = re.compile(r"hf_|snapshot|download|from_pretrained|hub|create_model|gdown|lfs|clone|https?:")


def command_hits(line):
    """Yield (pattern, key) for one command or code line."""
    if not PREFILTER.search(line):
        return
    for name, rx in PATTERNS:
        m = rx.search(line)
        if not m:
            continue
        if name == "from_pretrained_id":
            for g in rx.findall(line):
                yield (name, g)
        elif name in ("hf_hub_download", "snapshot_download", "hf_cli_download", "git_clone_hf", "torch_hub", "gdown", "timm_pretrained", "git_lfs"):
            q = FIRST_QUOTED.search(line)
            yield (name, q.group(1) if q else "")
    for hit in url_hits(line):
        yield hit


def scan_transcript(path, run):
    """Return list of (source, line_no, text) for commands and fetch_url URLs, and written paths."""
    cmds, fetched, written = [], [], set()
    pending = None
    skip_until = 0
    with open(path, errors="replace") as f:
        for i, line in enumerate(f, 1):
            s = line.rstrip("\n")
            st = s.strip()
            if st.startswith("⏺ "):
                pending = st[2:].strip()
                skip_until = i + 4
                continue
            if pending in ("write_file", "edit_file") and i <= skip_until and "· path=" in s:
                written.add(s.split("· path=", 1)[1].strip())
            if re.match(r"^\s+\$ ", s):
                cmds.append((i, s.split("$ ", 1)[1]))
            elif pending == "fetch_url" and i <= skip_until and st.startswith("{"):
                try:
                    fetched.append((i, json.loads(st).get("url", "")))
                except ValueError:
                    pass
    return cmds, fetched, written


def scan_run(run, rdir, mapping_note, ref_text):
    hits, weights = [], []
    seen = set()

    def add(source, pattern, key, text, file="", line_no=""):
        k = (source, pattern, key, text[:200])
        if k in seen:
            return
        seen.add(k)
        hits.append(dict(tier=run["tier"], run_id=run["id"], arxiv_id=run["arxiv_id"], model=run["model"],
                         verdict=run["audit"].get("verdict", ""), score=run["audit"].get("score", ""),
                         source=source, pattern=pattern, key=key, command=cut(text), file=file, line_no=line_no,
                         named_in_reference=named(key, ref_text)))

    cmds, fetched, written = scan_transcript(os.path.join(rdir, "agent.full.log"), run)
    exec_texts = []
    clog = os.path.join(rdir, "evidence", "commands.log")
    if os.path.exists(clog):
        with open(clog, errors="replace") as f:
            for i, line in enumerate(f, 1):
                text = line.rstrip("\n").split("] ", 1)[-1]
                exec_texts.append(text)
                for p, k in command_hits(exec_segments(text)):
                    add("command", p, k, text, "commands.log", i)
    for i, text in cmds:
        for p, k in command_hits(exec_segments(text)):
            add("command", p, k, text, "agent.full.log", i)
        exec_texts.append(text)
    for i, u in fetched:
        for p, k in url_hits(u):
            add("fetch_url", p, k, u, "agent.full.log", i)

    written_abs = {os.path.normpath(w) for w in written}

    py_names = {os.path.basename(t) for text in exec_texts for t in re.findall(r"[\w./-]+\.py\b", text)}
    for p, name in walk_files(rdir):
        rel = os.path.relpath(p, rdir)
        if name.lower().endswith(WEIGHT_EXT):
            size = fsize(p)
            if size >= 1 << 20:
                weights.append(dict(tier=run["tier"], run_id=run["id"], path=rel, size_mb=round(size / 2**20, 1)))
            continue
        if not name.endswith(WRITTEN_EXT) or fsize(p) > 1 << 20:
            continue
        link = ""
        if os.path.normpath(p) in written_abs:
            src = "written_file"
        else:
            # Other repo code counts only when an executed command runs that file or its clone dir.
            parts = rel.split("/")
            root = parts[1] if parts[0] == "workspace" and len(parts) > 2 else ""
            if not name.endswith(CODE_EXT):
                continue
            if name in py_names:
                link = "executed_repo_code"
            elif root and any(root in t for t in exec_texts):
                link = "executed_repo_dir"
            else:
                continue
            src = link
        ex = next((t for t in exec_texts if link == "executed_repo_code" and name in t
                   or link == "executed_repo_dir" and root in t), "") if link else ""
        with open(p, errors="replace") as f:
            for i, line in enumerate(f, 1):
                for pat, k in command_hits(line):
                    add(src, pat, k, ex or line, rel, i)
    return hits, weights


def walk_files(d):
    """Yield (path, name) for regular files under d, without stat calls per file."""
    with os.scandir(d) as it:
        for e in it:
            if e.is_dir(follow_symlinks=False):
                if e.name not in WALK_SKIP:
                    yield from walk_files(e.path)
            elif e.is_file(follow_symlinks=False):
                yield e.path, e.name


def fsize(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


PRIM = {"command", "fetch_url", "written_file", "executed_repo_code", "executed_repo_dir"}
BASE_RX = re.compile(r"llama|bert|gpt2|gpt-2|resnet|vit|clip|t5|bart|roberta|whisper|sam_vit|dinov2|stable-diffusion|qwen|mistral|pytorch/vision|efficientnet|vgg|mobilenet", re.I)
DATA_RX = re.compile(r"--repo-type dataset|datasets/|allenai/c4|dataset", re.I)


def summary(path, hits, mrows, weights, timeouts):
    """Counts per tier: scanned, runs with a primary hit, class counts, reproduced runs with class c or d."""
    out = {"tiers": {}, "note": "primary sources: command, fetch_url, written_file, executed_repo_code, executed_repo_dir"}
    for t in ("run", "retrain", "reimplement"):
        ms = [m for m in mrows if m["tier"] == t]
        hs = [h for h in hits if h["tier"] == t]
        prim = [h for h in hs if h["source"] in PRIM]
        runs = {h["run_id"] for h in prim}
        ids = {m["run_id"] for m in ms}
        scanned = {m["run_id"] for m in ms if m["status"] == "ok"}
        ver = {h["run_id"]: h["verdict"] for h in hs}
        cls = Counter(h["class"] for h in prim if h["class"])
        cd_runs = {h["run_id"] for h in prim if h["class"] in ("c", "d")}
        out["tiers"][t] = {
            "runs_in_index": len(ids),
            "runs_scanned": len(scanned),
            "scan_timeouts": sorted(m["run_id"] for m in ms if m["status"] == "scan_timeout"),
            "runs_with_primary_hit": len(runs),
            "runs_with_weight_file_ge_1MB": len({w["run_id"] for w in weights if w["tier"] == t}),
            "primary_hit_rows": len(prim),
            "class_counts_rows": dict(sorted(cls.items())),
            "runs_with_class_c_or_d_hit": len(cd_runs),
            "reproduced_runs_with_class_c_or_d_hit": sorted(r for r in cd_runs if ver.get(r) == "reproduced"),
            "reproduced_runs_with_any_primary_hit": sorted(r for r in runs if ver.get(r) == "reproduced"),
        }
    with open(path, "w") as f:
        json.dump(out, f, indent=1)


def review_lookup(rows, h):
    """First manual row for this run whose key matches (exact, or prefix if non-empty) and whose match text is in the command."""
    for r in rows:
        if r["run_id"] != h["run_id"]:
            continue
        k = r["key"]
        if not (h["key"] == k or (k and h["key"].startswith(k))):
            continue
        if r.get("match") and r["match"] not in h["command"]:
            continue
        return r["class"], r["basis"]
    return "", ""


def norm(x):
    return re.sub(r"[^a-z0-9]", "", x.lower())


def rule_class(h, claim):
    """Provisional class from the key and the claim. Only (a) and (c) need a name match; otherwise (d)."""
    key, cmd = h["key"], h["command"]
    if DATA_RX.search(cmd) and not h["pattern"] == "from_pretrained_id":
        return "d", "rule: dataset download"
    if not key:
        return "d", "rule: no repo id in the call"
    m = re.search(r"huggingface\.co/([^/\s]+/[^/\s)]+)", key) or re.search(r"/([^/\s]+/[^/\s]+)$", key)
    name = (m.group(1) if m else key).split("/")[-1]
    name = re.sub(r"[.@:].*$", "", name) if name.count(".") > 3 else name
    if BASE_RX.search(key) and norm(name) not in norm(claim):
        return "b", "rule: standard backbone name, not in claim"
    if norm(name) and len(norm(name)) >= 4 and norm(name) in norm(claim):
        return ("a" if h["named_in_reference"] == "yes" else "c"), "rule: key name appears in claim"
    return "d", "rule: name not in claim"


def named(key, ref_text):
    """True if the key (repo id or URL) appears in the paper's own LaTeX or info.json."""
    if not key or not ref_text:
        return ""
    m = re.search(r"(?:huggingface\.co|github\.com|githubusercontent\.com)/([^/\s]+/[^/\s)]+)", key)
    k = (m.group(1) if m else key).lower().rstrip("/")
    return "yes" if k and k in ref_text else "no"


def load_reference(rdir):
    txt = []
    for sub in ("reference/latex", "reference"):
        d = os.path.join(rdir, sub)
        if os.path.isdir(d):
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p) and name.endswith((".tex", ".json", ".txt", ".md")) and os.path.getsize(p) < 2 << 20:
                    with open(p, errors="replace") as f:
                        txt.append(f.read().lower())
    return "\n".join(txt)


def _work(job):
    r, rdir, note = job
    run = dict(id=r["id"], arxiv_id=r["arxiv_id"], model=r["model"], tier=r["tier"],
               audit=dict(verdict=r["audit"]["verdict"], score=r["audit"]["score"]))
    return scan_run(run, rdir, note, load_reference(rdir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--runs-root", default=RUNS_ROOT)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tiers", default="run,retrain,reimplement")
    ap.add_argument("--ids", default="")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--from-hits", default="", help="reuse hits.csv, weights.csv and mapping.csv from this dir (no scan)")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per run before it is marked scan_timeout")
    ap.add_argument("--review", default="", help="class_review.csv: run_id,key,class,basis")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows = load_index(a.index)
    tiers = set(a.tiers.split(","))
    ids = set(a.ids.split(",")) if a.ids else None
    rows = [r for r in rows if r["tier"] in tiers and (ids is None or r["id"] in ids)]
    mapping = map_runs(rows, load_stats(a.runs_root))

    review = []
    if a.review and os.path.exists(a.review):
        with open(a.review) as f:
            review = list(csv.DictReader(f))

    all_hits, all_weights, mrows = [], [], []
    if a.from_hits:
        all_hits = list(csv.DictReader(open(os.path.join(a.from_hits, "hits.csv"))))
        all_weights = list(csv.DictReader(open(os.path.join(a.from_hits, "weights.csv"))))
        mrows = list(csv.DictReader(open(os.path.join(a.from_hits, "mapping.csv"))))
        timeouts = {m["run_id"] for m in mrows if m["status"] == "scan_timeout"}
    else:
        jobs = []
        for r in rows:
            rdir, note = mapping[r["id"]]
            mrows.append(dict(run_id=r["id"], tier=r["tier"], run_dir=rdir, status=note))
            if note == "ok":
                jobs.append((r, rdir, note))
        pool = Pool(a.procs)
        futs = [(j[0], pool.apply_async(_work, (j,))) for j in jobs]
        timeouts = set()
        for r, fut in futs:
            try:
                h, w = fut.get(timeout=a.timeout)
            except TimeoutError:
                h, w = [], []
                timeouts.add(r["id"])
            all_hits += h
            all_weights += w
            print("scanned", r["id"], len(h), flush=True)
        for m in mrows:
            if m["run_id"] in timeouts:
                m["status"] = "scan_timeout"

        with open(os.path.join(a.out, "mapping.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["run_id", "tier", "run_dir", "status"])
            wr.writeheader()
            wr.writerows(mrows)
        with open(os.path.join(a.out, "weights.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["tier", "run_id", "path", "size_mb"])
            wr.writeheader()
            wr.writerows(all_weights)
    claims = {r["id"]: (r["claim"] or "") + " " + (r["target"] or "") for r in rows}
    for h in all_hits:
        c, b = review_lookup(review, h)
        if not c and h["tier"] != "run" and h["source"] in PRIM:
            c, b = rule_class(h, claims[h["run_id"]])
        h["class"], h["basis"] = c, b
    with open(os.path.join(a.out, "hits.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(HDR) + ["named_in_reference", "class", "basis"])
        wr.writeheader()
        wr.writerows(all_hits)
    summary(os.path.join(a.out, "summary.json"), all_hits, mrows, all_weights, timeouts)
    print("mapped", sum(1 for m in mrows if m["status"] == "ok"), "of", len(rows), "hits", len(all_hits), "timeouts", len(timeouts), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
