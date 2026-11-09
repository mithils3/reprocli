---
name: iclr-review
description: Use when drafting or revising an ICLR or ML-conference author response, rebuttal, or reply to reviewers.
---

# ICLR author responses

The rules come from 441 ICLR 2025 review threads. In 244 the reviewer moved from 5 or lower to 6 or higher after the discussion ("raised"), and in 197 the reviewer replied and stayed at 5 or lower ("unchanged"). Two kinds of measurement back them. Regex counts over the author posts (style_stats.md) never see the outcome. LLM coding (blind_stats.md) was done on copies with the group, scores, reviewer follow-ups and score-change sentences removed, with both groups mixed in every batch of ten. A bracket like [+11, +1 to +20] gives the raised-minus-unchanged gap in points and its 95% interval. "Corpus" marks a gap whose interval excludes zero. Every gap is a correlation: a concern that a run can fix may produce both the new run and the raise. With about 60 features tested, two or three chance gaps are expected. Other brackets name a source, coder notes on named threads, or a house rule set by the skill's author. A format study over 240 of these threads and 34,137 searched author comments from 2025 and 2026 sets the length and layout targets (style.md, Section 10). It tested 13 format features against the outcome, so about one chance gap is expected; "[format study, no outcome gap]" marks a target taken from common practice alone.

Files: style.md covers register, openings, concessions, disagreement wording, layout, and format and length (Section 10), with verbatim examples. concerns.md gives the move that went with raised threads for each kind of reviewer concern. stats.md holds the full tables. reference.md holds sources, method and older examples.

ICLR 2027 uses a 4-point scale: read "5" as the score just below the accept line and "6" as the accept line, and confirm it in the 2027 Reviewer Guide.

**If rules conflict:** corpus rules come first, then house rules on tone (6, 10), then the rest. **Revising a draft:** skip rules 1 and 2, then check 3, 6, 9, 10, 12 and 14 in that order, then 5, 21 and 23 for layout.

## Before writing

1. Focus on the reviewer just below the accept line and on the one furthest below the others [source: Kargaran et al. 2025; Gao et al. 2019].
2. Put every reviewer point in one sheet, look up its concern type in concerns.md, mark which answers need a new run, and start those runs first [house rule; runs carry the largest gaps below].

## The opening

3. Thank the reviewer in one sentence, then list the changes made for that reviewer as bullets, one change per bullet with its location in the revised PDF; the full list goes in the general response (rule 21) [corpus for the list: a summary of revisions in some author post, 53% against 43%, +11, +1 to +20; its place at the top is a house rule, since the opening move itself shows no gap: thanks then changes 10% against 7%].
4. Upload the revised PDF with changes marked in one colour, say the colour once, and point to each change in the authors' usual form, "in the revised manuscript (Section 4.2, lines 312-318)" or "Appendix F" [corpus: a pointer to revised text, 75% against 63%, +12, +3 to +20; format study: colour named 27% against 16%, +11, +0 to +21, at the edge; the wording of the pointer shows no gap, 52% against 50%].
5. Give every point the reviewer's own numbered label in bold on its own line, "**W1: <short paraphrase>**" or "**Q2: ...**", with the answer below it; bold numbered labels are the most common form (57 of 240 threads) [corpus: headings 91% against 83%, +9, +2 to +15; format study: numbered labels 58% against 42%, +17, +4 to +29, same threads, so not an independent test]. Quoting the reviewer in full adds nothing measurable (74% against 73%); put a long point in a blockquote above the label's answer if the paraphrase loses it.
21. Post one general response to all reviewers near the authors' median of 1,900 characters (about 280 words; the middle half runs 1,100 to 3,500): one line of thanks, one sentence on what reviewers valued, about six bullets that each name one change and its location, then any result that answers several reviewers [corpus, format study: a general response on the forum 71% against 57%, +14, +2 to +26; its length and layout are format study, no outcome gap].

## Conceding

6. House rule: a sentence that judges the paper or its authors also names the change. Frame: "The paper said A; the code (or data, or proof) does B; we changed C at D." "We agree" is fine with the change in the same or next sentence. "You are right ... our paper overstated" or "We rushed" standing alone is banned. The corpus shows no penalty either way (blunt admission 4% against 7%, −3, −8 to +1), so this rule rests on the author's judgment.
7. When a reviewer flags an overclaim, reword it everywhere, show old and new phrasing in the reply, and mark the new wording in the PDF. When the code does less than described, weaken the claim and, where a run can measure the gap, add that measurement [coder notes on raised threads 2QdsjiNXgj, eXB5TCrAu9, tkqNDbukWW; claim_overstated in concerns.md].

## Evidence

8. Answer empirical doubts with a new experiment or ablation [corpus: new experiment in the thread 62% against 52%, +11, +1 to +20; ablation 29% against 16%, +13, +5 to +20; per point, 64% of points answered by a new experiment sit in raised threads against 54% over all points].
9. Put results in the reply as numbers in a markdown table, methods as rows and metrics as columns with the best value in bold [corpus: tables 46% against 35%, +11, +2 to +20; format study 44% against 29%, +15, +3 to +27; numbers per 1,000 author words 46.7 against 37.0, +9.8, +2.6 to +15.7]. Tables usually carry the new runs, so this overlaps rule 8.
10. Do not answer a doubt with clarification alone when a number can answer it [corpus: threads where coders listed clarification among the evidence, 61% against 73%, −12, −20 to −3; per point, answers with numbers sit in raised threads 63% of the time against 51% without].
11. Run the reviewer's named baseline under your settings [concerns.md, missing_baseline: new experiment 65% raised against 33% to 38% for disagreeing, with intervals that touch].

## Disagreeing

12. Disagree with a fact and keep the tone level. Avoid flat assertion and dismissal [corpus: assertive disagreement 66% against 77%, −11, −19 to −2; dismissive 9% against 18%, −9, −15 to −2; the regex for "disagree" and "misunderstand" 14% against 25%]. Polite disagreement with evidence shows no gap (62% against 56%).
13. Disagree only where you must: points answered by disagreement sit in raised threads at 43% (35 to 51) against the 54% baseline, with or without evidence. Concede and scope what you can, and save disagreement for the point you will not give up.
14. Write the answer sentence in the reply, then its location as section, page and line [per point: location given 61% raised against 50% without].
15. Never tell a reviewer they misread. When several misread a point, rewrite the text [source: Soto Valero 2022].

## Length and follow-ups

16. Give a substantive point a full answer of 150 words or more with its number and location [per point: 64% raised at 150 words or more against 49% below; long answers also carry the runs, so read this with rule 8]. Never leave a major point unanswered, although both groups rarely do (3% against 4%). The format study agrees: the median labelled answer runs 140 words and 46% reach 150.
17. Avoid a terse reply [corpus: terse first post 1% against 7%, −6, −11 to −3].
18. Answer each reviewer message that raises a point with new content, and post each promised run once it exists, with a short notice of what changed and where [corpus: more than one author post 92% against 86%, +6, +1 to +13; coder notes: ln6QnzBd8o ablation never posted, UG62fwmOxZ upload treated as missing].
19. To a silent reviewer, with nothing new to report, send one civil reminder line naming what changed, and ask for no score [house rule; reminders 48% against 53% and score asks 7% against 7% show no gap].
20. Keep the revision recognizably the same paper [ICLR 2026 Author Guide].
22. Answer a minor point (wording, notation, a missing reference) in one to three sentences that name the fix and its location, as 17% of labelled answers do in under 60 words: "We created and included an overview figure, which is now Figure 2." [format study, no outcome gap].
23. Post the first reply to each reviewer as one to three comments of at most 5,000 characters each, which is where OpenReview stops a comment, and title them "Response to Reviewer X (1/2)" and "(2/2)". Aim near the authors' median of about 8,000 characters (1,150 words) per reviewer over the whole thread, with the middle half at 5,300 to 12,700, and let later posts be short notices [format study, no outcome gap for total length (8,252 against 7,502 characters, −1,429 to +2,469) or parts (32% against 26%, +7, −5 to +18); a post near the limit does show one, 38% against 23%, +15, +3 to +26, and it tracks how much was run].
24. End the first post on the last answer or one line inviting further questions, and end the last post with one line of thanks [format study, no outcome gap: 74% of first posts end on an answer; invitations 22% against 19%]. 2026 replies match 2025 in length and use numbered labels and tables more often (43% and 21% of matched comments against 32% and 16%), so these targets hold for the current cycle [format study].

## What shows no difference

Thanks (94% against 93%), hedges (88% against 87%), "we agree" (34% against 33%), apologies (15% against 21%, intervals overlap), the opening move, sentence length (median 22 words in both) and total length (median 1,244 against 1,063 author words, interval −28 to +332) do not separate the groups. In the format study, parts, blockquotes, markdown headings, line numbers, the "revised manuscript" phrase, an opening thanks (82% against 80%) and a closing invitation show no gap either. Spend the effort on runs, numbers and locations.
