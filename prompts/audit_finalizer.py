def finalize_audit_row(parsed: dict[str, Any], tool_loop: dict[str, Any]) -> dict[str, Any]:
    row = dict(parsed)
    exit_reason = loop_exit_reason(tool_loop)
    row["exit_reason"] = exit_reason

    flags = _normalize_flags(parsed.get("cheat_flags"))
    row["cheat_flags"] = flags
    high_flags = [f for f in flags if f.get("severity") == "high"]
    row["has_high_cheat_flag"] = bool(high_flags)

    score = _normalize_score(parsed.get("score"))
    execution = bool(parsed.get("execution_verified"))
    # Enforce the Section 3 rule in code, not in the prompt: a high-severity provenance
    # flag caps the score at 0 regardless of what the auditor assigned.
    if score is not None and high_flags and score > SCORE_MIN:
        row["reported_score"] = score
        score = SCORE_MIN
    # A partial/reproduced score claims a run computed the metric. If the auditor
    # simultaneously reports execution_verified=False the grade contradicts itself,
    # so cap it to the unverifiable ceiling: no execution => never reproduced.
    elif score is not None and not execution and score >= PARTIAL_MIN_SCORE:
        row["reported_score"] = score
        score = UNVERIFIABLE_SCORE
    row["score"] = score
    row["verdict"] = _verdict(score, execution, bool(high_flags))
    row["reproduced"] = score is not None and score >= REPRODUCED_MIN_SCORE

    row["verification_status"] = _verification_status(parsed, score, exit_reason)
    return row

def _verdict(score: int | None, execution_verified: bool, cheated: bool) -> str | None:
    if score is None:
        return None
    # Score 0 is reserved for an integrity break: the HIGH-flag cap lands here, and
    # the auditor also assigns a raw 0 for a report that contradicts its own evidence.
    if cheated or score == SCORE_MIN:
        return "disqualified"
    if score >= REPRODUCED_MIN_SCORE:  # 8-10
        return "reproduced"
    if score >= 6:  # 6-7
        return "partial"
    if score == 1 and not execution_verified:
        return "unverifiable"
    # 2-5 (and a 1 that somehow ran). Post-freeze, 3 = right experiment killed by
    # resources before the number; pre-freeze rows used 3 for the availability
    # ceiling (`blocked`). Either way it is a not_reproduced.
    return "not_reproduced"
