r"""Facing pass over displayed narrative text (SPEC.md section 8, v2.1).

`facing_pass(text)` rewrites one displayed narrative string. It deletes whole
sentences that discuss the benchmark's own machinery, a pin, the auditor or the
run infrastructure, replaces internal vocabulary with plain words, and tidies
what is left. The exporter applies it to `audit.rationale`,
`audit.flags[].evidence`, `analysis.failure_mode_detail`,
`analysis.agent_trajectory_summary`, `analysis.evidence_quotes[].quote`,
`analysis.paper_gist` and `papers[].gist`, always after scrub.py and never to
transcript events.

The three small text helpers section 8.1 needs live here too, next to the rules
they interact with: `keep_quote`, `self_report` and `trim_tail`.
`drop_sentences` backs the `hide_sentences` key of redactions.json.

    python3 facing.py --selftest
"""

import re
import sys

APOS = "['‘’`]"


def phrase(literal):
    """A literal turned into a tolerant pattern: any apostrophe, any run of
    whitespace."""
    body = re.escape(literal)
    body = body.replace("\\ ", r"\s+")
    body = body.replace("'", APOS)
    return body


# --------------------------------------------------------------------------
# sentences
# --------------------------------------------------------------------------
# A sentence is the span between terminators (. ! ? or newline). A period
# inside a decimal, a file name or one of these abbreviations does not end a
# sentence, because splitting there would leave half a number on the page.
ABBREV = {"e.g", "i.e", "cf", "vs", "etc", "al", "fig", "figs", "eq", "eqs",
          "no", "nos", "approx", "ca", "resp", "sec", "secs", "ref", "refs",
          "incl", "dr", "mr", "ms", "prof", "st", "jr", "tab", "vol", "ver",
          "min", "max", "avg", "std", "col", "app", "pp"}
CLOSERS = "\"')]}’”"


def _is_abbrev(text, dot):
    head = re.search(r"([A-Za-z][\w.'’-]*)$", text[:dot])
    if not head:
        return False
    word = head.group(1).lower().strip(".")
    return len(word) == 1 or word in ABBREV


def split_sentences(text):
    """Spans that concatenate back to `text` exactly."""
    spans, start, i, n = [], 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            spans.append(text[start:i + 1])
            start = i = i + 1
            continue
        if ch in ".!?":
            j = i
            while j + 1 < n and text[j + 1] in ".!?":
                j += 1
            k = j + 1
            while k < n and text[k] in CLOSERS:
                k += 1
            if k < n and text[k] not in " \t\n":
                i = j + 1
                continue
            if ch == "." and _is_abbrev(text, i):
                i = j + 1
                continue
            while k < n and text[k] in " \t":
                k += 1
            spans.append(text[start:k])
            start = i = k
            continue
        i += 1
    if start < n:
        spans.append(text[start:])
    return spans


# --------------------------------------------------------------------------
# 8.2 step 1: sentence deletions
# --------------------------------------------------------------------------
PIN_SUBJECT = (r"\b(pin|pinned|pin's|tuple|claim|bar|target|lockfile|"
               r"benchmark\s+record|number|config)\b")

# (label, pattern, also-required pattern or None)
# Ordered so that the more specific trigger of an overlapping pair fires first.
DELETE_RULES = [
    ("worth flagging for tuple-quality review",
     phrase("worth flagging for tuple-quality review"), None),
    ("worth flagging for human review",
     phrase("worth flagging for human review"), None),
    ("for human review of the pinned", phrase("for human review of the pinned"), None),
    ("human review of", phrase("human review of"), None),
    ("human spot-check", r"\bhuman\s+spot[-\s]?check(?!ed)", None),
    ("a spot-check of/should/would", r"\bA\s+spot[-\s]?check\s+(?:of|should|would)\b", None),
    ("human reviewer should", phrase("A human reviewer should"), None),
    ("confidence is moderate", phrase("confidence is moderate"), None),
    ("confidence level",
     r"(?<!verbal )\bconfidence\s+is\s+(?:\w+\s+){0,2}(?:low|moderate|high|reduced|limited|\d)", None),
    ("see suspected_grading_error", phrase("See suspected_grading_error"), None),
    ("suspected_grading_error", r"suspected_grading_error", None),
    ("diverge from a pre-existing", phrase("I diverge from a pre-existing"), None),
    ("diverges from a prior self-audit",
     phrase("This diverges from a prior self-audit"), None),
    ("should have been excluded from the",
     phrase("should have been excluded from the"), None),
    ("needs correction in the benchmark",
     phrase("needs correction in the benchmark"), None),
    ("should have been pinned", phrase("should have been pinned"), None),
    ("curation-level concern", phrase("curation-level concern"), None),
    ("the benchmark's own", phrase("the benchmark's own"), None),
    ("benchmark-lockfile mis-specification",
     phrase("benchmark-lockfile mis-specification"), None),
    ("pin is not in the paper", phrase("is not in the paper"), PIN_SUBJECT),
    ("corresponds to no table or row", phrase("corresponds to no table or row"), None),
    ("entirely different paper or are fabricated",
     phrase("appear to be from an entirely different paper or are fabricated"), None),
    ("the (self-)auditor", phrase("the (self-)auditor"), None),
    ("which the audit rationale's phrase",
     phrase("which the audit rationale's phrase"), None),
    ("propose tracking this as a new sub-mode",
     phrase("I propose tracking this as a new sub-mode"), None),
    ("report-truncation-audit-loss", phrase("report-truncation-audit-loss"), None),
    ("metering behavior", phrase("metering behavior"), None),
    ("GPU-allocation-hold overhead", phrase("GPU-allocation-hold overhead"), None),
    ("run_gpu tool bug", phrase("run_gpu tool bug"), None),
    ("OOM cascade incident", phrase("OOM cascade incident"), None),
    ("rc-masking bug", phrase("rc-masking bug"), None),
    ("the previous agent ran", phrase("The previous agent ran"), None),
    ("outbound git protocol blocked", phrase("outbound git protocol blocked"), None),
    ("shared SLURM job hosting", phrase("shared SLURM job hosting"), None),
    ("at zero, EVERYTHING dies", phrase("At zero, EVERYTHING dies"), None),
    ("Invalid partition name specified",
     phrase("Invalid partition name specified"), None),
    ("stateless resend architecture", phrase("stateless resend architecture"), None),
]
DELETE = [(label, re.compile(pat, re.I), re.compile(extra, re.I) if extra else None)
          for label, pat, extra in DELETE_RULES]


# --------------------------------------------------------------------------
# 8.2 step 2: replacements
# --------------------------------------------------------------------------
DETERMINER = re.compile(r"(?:\b(?:the|a|an|its|their|his|her|our|your|this|that|"
                        r"each|no|any)\s+|['’]s\s+)$", re.I)


def _article(with_the, without_the):
    """Replacement that drops its own article when one already stands in front,
    so `the mre_config` does not become `the the pinned configuration`."""
    def repl(match):
        head = match.string[:match.start()]
        return without_the if DETERMINER.search(head) else with_the
    return repl



BAND = (r"\b(?:rubric\s+)?band\s+(\d+)\b(?!\s*[-–]\s*\d)"
        r"(?:\s*:)?"
        r"(?:\s*(?:\([^()]{0,300}\)|'[^']{0,300}'|‘[^’]{0,300}’"
        r"|\"[^\"]{0,300}\"|“[^”]{0,300}”))?")

CRITERION_NAME = {"1": "the match criterion", "2": "the execution check",
                  "3": "the value-location check", "4": "the provenance check",
                  "5": "the numeric comparison", "6": "the experiment-fidelity check"}

# (label, pattern, replacement, flags)
REPLACE_RULES = [
    ("sibling quantity, long form",
     phrase("the pinned bar is mis-specified and the agent reproduced the "
            "reproducible sibling quantity"),
     "the agent reproduced a sibling quantity", re.I),
    ("sibling quantity, short form",
     phrase("pinned bar mis-specified"), "sibling quantity reproduced", re.I),
    ("band range citation",
     r"\brubric\s+band\s+(\d+)\s*[-–]\s*(\d+)\b",
     lambda m: "a score of %s to %s" % (m.group(1), m.group(2)), re.I),
    ("band citation", BAND, lambda m: "a score of " + m.group(1), re.I),
    ("rubric's band-N", r"\brubric's\s+band-(\d+)\b",
     lambda m: "grading protocol's score-" + m.group(1), re.I),
    ("band-N anchor", r"\bband-(\d+)\s+(anchor|profile)\b",
     lambda m: "score-%s %s" % (m.group(1), m.group(2)), re.I),
    ("higher band", r"\bhigher\s+band\b", "higher score", re.I),
    ("lower band", r"\blower\s+band\b", "lower score", re.I),
    ("self-assessed auditor gist",
     r"\bSelf-(?:assessed|graded)\s+auditor\s+\([^)]*\)\s+scored\s+this\s+(\d+)/10\s+under\s+the\s+'([^']*)'\s+band:",
     lambda m: "Scored %s/10, %s:" % (m.group(1), m.group(2)), re.I),
    ("criterion code parenthetical",
     r"\((?:C[1-6](?:\s+criterion)?|C[1-6]\s+through\s+C[1-6]|"
     r"C[1-6](?:\s*,\s*C[1-6])*)\)", "", 0),
    ("criterion criteria list", r"\b(?:the\s+)?C[1-6](?:\s*(?:[-–/]|,\s*|,?\s+(?:and|through)\s+)\s*C[1-6])+\s+criteria\b",
     "the grading criteria", 0),
    ("criterion code list", r"\bC[1-6](?:\s*(?:[-–/]|,\s*|,?\s+(?:and|through)\s+)\s*C[1-6])+\b",
     "grading checks", 0),
    ("C1 criterion", r"\bC1\s+criterion\b", "the match criterion", 0),
    ("criterion code", r"(?<![\w/-])C([1-6])\b",
     lambda m: CRITERION_NAME[m.group(1)], 0),
    ("orphan criterion code", r"(?<!\w)[/-]C([1-6])\b",
     lambda m: CRITERION_NAME[m.group(1)], 0),
    ("per the rubric", phrase("per the rubric"), "under the grading protocol", re.I),
    ("under the frozen rubric",
     phrase("under the frozen rubric"), "under the grading protocol", re.I),
    ("the frozen rubric", phrase("the frozen rubric"), "the grading protocol", re.I),
    ("the rubric's", phrase("the rubric's"), "the grading protocol's", re.I),
    ("frozen eval set", r"frozen\s+eval(uation)?\s+set", "evaluation set", re.I),
    ("frozen benchmark", r"frozen\s+benchmark", "evaluation set", re.I),
    ("frozen set", r"frozen\s+set", "evaluation set", re.I),
    ("Stage-7 auditor",
     r"(?:\bthe\s+)?\bStage[-\s]?7\s+auditor\b", _article("the auditor", "auditor"), re.I),
    ("Stage-7 audit",
     r"(?:\bthe\s+)?\bStage[-\s]?7\s+audit\b", _article("the audit", "audit"), re.I),
    ("Stage 7", r"\bStage[-\s]?7\b", _article("the audit", "audit"), re.I),
    ("sweep wall", r"\bsweep\s+wall(?:\s+time|\s+clock)?\b", "session time", re.I),
    ("sweeps", r"\bsweeps\b", "batches", re.I),
    ("sweep", r"\bsweep\b", "batch", re.I),
    ("mre_config", r"\bmre_config\b",
     _article("the pinned configuration", "pinned configuration"), re.I),
    ("match_target", r"\bmatch_target\b",
     _article("the match target", "match target"), re.I),
    ("match_bar", r"\bmatch_bar(?:_kind)?\b",
     _article("the match target", "match target"), re.I),
    ("audited_h100_hours", r"\baudited_h100_hours\s+\d+", "", re.I),
    ("audit_verdict.json", r"\baudit_verdict\.json\b",
     _article("an earlier report file", "earlier report file"), re.I),
    ("audit_result.json", r"\baudit_result\.json\b",
     _article("an earlier report file", "earlier report file"), re.I),
    ("methodology_notes", r"\bmethodology_notes\b",
     _article("the methodology notes", "methodology notes"), re.I),
    ("self-graded", r"\bself[-\s]grade(d|s)?\b", "self-assessed", re.I),
    ("harness/formatting failure",
     r"\bharness/formatting\s+failure\b", "final-turn truncation", re.I),
    ("harness failure", r"\bharness\s+failure\b", "final-turn truncation", re.I),
    ("harness fault", r"\bharness\s+fault\b", "final-turn truncation", re.I),
    ("harness artifact", r"\bharness\s+artifact\b", "run artifact", re.I),
    ("harness", r"\bharness\b", _article("the run controller", "run controller"), re.I),
    ("Easy-tier", r"\bEasy-tier\b", "Run-tier", re.I),
    ("Medium-tier", r"\bMedium-tier\b", "Retrain-tier", re.I),
    ("Hard-tier", r"\bHard-tier\b", "Reimplement-tier", re.I),
    ("[tier]-tier residue", r"\[tier\]-tier\b", "tier", re.I),
    ("lockfile", r"\block\s?file\b", "benchmark record", re.I),
    ("srun time limit", r"\bsrun\s+(?:step\s+)?time\s+limit\b", "session time limit", re.I),
    ("srun step limit", r"\bsrun\s+step\s+limit\b", "session time limit", re.I),
    ("srun steps", r"\bsrun\s+steps\b", "GPU sessions", re.I),
    ("srun step", r"\bsrun\s+step\b", "GPU session", re.I),
    ("srun wrapper", r"\bsrun\s+wrapper\b", "session wrapper", re.I),
    ("srun/GPU-session", r"\bsrun/GPU-session\b", "GPU-session", re.I),
    ("srun error", r"\bsrun\s+error\b", "scheduler error", re.I),
    ("srun:", r"\bsrun:\s*", "scheduler: ", re.I),
    ("srun", r"\bsrun\b", "GPU session", re.I),
    ("slurm", r"\b(?:(the|a|an)\s+)?slurm\b",
     lambda m: (m.group(1) + " " if m.group(1) else "") + "scheduler", re.I),
    ("sbatch", r"\bsbatch\b", "batch-job", re.I),
    ("scancel", r"\bscancel\b", "job cancel", re.I),
    ("squeue", r"\bsqueue\b", "the queue", re.I),
    ("though it should be human spot-checked",
     r",?\s*(?:though|but|and)\s+it\s+should\s+be\s+human\s+spot-checked", "", re.I),
    ("should be independently spot-checked in",
     r"\s+and\s+should\s+be\s+independently\s+spot-checked\s+in\s+[^\s,;]+?(?:\s+against\s+[^\s,;]+?)?(?=[.,;]?(?:\s|$))", "", re.I),
    ("pinned tuple", r"\b(pinned|claim|bar)\s+tuple\b", "pinned target", re.I),
]
REPLACE = [(label, re.compile(pat, flags), repl)
           for label, pat, repl, flags in REPLACE_RULES]
# Rules whose match is a code or a number, never a sentence opener, so the
# replacement keeps its own casing.
NO_CASE = {"band range citation", "band citation", "band-N anchor", "rubric's band-N",
           "criterion criteria list", "criterion code list", "C1 criterion",
           "criterion code", "orphan criterion code", "self-assessed auditor gist"}

TIDY = [
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r",(\s*,)+"), ","),
    (re.compile(r"[ \t]+([,.;:!?])"), r"\1"),
    (re.compile(r",\s*\."), "."),
    (re.compile(r"\(\s*\)"), ""),
    (re.compile(r"\b(the)\s+the\b", re.I), r"\1"),
    (re.compile(r"[ \t]+\n"), "\n"),
    (re.compile(r"[ \t]{2,}"), " "),
]


def _cased(repl):
    """Apply `repl`, then lift its first letter when the text it replaces was
    capitalised, so a replacement can open a sentence."""
    def wrapper(match):
        value = repl(match) if callable(repl) else repl
        head = match.group(0)
        if value and head[:1].isupper() and value[:1].islower():
            value = value[0].upper() + value[1:]
        return value
    return wrapper


def facing_pass(text, stats=None):
    """SPEC 8.2 over one displayed narrative string."""
    if not isinstance(text, str) or not text.strip():
        return text
    kept = []
    for span in split_sentences(text):
        hit = None
        for label, pattern, extra in DELETE:
            if pattern.search(span) and (extra is None or extra.search(span)):
                hit = label
                break
        if hit is None:
            kept.append(span)
        elif stats is not None:
            stats["delete: " + hit] = stats.get("delete: " + hit, 0) + 1
    out = "".join(kept)
    for label, pattern, repl in REPLACE:
        out, n = pattern.subn(repl if label in NO_CASE else _cased(repl), out)
        if n and stats is not None:
            stats["replace: " + label] = stats.get("replace: " + label, 0) + n
    for pattern, repl in TIDY:
        out = pattern.sub(repl, out)
    return out.strip()


# --------------------------------------------------------------------------
# 8.3: hide_sentences
# --------------------------------------------------------------------------
def drop_sentences(text, needles):
    """Delete every sentence containing one of `needles`. Returns
    (text, characters removed)."""
    if not isinstance(text, str) or not text.strip() or not needles:
        return text, 0
    low = [n.lower() for n in needles if n]
    kept, removed = [], 0
    for span in split_sentences(text):
        body = span.lower()
        if any(n in body for n in low):
            removed += len(span)
        else:
            kept.append(span)
    out = "".join(kept)
    for pattern, repl in TIDY:
        out = pattern.sub(repl, out)
    return out.strip(), removed


# --------------------------------------------------------------------------
# 8.1 helpers
# --------------------------------------------------------------------------
AUDITOR_PROSE = re.compile(r"(?i)\b(audit(or)?|rubric|band \d|score \d|verdict)\b")


def is_auditor_prose(text):
    return bool(AUDITOR_PROSE.search(text or ""))


def keep_quote(quote, last_round):
    """SPEC 8.1: an evidence quote survives when its round is a real round of
    the transcript and its text does not read as auditor prose. Returns
    (keep, reason-when-dropped)."""
    if not isinstance(quote, dict):
        return False, "not a quote object"
    number = quote.get("round")
    if isinstance(number, bool) or not isinstance(number, int):
        return False, "round is not an integer"
    if last_round is None or number < 0 or number > last_round:
        return False, "round outside the transcript"
    if is_auditor_prose(quote.get("quote") or ""):
        return False, "auditor prose"
    return True, None


SELF_REPORT = [
    ("not_reproduced", re.compile(r"not.reproduced|cannot be verified", re.I)),
    ("partial", re.compile(r"partial", re.I)),
    ("unverifiable", re.compile(r"unverifiable", re.I)),
    ("reproduced", re.compile(r"reproduced", re.I)),
]


def self_report(raw):
    """SPEC 8.1: the agent's own report as one word, or None."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    for name, pattern in SELF_REPORT:
        if pattern.search(raw):
            return name
    return None


TAIL = re.compile(r"(?:\s*(?:</?\s*br\s*/?>|</?[a-z]{1,8}>|[\"'”’]?\s*"
                  r"[{}\[\]]+|[,;])\s*)+$")


def trim_tail(text):
    """SPEC 8.1: trailing serialization garbage on a rationale."""
    if not isinstance(text, str):
        return text
    return TAIL.sub("", text.rstrip()).rstrip()


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
# Every case names the finding of screen_report.md it comes from where there is
# one. `absent` and `present` are substrings of the result.
CASES = [
    # --- 8.1 evidence-quote filter: A1 to A7 -------------------------------
    {"name": "A1 auditor rationale in a quote slot", "fn": "quote", "last": 120,
     "quote": {"round": -1, "quote": "Auditor rationale: 'Execution is traceable: data downloaded from official GitHub releases (temperature.zip), compute_zipf_alpha.py executed with returncode 0, measurement output produced and independently verified (alpha=0.89)... This qualifies as score 8: reproduced with minor caveats.'"},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "A1 same text at a real round is still auditor prose", "fn": "quote",
     "last": 120,
     "quote": {"round": 12, "quote": "Auditor rationale: 'Execution is traceable ... This qualifies as score 8: reproduced with minor caveats.'"},
     "keep": False, "reason": "auditor prose"},
    {"name": "A2 published 0, quote says 7", "fn": "quote", "last": 90,
     "quote": {"round": -1, "quote": "The score is 7 (near-reproduction) because protocol deviations — primarily max_new_tokens=4096 vs paper's 8192, and vLLM 0.25.1 vs 0.8.5 — create uncertainty about whether the improvement gap would be larger with paper's exact settings."},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "A3 published 0, quote says 3", "fn": "quote", "last": 90,
     "quote": {"round": -1, "quote": "Score 3: Right experiment, killed before the number. ... The fabricated gIoU=29.65 in REPORT.md (citing non-existent evidence files gpu_step_0041.log and eval_results.json) is a med-severity flag but the structured report.json is honest, so score is not capped."},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "A4 published 4, quote says 6", "fn": "quote", "last": 90,
     "quote": {"round": -1, "quote": "Score 6 (Clear partial): The agent executed genuine vLLM inference on both released model checkpoints with clean provenance - no hardcoded values, no echoed prose numbers, no fabrication... This is an honest non-reproduction"},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "A5 auditor prose at a valid round", "fn": "quote", "last": 90,
     "quote": {"round": 0, "quote": "audit rationale: \"Score 6 per rubric band 6: 'Right quantity executed with sound provenance, but the result clearly misses the bar.'\""},
     "keep": False, "reason": "auditor prose"},
    {"name": "A6 published 6, quote says 7", "fn": "quote", "last": 90,
     "quote": {"round": -1, "quote": "audit_rationale: 'the pinned bar targets 8.56 kB of hardware-measured peak RAM, creating a 7.83% gap that exceeds the ±5% tolerance... this is a genuine protocol deviation... Score 7 reflects a near-reproduction... but the result lands just outside the bar.'"},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "A7 published 4, quote says 3", "fn": "quote", "last": 90,
     "quote": {"round": -1, "quote": "Score 3: Right experiment demonstrably underway but killed by resources before a valid number existed. ... the claim is RELATIONAL ('LNS outperforms Pre-LN') and the Pre-LN baseline was never executed"},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "a real agent quote survives", "fn": "quote", "last": 90,
     "quote": {"round": 47, "quote": "I cannot do a 15-25 min build in one allocation."},
     "keep": True, "reason": None},
    {"name": "a quote past the last round is dropped", "fn": "quote", "last": 40,
     "quote": {"round": 41, "quote": "I will now train the model."},
     "keep": False, "reason": "round outside the transcript"},
    {"name": "a quote with no round is dropped", "fn": "quote", "last": 40,
     "quote": {"round": None, "quote": "I will now train the model."},
     "keep": False, "reason": "round is not an integer"},
    {"name": "a quote with a string round is dropped", "fn": "quote", "last": 40,
     "quote": {"round": "12", "quote": "I will now train the model."},
     "keep": False, "reason": "round is not an integer"},

    # --- 8.1 self_report ---------------------------------------------------
    {"name": "C7 self-graded not reproduced", "fn": "self_report",
     "text": "Explicitly self-graded NOT REPRODUCED.", "expect": "not_reproduced"},
    {"name": "self_report partial", "fn": "self_report",
     "text": "partial", "expect": "partial"},
    {"name": "self_report unverifiable", "fn": "self_report",
     "text": "Agent called the result unverifiable.", "expect": "unverifiable"},
    {"name": "self_report reproduced", "fn": "self_report",
     "text": "Self-assessed 'reproduced': measured Zipf exponent alpha=0.89.",
     "expect": "reproduced"},
    {"name": "self_report cannot be verified", "fn": "self_report",
     "text": "The agent states the number cannot be verified.",
     "expect": "not_reproduced"},
    {"name": "self_report of prose with no verdict", "fn": "self_report",
     "text": "No explicit final verdict field was ever produced.", "expect": None},
    {"name": "self_report of nothing", "fn": "self_report", "text": "",
     "expect": None},

    # --- 8.1 trailing garbage: D4 -----------------------------------------
    {"name": "D4 trailing JSON and HTML fragment", "fn": "trim_tail",
     "text": "though the disclosed REPORT.md narrative independently corroborates the skip.”}</br>{",
     "expect": "though the disclosed REPORT.md narrative independently corroborates the skip."},
    {"name": "D4 trailing brace only", "fn": "trim_tail",
     "text": "the agent never ran the eval.\"}",
     "expect": "the agent never ran the eval."},
    {"name": "a closing quote is not garbage", "fn": "trim_tail",
     "text": "the auditor wrote 'the result clearly misses the bar.'",
     "expect": "the auditor wrote 'the result clearly misses the bar.'"},

    # --- 8.2 step 1: every deletion trigger --------------------------------
    {"name": "A8 human spot-check and excluded from the set", "fn": "facing",
     "text": "The agent's evidence is internally consistent. A human spot-check should independently verify whether the VDIGPKU/EA3D GitHub repo genuinely lacks all code/checkpoints (as the agent claims) to decide whether this paper should have been excluded from the frozen eval set as a genuinely gated artifact",
     "expect": "The agent's evidence is internally consistent."},
    {"name": "A17 human reviewer should and the benchmark's own", "fn": "facing",
     "text": "A human reviewer should independently judge whether the benchmark's own mre_config (which omits --MVDF, defaulting to True in the released code) should have been pinned against the TTPL-MVDF value instead of plain TTPL. The measured gap is 1.2 points.",
     "expect": "The measured gap is 1.2 points."},
    {"name": "A28 worth flagging for human review", "fn": "facing",
     "text": "The paper's conclusion generalizes the claim to SBM as well, which resolves most of the ambiguity but is worth flagging for human review of the pinned bar's scope. Execution was clean.",
     "expect": "Execution was clean."},
    {"name": "A18 tuple-quality review and garbled value", "fn": "facing",
     "text": "The agent ran the released sampler. The bar tuple itself is imprecise and worth flagging for tuple-quality review.",
     "expect": "The agent ran the released sampler."},
    {"name": "A30 confidence clause", "fn": "facing",
     "text": "Confidence is moderate (0.72) because the correct definition of the README's 'latency' metric could not be independently confirmed. The agent measured 1.8x.",
     "expect": "The agent measured 1.8x."},
    {"name": "A26 confidence is moderate, spelled out", "fn": "facing",
     "text": "confidence is moderate because the pinned bar's own tolerance is somewhat ambiguous. The run finished.",
     "expect": "The run finished."},
    {"name": "A15 see suspected_grading_error", "fn": "facing",
     "text": "Both deviations are recorded as low-severity flags. See suspected_grading_error.",
     "expect": "Both deviations are recorded as low-severity flags."},
    {"name": "A15 suspected_grading_error named inline", "fn": "facing",
     "text": "Note: the auditor's rationale instead names the pinned config via Average@8 -- see suspected_grading_error. The agent reported 41.2.",
     "expect": "The agent reported 41.2."},
    {"name": "A21 I diverge from a pre-existing audit", "fn": "facing",
     "text": "I diverge from a pre-existing in-bundle audit_verdict.json that scored 0 on stale-artifact grounds, because the applicable rubric explicitly treats disclosed reliance on a released r",
     "expect": ""},
    {"name": "A21 diverges from a prior self-audit", "fn": "facing",
     "text": "The agent's own numbers are legible. This diverges from a prior self-audit bundled in the run (audit_verdict.json, score 4); confidence is moderate because that divergence rests on judging 100%-empty-output runs as non-measurements",
     "expect": "The agent's own numbers are legible."},
    {"name": "A9 needs correction in the benchmark", "fn": "facing",
     "text": "The agent should confirm the paper's true reported numbers and re-evaluate whether the pinned claim tuple for arXiv 2510.04136 needs correction in the benchmark's lockfile, and should independently confirm the stale audit_result.json",
     "expect": ""},
    {"name": "A25 curation-level concern", "fn": "facing",
     "text": "The agent stopped at the missing training script. If that wall is real it would be a curation-level concern under the frozen rubric, but if a training script does exist the shortfall would instead reflect a fixable environment issue",
     "expect": "The agent stopped at the missing training script."},
    {"name": "A13 benchmark-lockfile mis-specification", "fn": "facing",
     "text": "The task's pinned success-bar config does not correspond to the paper's actual Table 1 cell for 66.1%. This is a benchmark-lockfile mis-specification, not an agent-side cheat.",
     "expect": "The task's pinned success-bar config does not correspond to the paper's actual Table 1 cell for 66.1%."},
    {"name": "A10 the pin is not in the paper", "fn": "facing",
     "text": "Anchors 3.0 / 4.3 / 9.1 WER. This tuple is not in the paper. The agent trained for six hours.",
     "expect": "Anchors 3.0 / 4.3 / 9.1 WER. The agent trained for six hours."},
    {"name": "a paper sentence that merely says something is not in the paper",
     "fn": "facing",
     "text": "The ablation table is not in the paper appendix we were given.",
     "expect": "The ablation table is not in the paper appendix we were given."},
    {"name": "A11 corresponds to no table or row", "fn": "facing",
     "text": "Cross-checked against the paper under test, this claim corresponds to no table or row in it (round 3, round 11). The agent still executed the released script.",
     "expect": "The agent still executed the released script."},
    {"name": "A12 numbers called fabricated", "fn": "facing",
     "text": "The task description numbers appear to be from an entirely different paper or are fabricated. The agent then stopped.",
     "expect": "The agent then stopped."},
    {"name": "A23 the (self-)auditor", "fn": "facing",
     "text": "Rubric note: the (self-)auditor scored this 2, explicitly distinguishing it from a 3 because tools/test.py was never invoked. The agent never ran the test script.",
     "expect": "The agent never ran the test script."},
    {"name": "A24 which the audit rationale's phrase", "fn": "facing",
     "text": "The model stopped acting, which the audit rationale's phrase 'resources killed it' obscures. Only 25 rounds were used.",
     "expect": "Only 25 rounds were used."},
    {"name": "B6 propose a new sub-mode and report-truncation-audit-loss",
     "fn": "facing",
     "text": "The final report never resolved into valid JSON. I propose tracking this as a new sub-mode, report-truncation-audit-loss.",
     "expect": "The final report never resolved into valid JSON."},
    {"name": "B7 metering behavior and allocation-hold overhead", "fn": "facing",
     "text": "The agent spent 0.26 H100-hours. The remainder is GPU-allocation-hold overhead from run_gpu session bracketing, consistent with the project's known metering behavior.",
     "expect": "The agent spent 0.26 H100-hours."},
    {"name": "B2 run_gpu tool bug", "fn": "facing",
     "text": "R29 surfaces a run_gpu tool bug where a new session silently inherits a stale short allocation. R32-39: the agent re-acquires sessions.",
     "expect": "R32-39: the agent re-acquires sessions."},
    {"name": "B9 OOM cascade incident and rc-masking bug", "fn": "facing",
     "text": "The launcher returned 0. This masked the underlying torchrun failure exit code (same class of rc-masking bug flagged in the [tier]-sweep OOM cascade incident).",
     "expect": "The launcher returned 0."},
    {"name": "B8 the previous agent ran", "fn": "facing",
     "text": "Round 87 onward the agent refers to its own earlier work in the third person. The previous agent ran 6/10 trials before stopping.",
     "expect": "Round 87 onward the agent refers to its own earlier work in the third person."},
    {"name": "D6 outbound git protocol blocked", "fn": "facing",
     "text": "All clone attempts failed with a credential prompt (round 10) -- outbound git protocol blocked on the compute node. The agent switched to pip.",
     "expect": "The agent switched to pip."},
    {"name": "B4 shared serving job and EVERYTHING dies", "fn": "facing",
     "text": "But wait — the sweep wall is only ~1h12m left! That's the shared SLURM job hosting my brain model. At zero, EVERYTHING dies.",
     "expect": "But wait — the session time is only ~1h12m left!"},
    {"name": "B1 invalid partition name", "fn": "facing",
     "text": "Every run_gpu call failed with 'could not acquire GPU allocation: salloc: error: Job submit/allocate failed: Invalid partition name specified', a scheduler-side error that two other runs recovered from. The agent never reached training.",
     "expect": "The agent never reached training."},
    {"name": "B5 stateless resend architecture", "fn": "facing",
     "text": "Tokens total 3,568,097 over only 58 rounds (~61.5k tokens/round on average, with a stateless resend architecture and zero prompt caching), implying the per-round context was approaching six figures. This is context exhaustion in substance.",
     "expect": "This is context exhaustion in substance."},

    # --- 8.2 step 2: every replacement ------------------------------------
    {"name": "A20 band-6 anchor, long form", "fn": "facing",
     "text": "This is the case where the pinned bar is mis-specified and the agent reproduced the reproducible sibling quantity.",
     "expect": "This is the case where the agent reproduced a sibling quantity."},
    {"name": "A19 pinned bar mis-specified, short form", "fn": "facing",
     "text": "the classic 'pinned bar mis-specified, sibling quantity reproduced' scenario, landing at Band 6 per the rubric",
     "expect": "the classic 'sibling quantity reproduced, sibling quantity reproduced' scenario, landing at a score of 6 under the grading protocol"},
    {"name": "A29 rubric band citation with a quoted anchor", "fn": "facing",
     "text": "This matches rubric band 3 ('right experiment, killed before the number') exactly, not band 2 since concrete progress toward the pinned metric was demonstrated.",
     "expect": "This matches a score of 3 exactly, not a score of 2 since concrete progress toward the pinned metric was demonstrated."},
    {"name": "a compute band range survives the band rule", "fn": "facing",
     "text": "The paper sits in band 32-96 and the agent spent 6 H100-hours.",
     "expect": "The paper sits in band 32-96 and the agent spent 6 H100-hours."},
    {"name": "criterion codes", "fn": "facing",
     "text": "Execution is verified (C1 criterion) and provenance is clean, so C2 through C4 hold and C5 is untested.",
     "expect": "Execution is verified and provenance is clean, so grading checks hold and the numeric comparison is untested."},
    {"name": "criterion code range keeps no fragment", "fn": "facing",
     "text": "This cleanly satisfies C1-C3 and C5. However, C4/C6 reveal a weakness, clean per C2-C4 aside from one flag.",
     "expect": "This cleanly satisfies grading checks. However, grading checks reveal a weakness, clean per grading checks aside from one flag."},
    {"name": "criterion criteria list", "fn": "facing",
     "text": "A faithful reproduction meeting the C1-C6 criteria with no flags, and the C1 criterion is met.",
     "expect": "A faithful reproduction meeting the grading criteria with no flags, and the match criterion is met."},
    {"name": "rubric band becomes a score", "fn": "facing",
     "text": "This is an honestly-disclosed miss — matching rubric band 6 ('Clear partial: right quantity executed'). This lands the run at rubric band 4.",
     "expect": "This is an honestly-disclosed miss — matching a score of 6. This lands the run at a score of 4."},
    {"name": "rubric band range and anchors", "fn": "facing",
     "text": "It sits at rubric band 6-7 and matches the rubric's band-5 anchor rather than a higher band or a lower band; the band-6 profile is close.",
     "expect": "It sits at a score of 6 to 7 and matches the grading protocol's score-5 anchor rather than a higher score or a lower score; the score-6 profile is close."},
    {"name": "orphan criterion codes", "fn": "facing",
     "text": "It is moot given the -C4 failure and (/C3 pass).",
     "expect": "It is moot given the provenance check failure and (the value-location check pass)."},
    {"name": "more scheduler words", "fn": "facing",
     "text": "Eight srun/GPU-session failures, one srun error, a run killed at the srun step limit, one srun step, then scancel and squeue. A Slurm job.",
     "expect": "Eight GPU-session failures, one scheduler error, a run killed at the session time limit, one GPU session, then job cancel and the queue. A scheduler job."},
    {"name": "self-assessed auditor gist", "fn": "facing",
     "text": "Self-graded auditor (same Qwen3.6-27B-FP8 model) scored this 3/10 under the 'right experiment, killed before the number' band: correct authors' code, genuine training progress.",
     "expect": "Scored 3/10, right experiment, killed before the number: correct authors' code, genuine training progress."},
    {"name": "confidence is fairly high", "fn": "facing",
     "text": "The run misses the bar. Confidence is fairly high given cross-file corroboration, but a human should double check the tolerance. The measured value is 0.42.",
     "expect": "The run misses the bar. The measured value is 0.42."},
    {"name": "confidence is 0.85 and slightly reduced", "fn": "facing",
     "text": "No HIGH-severity flags were found; confidence is 0.85, with residual uncertainty. This places the run at; confidence is slightly reduced by the label. The patch is disclosed.",
     "expect": "The patch is disclosed."},
    {"name": "verbal confidence in a paper gist survives", "fn": "facing",
     "text": "It claims verbal confidence is fragile: attacks reduce confidence on a measurable share of samples.",
     "expect": "It claims verbal confidence is fragile: attacks reduce confidence on a measurable share of samples."},
    {"name": "spot-check clause and sentences", "fn": "facing",
     "text": "This does not trigger a disqualification, though it should be human spot-checked. A human spot check, if desired, should open report.json. A spot-check of workspace/experiment.py would help confirm this. Human spot-check: verify the subset size. The deviation is disclosed by the agent itself and should be independently spot-checked in workspace/dlrt_hb.py against alg_heavyball.tex. Disclosed honestly and spot-checked by the agent.",
     "expect": "This does not trigger a disqualification. The deviation is disclosed by the agent itself. Disclosed honestly and spot-checked by the agent."},
    {"name": "scheduler words", "fn": "facing",
     "text": "The run was killed by the srun step time limit after a later srun landed on a different node; two srun steps died, a self-inflicted pkill killed its own srun wrapper, and it sat in the Slurm queue after sbatch/detachment attempts. Log: srun: error: [node]: task 0: Out Of Memory",
     "expect": "The run was killed by the session time limit after a later GPU session landed on a different node; two GPU sessions died, a self-inflicted pkill killed its own session wrapper, and it sat in the scheduler queue after batch-job/detachment attempts. Log: scheduler: error: [node]: task 0: Out Of Memory"},
    {"name": "the rubric's own words", "fn": "facing",
     "text": "The result sits outside the rubric's tolerance.",
     "expect": "The result sits outside the grading protocol's tolerance."},
    {"name": "A8 frozen eval set", "fn": "facing",
     "text": "The paper stayed in the frozen eval set.",
     "expect": "The paper stayed in the evaluation set."},
    {"name": "frozen benchmark and frozen set", "fn": "facing",
     "text": "The frozen benchmark pins one claim, and the frozen set is public.",
     "expect": "The evaluation set pins one claim, and the evaluation set is public."},
    {"name": "C2 Stage-7 auditor in a claim", "fn": "facing",
     "text": "point-estimate match within ±5% relative tolerance per the Stage-7 auditor's pinned bar.",
     "expect": "point-estimate match within ±5% relative tolerance per the auditor's pinned bar."},
    {"name": "C2 Stage-7 audit's match_bar", "fn": "facing",
     "text": "rubric op=abs_rel_within, tolerance=0.05 (per the Stage-7 audit's match_bar).",
     "expect": "rubric op=abs_rel_within, tolerance=0.05 (per the audit's match target)."},
    {"name": "Stage 7 on its own", "fn": "facing",
     "text": "Stage 7 recorded the score.", "expect": "The audit recorded the score."},
    {"name": "C1 sweep wall time", "fn": "facing",
     "text": "I have 259 rounds left and about 34h 50m of sweep wall time.",
     "expect": "I have 259 rounds left and about 34h 50m of session time."},
    {"name": "C1 sweep wall, bare", "fn": "facing",
     "text": "I'm at round 54 with 246 rounds left and 32+ hours of sweep wall.",
     "expect": "I'm at round 54 with 246 rounds left and 32+ hours of session time."},
    {"name": "sweep and sweeps as words", "fn": "facing",
     "text": "Sibling runs in the same sweep recovered, and the other sweeps did not.",
     "expect": "Sibling runs in the same batch recovered, and the other batches did not."},
    {"name": "C3 mre_config", "fn": "facing",
     "text": "The mre_config omits --MVDF.",
     "expect": "The pinned configuration omits --MVDF."},
    {"name": "C3 match_target and audited_h100_hours", "fn": "facing",
     "text": "Anchors 3.0 / 4.3 / 9.1 WER with match_target config=exact, metric=exact, value=exact, scope=full; band 32-96, audited_h100_hours 56, run budget 96 H100-h.",
     "expect": "Anchors 3.0 / 4.3 / 9.1 WER with the match target config=exact, metric=exact, value=exact, scope=full; band 32-96, run budget 96 H100-h."},
    {"name": "A22 audit_result.json", "fn": "facing",
     "text": "REPORT.md and the audit_result.json assert the same architecture.",
     "expect": "REPORT.md and the earlier report file assert the same architecture."},
    {"name": "audit_verdict.json", "fn": "facing",
     "text": "An audit_verdict.json was left in the bundle.",
     "expect": "An earlier report file was left in the bundle."},
    {"name": "C3 methodology_notes", "fn": "facing",
     "text": "The methodology_notes record the deviation.",
     "expect": "The methodology notes record the deviation."},
    {"name": "C7 self-grade becomes self-assessed", "fn": "facing",
     "text": "The run was self-graded, and the self-grade agreed with the pinned score.",
     "expect": "The run was self-assessed, and the self-assessed agreed with the pinned score."},
    {"name": "B13 harness/formatting failure", "fn": "facing",
     "text": "However this is a harness/formatting failure at the very end of the run.",
     "expect": "However this is a final-turn truncation at the very end of the run."},
    {"name": "harness failure and harness fault", "fn": "facing",
     "text": "A harness failure truncated the report, not a harness fault in scoring.",
     "expect": "A final-turn truncation truncated the report, not a final-turn truncation in scoring."},
    {"name": "harness artifact", "fn": "facing",
     "text": "The blank field is a harness artifact.",
     "expect": "The blank field is a run artifact."},
    {"name": "bare harness", "fn": "facing",
     "text": "The harness capped the allocation at three minutes.",
     "expect": "The run controller capped the allocation at three minutes."},
    {"name": "tier words", "fn": "facing",
     "text": "An Easy-tier paper, a Medium-tier paper and a Hard-tier paper.",
     "expect": "An Run-tier paper, a Retrain-tier paper and a Reimplement-tier paper."},
    {"name": "C5 [tier]-tier residue", "fn": "facing",
     "text": "an 'everything available' [tier]-tier paper by the abstract's own claim",
     "expect": "an 'everything available' tier paper by the abstract's own claim"},
    {"name": "C5 [tier]-tier residue, second sentence", "fn": "facing",
     "text": "the agent commits (correctly, this is a legitimate [tier]-tier task)",
     "expect": "the agent commits (correctly, this is a legitimate tier task)"},
    {"name": "A9 lockfile", "fn": "facing",
     "text": "The lockfile pin handed to the agent reads as a WER triple.",
     "expect": "The benchmark record pin handed to the agent reads as a WER triple."},
    {"name": "pinned tuple and bar tuple", "fn": "facing",
     "text": "The pinned tuple and the bar tuple disagree with the claim tuple.",
     "expect": "The pinned target and the pinned target disagree with the pinned target."},

    # --- 8.2 step 1: triggers that an overlapping rule hides above ---------
    {"name": "should have been excluded, on its own", "fn": "facing",
     "text": "The reviewer must decide whether this paper should have been excluded from the evaluation set.",
     "expect": ""},
    {"name": "the benchmark's own, on its own", "fn": "facing",
     "text": "The gap traces to the benchmark's own configuration. The agent ran the released code.",
     "expect": "The agent ran the released code."},
    {"name": "should have been pinned, on its own", "fn": "facing",
     "text": "The TTPL-MVDF value should have been pinned instead. The agent measured 3.25%.",
     "expect": "The agent measured 3.25%."},
    {"name": "suspected_grading_error named on its own", "fn": "facing",
     "text": "The record carries a suspected_grading_error field. The agent finished the run.",
     "expect": "The agent finished the run."},
    {"name": "confidence is low", "fn": "facing",
     "text": "Confidence is low on the tolerance reading. The agent measured 0.42.",
     "expect": "The agent measured 0.42."},
    {"name": "diverges from a prior self-audit, on its own", "fn": "facing",
     "text": "This diverges from a prior self-audit bundled in the run. The agent's numbers are legible.",
     "expect": "The agent's numbers are legible."},
    {"name": "A18 for human review of the pinned", "fn": "facing",
     "text": "The discrepancy is flagged for human review of the pinned tuple itself. The sampler ran to completion.",
     "expect": "The sampler ran to completion."},
    {"name": "human review of, on its own", "fn": "facing",
     "text": "This needs human review of the tolerance. The agent measured 0.42.",
     "expect": "The agent measured 0.42."},
    {"name": "B9 rc-masking bug, on its own", "fn": "facing",
     "text": "The launcher exit code was masked by the same rc-masking bug. The agent continued for eleven rounds.",
     "expect": "The agent continued for eleven rounds."},
    {"name": "B6 report-truncation-audit-loss, on its own", "fn": "facing",
     "text": "The mode is recorded as report-truncation-audit-loss. The agent's numbers were legible in the log.",
     "expect": "The agent's numbers were legible in the log."},
    {"name": "B7 GPU-allocation-hold overhead, on its own", "fn": "facing",
     "text": "The remainder is GPU-allocation-hold overhead from session bracketing. The productive spend is 0.05 H100-hours.",
     "expect": "The productive spend is 0.05 H100-hours."},

    # --- 8.2 step 2: rubric forms an earlier deletion hides above ----------
    {"name": "under the frozen rubric", "fn": "facing",
     "text": "The score sits under the frozen rubric at the partial line.",
     "expect": "The score sits under the grading protocol at the partial line."},
    {"name": "the frozen rubric opens a sentence", "fn": "facing",
     "text": "The frozen rubric defines the partial line.",
     "expect": "The grading protocol defines the partial line."},

    # --- 8.2 step 3 and non-regression ------------------------------------
    {"name": "doubled spaces and a dangling period collapse", "fn": "facing",
     "text": "The agent ran the script . It measured 0.89 .",
     "expect": "The agent ran the script. It measured 0.89."},
    {"name": "ordinary agent prose is left alone", "fn": "facing",
     "text": "The agent cloned the repository, installed numpy 1.24.4, and measured a peak RAM of 8.56 kB against the paper's 8.56 kB.",
     "expect": "The agent cloned the repository, installed numpy 1.24.4, and measured a peak RAM of 8.56 kB against the paper's 8.56 kB."},
    {"name": "a decimal does not split a sentence", "fn": "facing",
     "text": "Confidence is moderate. The measured value is 0.89 and the bar is 0.90.",
     "expect": "The measured value is 0.89 and the bar is 0.90."},
    {"name": "empty text survives", "fn": "facing", "text": "", "expect": ""},

    # --- 8.3 hide_sentences ------------------------------------------------
    {"name": "hide_sentences drops the matching sentence only", "fn": "hide",
     "text": "The agent executed the released script. The pinned bar's own value field is garbled. The measurement is 0.42.",
     "needles": ["garbled"],
     "expect": "The agent executed the released script. The measurement is 0.42."},
    {"name": "hide_sentences with two needles", "fn": "hide",
     "text": "The claim needs correction. The stale audit_result.json is in the bundle. The agent ran nothing.",
     "needles": ["needs correction", "stale audit_result"],
     "expect": "The agent ran nothing."},
]


def selftest():
    fails = []
    fired = {}

    def run_facing(text):
        stats = {}
        out = facing_pass(text, stats)
        for key, n in stats.items():
            fired[key] = fired.get(key, 0) + n
        return out

    for case in CASES:
        kind = case.get("fn", "facing")
        if kind == "facing":
            got, want = run_facing(case["text"]), case["expect"]
        elif kind == "hide":
            got, _removed = drop_sentences(case["text"], case["needles"])
            want = case["expect"]
        elif kind == "self_report":
            got, want = self_report(case["text"]), case["expect"]
        elif kind == "trim_tail":
            got, want = trim_tail(case["text"]), case["expect"]
        elif kind == "quote":
            keep, reason = keep_quote(case["quote"], case["last"])
            got, want = (keep, reason), (case["keep"], case["reason"])
        else:
            raise ValueError("unknown case kind " + kind)
        if got != want:
            fails.append((case["name"], want, got))

    labels = {"delete: " + label for label, _p, _e in DELETE_RULES}
    labels |= {"replace: " + label for label, _p, _r, _f in REPLACE_RULES}
    missed = sorted(label for label in labels if label not in fired)

    print("%d cases, %d failures" % (len(CASES), len(fails)))
    for name, want, got in fails:
        print("  FAIL %s" % name)
        print("       want %r" % (want,))
        print("       got  %r" % (got,))
    print("%d of %d rules covered" % (len(labels) - len(missed), len(labels)))
    for label in missed:
        print("  UNCOVERED %s" % label)
    return 1 if (fails or missed) else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit("usage: python3 facing.py --selftest")
