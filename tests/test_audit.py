"""Tests for the audit-mode finalizer: the anti-cheat cap is enforced in code."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.audit import finalize_audit_row  # noqa: E402
from reprocli_vllm.audit_inputs import build_audit_prompt, claim_block  # noqa: E402


def _verdict_row(verdict: str, flags=None) -> dict:
    return {
        "paper_id": "2505.10978",
        "central_claim": "86.7% on ALFWorld",
        "target_metric": "success_rate",
        "reference_value": 86.7,
        "op": "abs_rel_within",
        "tolerance": 0.05,
        "execution_verified": True,
        "execution_evidence": "ran run_alfworld.sh, eval log present",
        "measured_value": 86.7,
        "measured_citation": "out/res.json:1",
        "cheat_flags": flags or [],
        "value_comparison": "86.7 within 5% of 86.7",
        "methodology_notes": "",
        "verdict": verdict,
        "confidence": 0.9,
        "rationale": "x",
    }


def test_high_flag_caps_verdict():
    flags = [{"kind": "hardcoded_constant", "evidence": "print(86.7) in eval.py:40", "severity": "high"}]
    row = finalize_audit_row(_verdict_row("reproduced", flags), {"exit_reason": "natural"})
    assert row["verdict"] == "not_reproduced"
    assert row["reported_verdict"] == "reproduced"
    assert row["reproduced"] is False
    assert row["has_high_cheat_flag"] is True
    assert row["verification_status"] == "verified"


def test_clean_reproduced_passes():
    row = finalize_audit_row(_verdict_row("reproduced"), {"exit_reason": "natural"})
    assert row["verdict"] == "reproduced"
    assert row["reproduced"] is True
    assert "reported_verdict" not in row


def test_low_flag_does_not_cap():
    flags = [{"kind": "cherry_picked_metric", "evidence": "minor", "severity": "low"}]
    row = finalize_audit_row(_verdict_row("partial", flags), {"exit_reason": "natural"})
    assert row["verdict"] == "partial"
    assert row["reproduced"] is False


def test_invalid_verdict_is_degraded():
    bad = _verdict_row("totally-made-up")
    row = finalize_audit_row(bad, {"exit_reason": "natural"})
    assert row["verification_status"] == "degraded"


def test_missing_paper_id_is_degraded():
    bad = _verdict_row("reproduced")
    bad["paper_id"] = ""
    row = finalize_audit_row(bad, {"exit_reason": "natural"})
    assert row["verification_status"] == "degraded"


def test_claim_block_uses_central_claim():
    block = claim_block({"central_claim": "msf-CNN uses 50% less RAM", "claim_evidence": {"x": 1}})
    assert "msf-CNN uses 50% less RAM" in block
    assert "Reported numbers" in block


def test_build_audit_prompt_fills_placeholders():
    template = "CLAIM:{CENTRAL_CLAIM}\nRUBRIC:{RUBRIC}\nBUNDLE:{RUN_BUNDLE}"
    out = build_audit_prompt(template, "RUBRIC_TEXT", {"central_claim": "C"}, "2505.10978", None)
    assert "{CENTRAL_CLAIM}" not in out and "{RUBRIC}" not in out and "{RUN_BUNDLE}" not in out
    assert "RUBRIC_TEXT" in out
    assert "NO AGENT RUN BUNDLE WIRED YET" in out
