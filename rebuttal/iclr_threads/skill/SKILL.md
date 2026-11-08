---
name: iclr-review
description: Use when drafting or revising an ICLR or ML-conference author response, rebuttal, or reply to reviewers.
---

# ICLR author responses

These rules come from 244 ICLR 2025 threads where a reviewer moved from reject (5 or lower) to accept (6 or higher) after the rebuttal ("raised") and 48 where the reviewer replied and stayed at reject ("unchanged"). "Raised 66%, unchanged 44%" means the share of threads in each group with the feature. Only new experiment and summary of revisions show a gap with non-overlapping intervals; every other rule is a hypothesis or a house rule. With 32 features tested at 95%, one or two chance gaps are expected, and every gap is a correlation. Each bracket names its basis: corpus, suggestive (gap of 15 points or more, overlapping intervals), no corpus support (gap kept as context), a source, coder notes on named threads, or a house rule set by the skill's author. Examples, phrase lists and sources are in reference.md.

ICLR 2027 uses a 4-point scale: read "5" as the score just below the accept line and "6" as the accept line; confirm it in the 2027 Reviewer Guide.

**If rules conflict:** corpus rules (3, 11) come first, then house rules on tone (4, 8), then suggestive rules (12, 13). Cut no-support rules first when space is short.

**Revising a draft:** skip rules 1 and 2, then check rules 3, 4, 5, 10, 11 and 19 in that order.

## Before writing

1. Focus on the reviewer just below the accept line and the one furthest below the others [source: Kargaran et al. 2025; Gao et al. 2019; the corpus cannot test it].
2. Put every reviewer point in one sheet, mark which answers need a new run, and start those runs first [source: Parikh, Batra and Lee 2020, search excerpts only].

## The opening

3. Thank the reviewer in one sentence, then list the changes as bullets, one change per bullet with its location in the revised PDF, uploaded with changes in color. A concession sits inside the bullet that names its fix [corpus: summary of revisions, raised 96%, unchanged 79%; putting it first is a house rule].

## Conceding

4. House rule: any sentence that judges the paper or its authors also names the change. Frame: "The paper said A; the code (or data, or proof) does B; we changed C at D." "We agree with your comment" is fine with the change in the same or next sentence; "You are right ... our paper overstated" or "We rushed" standing alone is banned [house rule; the corpus shows no penalty for blunt admissions, raised 12%, unchanged 6%; any concession 94%, 96%].
5. When a reviewer flags an overclaim, reword it everywhere, show old and new phrasing as a table in the reply, and mark the new wording in color in the PDF. When the code does less than described, weaken the claim and, where a run can measure the gap, add that measurement too [coder notes on raised threads 2QdsjiNXgj, eXB5TCrAu9, tkqNDbukWW].
6. Add a remaining limitation to the Limitations section and give its location [no corpus support: raised 7%, unchanged 2%].

## Disagreeing

7. Ground each disagreement in a number, figure, definition or new run [no corpus support: raised 64%, unchanged 56%].
8. House rule: keep the tone level and drop flat assertions [assertive raised 45%, unchanged 58%, intervals overlap].
9. Never tell a reviewer they misread. When several misread a point, rewrite the text [source: Soto Valero 2022].
10. Write the answer sentence in the reply, then its location as Section, page and line. A pointer alone is enough only with the target sentence quoted beside it [no corpus support: bare pointers raised 16%, unchanged 23%].

## Evidence

11. Answer empirical doubts with new experiments [corpus: raised 66%, unchanged 44%].
12. Run the reviewer's named baseline under your method's settings [suggestive: raised 24%, unchanged 8%].
13. Report results as numbers in a table inside the reply [suggestive: raised 52%, unchanged 35%; likely overlaps rule 11].
14. Do not count on citations, theory or ablations alone [citation raised 28%, unchanged 35%; theory 14%, 15%; ablation 24%, 21%].

## Structure and length

15. Give each point a heading quoting it briefly [no corpus support: raised 90%, unchanged 79%].
16. Answer each point in one to three sentences plus its location, with a table only for numbers [house rule; median 950 author words in both groups].
17. Keep the revision recognizably the same paper [ICLR 2026 Author Guide; unchanged thread 7BDUTI6aS7].

## Follow-ups

18. Answer each reviewer message that raises a point with new content [house rule; median author posts 4 and 3, untested].
19. Post each promised run or upload in the thread once it exists, with a dated notice of what changed and where [coder notes: ln6QnzBd8o, ablation never posted; UG62fwmOxZ, reviewer treated the upload as missing].
20. To a silent reviewer, with nothing new to report, send one civil reminder line naming what changed and asking for no score [house rule; reminders 38% in both groups].

## What to avoid

21. Deferring a requested run or change that fits in the discussion period; when deferring, say why and what you did now [qualitative: unchanged BfI0D1ci9r, later withdrawn, and OnBCQgi2LY; raised dRXxFEY8ZE also deferred].
22. Assurances and novelty claims with no new evidence [coder notes on unchanged mBJF0p9yRR and PflweLMInP].
