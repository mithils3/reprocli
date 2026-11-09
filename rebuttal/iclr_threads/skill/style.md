# Style and register of replies that went with a raised score

## 1. What the data are

This file draws on 441 ICLR 2025 review threads in which the authors replied. In 244 of them the reviewer went from 5 or lower to 6 or higher after the rebuttal, and this file calls those threads raised; in the other 197 the reviewer replied and stayed at 5 or lower, and this file calls those unchanged. Two sources feed it. style_stats.md counts surface markers in the author posts with regular expressions, so it is deterministic and never saw the outcome. blind_stats.md holds codes that a language model assigned to each thread without seeing the group, the scores, the reviewer's follow-ups or any author sentence about a score change, and blind_evidence.md holds the verbatim sentences behind those codes. Each number gives the raised share, the unchanged share, and the difference in percentage points with its 95% interval where the file reports one, and a gap is called supported only when that interval excludes 0. Every gap is a correlation: a reviewer whose concern can be fixed with one more run may prompt both the experiment and the raise, so a style that travels with raised threads may mark a fixable review as much as it causes a raise.

## 2. Register and tone

The one supported gap in register is the terse first post, which is rare among raised threads. Formal, warm, deferential and defensive registers show no clear difference, so spend the effort on content.

- Answer every substantive point in full sentences that carry the reason. (blind_stats.md, terse: raised 1%, unchanged 7%, -6 [-11, -3])
- Write in a formal, neutral voice or a warm one as you prefer. (blind_stats.md, formal_neutral: raised 64%, unchanged 58%, +6 [-3, +15]; warm: raised 23%, unchanged 20%, +3 [-5, +11])
- Skip deference as a tactic, since it shows no gain. (blind_stats.md, deferential: raised 7%, unchanged 8%, -1 [-6, +4]; defensive: raised 6%, unchanged 8%, -2 [-7, +3])

## 3. Openings

Three quarters of threads in both groups open with a generic thank-you, and no opening move shows a supported gap.

- Open with one sentence of thanks, then go to the first point or the list of changes. (blind_stats.md, thanks_generic: raised 75%, unchanged 71%, +4 [-4, +13]; thanks_then_changes_summary: raised 10%, unchanged 7%, +3 [-2, +8]; style_stats.md, thanks_in_first_40w: raised 66%, unchanged 65%, +1, no interval on the difference)
- Do not spend the first paragraph restating the review. (blind_stats.md, restate_reviewer_points: raised 7%, unchanged 11%, -5 [-10, +1]; no clear difference)

Raised openers are short and move on:

- "We thank the reviewer for the careful reading and thoughtful comments." (https://openreview.net/forum?id=6tyPSkshtF)
- "**Q1:** The paper has multiple grammatical errors and spelling mistakes." (https://openreview.net/forum?id=Y8L5RB4GWb)

## 4. Conceding

Nearly every thread in both groups concedes something, and no concession style separates them. What the writer controls is whether the concession arrives with a change the reviewer can check, and pointing to revised text is one of the supported gaps (Section 6).

- Concede where the reviewer is right, and name the change and its location in the same or the next sentence. (blind_stats.md, any concession: raised 95%, unchanged 95%, +0 [-4, +4]; agree_and_fixed: raised 79%, unchanged 75%, +4 [-4, +12])
- Scope a claim in part when only part of the criticism holds. (blind_stats.md, agree_partially_scoped: raised 61%, unchanged 60%, +0 [-9, +9])
- Admit a real mistake plainly; a blunt admission shows no clear penalty. (blind_stats.md, blunt_admission: raised 4%, unchanged 7%, -3 [-8, +1])

Raised examples across the styles:

- Agree and fix: "Thank you for suggesting additional quantitative metrics; we have included CLIP, TIFA, and ImageReward evaluations, which strengthen the empirical caliber of our paper." (https://openreview.net/forum?id=2o58Mbqkd2)
- Agree in part and scope: "While MemTree's cumulative time cost is 1.4x higher due to continuous updates, this trade-off allows real-time memory updates, making it well-suited for online scenarios." (https://openreview.net/forum?id=moXtEmCleY)
- Agree in part and scope: "We emphasized and added sentences in the revised version of the paper so it is clear that the generalization bound is an application, and that we are not claiming that the idea of using Lipschitz continuous functions over compact spaces to derive generalization bounds is new." (https://openreview.net/forum?id=qKgd7RaAem)
- Recast as clarification: "We see how this sentence might be unclear and would like to clarify." (https://openreview.net/forum?id=VfYShlQbj7)
- Limitation added: "We have also added a dedicated section discussing the limitations of our framework to clearly address this point." (https://openreview.net/forum?id=WYsNjw02DE)
- Blunt admission: "At the very beginning, we need to admit that we have a bug in the evaluation script of the 7B model." (https://openreview.net/forum?id=n9PDaFNi8t)

## 5. Disagreeing

Disagreement itself is universal, appearing in 95% of threads in both groups (blind_stats.md, any disagreement: raised 95%, unchanged 95%, +0 [-4, +4]). Two disagreement styles are rarer in raised threads: the assertive one, which states the authors' position without a reason, and the dismissive one, which calls the reviewer's point irrelevant or beneath an answer. Disagreeing politely with evidence is somewhat more common in raised threads, though that gap's interval includes 0. Assertive sentences still appear in two thirds of raised threads, so a single flat line does not sink a reply; the gap is in how often a thread falls back on them.

- Put the reason, number or definition in the same sentence as the disagreement. (blind_stats.md, polite_with_evidence: raised 62%, unchanged 56%, +6 [-3, +15]; no clear difference on its own)
- Cut sentences that assert the position with no support. (blind_stats.md, assertive: raised 66%, unchanged 77%, -11 [-19, -2])
- Never call a point irrelevant, tangential or out of bounds without the reason. (blind_stats.md, dismissive: raised 9%, unchanged 18%, -9 [-15, -2])
- The word "disagree" is optional, since a reason does the work. (style_stats.md, disagree: raised 14%, unchanged 25%, -11, no interval on the difference; respectfully: raised 7%, unchanged 12%, -5, no interval on the difference)

Polite with evidence, raised:

- "The differences in Table 4 are not easy to surpass because the experimental results of the baselines in Table 4 are obtained through hyperparameter tuning (with lr = [0.1, 0.01, 0.001]) and 5 different random seeds." (https://openreview.net/forum?id=uApm5otXfH)
- "This is because while the oscillations remain bounded, the distance between GD and gradient flow grows over time and soon overtakes the size of the oscillations." (https://openreview.net/forum?id=sIE2rI3ZPs)

Polite with evidence, unchanged, which shows the style alone does not guarantee a raise:

- "Unfortunately, this is not possible directly since, in the Tree MDP, each node can have multiple child nodes." (https://openreview.net/forum?id=YDuYWjbKDA)

Assertive and dismissive, unchanged:

- "This is a slight misunderstanding." (https://openreview.net/forum?id=J9eKm7j6KD)
- "We kindly remind you that ICLR guidelines discourage requests for significant additional experiments." (https://openreview.net/forum?id=F52tAK5Gbg)
- "Therefore, we do not plan to pursue this suggestion further." (https://openreview.net/forum?id=ts1F3BVaDI)

Assertive and dismissive lines also occur in raised threads, where other answers carried the reviewer:

- "Regarding your suggestion concerning PEFT on SSM LLMs, we believe this is irrelevant to our paper and research track." (https://openreview.net/forum?id=PPjpGTPG5K)
- "Basically, we are not required to compare with arxiv paper within 4 months." (https://openreview.net/forum?id=HyPofygOCT)

## 6. Numbers and evidence density

This is where the clearest gaps sit. Raised replies carry more numbers per 1,000 author words, use more tables, and more often add a new experiment, an ablation, or a pointer to revised text, while total length shows no clear difference.

- Put the numbers in the reply itself. (style_stats.md, number_per_k: raised median 46.7, unchanged median 37.0 numbers per 1,000 author words, +9.8 [+2.6, +15.7])
- Report new results as a markdown table. (blind_stats.md, uses_tables: raised 46%, unchanged 35%, +11 [+2, +20]; numbers_table: raised 54%, unchanged 41%, +13 [+4, +22])
- Answer an empirical doubt with a new experiment or an ablation. (blind_stats.md, new_experiment: raised 62%, unchanged 52%, +11 [+1, +20]; ablation: raised 29%, unchanged 16%, +13 [+5, +20])
- Do not rely on clarification alone when a run could answer the point. (blind_stats.md, clarification: raised 61%, unchanged 73%, -12 [-20, -3])
- Point to where the revised paper changed. (blind_stats.md, revised_text_pointer: raised 75%, unchanged 63%, +12 [+3, +20]); pointers to sections in general show no clear difference (style_stats.md, location_ref_per_k: raised 3.7, unchanged 3.8, -0.1 [-1.0, +0.8])
- Write as long as the answers need. (style_stats.md, words: raised median 1,244, unchanged median 1,063, +181 [-28, +332]; no clear difference)

Raised sentences that carry their numbers:

- "PDT requires 2596.30 TFLOPs to reach the baseline's best loss, compared to SGD's 3404.32 TFLOPs, representing a 23.74% reduction in total computation cost." (https://openreview.net/forum?id=eVsSjNRuAp)
- "Notably, as Ego4D inherently features instances of missing audio, we conducted evaluations at 50%, 75%, and 100% missing rates." (https://openreview.net/forum?id=1L52bHEL5d)

## 7. Layout

Two layout features are supported: a heading or label for each reviewer point, and a summary of revisions somewhere in the thread. Quoting the reviewer, bold and markdown headings show no clear difference.

- Give each reviewer point its own heading or label, such as W1 or Q2. (blind_stats.md, per_point_headings: raised 91%, unchanged 83%, +9 [+2, +15]; style_stats.md, point_label: raised 56%, unchanged 47%, +9, no interval on the difference)
- Include a summary of revisions that lists each change and where it sits. (blind_stats.md, summary_of_revisions: raised 53%, unchanged 43%, +11 [+1, +20])
- Quote the reviewer's line above the answer if it helps the reader; it shows no clear difference. (blind_stats.md, quotes_reviewer: raised 74%, unchanged 73%, +1 [-8, +9]; style_stats.md, blockquote: raised 44%, unchanged 37%, +7, no interval on the difference)
- Use bold and markdown headings for navigation only. (style_stats.md, bold: raised 83%, unchanged 73%, +10, no interval on the difference; bold_per_k: raised 7.5, unchanged 6.9, +0.7 [-1.0, +3.0]; md_heading_per_k: raised 0.4, unchanged 0.0, +0.4 [-0.3, +0.9])

Three layouts from raised threads, as the blind coders described them:

- "Opens with thanks; quotes each review point in a blockquote, then answers in bullets, adding new tables and appendix pointers; closes with a line on the limits of decoding overlapping watermarks." (https://openreview.net/forum?id=IkZVDzdC8M)
- "Opens with thanks, then one bold Q-numbered heading per reviewer question that restates it. Each answer gives evidence and appendix or line pointers. A second post continues the numbering, and a third post is a short thanks." (https://openreview.net/forum?id=h2Q3gOIz8q)
- "Bold bracketed tag per review item (for example [Q1]) that restates the point, then one answer paragraph; a comparison table for the new baseline; closes with a request for feedback." (https://openreview.net/forum?id=1qbZekXGrp)

## 8. Closings and follow-ups

No closing form separates the groups. Reminders to a silent reviewer and direct requests to raise the score appear at the same rates in both, so neither helps nor hurts on this evidence. Posting more than once is more common in raised threads, though this partly reflects reviewers who wrote back and gave the authors something to answer.

- End with the last answer or a one-line invitation to ask more. Raised examples: "Please let us know if you have any further questions." (https://openreview.net/forum?id=Gi5aWK8tOx) and "Please don't hesitate if any questions or remarks remain!" (https://openreview.net/forum?id=vhPE3PtTgC)
- Asking for the score is optional; it shows no gap. (style_stats.md, score_ask: raised 7%, unchanged 7%, +0, no interval on the difference; last_post_score_ask: raised 5%, unchanged 4%, +1, no interval on the difference)
- Send a reminder if the reviewer is silent; it shows no gap either way. (blind_stats.md, reminder_nudge: raised 48%, unchanged 53%, -4 [-14, +5])
- Post again when the reviewer replies or a promised result lands. (blind_stats.md, more than one author post: raised 92%, unchanged 86%, +6 [+1, +13])
- When a result is still running, say what remains and when it will arrive. Raised example: "The remaining data will take approximately one day to process, after which the overall results will be updated." (https://openreview.net/forum?id=J6e4hurEKd)
- Keep follow-ups level when the reviewer holds the score. Unchanged examples: "If we have addressed your concerns, we kindly ask you to reevaluate your score." (https://openreview.net/forum?id=MDvecs7EvO) and "This perfunctory response only shows our efforts in rebutall are not being respected." (https://openreview.net/forum?id=pbJMPo4HwR)

## 9. Things that show no difference

These markers appear at similar rates in both groups, so a writer can stop tuning them. Thanking the reviewer is near universal (style_stats.md, thanks: raised 94%, unchanged 93%, +1, no interval on the difference; thanks_per_k: raised 4.2, unchanged 3.4, +0.8 [+0.0, +1.6]). Hedges such as "may" and "we believe" are equally common (style_stats.md, hedge: raised 88%, unchanged 87%, +1, no interval on the difference; hedge_per_k: raised 3.1, unchanged 2.8, +0.3 [-0.2, +0.7]), and so are boosters such as "clearly" (style_stats.md, booster_per_k: raised 1.0, unchanged 1.0, -0.0 [-0.3, +0.3]). Saying "we agree" or "you are right" makes no clear difference (style_stats.md, we_agree: raised 34%, unchanged 33%, +1, no interval on the difference; you_are_right: raised 7%, unchanged 6%, +1, no interval on the difference). Apologies are slightly rarer in raised threads, though the file reports no interval and the median rate is zero in both (style_stats.md, apology: raised 15%, unchanged 21%, -6, no interval on the difference; apology_per_k: raised 0.0, unchanged 0.0, +0.0 [+0.0, +0.0]). Median sentence length is 22 words in both groups (style_stats.md, sent_len_median: raised 22.0, unchanged 22.0, +0.0 [-0.5, +1.0]). The opening move (Section 3) and the style of a concession (Section 4) also belong on this list.

## 10. Format and length

This section describes how ICLR authors lay out a reply, so a draft can match them. It draws on three sources, and each number names its file.

- Full threads: rebuttal/iclr_threads/format_sample.jsonl in the reprocli repo, 240 ICLR 2025 reviewer threads (120 raised, 120 unchanged, a subsample of the 441 threads above). Scripts in rebuttal/iclr_threads/format_study/ measured them, and their printout is format_study/output.txt, cited below as output.txt.
- Six blind readers' notes, format_notes_1.md to format_notes_6.md with per-thread rows in format_notes_1.jsonl to format_notes_6.jsonl, 40 threads each, outcome hidden. The readers worked from structure and scripts (headings, first and last sentences, table and pointer scans, targeted reads) and did not read every line, so their point counts and words per point are estimates.
- Search corpus: rebuttal/results/style/author_comments.jsonl, 34,137 author comments returned by OpenReview search (26,612 from 2025, 7,525 from 2026), with its method in iclr_author_responses.md. Search returns only comments that match a query, so its per-thread totals undercount. The 2026 part came from two queries only ("we thank" and "thank the reviewer"), so the year comparison uses the comments in both years whose text contains one of those phrases, called matched below.

Everything here describes common practice. The raised against unchanged comparison of these format features is in stats.md, Part 3, and Section 10.10 summarises it.

### 10.1 Length per reviewer

- Total author text in a reviewer thread has a median of 8,050 characters, about 1,150 words, with quartiles of 5,285 and 12,694 characters (784 and 1,821 words) (output.txt). The six reader samples gave medians from 6,918 to 9,522 characters (format_notes_1.md to format_notes_6.md). The search corpus gives 2,526 characters per thread, which undercounts because search drops the comments that do not match (iclr_author_responses.md).
- A thread holds a median of 3 author posts, with quartiles of 2 and 5, and 25 of 240 threads hold a single post (output.txt).
- A post holds a median of 2,739 characters, with quartiles of 899 and 4,097 over 893 posts. The first post is the long one, with a median of 3,994 and quartiles of 2,967 and 4,642, and the later posts are short notices and follow-ups (output.txt). No post body in the sample runs past 5,009 characters and 85 of 893 sit above 4,800, so treat 5,000 characters as the limit of one OpenReview comment (output.txt). The search corpus gives a median of 2,264 characters per comment, with quartiles of 693 and 3,896 (iclr_author_responses.md).

### 10.2 Parts

- 70 of 240 threads (29%) label their posts as parts (output.txt). A count such as "(1/3)", "[1/2]" or "Part 1/2" appears in 35, "Part 1" or "Part I" in 27, and "(cont.)" or "Continued" in 8. The readers counted 13, 16, 13, 17, 13 and 6 of 40 split threads in their samples (format_notes_1.md to format_notes_6.md).
- The label sits in the post title, as in "Authors' Responses to Reviewer gqu4 (1/5)" (https://openreview.net/forum?id=bhK7U37VW8), and "Response to Reviewer X" is the most common title, on 105 of the 489 titled posts (output.txt). A part ends where the 5,000-character limit falls, often between two points.

### 10.3 Point headings

Half the threads number their points with the reviewer's own labels, and the rest quote the reviewer or use a short bold topic (output.txt, 240 threads, first labelled point per thread).

| form | threads | verbatim example |
|---|---|---|
| Bold numbered label on its own line | 57 | "**W1: OwLore may lead to increased time cost.**" (https://openreview.net/forum?id=AEwtGiJVPi) |
| Blockquoted reviewer sentence, no number | 46 | "> The work appears to be a direct extension ... it would be beneficial to further emphasize how the authors handle these complexities." (https://openreview.net/forum?id=gYNBQygmXG) |
| Bold topic lead-in, no number | 38 | "**Multiple Seeds / Standard Deviation:**" (https://openreview.net/forum?id=uN2kkAvarI) |
| Numbered label inside a blockquote | 34 | "> **Q3.** The minimal performance gains may not justify the added memory and computational overheads." then "**A3.**" (https://openreview.net/forum?id=CuupjjjT3U) |
| No headings | 21 | |
| Markdown heading with a topic | 15 | "## **KV Cache Memory Reduction Compared to Pruning Methods**" (https://openreview.net/forum?id=HyPofygOCT) |
| Markdown heading with a numbered label | 14 | "### W1. Experiments on varying forecasting, observation and spatial range." (https://openreview.net/forum?id=ts1F3BVaDI) |
| Plain numbered label | 13 | "Q1: The reliability of the scorer LLM (e.g., Gemma-7B-it) is uncertain." then "A1:" (https://openreview.net/forum?id=bhK7U37VW8) |

- Numbered labels appear in 120 of 240 threads. Among them 45 use Q labels only, 43 use W and Q labels, 23 use W only, and 9 use C for comment or concern (output.txt). A separate answer label such as "A1:", "R1:" or "**Response:**" appears in 70 threads (output.txt).
- The label carries a short paraphrase or the reviewer's sentence, and a long reviewer point goes in a blockquote above the answer.

### 10.4 Answer shape

- Over 643 numbered points in 120 threads, an answer runs a median of 140 words, with quartiles of 78 and 255. 110 answers (17%) run under 60 words and 296 (46%) reach 150 words (output.txt). The readers estimated a median of 260 words per point, with quartiles of 162 and 374, by dividing total words by the points they counted, which also counts quoted review text (format_notes_1.jsonl to format_notes_6.jsonl).
- 62% of these answers carry a number (400 of 643), 48% name a location such as a Table, Figure, Section, Appendix, line or page (307), 28% state a change in words like "we have added" or "revised" (182), 14% hold a table (88), and 22% thank the reviewer in their first two sentences (143) (output.txt).
- The shape the readers describe most often is a label, a direct answer in the first sentence, the number or line range, then the pointer to the revision (format_notes_5.md). A minor point such as wording, notation or a missing reference gets one to three sentences.

### 10.5 Tables

- 88 of 240 threads (37%) hold at least one markdown table, and those threads hold a median of 2 tables, with quartiles of 1 and 4 (output.txt).
- In the readers' descriptions, the tables hold new results set against baselines or benchmarks (49 descriptions), ablation grids or hyperparameter sweeps (10), and cost or runtime (4) (format_notes_1.jsonl to format_notes_6.jsonl, the tables.holds field). A typical table has methods as rows, metrics as columns, and the best value in bold (format_notes_1.jsonl, t075).
- In the search corpus 15.7% of matched 2025 comments and 21.3% of matched 2026 comments hold a table (output.txt).

### 10.6 Pointing to the revised PDF

- Over 240 threads, a reply names a Table or Figure number in 72%, a Section in 48%, an Appendix in 46%, the revised document by name in 51%, line numbers in 28%, a colour or highlight in 21%, and a page in 9% (output.txt).
- The revised document is named as "in the revised manuscript" (52 uses), "in the revised paper" (28), "in the revised version" (27) and "in the updated manuscript" (14). Colour is named as "highlighted in red" (6), "marked in blue" (3) or "highlighted in blue" (3). Lines are given as "Line N" or "lines N-N" (312 line references) (output.txt).
- Verbatim forms: "We already include other Triplane-based 3D generation methods in the revised paper (Line 139-144)." (https://openreview.net/forum?id=nhAyhTxrXu); "The updated theoretical results and corresponding proofs have been added to **Appendix B of the updated manuscript**, highlighted in blue for clarity." (https://openreview.net/forum?id=v4PnwdA056); "We also try with different teacher LLMs: GPT-4o (Table 2, L378-393) and GPT-4o-mini (Table 5, L972-986 in the revised PDF)." (https://openreview.net/forum?id=00SnKBGTsz)

### 10.7 General response

- 153 of the 240 threads (64%) sit on a forum with a general response (output.txt). The search corpus finds one on 28.2% of forums, which undercounts for the same reason as above (iclr_author_responses.md).
- A general response runs a median of 1,919 characters, about 284 words, with quartiles of 1,127 and 3,506 characters (171 and 474 words) (output.txt). The search corpus gives a median of 1,717 characters, with quartiles of 894 and 2,792 (iclr_author_responses.md).
- Of the 153, 94% thank the reviewers, 74% name a location, 73% use words such as summary, revision or changes, 55% hold a bullet list (a median of 6 bullets), 46% combine bullets with locations, 50% name a colour or highlight, 32% use bold lead-ins, 18% recap what reviewers praised, 13% use markdown headings, and 12% hold a table (output.txt).
- Its title is most often "General Response", then "Global Response", "Common Response" and "Revision Summary" (output.txt). The usual order is one line of thanks, a sentence on what reviewers valued, a bulleted list of changes with their locations, and results that answer several reviewers at once.

### 10.8 Openings and closings

- The first sentence of the first post thanks the reviewer in 195 of 240 threads (81%), 31 (13%) open directly on a point label or quote, and 27 (11%) open with a "Dear Reviewer" line (output.txt). The most common first words are "Thank you for" (68) and "We thank the" (31).
- The first post ends on its last answer in 178 threads (74%), on thanks in 37 (15%), and on an invitation to ask more in 25 (10%). The last post ends on thanks in 97 (40%), on an answer in 93 (39%), on an invitation in 49 (20%), and on a score request in 1 (output.txt). The most common closing words are "Thank you again for".

### 10.9 2025 against 2026

The matched search comments give 6,711 reviewer-thread comments from 2025 and 3,299 from 2026 (output.txt, corpus.py block). Shares are compared with Newcombe intervals and medians with a bootstrap.

- Length is about the same: a median of 3,332 characters in 2025 and 3,181 in 2026, a difference of −151 [−270, −43], under 5%. Per-thread totals are 3,453 and 3,246, both undercounted.
- 2026 replies use more structure: numbered point labels 32.1% to 43.3% (+11.3 [+9.2, +13.3]), markdown headings 15.5% to 23.7% (+8.2 [+6.5, +9.9]), bold lead-ins 43.3% to 50.7% (+7.4 [+5.3, +9.5]), and tables 15.7% to 21.3% (+5.6 [+4.0, +7.3]).
- 2026 replies quote the reviewer a little less (blockquotes 33.2% to 29.1%, −4.1 [−6.0, −2.2]) and give line numbers less often (21.8% to 14.8%, −7.0 [−8.5, −5.4]). Parts are unchanged (22.7% and 23.5%, +0.8 [−1.0, +2.6]).
- General responses (909 in 2025, 170 in 2026) are about as long (1,856 and 2,017 characters, +161 [−292, +583]), open with "Dear" more often (12.4% to 28.2%), and name the revised document less often (54.6% to 32.4%, −22.2 [−29.5, −14.2]). These data do not show why that phrase fell.
- Verbatim 2026 point answers are among the examples below.

### 10.10 Format and the outcome

Over 13 format features in the 240 threads, five gaps have intervals that exclude zero: a table (44% against 29%), numbered point labels (58% against 42%), a general response on the forum (71% against 57%), a post near the 5,000-character limit (38% against 23%), and named colour marking (27% against 16%, with the lower bound at zero) (stats.md, Part 3). With 13 features about one chance gap is expected. Each gap is a correlation, these features travel together with effort and with fixable reviews, and the 240 threads are a subsample of the 441, so the table and heading gaps come from the same threads as the earlier findings and add no independent test. Total length, posts, characters per post, parts, quotes, markdown headings, the revised-document phrase, line numbers, opening thanks and closing invitations show no gap.

### 10.11 Efficient point answers (verbatim)

Chosen for shape alone, each with a label, a direct first sentence, a number or a change, and a location.

- 2025: "**W1: OwLore may lead to increased time cost.** ... We would like to clarify that the outlier scores are computed only once before the fine-tuning process begins, not with each update. ... For example, in our experiments with the LLaMA2-7B model, the computation of outlier scores takes approximately 73 secs. In contrast, the total fine-tuning time is about 1.6 hours, making the outlier score computation a negligible portion (approximately 1.2%) of the overall training time." (https://openreview.net/forum?id=AEwtGiJVPi)
- 2025: "**A7**: Thanks for your suggestion! The new results on the VisA dataset are given in the ***General Response.*** Our method outperforms others across all the segmentation models, with an **11.71%** average improvement on IoU." (https://openreview.net/forum?id=VzZTHukfCB)
- 2025: "A1: Thank you for your valuable suggestion. We have added detailed evaluations of the alignment of the scorer LLM in Appendix F. These evaluations demonstrate that Gemma-7B-it exhibits strong and aligned performance in scoring." (https://openreview.net/forum?id=bhK7U37VW8)
- 2025: "**Response:** This is a good suggestion. We created and included an overview figure, which is now Figure 2." (https://openreview.net/forum?id=STBPaproaB)
- 2026: "**Q7 – Cross-family generalization** We have evaluated this cross-architecture generalization and reported it in (Table 4): training on three families and testing on the fourth yields 24–28% MAPE, while IrEne’s error is 49–58% in the same setting." (https://openreview.net/forum?id=aPJeT2Ii3u)
- 2026: "> Q2. Another concern is evaluation cost and practicality. We have added a cost analysis for a single evaluation to the **Appendix D.1**. On average, the evaluator processes 424 input tokens and produces 127 output tokens per evaluation. The estimated cost per evaluation is approximately USD 0.72." (https://openreview.net/forum?id=aKyBCsPOHB)
- 2026: "> Q4/W7: Could you add a small slice evaluating non-temporal questions to demonstrate breadth beyond time-centric tasks? Our evaluation on LoCoMo and REALTALK already includes both temporal and non-temporal questions. In Appendix C.7, we further introduce this evaluation perspective and report that the performance of REMem-I on LoCoMo non-temporal questions (75.0 LLM-J) is comparable to its performance on temporal ones (77.7 LLM-J), indicating that REMem is not limited to time-centric tasks." (https://openreview.net/forum?id=fugnQxbvMm)
- 2026: "> **W3: Clarification of performance gain** We thank the reviewer for the careful observation. The "up to 20.3%" improvement refers to the gain over SubgraphRAG + Llama3.1-8B. ... We have clarified this distinction in Section 5.2 of the revised manuscript." (https://openreview.net/forum?id=9EPlA1Wt4s)
