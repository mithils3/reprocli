#!/usr/bin/env python3
"""E7: re-derive each eval claim's target from its paper with gpt-6.1-sol, then compare with the frozen tuple.

Runs on DeltaAI with python3.12 (stdlib only, OPENAI_API_KEY in the environment):
  python3.12 rebuttal/e7_rederive.py fetch [--limit N]    paper PDFs to text, cached in PAPERS_DIR
  python3.12 rebuttal/e7_rederive.py run [--limit N]      API calls, resumes from rederived.jsonl
  python3.12 rebuttal/e7_rederive.py compare              comparison.csv, disagreements.csv, summary.json
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys
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
MODEL = "gpt-6.1-sol"
URL = "https://api.openai.com/v1/chat/completions"
PRICES = {"flex": (1.00, 0.05, 5.00), "standard": (2.00, 0.10, 10.00)}  # per M tokens: in, cached in, out
ITEM_CAP = 20.0
OPENAI_CAP = 700.0
MAX_PAPER_CHARS = 800_000  # about 200k tokens at 4 characters per token
TOLERANCE = 0.05
THREADS = 4
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?")
NUM_TEXT = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")

PROMPT = """Below is the full text of a research paper, extracted from its PDF (tables may be flattened).

<paper>
{paper}
</paper>

A reader wrote the sentence below about one result in this paper. Every number in it has been replaced with [X]. Find the result in the paper that the sentence describes and copy its value exactly as the paper prints it. Do not guess a value the paper does not print.

<claim>
{claim}
</claim>

Return a JSON object with these keys:
- "metric": the metric name as the paper writes it
- "dataset_split": the dataset and split the result is reported on
- "configuration": the model, method, setting or table row that produced the number, in the paper's words
- "value": the number exactly as printed, as a string, without the unit
- "units": the unit as printed ("%", "kB", "" if none)
- "table_or_figure": the table or figure label holding the number
- "quote": the sentence or table row that states the value, copied verbatim"""

LOCK = threading.Lock()


def mask_numbers(text):
    return NUM_RE.sub("[X]", text)


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
        req = urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers={"User-Agent": "reprocli-e7/1.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            pdf.write_bytes(r.read())
        subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], check=True)
        print("fetched", aid, out.stat().st_size, "bytes", flush=True)
        time.sleep(3)


def ledger_total(item=None, provider=None):
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if (item is None or d.get("item") == item) and (provider is None or d.get("provider") == provider):
            total += d.get("usd", 0.0)
    return total


def append_ledger(entry):
    with LOCK:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a") as f:
            f.write(json.dumps(entry) + "\n")


def cost_of(usage, tier):
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    inp, out = usage["prompt_tokens"], usage["completion_tokens"]
    p_in, p_cached, p_out = PRICES[tier]
    return (inp - cached) * p_in / 1e6 + cached * p_cached / 1e6 + out * p_out / 1e6, inp, cached, out


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


def derive_one(row, key, done_ids):
    aid = row["custom_id"]
    paper = (PAPERS_DIR / f"{aid}.txt").read_text(errors="replace")[:MAX_PAPER_CHARS]
    claim = mask_numbers(row["central_claim"])
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You extract numeric results from research papers. Answer with a JSON object only."},
            {"role": "user", "content": PROMPT.format(paper=paper, claim=claim)},
        ],
        "reasoning_effort": "high",
        "max_completion_tokens": 24000,
        "response_format": {"type": "json_object"},
        "service_tier": "flex",
    }
    rec = {"custom_id": aid, "tier": row["tier"], "claim_masked": claim}
    payload, tier_used = call_model(body, key)
    if payload is None:
        rec.update(error=tier_used)
    else:
        choice = payload["choices"][0]
        usd, inp, cached, out = cost_of(payload["usage"], "flex" if tier_used == "flex" else "standard")
        append_ledger({"ts": dt.datetime.now().isoformat(timespec="seconds"), "item": "E7", "provider": "openai",
                       "model": MODEL, "in": inp, "cached": cached, "out": out, "usd": round(usd, 6),
                       "tier": tier_used, "custom_id": aid})
        rec.update(tier_used=tier_used, finish_reason=choice.get("finish_reason"), usd=round(usd, 6),
                   in_tokens=inp, cached_tokens=cached, out_tokens=out, error=None)
        try:
            rec.update({k: v for k, v in json.loads(choice["message"]["content"]).items()
                        if k in ("metric", "dataset_split", "configuration", "value", "units", "table_or_figure", "quote")})
        except (json.JSONDecodeError, TypeError, KeyError):
            rec.update(error="parse_error", raw_head=str(choice.get("message", {}).get("content"))[:300])
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
        sys.exit("OpenAI ledger total would pass the $700 cap")
    todo = [r for r in claims[:limit] if r["custom_id"] not in done]
    print("todo", len(todo), "already done", len(done), flush=True)
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = []
        for row in todo:
            futures.append(pool.submit(lambda r=row: (
                None if ledger_total("E7") >= ITEM_CAP else derive_one(r, key, done))))
        for f in futures:
            rec = f.result()
            if rec is None:
                print("E7 cap reached, stopping", flush=True)
                break
            print(rec["custom_id"], rec.get("value"), rec.get("error") or "", rec.get("usd", ""), flush=True)
    print("E7 ledger total", round(ledger_total("E7"), 4), flush=True)


def parse_num(s):
    if s is None:
        return None
    m = NUM_TEXT.search(str(s).replace(",", ""))
    return float(m.group()) if m else None


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", str(s or "").lower()))


def same(a, b, match_at, check_at):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return "check"
    jac = len(ta & tb) / len(ta | tb)
    if jac >= match_at:
        return "match"
    return "check" if jac >= check_at else "mismatch"


def wilson(k, n, z=1.959964):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(center - half, 4), round(center + half, 4)


def compare(claims):
    rederived = {}
    for line in (RESULTS / "rederived.jsonl").read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            rederived[d["custom_id"]] = d
    rows = []
    for c in claims:
        t = c["match_target"]
        d = rederived.get(c["custom_id"], {"error": "missing"})
        if d.get("error"):
            metric = config = "check"
            gap, reason = None, d["error"]
        else:
            metric = same(t["metric"], d.get("metric"), 0.8, 0.25)
            config = same(t["config"], d.get("configuration"), 0.6, 0.3)
            tv, dv = parse_num(t["value"]), parse_num(d.get("value"))
            if tv is None or dv is None:
                gap = None
            elif tv == 0:
                gap = 0.0 if dv == 0 else math.inf
            else:
                gap = abs(dv - tv) / abs(tv)
            reason = ";".join(k for k, ok in (("metric", metric == "match"), ("config", config == "match"),
                                             ("value", gap is not None and gap <= TOLERANCE)) if not ok)
        agree = metric == "match" and config == "match" and gap is not None and gap <= TOLERANCE
        rows.append({
            "custom_id": c["custom_id"], "tier": c["tier"],
            "metric_frozen": t["metric"], "metric_derived": d.get("metric", ""), "metric_match": metric,
            "config_frozen": t["config"], "config_derived": d.get("configuration", ""), "config_match": config,
            "scope_frozen": t["scope"], "split_derived": d.get("dataset_split", ""),
            "value_frozen": t["value"], "value_derived": d.get("value", ""), "units_derived": d.get("units", ""),
            "gap_rel": "" if gap is None else (round(gap, 6) if math.isfinite(gap) else "inf"),
            "tolerance": TOLERANCE, "agree": agree, "failed_checks": reason,
            "quote": d.get("quote", ""), "error": d.get("error") or "",
        })
    fields = list(rows[0].keys())
    with (RESULTS / "comparison.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    dis = [r for r in rows if not r["agree"]]
    with (RESULTS / "disagreements.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(dis)
    n = len(rows)
    k = sum(r["agree"] for r in rows)
    lo, hi = wilson(k, n)
    by_tier = {}
    for tier in ("Easy", "Medium", "Hard"):
        sub = [r for r in rows if r["tier"] == tier]
        kt = sum(r["agree"] for r in sub)
        tlo, thi = wilson(kt, len(sub))
        by_tier[tier] = {"agree": kt, "n": len(sub), "wilson95": [tlo, thi]}
    summary = {
        "model": MODEL, "service_tier": "flex", "tolerance_default": TOLERANCE,
        "agree": k, "n": n, "wilson95": [lo, hi], "interval": "Wilson score 95%",
        "by_tier": by_tier,
        "errors": sum(1 for r in rows if r["error"]),
        "tier_fallback_standard": sum(1 for d in rederived.values() if d.get("tier_used") == "standard_fallback"),
        "metric_match_counts": {v: sum(r["metric_match"] == v for r in rows) for v in ("match", "check", "mismatch")},
        "config_match_counts": {v: sum(r["config_match"] == v for r in rows) for v in ("match", "check", "mismatch")},
        "total_usd_e7_ledger": round(ledger_total("E7"), 4),
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
