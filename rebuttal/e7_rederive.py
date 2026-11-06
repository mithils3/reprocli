#!/usr/bin/env python3
"""E7 v2: check each frozen target against its paper with gpt-6.1-sol (flex, reasoning high).

Step 1 (value-blind lookup): find the paper's value for the frozen metric, dataset/split and configuration.
Step 2 (tuple check): the claim sentence unmasked plus the frozen tuple; judge metric, configuration and value support.
Both steps use the Responses API with a strict json_schema. Runs on DeltaAI with python3.12, stdlib only,
OPENAI_API_KEY in the environment:
  e7_rederive.py fetch [--limit N]    paper text to PAPERS_DIR
  e7_rederive.py run [--limit N]      API calls; resumes from results/e7/rederived.jsonl
  e7_rederive.py compare              comparison.csv, disagreements.csv, summary.json
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CLAIMS_URL = "https://huggingface.co/datasets/Mithilss/reclaim/resolve/main/eval_100.jsonl"
WORK = Path("/work/nvme/bfvr/msalunkhe/rebuttal")
CLAIMS = WORK / "e7" / "eval_100.jsonl"
PAPERS_DIR = WORK / "e7" / "papers"
LEDGER = WORK / "spend.jsonl"
RESULTS = Path(__file__).resolve().parent / "results" / "e7"
URL = "https://api.openai.com/v1/responses"
MODEL = "gpt-6.1-sol"
PRICES = {"flex": (1.00, 0.05, 5.00), "standard": (2.00, 0.10, 10.00)}  # per M tokens: in, cached in, out
ITEM_CAP = 20.0
OPENAI_CAP = 700.0
MAX_PAPER_CHARS = 800_000  # about 200k tokens at 4 characters per token
TOLERANCE = 0.05
THREADS = 4

S1 = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "value": {"type": "string"},
        "units": {"type": "string"},
        "table_or_figure": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["found", "value", "units", "table_or_figure", "quote"],
    "additionalProperties": False,
}
S2 = {
    "type": "object",
    "properties": {
        "metric_ok": {"type": "boolean"},
        "config_ok": {"type": "boolean"},
        "value_supported": {"type": "boolean"},
        "quote": {"type": "string"},
        "problem": {"type": "string"},
    },
    "required": ["metric_ok", "config_ok", "value_supported", "quote", "problem"],
    "additionalProperties": False,
}

SYS = "You read research papers and answer with the JSON object only. Copy numbers exactly as the paper prints them."

LOOKUP = """<paper>
{paper}
</paper>

Find the number this paper reports for exactly one cell of its results:
- metric: {metric}
- dataset and split: {scope}
- configuration: {config}

Copy the value as printed, without the unit. Give the unit as printed, the table or figure label, and the verbatim sentence or table row that states it. If the paper does not report this cell, set found to false and leave the other four fields as empty strings. Do not guess, and do not use a value from another cell."""

TUPLE = """<paper>
{paper}
</paper>

A reader wrote this claim about the paper:
<claim>{claim}</claim>

The claim was turned into this target tuple:
- metric: {metric}
- dataset and split: {scope}
- configuration: {config}
- value: {value}

Answer from the paper and the claim only.
- metric_ok: is the tuple's metric the one the claim sentence refers to?
- config_ok: is the tuple's configuration the one the claim sentence refers to?
- value_supported: does the paper report this value for this metric, dataset and split, and configuration?
Give a verbatim quote from the paper that bears on value_supported. In problem, say in one sentence what is wrong, or leave it empty if nothing is."""

LOCK = threading.Lock()


def load_claims(path=CLAIMS):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(CLAIMS_URL, path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def fetch(claims, limit):
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    for row in claims[:limit]:
        aid = row["custom_id"]
        out = PAPERS_DIR / f"{aid}.txt"
        if out.exists() and out.stat().st_size > 0:
            continue
        pdf = PAPERS_DIR / f"{aid}.pdf"
        req = urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers={"User-Agent": "reprocli-e7/2.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            pdf.write_bytes(r.read())
        subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], check=True)
        print("fetched", aid, out.stat().st_size, "bytes", flush=True)
        time.sleep(3)


def ledger_total(item=None, provider=None, version=None):
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if ((item is None or d.get("item") == item) and (provider is None or d.get("provider") == provider)
                and (version is None or d.get("version") == version)):
            total += d.get("usd", 0.0)
    return total


def append_ledger(entry):
    with LOCK:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a") as f:
            f.write(json.dumps(entry) + "\n")


def cost_of(inp, cached, out, tier):
    p_in, p_cached, p_out = PRICES[tier]
    return (inp - cached) * p_in / 1e6 + cached * p_cached / 1e6 + out * p_out / 1e6


def charge(payload, tier_used, step, aid):
    u = payload.get("usage") or {}
    cached = (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
    inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
    tier = "flex" if tier_used == "flex" else "standard"
    usd = cost_of(inp, cached, out, tier)
    append_ledger({"ts": dt.datetime.now().isoformat(timespec="seconds"), "item": "E7", "version": "v2",
                   "provider": "openai", "model": MODEL, "step": step, "custom_id": aid,
                   "in": inp, "cached": cached, "out": out, "usd": round(usd, 6), "tier": tier_used})
    return usd


def post(body, key):
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"error_type": e.reason}
    except urllib.error.URLError as e:
        return 0, {"error_type": str(e.reason)[:120]}


def call_model(body, key):
    """Flex with backoff on 429/408 for up to 10 minutes, then one standard-price retry."""
    start, delay, transient = time.time(), 5, 0
    while True:
        status, payload = post(body, key)
        if status == 200:
            return payload, "flex"
        if status in (429, 408):
            if time.time() - start > 600:
                break
            time.sleep(min(delay, 60))
            delay *= 2
            continue
        if status in (0, 500, 502, 503, 504) and transient < 3:
            transient += 1
            time.sleep(20)
            continue
        return None, f"http_{status}:{payload.get('error_type', '')}"
    body2 = {k: v for k, v in body.items() if k != "service_tier"}
    status, payload = post(body2, key)
    if status == 200:
        return payload, "standard_fallback"
    return None, f"http_{status}:{payload.get('error_type', '')}"


def out_text(payload):
    for item in payload.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text")
    return None


def check(obj, schema):
    if not isinstance(obj, dict) or set(obj) != set(schema["required"]):
        return "keys"
    for k, spec in schema["properties"].items():
        want = {"boolean": bool, "string": str}[spec["type"]]
        if not isinstance(obj[k], want):
            return f"type:{k}"
    if "found" in obj:
        if obj["found"] and not all(obj[k].strip() for k in ("value", "units", "table_or_figure", "quote")):
            return "found_but_blank"
    elif not obj["quote"].strip():
        return "quote_blank"
    return None


def ask(step, user, schema, key, aid):
    """Ask once; re-ask once on a schema failure. Returns (object, tier_used, error)."""
    body = {
        "model": MODEL,
        "input": [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
        "reasoning": {"effort": "high"},
        "text": {"format": {"type": "json_schema", "name": f"e7_step{step}", "strict": True, "schema": schema}},
        "max_output_tokens": 32000,
        "service_tier": "flex",
    }
    err = None
    for _ in range(2):
        payload, tier_used = call_model(body, key)
        if payload is None:
            return None, None, tier_used
        charge(payload, tier_used, step, aid)
        if payload.get("status") != "completed":
            err = "incomplete:" + str((payload.get("incomplete_details") or {}).get("reason"))
            continue
        text = out_text(payload)
        if not text:
            err = "no_text"
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            err = "json"
            continue
        err = check(obj, schema)
        if err is None:
            return obj, tier_used, None
    return None, tier_used, f"schema:{err}"


def derive_one(row, key):
    aid = row["custom_id"]
    t = row["match_target"]
    paper = (PAPERS_DIR / f"{aid}.txt").read_text(errors="replace")[:MAX_PAPER_CHARS]
    u1 = LOOKUP.format(paper=paper, metric=t["metric"], scope=t["scope"], config=t["config"])
    u2 = TUPLE.format(paper=paper, claim=row["central_claim"], metric=t["metric"], scope=t["scope"],
                      config=t["config"], value=t["value"])
    s1, tier1, e1 = ask(1, u1, S1, key, aid)
    s2, tier2, e2 = ask(2, u2, S2, key, aid)
    rec = {"custom_id": aid, "tier": row["tier"], "step1_tier": tier1, "step2_tier": tier2,
           "step1_error": e1, "step2_error": e2}
    if s1:
        rec.update({f"lookup_{k}": v for k, v in s1.items()})
    if s2:
        rec.update({f"tuple_{k}": v for k, v in s2.items()})
    with LOCK:
        with (RESULTS / "rederived.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def run(claims, limit):
    key = os.environ["OPENAI_API_KEY"]
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "rederived.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["custom_id"] for l in out.read_text().splitlines() if l.strip()}
    if ledger_total(provider="openai") + ITEM_CAP > OPENAI_CAP:
        raise SystemExit("OpenAI ledger total would pass the $700 cap")
    todo = [r for r in claims[:limit] if r["custom_id"] not in done]
    print("todo", len(todo), "already done", len(done), flush=True)
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = [pool.submit(lambda r=row: None if ledger_total("E7") >= ITEM_CAP else derive_one(r, key))
                   for row in todo]
        for f in futures:
            rec = f.result()
            if rec is None:
                print("E7 item cap reached, stopping", flush=True)
                break
            print(rec["custom_id"], rec.get("lookup_value"), rec.get("lookup_found"),
                  rec.get("tuple_value_supported"), rec.get("step1_error") or "", rec.get("step2_error") or "",
                  flush=True)
    print("E7 ledger total", round(ledger_total("E7"), 4), "v2", round(ledger_total("E7", version="v2"), 4), flush=True)


def parse_num(s):
    if s is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None


def wilson(k, n, z=1.959964):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def value_gap(tv_str, dv_str, dv_units):
    """Relative gap after percent-vs-fraction normalization. Returns (gap, note)."""
    tv, dv = parse_num(tv_str), parse_num(dv_str)
    if tv is None or dv is None:
        return None, ""
    pct_f = "%" in str(tv_str)
    pct_d = "%" in f"{dv_str} {dv_units}"
    note = ""
    if pct_f and not pct_d and abs(dv) <= 1:
        dv, note = dv * 100, "derived fraction x100"
    elif pct_d and not pct_f and abs(tv) <= 1:
        dv, note = dv / 100, "derived percent /100"
    if tv == 0:
        return (0.0 if dv == 0 else math.inf), note
    return abs(dv - tv) / abs(tv), note


def compare(claims):
    recs = {}
    for line in (RESULTS / "rederived.jsonl").read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            recs[d["custom_id"]] = d
    rows = []
    for c in claims:
        t = c["match_target"]
        d = recs.get(c["custom_id"], {})
        found = d.get("lookup_found")
        gap, note = value_gap(t["value"], d.get("lookup_value"), d.get("lookup_units"))
        value_agree = bool(found) and gap is not None and gap <= TOLERANCE
        t_ok = [d.get(f"tuple_{k}") for k in ("metric_ok", "config_ok", "value_supported")]
        reasons = []
        if not found:
            reasons.append("not_found" if found is False else "lookup_error")
        elif not value_agree:
            reasons.append("value_gap" if gap is not None else "value_unparsed")
        for name, ok in zip(("metric", "config", "value_supported"), t_ok):
            if ok is False:
                reasons.append(f"tuple_{name}")
            elif ok is None:
                reasons.append(f"tuple_error")
                break
        if d.get("step1_error") or d.get("step2_error"):
            reasons.append("schema_error")
        rows.append({
            "custom_id": c["custom_id"], "tier": c["tier"],
            "metric_frozen": t["metric"], "scope_frozen": t["scope"], "config_frozen": t["config"],
            "value_frozen": t["value"],
            "lookup_found": found, "lookup_value": d.get("lookup_value", ""), "lookup_units": d.get("lookup_units", ""),
            "lookup_table": d.get("lookup_table_or_figure", ""), "lookup_quote": d.get("lookup_quote", ""),
            "pct_normalization": note, "gap_rel": "" if gap is None else (round(gap, 6) if math.isfinite(gap) else "inf"),
            "value_agree": value_agree,
            "tuple_metric_ok": t_ok[0], "tuple_config_ok": t_ok[1], "tuple_value_supported": t_ok[2],
            "tuple_quote": d.get("tuple_quote", ""), "tuple_problem": d.get("tuple_problem", ""),
            "step1_error": d.get("step1_error") or "", "step2_error": d.get("step2_error") or "",
            "disagree": bool(reasons) or not value_agree, "reasons": ";".join(reasons),
        })
    fields = list(rows[0].keys())
    with (RESULTS / "comparison.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    dis = [r for r in rows if r["disagree"]]
    with (RESULTS / "disagreements.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(dis)

    def tally(sub, key):
        return sum(1 for r in sub if r[key] is True), len(sub)

    tiers = ("Easy", "Medium", "Hard")
    summary = {
        "model": MODEL, "api": "responses", "service_tier": "flex", "reasoning_effort": "high",
        "tolerance": TOLERANCE, "interval": "Wilson score 95%", "n": len(rows),
        "step1_value_agree": dict(zip(("k", "n"), tally(rows, "value_agree"))),
        "step1_not_found": sum(1 for r in rows if r["lookup_found"] is False),
        "step2": {},
        "by_tier": {},
        "rows_disagree": len(dis),
        "schema_errors": {"step1": sum(1 for r in rows if r["step1_error"]), "step2": sum(1 for r in rows if r["step2_error"])},
        "cost_v2_usd": round(ledger_total("E7", version="v2"), 4),
        "cost_e7_ledger_total_usd": round(ledger_total("E7"), 4),
    }
    summary["step1_value_agree"]["wilson95"] = wilson(summary["step1_value_agree"]["k"], len(rows))
    for key in ("tuple_metric_ok", "tuple_config_ok", "tuple_value_supported"):
        k, n = tally(rows, key)
        summary["step2"][key] = {"k": k, "n": n, "wilson95": wilson(k, n)}
    for tier in tiers:
        sub = [r for r in rows if r["tier"] == tier]
        summary["by_tier"][tier] = {
            "n": len(sub),
            "step1_value_agree": tally(sub, "value_agree")[0],
            "not_found": sum(1 for r in sub if r["lookup_found"] is False),
            "tuple_metric_ok": tally(sub, "tuple_metric_ok")[0],
            "tuple_config_ok": tally(sub, "tuple_config_ok")[0],
            "tuple_value_supported": tally(sub, "tuple_value_supported")[0],
        }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "run", "compare"])
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()
    claims = load_claims()
    if args.cmd == "fetch":
        fetch(claims, args.limit)
    elif args.cmd == "run":
        run(claims, args.limit)
    else:
        compare(claims)


if __name__ == "__main__":
    main()
