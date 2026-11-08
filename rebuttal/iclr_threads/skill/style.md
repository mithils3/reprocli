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
