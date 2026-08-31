r"""Snapshot exporter for the anonymized reviewer viewer (SPEC.md v2.1).

Selects the nine paper sweeps of SPEC section 1, resolves each run's pinned
Claude Sonnet 5 grade, applies the failure-mode vocabulary of section 2, strips
every identifier through scrub.py per section 3, runs the facing pass of
section 8 over the displayed narrative fields, and writes the section 4 data
contract into public/data/ plus manifest.json and export_report.md. The report
ends with the section 7 concordance against the paper. Exits 1 if the leak gate
finds anything under public/.

    source <(grep -E '^export SUPABASE_SERVICE_KEY' ~/.bashrc)
    python3 export.py
    python3 export.py --limit 5 --out .scratch/dry     # a dry bundle, no publish

Reads repro_runs, repro_events, audit_runs, audit_events and repro_analyses.
Never writes to the database. Never reads host_*, repro_tags or
repro_sweeps.aggregates.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import concordance
import facing
import scrub

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "public")
DATA = os.path.join(OUT, "data")
RUNS_DIR = os.path.join(DATA, "runs")
META = HERE          # where manifest.json and export_report.md land
DRY = False
NOTES = os.path.normpath(os.path.join(HERE, "..", "..", "notes", "Analysis"))
SUPABASE_URL = "https://rjnkpoxwdslkgxjliakq.supabase.co"
HF_EVAL = ("https://huggingface.co/datasets/Mithilss/reprobench-splits"
           "/resolve/main/eval_100.jsonl")
PAGE = 1000
# --cache: transcript rows fetched once are reused from here (local only).
CACHE_DIR = None
CACHED_TABLES = ("repro_events", "audit_events")
GENERATED = dt.date.today().isoformat()

MODELS = [
    {"key": "dsv4", "name": "DeepSeek-V4", "id": "deepseek-ai/DeepSeek-V4-Flash-0731"},
    {"key": "qwen3", "name": "Qwen3.6-27B", "id": "Qwen/Qwen3.6-27B-FP8"},
    {"key": "minimax", "name": "MiniMax-M2.7", "id": "MiniMaxAI/MiniMax-M2.7"},
]
TIERS = [
    {"key": "run", "name": "Run",
     "what": "code, data and weights released; execute or evaluate"},
    {"key": "retrain", "name": "Retrain",
     "what": "code and data released, no released weights; train before evaluating"},
    {"key": "reimplement", "name": "Reimplement",
     "what": "no released code; rebuild the method from the paper"},
]
AUDITOR = {"id": "claude-sonnet-5", "name": "Claude Sonnet 5"}

# SPEC 1: one row per cell. `slug` is the sweep's DB slug, kept only so the
# report can name the sweep; it never reaches public/data.
SWEEPS = [
    ("dsv4", "run", "easy-2883229-dsv4", "easy-sweep-2883229-dsv4-analyses.json"),
    ("dsv4", "retrain", "medium-2896059-dsv4", "medium-sweep-2896059-dsv4-analyses.json"),
    ("dsv4", "reimplement", "hard-2918306-dsv4", "hard-sweep-2918306-dsv4-analyses.json"),
    ("qwen3", "run", "easy-2687371-qwen3", "easy-sweep-2687371-qwen3-analyses.json"),
    ("qwen3", "retrain", "medium-2698678-qwen3", "medium-sweep-2698678-qwen3-analyses.json"),
    ("qwen3", "reimplement", "hard-2672018", "hard-sweep-2672018-analyses.json"),
    ("minimax", "run", "easy-2652648-minimax", "easy-sweep-2652648-minimax-analyses.json"),
    ("minimax", "retrain", "medium-2690187", "medium-sweep-2690187-minimax-analyses.json"),
    ("minimax", "reimplement", "hard-2936132-minimax", "hard-sweep-2936132-minimax-analyses.json"),
]
# SPEC 2 step 3: the two sweeps whose dissection was graded by the agent's own
# family before the pinned re-audit, so a mode may contradict the pinned verdict.
BAND_SWEEPS = {"easy-2652648-minimax", "easy-2687371-qwen3"}

MODES = [
    ("reproduced-clean", "Reproduced clean"),
    ("near-miss-partial", "Near-miss partial"),
    ("reimplement-without-validating", "Reimplemented without validating"),
    ("environment-fights", "Environment fights"),
    ("artifact-provenance-mismatch", "Artifact provenance mismatch"),
    ("scope-substitution", "Scope substitution"),
    ("stale-artifact-reliance", "Stale-artifact reliance"),
    ("procrastination/wall-kill", "Procrastination and wall kill"),
    ("killed-before-the-number", "Killed before the number"),
]
MODE_KEYS = {k for k, _ in MODES}
# SPEC 2 step 2: exact synonyms only.
ALIAS = {
    "success": "reproduced-clean",
    "procrastination-wall-kill": "procrastination/wall-kill",
    "procrastination": "procrastination/wall-kill",
    "honest-shortfall": "near-miss-partial",
    "quantitative-miss": "near-miss-partial",
    "environment-setup-spiral": "environment-fights",
    "stale-artifact-substitution": "stale-artifact-reliance",
    "artifact-substitution-gap": "artifact-provenance-mismatch",
}
EXIT_LABELS = {
    "natural": "Finished",
    "budget_exhausted": "Budget exhausted",
    "context_budget": "Context limit",
    "round_limit": "Round limit",
    "wall_clock": "Time limit",
    "timeout": "Time limit",
    "error": "Ended with error",
}
TIER_OF_LOCKFILE = {"easy": "run", "medium": "retrain", "hard": "reimplement"}

EVENT_FIELDS = ["seq", "round_index", "kind", "role", "reasoning", "content",
                "exit_reason", "finish_reason", "tool_name", "command",
                "detail_kind", "args", "ok", "rc", "duration_s", "cost_h100",
                "remaining_h100", "error", "path", "stdout", "stderr",
                "truncated"]
# SPEC 8.3: the dotted paths redactions.json may blank.
REDACTABLE = {"audit.rationale", "audit.flags", "analysis.failure_mode_detail",
              "analysis.agent_trajectory_summary", "analysis.evidence_quotes",
              "analysis.paper_gist", "self_report"}
BLANK = {"audit.flags": [], "analysis.evidence_quotes": []}
# SPEC 8.2: the displayed narrative fields the facing pass rewrites.
NARRATIVE = ["audit.rationale", "audit.flags[].evidence",
             "analysis.failure_mode_detail", "analysis.agent_trajectory_summary",
             "analysis.evidence_quotes[].quote", "analysis.paper_gist"]


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------
def _key():
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        sys.exit("SUPABASE_SERVICE_KEY is not set. "
                 "source <(grep -E '^export SUPABASE_SERVICE_KEY' ~/.bashrc)")
    return key


def fetch(url, headers=None, attempts=5):
    """GET with backoff on transient failures."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url)
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise
            last = e
        except Exception as e:  # timeouts, DNS, reset connections
            last = e
        if i == attempts - 1:
            raise last
        time.sleep(2 ** i)


def select(table, params, key=None):
    """One PostgREST result set, paged on limit/offset until a short page.

    The server caps a response at 1000 rows whatever the client asks for, so
    every read goes through here rather than a single wide limit.
    """
    key = key or _key()
    headers = {"apikey": key, "Authorization": "Bearer " + key}
    cache_path = None
    if CACHE_DIR and table in CACHED_TABLES:
        stamp = table + "?" + urllib.parse.urlencode(sorted(params.items()))
        cache_path = os.path.join(CACHE_DIR, hashlib.sha1(stamp.encode()).hexdigest() + ".json.gz")
        if os.path.exists(cache_path):
            with gzip.open(cache_path, "rt", encoding="utf-8") as fh:
                return json.load(fh)
    out, offset = [], 0
    while True:
        q = dict(params)
        q["limit"] = str(PAGE)
        q["offset"] = str(offset)
        url = "%s/rest/v1/%s?%s" % (SUPABASE_URL, table, urllib.parse.urlencode(q))
        rows = json.loads(fetch(url, headers).decode())
        out.extend(rows)
        if len(rows) < PAGE:
            break
        offset += PAGE
    if cache_path:
        with gzip.open(cache_path, "wt", encoding="utf-8") as fh:
            json.dump(out, fh)
    return out


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def ts(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def num(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stamp(row):
    return str((row or {}).get("updated_at") or "")


def norm_mode(raw):
    """SPEC 2 steps 1-2. Returns (mode, original slug)."""
    original = (str(raw).strip() if raw else "") or None
    if not original:
        return "other", None
    body = re.sub(r"\s*\([^()]*\)\s*$", "", original).strip().lower()
    hyphen = body.replace("_", "-")
    for candidate in (body, hyphen):
        if candidate in ALIAS:
            return ALIAS[candidate], original
    if hyphen in MODE_KEYS:
        return hyphen, original
    return "other", original


def exit_label(raw):
    return EXIT_LABELS.get(str(raw or "").strip().lower(), "Ended")


def parse_links(raw):
    """Mirrors estimates.js parseLinks: verified_links is an object, an array
    or a python-dict string."""
    urls = []
    if isinstance(raw, list):
        urls = list(raw)
    elif isinstance(raw, dict):
        for value in raw.values():
            urls.extend(value if isinstance(value, list) else [value])
    elif isinstance(raw, str):
        urls = re.findall(r"https?://[^\s'\"\]]+", raw)
    urls = [u for u in urls if isinstance(u, str)]
    code = next((u for u in urls if re.search(
        r"github\.com|gitlab\.com|bitbucket\.org|huggingface\.co", u)), None)
    paper = next((u for u in urls if re.search(
        r"arxiv\.org|openreview\.net|doi\.org|\.pdf($|\?)", u)), None)
    if not paper:
        paper = next((u for u in urls if u != code), None)
    return paper, code


def norm_flags(raw):
    """Every flag shape the graders have written, reduced to {kind,severity,evidence}."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out = []
    for flag in raw:
        if not isinstance(flag, dict):
            continue
        out.append({
            "kind": flag.get("kind") or flag.get("type") or "other",
            "severity": flag.get("severity") or flag.get("level") or "low",
            "evidence": flag.get("evidence") or flag.get("detail") or "",
        })
    return out


def final_verdict_json(events):
    """The auditor's verdict object, parsed out of its last `final` event."""
    for row in reversed(events or []):
        if row.get("kind") != "final":
            continue
        body = row.get("content") or ""
        match = re.search(r"\{.*\}", body, re.S)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def compact_event(row, start):
    out = {}
    for field in EVENT_FIELDS:
        value = row.get(field)
        if value is not None:
            out[field] = value
    created = ts(row.get("created_at"))
    if created and start:
        out["t_rel_s"] = round((created - start).total_seconds(), 1)
    return out


def tree_bytes(root):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            total += os.path.getsize(os.path.join(dirpath, name))
    return total


GATE_PATS = None


def dumps(obj):
    """Serialize, then re-escape any control character whose JSON escape letter
    would let a raw grep read a gate literal across it."""
    return scrub.deescape(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")), GATE_PATS)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(obj))


def write_gz(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(gzip.compress(dumps(obj).encode("utf-8"), 9, mtime=0))


def load_redactions():
    """SPEC 8.3. hide_runs drops runs, hide_fields blanks dotted paths,
    hide_sentences deletes every sentence carrying one of its substrings."""
    empty = {"hide_runs": [], "hide_fields": {}, "hide_sentences": {}}
    path = os.path.join(HERE, "redactions.json")
    if not os.path.exists(path):
        write_json(path, empty)
        return empty
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {"hide_runs": list(raw.get("hide_runs") or []),
            "hide_fields": dict(raw.get("hide_fields") or {}),
            "hide_sentences": dict(raw.get("hide_sentences") or {})}


def render_target(row):
    """SPEC 8.1: the lockfile's structured match target as one line,
    "metric = value on scope, bar kind"."""
    target = row.get("match_target")
    if not isinstance(target, dict):
        return None
    metric = str(target.get("metric") or "").strip()
    value = str(target.get("value") or "").strip()
    scope = str(target.get("scope") or "").strip()
    kind = str(target.get("match_bar_kind") or "").strip().replace("_", " ")
    if not metric or not value:
        return None
    out = "%s = %s" % (metric, value)
    if scope:
        out += " on " + scope
    if kind:
        out += ", " + kind
    return out


def map_narrative(audit, analysis, fn):
    """Apply fn over every displayed narrative string of one run (SPEC 8.2).
    Returns the number of characters it removed. Never touches events."""
    removed = 0
    pairs = [(audit, "rationale"), (analysis, "failure_mode_detail"),
             (analysis, "agent_trajectory_summary"), (analysis, "paper_gist")]
    for block, field in pairs:
        value = block.get(field)
        if isinstance(value, str):
            new = fn(value)
            removed += max(0, len(value) - len(new))
            block[field] = new.strip() or None
    for flag in audit.get("flags") or []:
        value = flag.get("evidence")
        if isinstance(value, str):
            new = fn(value)
            removed += max(0, len(value) - len(new))
            flag["evidence"] = new
    quotes = []
    for quote in analysis.get("evidence_quotes") or []:
        value = quote.get("quote")
        if isinstance(value, str):
            new = fn(value)
            removed += max(0, len(value) - len(new))
            quote["quote"] = new
            if not new.strip():
                continue
        quotes.append(quote)
    analysis["evidence_quotes"] = quotes
    return removed


def fallback_rationale(entry, passes, key):
    """SPEC 8.1: a rationale under 40 characters falls back to the other
    finished pinned-auditor pass, then to the dissection's rationale_gist."""
    pinned = entry.get("pinned") or {}
    for row in passes.get(entry["raw_id"]) or []:
        if row.get("audit_run_id") == pinned.get("audit_run_id"):
            continue
        events = select("audit_events",
                        {"select": "*", "audit_run_id": "eq." + row["audit_run_id"],
                         "order": "seq.asc"}, key)
        text = (final_verdict_json(events) or {}).get("rationale")
        if isinstance(text, str) and len(text.strip()) >= 40:
            return text.strip(), "the other finished %s pass" % AUDITOR["name"]
    gist = (entry["record"].get("audit_summary") or {}).get("rationale_gist")
    if isinstance(gist, str) and len(gist.strip()) >= 40:
        return gist.strip(), "the dissection rationale_gist"
    return None, "none, the card shows score and verdict only"


def blank(path, audit, analysis):
    """SPEC 8.3 hide_fields. Returns the characters removed."""
    block, _dot, field = path.partition(".")
    target = {"audit": audit, "analysis": analysis}.get(block)
    if target is None:
        field, target = path, analysis
    size = len(dumps(target.get(field))) if target.get(field) is not None else 0
    target[field] = BLANK.get(path, None)
    return size


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Export the anonymized reviewer bundle (SPEC.md).")
    parser.add_argument("--limit", type=int, default=0,
                        help="export at most N runs, into a dry bundle")
    parser.add_argument("--only", default="",
                        help="comma separated anon ids, into a dry bundle")
    parser.add_argument("--out", default="",
                        help="write the dry bundle here (default .scratch/dry)")
    parser.add_argument("--cache", action="store_true",
                        help="reuse transcript rows fetched by an earlier --cache "
                             "run from .scratch/cache/ (selection stays live)")
    return parser.parse_args(argv[1:])


def set_paths(args):
    """A dry run writes a complete bundle somewhere harmless and leaves
    public/, manifest.json and export_report.md untouched."""
    global OUT, DATA, RUNS_DIR, META, DRY
    if not (args.limit or args.only or args.out):
        return
    DRY = True
    META = os.path.abspath(args.out or os.path.join(HERE, ".scratch", "dry"))
    # the same public/data layout, so the leak gate sees the same relative
    # paths it sees in a real export
    OUT = os.path.join(META, "public")
    DATA = os.path.join(OUT, "data")
    RUNS_DIR = os.path.join(DATA, "runs")


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------
def main(argv):
    global GATE_PATS, CACHE_DIR
    args = parse_args(argv)
    set_paths(args)
    if args.cache:
        CACHE_DIR = os.path.join(HERE, ".scratch", "cache")
        os.makedirs(CACHE_DIR, exist_ok=True)
    key = _key()
    started = time.time()

    # ---- 1. the dissection records of record ------------------------------
    print("reading the dissection records")
    sweeps, records = [], []
    for model_key, tier_key, slug, filename in SWEEPS:
        path = os.path.join(NOTES, filename)
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        sweep_key = "%s-%s" % (model_key, tier_key)
        sweeps.append({"key": sweep_key, "model": model_key, "tier": tier_key,
                       "slug": slug, "n_records": len(rows)})
        for row in rows:
            records.append((sweep_key, slug, model_key, tier_key, row))
        print("  %-24s %3d records" % (slug, len(rows)))

    # ---- 2. the database ---------------------------------------------------
    print("reading repro_runs / audit_runs / repro_analyses")
    run_rows = select("repro_runs", {"select": "*"}, key)
    audit_rows = select("audit_runs", {"select": "*"}, key)
    analysis_rows = select("repro_analyses",
                           {"select": "run_id,sweep_slug,arxiv_id,failure_mode,"
                                      "audit_score,audit_verdict"}, key)
    by_run = {r["run_id"]: r for r in run_rows}
    by_analysis = {r["run_id"]: r for r in analysis_rows}
    print("  repro_runs %d, audit_runs %d, repro_analyses %d"
          % (len(run_rows), len(audit_rows), len(analysis_rows)))

    # pinned grade = latest finished claude-sonnet-5 pass with an integer score
    claude_passes, claude_all = {}, {}
    for row in audit_rows:
        if row.get("model") != AUDITOR["id"] or row.get("status") != "finished":
            continue
        if not isinstance(row.get("score"), int) or isinstance(row.get("score"), bool):
            continue
        graded = row.get("graded_run_id")
        claude_all.setdefault(graded, []).append(row)
        prev = claude_passes.get(graded)
        if prev is None or stamp(row) >= stamp(prev):
            claude_passes[graded] = row
    for rows in claude_all.values():
        rows.sort(key=stamp, reverse=True)

    # ---- 3. the lockfile ---------------------------------------------------
    print("reading the lockfile")
    lockfile = {}
    for line in fetch(HF_EVAL).decode().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("custom_id") and row["custom_id"] not in lockfile:
            lockfile[row["custom_id"]] = row
    print("  eval_100 rows %d" % len(lockfile))

    # ---- 4. selection ------------------------------------------------------
    selected, dropped, grade_source = [], [], {}
    for sweep_key, slug, model_key, tier_key, record in records:
        raw_id = record.get("run_id")
        arxiv = record.get("arxiv_id")
        run = by_run.get(raw_id)
        if run is None:
            dropped.append({"sweep": "%s-%s" % (model_key, tier_key),
                            "arxiv_id": arxiv, "why": "no run row"})
            continue
        pinned = claude_passes.get(raw_id)
        if pinned is not None:
            source = "pinned auditor pass"
            grade = {"score": pinned.get("score"), "verdict": pinned.get("verdict"),
                     "reproduced": pinned.get("reproduced")}
        elif (run.get("audit_model") == AUDITOR["id"]
              and isinstance(run.get("audit_score"), int)
              and not isinstance(run.get("audit_score"), bool)):
            source = "the run row's stored grade"
            grade = {"score": run.get("audit_score"), "verdict": run.get("audit_verdict"),
                     "reproduced": run.get("audit_reproduced")}
        else:
            dropped.append({"sweep": "%s-%s" % (model_key, tier_key),
                            "arxiv_id": arxiv,
                            "why": "no pinned %s grade (last grader %s)"
                                   % (AUDITOR["id"], run.get("audit_model"))})
            continue
        anon_id = "%s-%s-%s" % (model_key, tier_key, arxiv)
        grade_source[anon_id] = source
        selected.append({"anon_id": anon_id, "raw_id": raw_id, "sweep": sweep_key,
                         "slug": slug, "model": model_key, "tier": tier_key,
                         "arxiv_id": arxiv, "record": record, "run": run,
                         "pinned": pinned, "grade": grade})
    print("  selected %d runs, dropped %d" % (len(selected), len(dropped)))
    if args.only:
        wanted = {name.strip() for name in args.only.split(",") if name.strip()}
        selected = [e for e in selected if e["anon_id"] in wanted]
    if args.limit:
        selected = selected[:args.limit]
    if DRY:
        print("  dry run: %d runs into %s" % (len(selected), OUT))

    # ---- 5. the raw-id replace table (SPEC 3.1) ---------------------------
    included = {s["raw_id"]: s["anon_id"] for s in selected}
    pinned_audit = {s["pinned"]["audit_run_id"]: s["anon_id"]
                    for s in selected if s["pinned"]}
    id_map = {}
    for row in run_rows:
        rid = row.get("run_id")
        if rid:
            id_map[rid] = included.get(rid, "[run]")
    for row in audit_rows:
        aid = row.get("audit_run_id")
        if aid:
            id_map[aid] = pinned_audit.get(aid, "[run]")
    scrub.set_id_map(id_map)
    job_ids = set()
    for row in run_rows:
        for field in ("batch_id", "batch_label", "run_id"):
            job_ids.update(re.findall(r"\d{7}", str(row.get(field) or "")))
    scrub.add_job_ids(job_ids)
    GATE_PATS = scrub.gate_patterns()
    print("  id replace table %d ids, %d known job ids"
          % (len(id_map), len(job_ids | scrub.JOB_IDS)))

    # ---- 6. failure modes (SPEC 2) ----------------------------------------
    relabels, mode_sources, slug_table = [], {}, {}
    for entry in selected:
        raw_mode = entry["record"].get("failure_mode")
        if raw_mode:
            mode_sources[entry["anon_id"]] = "dissection record"
        else:
            fallback = by_analysis.get(entry["raw_id"]) or {}
            raw_mode = fallback.get("failure_mode")
            mode_sources[entry["anon_id"]] = "repro_analyses fallback"
        mode, original = norm_mode(raw_mode)
        if entry["slug"] in BAND_SWEEPS:
            verdict = entry["grade"]["verdict"]
            score = entry["grade"]["score"]
            before = mode
            if mode == "reproduced-clean" and verdict != "reproduced":
                mode = "near-miss-partial" if score in (6, 7) else "other"
            elif mode == "near-miss-partial" and verdict == "reproduced":
                mode = "reproduced-clean"
            if mode != before:
                relabels.append({"id": entry["anon_id"], "from": before, "to": mode,
                                 "score": score, "verdict": verdict})
        entry["mode"] = mode
        entry["mode_slug"] = original
        slug_table.setdefault(original or "(none)", {"mode": mode, "n": 0})["n"] += 1
    print("  band-consistency relabels %d" % len(relabels))

    # ---- 7. per-run bundles ------------------------------------------------
    redactions = load_redactions()
    hide_runs = set(redactions["hide_runs"])
    applied_redactions = []
    selected = [e for e in selected if e["anon_id"] not in hide_runs]
    for anon_id in sorted(hide_runs):
        applied_redactions.append("hide_runs: dropped " + anon_id)

    print("reading transcripts for %d runs" % len(selected))
    if os.path.isdir(RUNS_DIR):
        for name in os.listdir(RUNS_DIR):
            os.remove(os.path.join(RUNS_DIR, name))
    index_runs, exit_raw, n_events, n_audit_events = [], {}, 0, 0
    quote_drops, self_reports, facing_stats = {}, {}, {}
    rationale_fallbacks, tails_trimmed, facing_chars, gist_of = [], 0, 0, {}
    for i, entry in enumerate(selected, 1):
        run, record, grade = entry["run"], entry["record"], entry["grade"]
        start = ts(run.get("started_at"))
        events = select("repro_events",
                        {"select": "*", "run_id": "eq." + entry["raw_id"],
                         "order": "seq.asc"}, key)
        n_events += len(events)

        audit_events, audit_json = [], None
        if entry["pinned"]:
            audit_events = select("audit_events",
                                  {"select": "*",
                                   "audit_run_id": "eq." + entry["pinned"]["audit_run_id"],
                                   "order": "seq.asc"}, key)
            n_audit_events += len(audit_events)
            audit_json = final_verdict_json(audit_events)

        # the pinned pass's prose. repro_runs.audit_rationale is the LAST grade
        # uploaded, so it is only the pinned one when that grader was the pin.
        if run.get("audit_model") == AUDITOR["id"]:
            rationale = run.get("audit_rationale")
            flags = norm_flags(run.get("audit_flags"))
        elif audit_json:
            rationale = audit_json.get("rationale")
            flags = norm_flags(audit_json.get("cheat_flags"))
        else:
            rationale, flags = None, []

        finished = ts(run.get("finished_at"))
        duration = round((finished - start).total_seconds()) if (finished and start) else None
        raw_exit = run.get("exit_reason")
        exit_raw[str(raw_exit)] = exit_raw.get(str(raw_exit), 0) + 1

        # SPEC 8.1: the rationale of record, trimmed, with its fallbacks
        if isinstance(rationale, str):
            trimmed = facing.trim_tail(rationale)
            if trimmed != rationale:
                tails_trimmed += 1
            rationale = trimmed
        if not rationale or len(rationale.strip()) < 40:
            replacement, source = fallback_rationale(entry, claude_all, key)
            rationale = facing.trim_tail(replacement) if replacement else None
            rationale_fallbacks.append({"id": entry["anon_id"], "source": source})

        # SPEC 8.1: quotes keep a real round of this transcript and agent prose
        numbers = [e.get("round_index") for e in events
                   if isinstance(e.get("round_index"), int)
                   and not isinstance(e.get("round_index"), bool)]
        last_round = max(numbers) if numbers else None
        quotes = []
        for quote in record.get("evidence_quotes") or []:
            if not isinstance(quote, dict):
                continue
            item = {"round": quote.get("round"), "quote": quote.get("quote")}
            keep, why = facing.keep_quote(item, last_round)
            if keep:
                quotes.append(item)
            else:
                quote_drops[why] = quote_drops.get(why, 0) + 1

        # SPEC 8.1: the agent's own report as one word
        selfclaim = record.get("agent_final_selfclaim") or {}
        word = facing.self_report(selfclaim.get("claimed_outcome"))
        self_reports[str(word)] = self_reports.get(str(word), 0) + 1

        analysis = scrub.scrub({
            "paper_gist": record.get("paper_gist"),
            "failure_mode_detail": record.get("failure_mode_detail"),
            "agent_trajectory_summary": record.get("agent_trajectory_summary"),
            "evidence_quotes": quotes,
            "self_report": word,
        })
        audit = scrub.scrub({
            "score": grade["score"], "verdict": grade["verdict"],
            "reproduced": bool(grade["reproduced"]), "flags": flags,
            "rationale": rationale, "has_transcript": bool(audit_events),
        })

        # SPEC 8.3 hide_sentences first, since its substrings are quoted from
        # the text as the screen report read it, then SPEC 8.2, then the
        # blanking of whole fields last.
        needles = redactions["hide_sentences"].get(entry["anon_id"]) or []
        if needles:
            cut = map_narrative(audit, analysis,
                                lambda t: facing.drop_sentences(t, needles)[0])
            if cut:
                applied_redactions.append(
                    "hide_sentences | %s | %s | %d characters"
                    % (entry["anon_id"], "; ".join(needles), cut))
        facing_chars += map_narrative(
            audit, analysis, lambda t: facing.facing_pass(t, facing_stats))
        for path in redactions["hide_fields"].get(entry["anon_id"], []):
            if path not in REDACTABLE:
                applied_redactions.append("hide_fields | %s | %s | unknown path, "
                                          "ignored" % (entry["anon_id"], path))
                continue
            applied_redactions.append("hide_fields | %s | %s | %d characters"
                                      % (entry["anon_id"], path,
                                         blank(path, audit, analysis)))

        gist = analysis.get("paper_gist")
        if gist and entry["arxiv_id"] not in gist_of:
            gist_of[entry["arxiv_id"]] = gist

        lock = lockfile.get(entry["arxiv_id"]) or {}
        claim = scrub.scrub_text((lock.get("central_claim") or "").strip()) or None
        target = render_target(lock)
        index_entry = {
            "id": entry["anon_id"], "arxiv_id": entry["arxiv_id"],
            "model": entry["model"], "tier": entry["tier"], "sweep": entry["sweep"],
            "exit_label": exit_label(raw_exit),
            "rounds": run.get("tool_rounds_used"), "tool_calls": run.get("tool_calls"),
            "budget_h100": num(run.get("budget")) or num(run.get("total_h100")),
            "spent_h100": num(run.get("spent_h100")),
            "duration_s": duration,
            "tokens": {"prompt": run.get("prompt_tokens"),
                       "completion": run.get("completion_tokens"),
                       "total": run.get("total_tokens"),
                       "cached": run.get("cached_tokens"),
                       "reasoning": run.get("reasoning_tokens")},
            "audit": audit,
            "mode": entry["mode"],
            "mode_slug": scrub.scrub_text(entry["mode_slug"] or "") or None,
            "claim": claim,
            "self_report": analysis["self_report"],
        }
        if target:
            index_entry["target"] = scrub.scrub_text(target)
        bundle = {
            "run": index_entry,
            "events": scrub.scrub([compact_event(e, start) for e in events]),
            "analysis": analysis,
            "audit_events": None,
        }
        if audit_events:
            audit_start = ts(entry["pinned"].get("started_at"))
            bundle["audit_events"] = scrub.scrub(
                [compact_event(e, audit_start) for e in audit_events])
        write_gz(os.path.join(RUNS_DIR, entry["anon_id"] + ".json.gz"), bundle)
        index_runs.append(index_entry)
        if i % 25 == 0 or i == len(selected):
            print("  %3d/%d runs, %d events, %d auditor events (%.0fs)"
                  % (i, len(selected), n_events, n_audit_events, time.time() - started))

    # ---- 8. sweep aggregates ----------------------------------------------
    out_sweeps = []
    for sweep in sweeps:
        rows = [r for r in index_runs if r["sweep"] == sweep["key"]]
        if not rows:
            continue
        scores = [r["audit"]["score"] for r in rows if isinstance(r["audit"]["score"], int)]
        verdicts, modes, dist = {}, {}, {}
        for row in rows:
            verdict = row["audit"]["verdict"] or "unscored"
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
            modes[row["mode"]] = modes.get(row["mode"], 0) + 1
        for score in range(11):
            dist[str(score)] = sum(1 for s in scores if s == score)
        spent = sum(r["spent_h100"] or 0 for r in rows)
        budget = sum(r["budget_h100"] or 0 for r in rows)
        out_sweeps.append({
            "key": sweep["key"], "model": sweep["model"], "tier": sweep["tier"],
            "n": len(rows),
            "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
            "n_reproduced": sum(1 for r in rows if r["audit"]["reproduced"]),
            "verdicts": verdicts, "modes": modes, "score_distribution": dist,
            "spent_h100": round(spent, 1), "budget_h100": round(budget, 1),
        })

    # ---- 9. papers ---------------------------------------------------------
    # The gist is the one already scrubbed and passed for the run pages.
    with_runs = {r["arxiv_id"] for r in index_runs}
    papers, orphan_arxiv = [], sorted(a for a in with_runs if a not in lockfile)
    for arxiv, row in sorted(lockfile.items()):
        paper_url, code_url = parse_links(row.get("verified_links"))
        paper = scrub.scrub({
            "arxiv_id": arxiv,
            "tier": TIER_OF_LOCKFILE.get(str(row.get("tier") or "").lower()),
            "band": row.get("h100_band"),
            "claim": (row.get("central_claim") or "").strip() or None,
            "predicted_h100": num(row.get("h100_hours_estimate")),
            "kind": row.get("paper_kind"),
            "paper_url": paper_url, "code_url": code_url,
        })
        target = render_target(row)
        if target:
            paper["target"] = scrub.scrub_text(target)
        paper["gist"] = gist_of.get(arxiv)
        papers.append(paper)
    no_runs = sorted(a for a in lockfile if a not in with_runs)

    # ---- 10. write ---------------------------------------------------------
    index = {
        "generated": GENERATED,
        "benchmark": {"name": "RECLAIM", "papers": len(lockfile), "venue": "NeurIPS 2025"},
        "auditor": dict(AUDITOR),
        "models": [dict(m) for m in MODELS],
        "tiers": [dict(t) for t in TIERS],
        "modes": [{"key": k, "name": n} for k, n in MODES] + [{"key": "other", "name": "Other"}],
        "sweeps": out_sweeps,
        "papers": papers,
        "runs": index_runs,
    }
    write_json(os.path.join(DATA, "index.json"), index)

    disagreements = []
    for entry in selected:
        stored = (by_analysis.get(entry["raw_id"]) or {}).get("audit_score")
        pinned_score = entry["grade"]["score"]
        if isinstance(stored, int) and stored != pinned_score:
            disagreements.append({"id": entry["anon_id"], "dissection": stored,
                                  "claude": pinned_score,
                                  "row": grade_source[entry["anon_id"]]})

    manifest = {
        "generated": GENERATED,
        "n_runs": len(index_runs),
        "n_sweeps": len(out_sweeps),
        "gate_hits": 0,
        "runs": [{"id": r["id"], "score": r["audit"]["score"],
                  "verdict": r["audit"]["verdict"], "mode": r["mode"]}
                 for r in index_runs],
        "dropped": dropped,
        "relabels": relabels,
        "score_notes": disagreements,
    }

    # ---- 11. leak gate (SPEC 3.3) -----------------------------------------
    print("running the leak gate over %s/" % os.path.relpath(OUT, HERE))
    hits, n_files, _bytes, allowed = scrub.gate_tree(OUT)
    total = sum(len(v) for v in hits.values())
    manifest["gate_hits"] = total
    write_json(os.path.join(META, "manifest.json"), manifest)
    data_bytes = tree_bytes(DATA)

    # ---- 12. concordance with the paper (SPEC 7) --------------------------
    print("checking the export against the paper")
    conc_table, mode_tables, conc_lines, n_fail, n_checks = concordance.report(
        os.path.join(DATA, "index.json"))
    for line in conc_lines:
        print("  " + line)

    write_report(out_sweeps, dropped, disagreements, orphan_arxiv, no_runs,
                 relabels, slug_table, exit_raw, mode_sources, applied_redactions,
                 data_bytes, hits, n_files, index_runs, allowed,
                 {"quote_drops": quote_drops, "self_reports": self_reports,
                  "rationale_fallbacks": rationale_fallbacks,
                  "tails_trimmed": tails_trimmed, "facing_chars": facing_chars,
                  "facing_stats": facing_stats, "concordance": conc_table,
                  "modes": mode_tables, "concordance_fails": n_fail,
                  "concordance_checks": n_checks,
                  "id_map": id_map})

    print("  %d files scanned, %d hits" % (n_files, total))
    for name, contexts in sorted(hits.items()):
        print("  LEAK %s (%d)" % (name, len(contexts)))
        for context in contexts[:20]:
            print("      " + context)
    print("%d runs / %d sweeps / %d agents, %.1f MB of data, leak gate %d hits"
          % (len(index_runs), len(out_sweeps), len(MODELS),
             data_bytes / 1e6, total))
    return 1 if total else 0


def anon_only(text, id_map):
    """SPEC: the report shows anon ids only. Every raw run or audit id and
    every 7 digit job id is replaced before the file is written."""
    for raw in sorted(id_map, key=len, reverse=True):
        if raw and raw in text:
            text = text.replace(raw, id_map[raw])
    return re.sub(r"(?<!\d)\d{7}(?!\d)", "[job]", text)


def write_report(out_sweeps, dropped, disagreements, orphan_arxiv, no_runs,
                 relabels, slug_table, exit_raw, mode_sources, applied_redactions,
                 data_bytes, hits, n_files, index_runs, allowed, extra):
    name_of = {m["key"]: m["name"] for m in MODELS}
    tier_of = {t["key"]: t["name"] for t in TIERS}
    lines = ["# Export report", "",
             "Generated %s by export.py against SPEC.md v2.1." % GENERATED, "",
             "## Counts per sweep", "",
             "| sweep | agent | tier | n | mean score | reproduced |",
             "|---|---|---|---|---|---|"]
    for sweep in out_sweeps:
        lines.append("| %s | %s | %s | %d | %.2f | %d |"
                     % (sweep["key"], name_of[sweep["model"]], tier_of[sweep["tier"]],
                        sweep["n"], sweep["mean_score"] or 0, sweep["n_reproduced"]))
    lines += ["", "Total %d runs across %d sweeps."
              % (len(index_runs), len(out_sweeps)), ""]

    lines += ["## Dropped dissected runs", ""]
    if dropped:
        lines.append("| sweep | arxiv | reason |")
        lines.append("|---|---|---|")
        for row in dropped:
            lines.append("| %s | %s | %s | " % (row["sweep"], row["arxiv_id"], row["why"]))
    else:
        lines.append("None. Every dissected run has a pinned %s grade." % AUDITOR["name"])
    lines.append("")

    lines += ["## Score disagreements", "",
              "The score stored on the dissection row against the pinned grade "
              "this export uses.", ""]
    if disagreements:
        lines.append("| run | dissection score | %s score | grade source |"
                     % AUDITOR["name"])
        lines.append("|---|---|---|---|")
        for row in disagreements:
            lines.append("| %s | %s | %s | %s |"
                         % (row["id"], row["dissection"], row["claude"], row["row"]))
    else:
        lines.append("None.")
    lines.append("")

    lines += ["## Failure-mode mapping", "",
              "| source slug | mode | n |", "|---|---|---|"]
    for slug in sorted(slug_table, key=lambda s: (-slug_table[s]["n"], s)):
        lines.append("| %s | %s | %d |" % (slug, slug_table[slug]["mode"],
                                           slug_table[slug]["n"]))
    other = sum(1 for r in index_runs if r["mode"] == "other")
    fallback = sum(1 for v in mode_sources.values() if v != "dissection record")
    lines += ["", "Runs displayed as `other`: %d." % other,
              "Runs whose mode came from the repro_analyses fallback: %d." % fallback, ""]

    lines += ["## Band-consistency relabels", ""]
    if relabels:
        lines.append("| run | from | to | pinned score | pinned verdict |")
        lines.append("|---|---|---|---|---|")
        for row in relabels:
            lines.append("| %s | %s | %s | %s | %s |"
                         % (row["id"], row["from"], row["to"], row["score"], row["verdict"]))
    else:
        lines.append("None.")
    lines.append("")

    lines += ["## Raw exit_reason values", "",
              "Listed so the exit_label map can be completed.", "",
              "| raw value | n | label |", "|---|---|---|"]
    for raw in sorted(exit_raw, key=lambda r: -exit_raw[r]):
        lines.append("| %s | %d | %s |" % (raw, exit_raw[raw], exit_label(raw)))
    lines.append("")

    lines += ["## Papers", "",
              "Included runs whose arxiv is not in eval_100: %s"
              % (", ".join(orphan_arxiv) if orphan_arxiv else "none"), "",
              "Papers in eval_100 with no runs: %s"
              % (", ".join(no_runs) if no_runs else "none"), ""]

    lines += ["## Facing pass (SPEC 8.1 and 8.2)", "",
              "Applied to the displayed narrative fields only, never to the "
              "transcript. Grades, verdicts, flag kinds and flag severities are "
              "untouched.", "",
              "- characters removed from narrative text: %d" % extra["facing_chars"],
              "- rationales with trailing serialization text trimmed: %d"
              % extra["tails_trimmed"], ""]
    lines += ["Evidence quotes dropped:", ""]
    if extra["quote_drops"]:
        lines.append("| reason | quotes |")
        lines.append("|---|---|")
        for why in sorted(extra["quote_drops"], key=lambda w: -extra["quote_drops"][w]):
            lines.append("| %s | %d |" % (why, extra["quote_drops"][why]))
    else:
        lines.append("None.")
    lines += ["", "Agent self-report after normalisation:", "",
              "| value | runs |", "|---|---|"]
    for word in sorted(extra["self_reports"], key=lambda w: -extra["self_reports"][w]):
        lines.append("| %s | %d |" % ("omitted" if word == "None" else word,
                                      extra["self_reports"][word]))
    lines += ["", "Audit rationales that fell back (under 40 characters):", ""]
    if extra["rationale_fallbacks"]:
        lines.append("| run | fallback |")
        lines.append("|---|---|")
        for row in extra["rationale_fallbacks"]:
            lines.append("| %s | %s |" % (row["id"], row["source"]))
    else:
        lines.append("None.")
    lines += ["", "Rules that fired, with the number of sentences deleted or "
              "spans replaced:", "", "| rule | n |", "|---|---|"]
    for label in sorted(extra["facing_stats"], key=lambda k: -extra["facing_stats"][k]):
        lines.append("| %s | %d |" % (label, extra["facing_stats"][label]))
    lines.append("")

    lines += ["## Redactions", "",
              "Every hide applied, with the characters it removed. "
              "`hide_sentences` runs before the facing pass, `hide_fields` after "
              "it.", ""]
    if applied_redactions:
        lines.append("| kind | run | field or substrings | removed |")
        lines.append("|---|---|---|---|")
        for row in applied_redactions:
            lines.append("| " + " | ".join(part.strip()
                                           for part in row.split("|")) + " |")
    else:
        lines.append("None applied. redactions.json is empty.")
    lines.append("")

    total = sum(len(v) for v in hits.values())
    lines += ["## Leak gate", "",
              "%d files under public/ scanned, %d hits." % (n_files, total), ""]
    for name, contexts in sorted(hits.items()):
        lines.append("- `%s`: %d" % (name, len(contexts)))
        for context in contexts[:20]:
            lines.append("  - " + context.replace("|", "\\|"))
    if not total:
        lines.append("Clean.")
    lines += ["", "### Longer words containing a brand name", "",
              "Muse and Laguna are short enough to sit inside ordinary words, so "
              "the gate matches them as whole tokens. Every longer word a plain "
              "substring `grep -i muse` or `grep -i laguna` over public/ would "
              "additionally return is listed here, and there are no others.", ""]
    if allowed:
        lines.append("| word | occurrences | what it is |")
        lines.append("|---|---|---|")
        what = {
            "museum": "a Tanks-and-Temples scene named in a benchmark paper",
            "nmuseum": "the same scene name, after an escaped newline in the JSON",
            "muse_glimmer": "a model architecture in a library listing",
            "lagunas": "the surname of an author of a benchmark paper",
            "lagunaconfig": "a model-config class in a library listing",
            "1muser": "an ANSI colour code abutting the word user",
        }
        for word in sorted(allowed, key=lambda w: (-allowed[w]["n"], w.lower())):
            lines.append("| %s | %d | %s |"
                         % (word, allowed[word]["n"],
                            what.get(word.lower(), "an ordinary word containing the name")))
    else:
        lines.append("None.")
    lines += ["", "Total bytes of the exported data: {:,} ({:.1f} MB).".format(
        data_bytes, data_bytes / 1e6), ""]

    lines += ["## Concordance with the paper", "",
              "Checked by concordance.py against public/data/index.json, one row "
              "per line of SPEC section 7. A FAIL is reported and never patched "
              "in the data.", ""]
    lines += extra["concordance"]
    lines += ["", "%d of %d checks pass."
              % (extra["concordance_checks"] - extra["concordance_fails"],
                 extra["concordance_checks"]), ""]

    lines += ["## Table: primary failure mode by tier", "",
              "The shape of the paper's tab:failure-modes, from the same data "
              "the site shows.", ""]
    lines += extra["modes"]

    body = anon_only("\n".join(lines), extra["id_map"])
    with open(os.path.join(META, "export_report.md"), "w", encoding="utf-8") as fh:
        fh.write(body)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
