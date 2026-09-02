"""Overlay re-pinned claim fields onto the frozen reprobench-splits rows.

The re-run regenerates the classifier output (now carrying a pinned, coherent
``match_target`` tuple) for exactly the 115 frozen papers. The released splits also
carry **selection metadata** (tier / score / signals / selection_band /
audited_h100_hours / the h100_* adjudication fields / split / verification_status /
verified_links) that anchors the frozen 100 + 15 selection and must NOT move.

So this is a *field-level* merge, keyed by arXiv id: overlay only the
claim-coherence fields (and the new ``match_target``) onto each existing row, and
preserve every other field exactly. The set of papers per split is unchanged.

Base files are the canonical loose JSONL on the Hub
(``eval_100.jsonl`` -> split ``test``; ``dev_split.jsonl`` -> split
``validation``). Pass ``--splits-repo`` to pull them, or ``--base-eval`` /
``--base-dev`` for local copies (e.g. the byte-identical v5 mirrors).

    python tools/merge_repin_into_splits.py \
        --repin outputs/v6/repin_eval_dev_115_extracted.jsonl \
        --splits-repo Mithilss/reprobench-splits \
        --out-eval outputs/v6/eval_100.jsonl \
        --out-dev  outputs/v6/dev_split.jsonl

Then upload each file with tools/upload_audit_pool_hf.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reprocli_openai.recheck import iter_jsonl, write_jsonl  # noqa: E402

# Only these classifier fields are overlaid; everything else on the frozen row is
# preserved verbatim so the selection and its bands cannot drift.
OVERLAY_FIELDS = ("central_claim", "claim_evidence", "mre_config", "agent_task", "match_target")
MATCH_TARGET_KEYS = ("config", "metric", "value", "scope", "match_bar_kind")
ID_FIELD = "custom_id"


def _row_id(row: dict) -> str | None:
    for key in (ID_FIELD, "arxiv_id", "paper_id", "id"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _index_repin(rows: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        rid = _row_id(row)
        if rid:
            indexed[rid] = row
    return indexed


def _check_match_target(rid: str, target: object) -> list[str]:
    """Return human-readable warnings for a structurally suspect tuple (not a
    semantic coherence check — that is the prompt's job)."""
    warns = []
    if not isinstance(target, dict):
        return [f"{rid}: match_target missing or not an object"]
    missing = [k for k in MATCH_TARGET_KEYS if not str(target.get(k, "")).strip()]
    if missing:
        warns.append(f"{rid}: match_target has empty/missing {missing}")
    return warns


def _download_base(repo: str) -> tuple[Path, Path]:
    from huggingface_hub import hf_hub_download

    paths = []
    for name in ("eval_100.jsonl", "dev_split.jsonl"):
        local = hf_hub_download(repo_id=repo, filename=name, repo_type="dataset")
        paths.append(Path(local))
    return paths[0], paths[1]


def _merge_one(base_path: Path, repin: dict[str, dict], out_path: Path) -> dict:
    base_rows = list(iter_jsonl(base_path))
    merged: list[dict] = []
    missing_ids: list[str] = []
    warnings: list[str] = []
    overlaid = 0
    for row in base_rows:
        rid = _row_id(row)
        new = dict(row)
        src = repin.get(rid) if rid else None
        if src is None:
            missing_ids.append(rid or "(no id)")
        else:
            for field in OVERLAY_FIELDS:
                if field in src:
                    new[field] = src[field]
            warnings.extend(_check_match_target(rid, new.get("match_target")))
            overlaid += 1
        merged.append(new)
    write_jsonl(out_path, merged)
    return {
        "base": str(base_path),
        "out": str(out_path),
        "rows": len(base_rows),
        "overlaid": overlaid,
        "missing_ids": missing_ids,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    repin = _index_repin(list(iter_jsonl(args.repin)))
    print(f"Loaded {len(repin)} re-pinned rows from {args.repin}")

    if args.splits_repo:
        base_eval, base_dev = _download_base(args.splits_repo)
    else:
        base_eval, base_dev = args.base_eval, args.base_dev
    if not (base_eval and base_dev):
        raise SystemExit("Provide --splits-repo or both --base-eval and --base-dev")

    results = [
        _merge_one(Path(base_eval), repin, args.out_eval),
        _merge_one(Path(base_dev), repin, args.out_dev),
    ]
    ok = True
    for r in results:
        print(
            f"\n{r['out']}: {r['rows']} rows, overlaid {r['overlaid']} "
            f"(base {r['base']})"
        )
        if r["missing_ids"]:
            ok = False
            print(f"  MISSING from re-pin ({len(r['missing_ids'])}): {r['missing_ids']}")
        for w in r["warnings"]:
            print(f"  WARN {w}")
    if not ok:
        raise SystemExit(
            "\nSome frozen papers had no re-pinned row — re-run those ids before upload."
        )
    print("\nMerge complete. Upload with tools/upload_audit_pool_hf.py.")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repin", type=Path, required=True, help="regenerated extracted JSONL (115 rows)")
    p.add_argument("--splits-repo", help="HF dataset repo to pull eval_100.jsonl / dev_split.jsonl from")
    p.add_argument("--base-eval", type=Path, help="local base eval_100.jsonl (alt to --splits-repo)")
    p.add_argument("--base-dev", type=Path, help="local base dev_split.jsonl (alt to --splits-repo)")
    p.add_argument("--out-eval", type=Path, default=Path("outputs/v6/eval_100.jsonl"))
    p.add_argument("--out-dev", type=Path, default=Path("outputs/v6/dev_split.jsonl"))
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
