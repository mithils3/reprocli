"""Tier composition analysis over verified v5 classifier rows.

Joins titles from the paper-bundle parquet, the PWC artifacts file, and the
arXiv API (cached), buckets papers by topic keywords, and prints tier
crosstabs, per-tier compute stats, and artifact-signal rates. Findings are
written up in notes/Analysis/Tier Composition (v5).md.

Usage: python tools/tier_composition.py
"""
import json
import re
import statistics
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "outputs/v5/neurips_2025_minimax_m2_trial_extracted.jsonl"
PARQUET = ROOT / "data/paper_bundle_dataset/data/train-00000.parquet"
PWC = ROOT / "data/paperswithcode/arxiv_artifacts.jsonl"
META = ROOT / "tools/verify_app/arxiv_meta.json"
TITLE_CACHE = ROOT / "outputs/v5/arxiv_title_cache.json"

EVAL = ["Easy", "Medium", "Hard"]

# first match wins, priority order
TOPICS = [
    ("theory/optim", r"\b(regret|convergence|sample complexity|minimax|convex|theoretic|provabl|bound[s]?\b|complexity of|pac[- ]|lower bound|approximation)\b"),
    ("RL", r"\b(reinforcement|\brl\b|policy (?:optimi|gradient|learning)|reward|bandit|q-learning|offline rl)\b"),
    ("LLM/NLP", r"\b(language model|llm|gpt|instruction|prompt|token|reasoning|chain[- ]of[- ]thought|text[- ]to|nlp|question answering|dialogue|in[- ]context|rlhf|preference)\b"),
    ("multimodal/VLM", r"\b(multimodal|multi-modal|vision[- ]language|vlm|clip|visual question|image[- ]text|text[- ]image)\b"),
    ("diffusion/genAI", r"\b(diffusion|flow matching|generative|gan\b|image generation|video generation|text-to-image|text-to-video|score-based)\b"),
    ("vision/3D", r"\b(image|vision|video|visual|segmentation|detection|3d\b|point cloud|nerf|gaussian splat|depth|pose|scene|object|face|optical)\b"),
    ("graph", r"\b(graph|gnn|node|knowledge graph|molecul)\b"),
    ("bio/science/med", r"\b(protein|drug|medical|clinical|brain|eeg|genom|cell|biolog|chem|physics|pde|weather|climate|antibody)\b"),
    ("privacy/robust/sec", r"\b(privacy|differential|federated|adversarial|attack|backdoor|jailbreak|robust|watermark|unlearning|safety)\b"),
    ("time-series/tabular", r"\b(time[- ]series|forecasting|tabular|anomaly)\b"),
    ("benchmark/dataset", r"\b(benchmark|dataset|evaluation suite)\b"),
]


def load_titles(needed_ids):
    titles = {}
    import pyarrow.parquet as pq
    t = pq.read_table(PARQUET, columns=["arxiv_id", "title"])
    titles.update(zip(t["arxiv_id"].to_pylist(), t["title"].to_pylist()))
    for line in open(PWC):
        d = json.loads(line)
        if d.get("title"):
            titles.setdefault(d["arxiv_id"], d["title"])
    if TITLE_CACHE.exists():
        titles.update(json.load(open(TITLE_CACHE)))
    missing = [i for i in needed_ids if i not in titles]
    fetched = {}
    for i in range(0, len(missing), 100):
        batch = missing[i:i + 100]
        url = ("http://export.arxiv.org/api/query?id_list="
               + ",".join(batch) + "&max_results=100")
        xml = urllib.request.urlopen(url, timeout=60).read().decode()
        for m in re.finditer(
                r"<entry>.*?<id>http://arxiv.org/abs/([\d.]+)v?\d*</id>"
                r".*?<title>(.*?)</title>", xml, re.S):
            fetched[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
        time.sleep(3)
    if fetched:
        titles.update(fetched)
        cached = json.load(open(TITLE_CACHE)) if TITLE_CACHE.exists() else {}
        cached.update(fetched)
        json.dump(cached, open(TITLE_CACHE, "w"))
    return titles


def topic(r):
    text = ((r["title"] or "") + " " + (r["abstract"] or "")[:400]).lower()
    for name, pat in TOPICS:
        if re.search(pat, text.replace("\n", " ")):
            return name
    return "other"


def hours(r):
    h = r.get("audited_h100_hours")
    if h is None:
        h = (r.get("h100_recomputed_hours")
             or (r.get("h100_estimate") or {}).get("hours"))
    return h if isinstance(h, (int, float)) else None


def main():
    rows = [json.loads(l) for l in open(EXTRACTED)]
    ver = [r for r in rows if r.get("verification_status") == "verified"]
    titles = load_titles([r["custom_id"] for r in ver])
    meta = json.load(open(META))
    for r in ver:
        r["title"] = titles.get(r["custom_id"], "")
        r["abstract"] = meta.get(r["custom_id"], {}).get("abstract", "")
    print(f"verified: {len(ver)}  with title: "
          f"{sum(1 for r in ver if r['title'])}")

    ne = [r for r in ver if r["tier"] in EVAL]
    base = Counter(r["tier"] for r in ne)
    print("\n=== base rates over", len(ne), "verified eval rows ===")
    print({t: f"{100 * base[t] / len(ne):.0f}%" for t in EVAL})

    tab = defaultdict(Counter)
    for r in ver:
        tab[topic(r)][r["tier"]] += 1
    print("\n=== Topic x Tier (% within topic over eval tiers) ===")
    print(f"{'topic':<20}{'n':>5}{'Easy':>7}{'Med':>7}{'Hard':>7}"
          f"{'A-B':>6}{'OoS':>6}")
    for name in sorted(tab, key=lambda k: -sum(tab[k].values())):
        c = tab[name]
        n, n_eval = sum(c.values()), sum(c[t] for t in EVAL)
        pct = (lambda t: f"{100 * c[t] / n_eval:.0f}%" if n_eval else "-")
        print(f"{name:<20}{n:>5}{pct('Easy'):>7}{pct('Medium'):>7}"
              f"{pct('Hard'):>7}{c['Artifact-Blocked']:>6}"
              f"{c['Out-of-Scope-Non-Empirical']:>6}")

    print("\n=== H100 hours by tier ===")
    for t in EVAL:
        hrs = sorted(h for r in ver if r["tier"] == t
                     if (h := hours(r)) is not None)
        print(f"{t:<8} n={len(hrs):<4} median={statistics.median(hrs):>7.1f}"
              f"  p25={hrs[len(hrs) // 4]:>7.1f}"
              f"  p75={hrs[3 * len(hrs) // 4]:>7.1f}"
              f"  >192h: {sum(1 for h in hrs if h > 192)}")

    print("\n=== median hours by topic x tier (cells with n>=5) ===")
    bytop = defaultdict(lambda: defaultdict(list))
    for r in ver:
        if r["tier"] in EVAL and (h := hours(r)) is not None:
            bytop[topic(r)][r["tier"]].append(h)
    for tp, cells in sorted(bytop.items(),
                            key=lambda kv: -sum(map(len, kv[1].values()))):
        line = f"{tp:<20}"
        for t in EVAL:
            v = cells[t]
            line += (f" {t}: {statistics.median(v):6.1f} (n={len(v):3d})"
                     if len(v) >= 5 else f" {t}:     -        ")
        print(line)

    print("\n=== Artifact signals by tier ===")
    for t in EVAL + ["Artifact-Blocked"]:
        sub = [r for r in ver if r["tier"] == t]
        def frac(key):
            vals = [r["signals"][key]["value"] for r in sub
                    if r.get("signals", {}).get(key)]
            return (f"{100 * sum(map(bool, vals)) / len(vals):.0f}%"
                    if vals else "-")
        print(f"{t:<17} n={len(sub):<4} code={frac('code_available'):>5}"
              f" data={frac('dataset_available'):>5}"
              f" std-data={frac('dataset_is_standard'):>5}"
              f" weights={frac('weights_available'):>5}")

    hard = [r for r in ver if r["tier"] == "Hard"]
    print("\n=== Hard tier score split (2 = weights w/o code) ===",
          dict(Counter(r["score"] for r in hard)))


if __name__ == "__main__":
    main()
