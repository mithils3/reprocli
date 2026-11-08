---
name: iclr-review
description: Use when drafting or revising an ICLR or ML-conference author response, rebuttal, or reply to reviewers.
---

# ICLR author responses

The rules come from 441 ICLR 2025 review threads. In 244 the reviewer moved from 5 or lower to 6 or higher after the discussion ("raised"), and in 197 the reviewer replied and stayed at 5 or lower ("unchanged"). Two kinds of measurement back them. Regex counts over the author posts (style_stats.md) never see the outcome. LLM coding (blind_stats.md) was done on copies with the group, scores, reviewer follow-ups and score-change sentences removed, with both groups mixed in every batch of ten. A bracket like [+11, +1 to +20] gives the raised-minus-unchanged gap in points and its 95% interval. "Corpus" marks a gap whose interval excludes zero. Every gap is a correlation: a concern that a run can fix may produce both the new run and the raise. With about 60 features tested, two or three chance gaps are expected. Other brackets name a source, coder notes on named threads, or a house rule set by the skill's author.

Files: style.md covers register, openings, concessions, disagreement wording and layout, with verbatim examples. concerns.md gives the move that went with raised threads for each kind of reviewer concern. stats.md holds the full tables. reference.md holds sources, method and older examples.

ICLR 2027 uses a 4-point scale: read "5" as the score just below the accept line and "6" as the accept line, and confirm it in the 2027 Reviewer Guide.

**If rules conflict:** corpus rules come first, then house rules on tone (6, 10), then the rest. **Revising a draft:** skip rules 1 and 2, then check 3, 6, 9, 10, 12 and 14 in that order.

## Before writing

1. Focus on the reviewer just below the accept line and on the one furthest below the others [source: Kargaran et al. 2025; Gao et al. 2019].
2. Put every reviewer point in one sheet, look up its concern type in concerns.md, mark which answers need a new run, and start those runs first [house rule; runs carry the largest gaps below].

## The opening

3. Thank the reviewer in one sentence, then list the changes as bullets, one change per bullet with its location in the revised PDF [corpus for the list: a summary of revisions in some author post, 53% against 43%, +11, +1 to +20; its place at the top is a house rule, since the opening move itself shows no gap: thanks then changes 10% against 7%].
4. Upload the revised PDF with changes marked, and point to it [corpus: a pointer to revised text, 75% against 63%, +12, +3 to +20].
5. Give every point its own label or heading, such as "W1" with a short paraphrase [corpus: 91% against 83%, +9, +2 to +15]. Quoting the reviewer in full adds nothing measurable (74% against 73%).

## Conceding

6. House rule: a sentence that judges the paper or its authors also names the change. Frame: "The paper said A; the code (or data, or proof) does B; we changed C at D." "We agree" is fine with the change in the same or next sentence. "You are right ... our paper overstated" or "We rushed" standing alone is banned. The corpus shows no penalty either way (blunt admission 4% against 7%, −3, −8 to +1), so this rule rests on the author's judgment.
7. When a reviewer flags an overclaim, reword it everywhere, show old and new phrasing in the reply, and mark the new wording in the PDF. When the code does less than described, weaken the claim and, where a run can measure the gap, add that measurement [coder notes on raised threads 2QdsjiNXgj, eXB5TCrAu9, tkqNDbukWW; claim_overstated in concerns.md].

## Evidence

8. Answer empirical doubts with a new experiment or ablation [corpus: new experiment in the thread 62% against 52%, +11, +1 to +20; ablation 29% against 16%, +13, +5 to +20; per point, 64% of points answered by a new experiment sit in raised threads against 54% over all points].
9. Put results in the reply as numbers in a table [corpus: tables 46% against 35%, +11, +2 to +20; numbers per 1,000 author words 46.7 against 37.0, +9.8, +2.6 to +15.7]. Tables usually carry the new runs, so this overlaps rule 8.
10. Do not answer a doubt with clarification alone when a number can answer it [corpus: threads where coders listed clarification among the evidence, 61% against 73%, −12, −20 to −3; per point, answers with numbers sit in raised threads 63% of the time against 51% without].
11. Run the reviewer's named baseline under your settings [concerns.md, missing_baseline: new experiment 65% raised against 33% to 38% for disagreeing, with intervals that touch].

## Disagreeing

12. Disagree with a fact and keep the tone level. Avoid flat assertion and dismissal [corpus: assertive disagreement 66% against 77%, −11, −19 to −2; dismissive 9% against 18%, −9, −15 to −2; the regex for "disagree" and "misunderstand" 14% against 25%]. Polite disagreement with evidence shows no gap (62% against 56%).
13. Disagree only where you must: points answered by disagreement sit in raised threads at 43% (35 to 51) against the 54% baseline, with or without evidence. Concede and scope what you can, and save disagreement for the point you will not give up.
14. Write the answer sentence in the reply, then its location as section, page and line [per point: location given 61% raised against 50% without].
15. Never tell a reviewer they misread. When several misread a point, rewrite the text [source: Soto Valero 2022].

## Length and follow-ups

16. Give a substantive point a full answer of 150 words or more with its number and location [per point: 64% raised at 150 words or more against 49% below; long answers also carry the runs, so read this with rule 8]. Never leave a major point unanswered, although both groups rarely do (3% against 4%).
17. Avoid a terse reply [corpus: terse first post 1% against 7%, −6, −11 to −3].
18. Answer each reviewer message that raises a point with new content, and post each promised run once it exists, with a short notice of what changed and where [corpus: more than one author post 92% against 86%, +6, +1 to +13; coder notes: ln6QnzBd8o ablation never posted, UG62fwmOxZ upload treated as missing].
19. To a silent reviewer, with nothing new to report, send one civil reminder line naming what changed, and ask for no score [house rule; reminders 48% against 53% and score asks 7% against 7% show no gap].
20. Keep the revision recognizably the same paper [ICLR 2026 Author Guide].

## What shows no difference

Thanks (94% against 93%), hedges (88% against 87%), "we agree" (34% against 33%), apologies (15% against 21%, intervals overlap), the opening move, sentence length (median 22 words in both) and total length (median 1,244 against 1,063 author words, interval −28 to +332) do not separate the groups. Spend the effort on runs, numbers and locations.
