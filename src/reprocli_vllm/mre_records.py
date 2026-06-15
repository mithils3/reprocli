"""Load the already-chosen MRE rows and render them for the curator prompt.

Verification targets must grade the *same* MRE the dataset points the agent
at, so each paper's classifier row (central_claim, mre_config, agent_task,
verified_links, tier) is injected into the prompt next to the paper text.

The source may be a local JSONL path or an HF reference of the form
``hf://datasets/<owner>/<name>/<file>`` so a cluster run can pull the audit
pool straight from the Hub.
"""

from __future__ import annotations

import json
from pathlib import Path

# Fields copied from the classifier extracted row into the curator prompt.
MRE_FIELDS = (
    "central_claim",
    "claim_evidence",
    "paper_kind",
    "mre_config",
    "agent_task",
    "verified_links",
    "tier",
    "score",
    "h100_estimate",
)


def load_mre_records(source) -> dict[str, dict]:
    path = _resolve_records_path(source)
    records: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        arxiv_id = str(row.get("custom_id") or row.get("paper_id") or row.get("arxiv_id") or "")
        if arxiv_id:
            records[arxiv_id] = row
    if not records:
        raise SystemExit(f"No MRE records found in {source}")
    return records


def _resolve_records_path(source) -> Path:
    parsed = _parse_hf_spec(str(source))
    if parsed is None:
        return Path(str(source))
    repo_id, filename = parsed
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset"))


def _parse_hf_spec(spec: str) -> tuple[str, str] | None:
    if not spec.startswith("hf://"):
        return None
    rest = spec[len("hf://") :]
    if rest.startswith("datasets/"):
        rest = rest[len("datasets/") :]
    segments = [segment for segment in rest.split("/") if segment]
    if len(segments) < 3:
        raise SystemExit(
            f"Bad hf:// mre-records spec: {spec} "
            "(expected hf://datasets/<owner>/<name>/<file>)"
        )
    return "/".join(segments[:2]), "/".join(segments[2:])


def mre_record_text(record: dict | None) -> str:
    if not record:
        return "(no MRE record found for this paper; derive the MRE from the paper text)"
    selected = {key: record[key] for key in MRE_FIELDS if key in record}
    return json.dumps(selected, ensure_ascii=False, indent=2)
