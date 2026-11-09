# iclr-review statistics

Two sources. Part 1 is the outcome-blind LLM coding (blind_stats.py over build_blind.py copies). Part 2 is regex stylometry over the author posts (style.py). The earlier tables coded with the outcome visible were inflated and are retired; see rebuttal/iclr_threads/stats.md in the repo for the record.

## Outcome-blind recode: raised vs unchanged

Threads coded blind: 441 (raised 244, unchanged 197). Coders saw the review, the authors' general response and the authors' posts; the group, the scores, reviewer follow-ups and author sentences about a score change were removed (build_blind.py). Each cell: count/threads = share [Wilson 95%]; diff = raised minus unchanged in points [Newcombe 95%]; * marks a difference whose interval excludes 0.

### Reply features (thread level)

| feature | raised | unchanged | diff |
|---|---|---|---|
| summary_of_revisions | 130/244 = 53% [47, 59] | 84/197 = 43% [36, 50] | +11 [+1, +20] * |
| per_point_headings | 223/244 = 91% [87, 94] | 163/197 = 83% [77, 87] | +9 [+2, +15] * |
| quotes_reviewer | 180/244 = 74% [68, 79] | 144/197 = 73% [67, 79] | +1 [-8, +9] |
| uses_tables | 113/244 = 46% [40, 53] | 69/197 = 35% [29, 42] | +11 [+2, +20] * |
| reminder_nudge | 118/244 = 48% [42, 55] | 104/197 = 53% [46, 60] | -4 [-14, +5] |
| any concession | 231/244 = 95% [91, 97] | 187/197 = 95% [91, 97] | +0 [-4, +4] |
| any disagreement | 231/244 = 95% [91, 97] | 187/197 = 95% [91, 97] | +0 [-4, +4] |
| any misstep flagged | 244/244 = 100% [98, 100] | 197/197 = 100% [98, 100] | +0 [-2, +2] |
| more than one author post | 225/244 = 92% [88, 95] | 169/197 = 86% [80, 90] | +6 [+1, +13] * |

### Opening move of the first post

| opening | raised | unchanged | diff |
|---|---|---|---|
| thanks_then_changes_summary | 24/244 = 10% [7, 14] | 13/197 = 7% [4, 11] | +3 [-2, +8] |
| thanks_generic | 183/244 = 75% [69, 80] | 139/197 = 71% [64, 76] | +4 [-4, +13] |
| direct_answer | 13/244 = 5% [3, 9] | 16/197 = 8% [5, 13] | -3 [-8, +2] |
| restate_reviewer_points | 16/244 = 7% [4, 10] | 22/197 = 11% [7, 16] | -5 [-10, +1] |
| concession_first | 4/244 = 2% [1, 4] | 1/197 = 1% [0, 3] | +1 [-1, +4] |
| other | 4/244 = 2% [1, 4] | 6/197 = 3% [1, 6] | -1 [-5, +2] |

### Register of the first post

| register | raised | unchanged | diff |
|---|---|---|---|
| formal_neutral | 156/244 = 64% [58, 70] | 114/197 = 58% [51, 65] | +6 [-3, +15] |
| warm | 56/244 = 23% [18, 29] | 39/197 = 20% [15, 26] | +3 [-5, +11] |
| deferential | 16/244 = 7% [4, 10] | 15/197 = 8% [5, 12] | -1 [-6, +4] |
| defensive | 14/244 = 6% [3, 9] | 15/197 = 8% [5, 12] | -2 [-7, +3] |
| terse | 2/244 = 1% [0, 3] | 14/197 = 7% [4, 12] | -6 [-11, -3] * |

### Evidence added (any in the thread)

| evidence | raised | unchanged | diff |
|---|---|---|---|
| new_experiment | 152/244 = 62% [56, 68] | 102/197 = 52% [45, 59] | +11 [+1, +20] * |
| new_baseline | 53/244 = 22% [17, 27] | 32/197 = 16% [12, 22] | +5 [-2, +13] |
| ablation | 71/244 = 29% [24, 35] | 32/197 = 16% [12, 22] | +13 [+5, +20] * |
| theory_or_proof | 32/244 = 13% [9, 18] | 22/197 = 11% [7, 16] | +2 [-4, +8] |
| clarification | 148/244 = 61% [54, 67] | 143/197 = 73% [66, 78] | -12 [-20, -3] * |
| revised_text_pointer | 182/244 = 75% [69, 80] | 124/197 = 63% [56, 69] | +12 [+3, +20] * |
| numbers_table | 131/244 = 54% [47, 60] | 80/197 = 41% [34, 48] | +13 [+4, +22] * |
| citation | 98/244 = 40% [34, 46] | 76/197 = 39% [32, 46] | +2 [-8, +11] |
| code_or_data_release | 18/244 = 7% [5, 11] | 7/197 = 4% [2, 7] | +4 [-1, +8] |

### Concession style (any in the thread)

| style | raised | unchanged | diff |
|---|---|---|---|
| agree_and_fixed | 192/244 = 79% [73, 83] | 147/197 = 75% [68, 80] | +4 [-4, +12] |
| agree_partially_scoped | 148/244 = 61% [54, 67] | 119/197 = 60% [53, 67] | +0 [-9, +9] |
| reframe_as_clarification | 33/244 = 14% [10, 18] | 26/197 = 13% [9, 19] | +0 [-6, +7] |
| limitation_added_to_paper | 9/244 = 4% [2, 7] | 10/197 = 5% [3, 9] | -1 [-6, +3] |
| blunt_admission | 9/244 = 4% [2, 7] | 14/197 = 7% [4, 12] | -3 [-8, +1] |

### Disagreement style (any in the thread)

| style | raised | unchanged | diff |
|---|---|---|---|
| polite_with_evidence | 152/244 = 62% [56, 68] | 111/197 = 56% [49, 63] | +6 [-3, +15] |
| points_to_paper_section | 47/244 = 19% [15, 25] | 41/197 = 21% [16, 27] | -2 [-9, +6] |
| new_experiment | 2/244 = 1% [0, 3] | 3/197 = 2% [1, 4] | -1 [-4, +2] |
| assertive | 161/244 = 66% [60, 72] | 151/197 = 77% [70, 82] | -11 [-19, -2] * |
| dismissive | 22/244 = 9% [6, 13] | 35/197 = 18% [13, 24] | -9 [-15, -2] * |

| quantity | raised median | unchanged median |
|---|---|---|
| author posts | 4.0 | 3 |
| author words (coder estimate) | 1000.0 | 880 |
| review points | 5.0 | 5 |
| concessions | 2.0 | 2 |
| disagreements | 2.0 | 2 |

### Reviewer points: answer move

Points 2371 in 441 threads. Raised share of all points: 54% [49, 59]. Each cell: points n, share of those points that sit in a raised thread [thread-cluster bootstrap 95%]. A cell whose interval sits wholly above the baseline goes with raised threads more than the average point.

| move | n | raised share |
|---|---|---|
| new_experiment | 436 | 64% [58, 71] |
| new_analysis_existing_data | 82 | 63% [52, 74] |
| text_revision | 509 | 56% [49, 62] |
| clarification_only | 558 | 55% [49, 62] |
| concede_and_scope | 128 | 49% [39, 59] |
| disagree_with_evidence | 328 | 43% [35, 51] |
| disagree_without_evidence | 136 | 43% [33, 54] |
| defer_future_work | 101 | 47% [36, 57] |
| not_addressed | 91 | 48% [35, 61] |

### Answer features, addressed points

| feature | n | raised share |
|---|---|---|
| has_numbers | 671 | 63% [57, 69] |
| no numbers | 1609 | 51% [46, 56] |
| location_given | 973 | 61% [55, 66] |
| no location | 1307 | 50% [44, 55] |
| answer_words >= 150 | 762 | 64% [58, 70] |
| answer_words < 150 | 1518 | 49% [44, 55] |

### Major points left unaddressed

- raised: 24 of 852 major points not addressed (3% [2, 4])
- unchanged: 32 of 795 major points not addressed (4% [3, 6])

### By concern type: answer move (moves with n >= 12)

#### clarity_or_presentation: 374 points, raised share 50% [43, 58]

| move | n | raised share |
|---|---|---|
| text_revision | 226 | 53% [45, 61] |
| clarification_only | 108 | 45% [34, 57] |
| not_addressed | 23 | 52% [32, 73] |

#### evaluation_validity: 306 points, raised share 56% [48, 63]

| move | n | raised share |
|---|---|---|
| new_experiment | 81 | 63% [52, 74] |
| new_analysis_existing_data | 29 | 69% [50, 88] |
| text_revision | 16 | 56% [31, 80] |
| clarification_only | 57 | 67% [53, 79] |
| concede_and_scope | 19 | 21% [5, 42] |
| disagree_with_evidence | 69 | 45% [32, 58] |
| disagree_without_evidence | 19 | 58% [32, 82] |

#### other: 300 points, raised share 52% [44, 60]

| move | n | raised share |
|---|---|---|
| new_experiment | 31 | 61% [41, 80] |
| text_revision | 36 | 61% [43, 77] |
| clarification_only | 120 | 51% [40, 62] |
| disagree_with_evidence | 43 | 40% [22, 59] |
| disagree_without_evidence | 21 | 33% [14, 56] |
| defer_future_work | 15 | 53% [27, 80] |
| not_addressed | 13 | 54% [22, 83] |

#### missing_experiment_or_ablation: 206 points, raised share 64% [56, 72]

| move | n | raised share |
|---|---|---|
| new_experiment | 132 | 64% [53, 73] |
| clarification_only | 13 | 69% [43, 93] |
| defer_future_work | 19 | 68% [47, 89] |

#### limitation_or_scope: 189 points, raised share 52% [44, 61]

| move | n | raised share |
|---|---|---|
| new_experiment | 33 | 61% [43, 78] |
| text_revision | 14 | 57% [25, 83] |
| clarification_only | 28 | 68% [48, 86] |
| concede_and_scope | 38 | 53% [36, 71] |
| disagree_with_evidence | 24 | 38% [18, 58] |
| disagree_without_evidence | 25 | 44% [22, 67] |
| defer_future_work | 20 | 35% [14, 57] |

#### reproducibility_or_details: 178 points, raised share 54% [45, 64]

| move | n | raised share |
|---|---|---|
| text_revision | 68 | 53% [39, 65] |
| clarification_only | 83 | 58% [45, 70] |

#### theory_or_proof: 169 points, raised share 53% [43, 63]

| move | n | raised share |
|---|---|---|
| text_revision | 33 | 58% [35, 77] |
| clarification_only | 53 | 66% [51, 79] |
| concede_and_scope | 17 | 53% [29, 76] |
| disagree_with_evidence | 43 | 37% [21, 56] |

#### missing_baseline: 160 points, raised share 51% [42, 59]

| move | n | raised share |
|---|---|---|
| new_experiment | 77 | 65% [53, 76] |
| disagree_with_evidence | 24 | 38% [18, 58] |
| disagree_without_evidence | 15 | 33% [11, 57] |
| defer_future_work | 13 | 23% [0, 50] |

#### novelty: 156 points, raised share 49% [41, 58]

| move | n | raised share |
|---|---|---|
| new_experiment | 12 | 75% [44, 100] |
| text_revision | 13 | 62% [33, 88] |
| clarification_only | 32 | 41% [24, 59] |
| disagree_with_evidence | 52 | 44% [30, 59] |
| disagree_without_evidence | 25 | 40% [22, 60] |

#### claim_overstated: 123 points, raised share 55% [45, 65]

| move | n | raised share |
|---|---|---|
| text_revision | 31 | 55% [35, 73] |
| clarification_only | 21 | 52% [30, 76] |
| concede_and_scope | 15 | 53% [27, 80] |
| disagree_with_evidence | 30 | 47% [29, 66] |

#### scalability_or_cost: 117 points, raised share 62% [51, 71]

| move | n | raised share |
|---|---|---|
| new_experiment | 38 | 74% [59, 88] |
| new_analysis_existing_data | 14 | 57% [27, 83] |
| clarification_only | 20 | 70% [50, 89] |
| disagree_with_evidence | 16 | 50% [20, 80] |

#### related_work: 92 points, raised share 57% [46, 68]

| move | n | raised share |
|---|---|---|
| text_revision | 46 | 61% [45, 76] |
| clarification_only | 12 | 50% [14, 80] |
| disagree_with_evidence | 12 | 33% [8, 67] |

#### numbers_table: 1 points, raised share 0% [0, 0]

| move | n | raised share |
|---|---|---|


## Surface style of author replies: raised vs unchanged

Threads with author text under the review: raised n=244, unchanged n=197. Share rows: % of threads with at least one match [Wilson 95%]. Rate rows: median matches per 1,000 author words, with a bootstrap 95% interval on the difference of medians. Patterns are in style.py.

### Share of threads with the marker

| marker | raised | unchanged | diff (pts) |
|---|---|---|---|
| thanks | 94% [90, 96] | 93% [89, 96] | +1 |
| apology | 15% [11, 20] | 21% [16, 28] | -6 |
| we_agree | 34% [28, 40] | 33% [27, 40] | +1 |
| you_are_right | 7% [5, 11] | 6% [3, 10] | +1 |
| respectfully | 7% [4, 11] | 12% [8, 17] | -5 |
| disagree | 14% [10, 19] | 25% [19, 31] | -11 |
| hedge | 88% [83, 92] | 87% [81, 91] | +1 |
| booster | 73% [67, 78] | 68% [61, 74] | +5 |
| we | 100% [98, 100] | 99% [97, 100] | +1 |
| you | 100% [98, 100] | 96% [93, 98] | +4 |
| location_ref | 90% [85, 93] | 86% [80, 90] | +4 |
| revised_pdf | 55% [48, 61] | 48% [41, 55] | +7 |
| color_mark | 11% [7, 15] | 6% [4, 10] | +5 |
| promise_future | 34% [29, 41] | 39% [32, 46] | -5 |
| score_ask | 7% [4, 11] | 7% [4, 11] | +0 |
| nudge | 14% [10, 19] | 10% [7, 15] | +4 |
| md_heading | 52% [45, 58] | 46% [39, 53] | +6 |
| bold | 83% [78, 87] | 73% [67, 79] | +10 |
| bullet | 56% [50, 62] | 57% [50, 64] | -1 |
| table | 48% [41, 54] | 35% [28, 41] | +13 |
| blockquote | 44% [38, 51] | 37% [31, 44] | +7 |
| latex | 52% [46, 58] | 55% [48, 62] | -3 |
| link | 30% [24, 36] | 28% [22, 35] | +2 |
| number | 100% [98, 100] | 99% [96, 100] | +1 |
| point_label | 56% [50, 62] | 47% [40, 54] | +9 |
| thanks_in_first_40w | 66% [60, 72] | 65% [59, 72] | +1 |
| agree_in_first_40w | 2% [1, 4] | 3% [1, 6] | -1 |
| last_post_score_ask | 5% [3, 8] | 4% [2, 7] | +1 |

### Medians

| quantity | raised | unchanged | diff of medians [95%] |
|---|---|---|---|
| words | 1244.0 | 1063.0 | +181.0 [-28.0, +332.0] |
| posts | 4.0 | 3.0 | +1.0 [+0.0, +1.0] |
| first_post_words | 609.5 | 567.0 | +42.5 [-12.0, +90.0] |
| sent_len_median | 22.0 | 22.0 | +0.0 [-0.5, +1.0] |
| thanks_per_k | 4.2 | 3.4 | +0.8 [+0.0, +1.6] |
| apology_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| we_agree_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| you_are_right_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| respectfully_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| disagree_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| hedge_per_k | 3.1 | 2.8 | +0.3 [-0.2, +0.7] |
| booster_per_k | 1.0 | 1.0 | -0.0 [-0.3, +0.3] |
| we_per_k | 30.4 | 30.9 | -0.4 [-2.4, +1.7] |
| you_per_k | 10.3 | 9.7 | +0.6 [-0.8, +2.5] |
| location_ref_per_k | 3.7 | 3.8 | -0.1 [-1.0, +0.8] |
| revised_pdf_per_k | 0.5 | 0.0 | +0.5 [-0.2, +0.7] |
| color_mark_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| promise_future_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| score_ask_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| nudge_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| md_heading_per_k | 0.4 | 0.0 | +0.4 [-0.3, +0.9] |
| bold_per_k | 7.5 | 6.9 | +0.7 [-1.0, +3.0] |
| bullet_per_k | 1.5 | 1.8 | -0.3 [-1.5, +1.1] |
| table_per_k | 0.0 | 0.0 | +0.0 [+0.0, +2.9] |
| blockquote_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.4] |
| latex_per_k | 0.8 | 1.1 | -0.2 [-2.0, +1.5] |
| link_per_k | 0.0 | 0.0 | +0.0 [+0.0, +0.0] |
| number_per_k | 46.7 | 37.0 | +9.8 [+2.6, +15.7] |
| point_label_per_k | 2.3 | 0.0 | +2.3 [+0.0, +2.7] |

## Part 3. Format study: raised vs unchanged

Threads: 240 ICLR 2025 reviewer threads from rebuttal/iclr_threads/format_sample.jsonl (raised 120, unchanged 120), a subsample of the 441 above, joined on thread_id. Features are regex counts over the author posts, which never see the group (rebuttal/iclr_threads/format_study/groups.py; printout in format_study/output.txt). Each cell: count/threads = share [Wilson 95%]; diff = raised minus unchanged in points [Newcombe 95%]; * marks a difference whose interval excludes 0. Medians use a bootstrap interval (2,000 resamples). With 13 share features, about one chance gap is expected at the 5% level, and every gap is a correlation. The table and label gaps re-measure threads already in Part 1 (uses_tables, per_point_headings) and are not independent of it. "Near the cap" means a post body above 4,800 characters, since no post runs past about 5,000.

| feature | raised | unchanged | diff |
|---|---|---|---|
| Posts labelled as parts, such as (1/3) or Part 1 | 39/120 = 32% [25, 41] | 31/120 = 26% [19, 34] | +7 [-5, +18] |
| Any markdown table | 53/120 = 44% [36, 53] | 35/120 = 29% [22, 38] | +15 [+3, +27] * |
| A general response on the forum | 85/120 = 71% [62, 78] | 68/120 = 57% [48, 65] | +14 [+2, +26] * |
| Numbered point labels at line start (W1, Q2, Weakness 3) | 70/120 = 58% [49, 67] | 50/120 = 42% [33, 51] | +17 [+4, +29] * |
| Reviewer text quoted in a blockquote | 52/120 = 43% [35, 52] | 43/120 = 36% [28, 45] | +8 [-5, +20] |
| Markdown headings (#, ##, ###) | 25/120 = 21% [15, 29] | 25/120 = 21% [15, 29] | +0 [-10, +10] |
| Phrase naming the revised document ("in the revised manuscript") | 62/120 = 52% [43, 60] | 60/120 = 50% [41, 59] | +2 [-11, +14] |
| Colour marking named (in blue, highlighted) | 32/120 = 27% [20, 35] | 19/120 = 16% [10, 23] | +11 [+0, +21] * |
| Line numbers given (Line 139, L460) | 34/120 = 28% [21, 37] | 32/120 = 27% [20, 35] | +2 [-10, +13] |
| First sentence thanks the reviewer | 99/120 = 82% [75, 88] | 96/120 = 80% [72, 86] | +2 [-7, +12] |
| Last post ends with an invitation to ask more | 26/120 = 22% [15, 30] | 23/120 = 19% [13, 27] | +2 [-8, +13] |
| Opens with a "Dear Reviewer" line | 18/120 = 15% [10, 22] | 9/120 = 8% [4, 14] | +8 [-1, +16] |
| A post within 200 characters of the 5,000 cap | 46/120 = 38% [30, 47] | 28/120 = 23% [17, 32] | +15 [+3, +26] * |

| quantity | raised | unchanged | diff of medians [95%] |
|---|---|---|---|
| Author characters per thread | 8,252.0 (n=120) | 7,502.0 (n=120) | +750.0 [-1,428.5, +2,469.0] |
| Author posts per thread | 3.5 (n=120) | 3.0 (n=120) | +0.5 [+0.0, +1.0] |
| Characters per post (thread median) | 2,704.8 (n=120) | 2,757.5 (n=120) | -52.8 [-444.0, +329.0] |
| Tables per thread | 0.0 (n=120) | 0.0 (n=120) | +0.0 [+0.0, +1.0] |
| Words per numbered point (threads with labels) | 239.7 (n=70) | 218.8 (n=50) | +20.8 [-61.9, +69.9] |

Point level (643 numbered points in 120 threads; points cluster within threads, so these intervals are too narrow): a location named 52% against 42%, +9 [+1, +17]; a table in the answer 17% against 9%, +9 [+3, +14]; a number 65% against 59%, +6 [-1, +14]; a stated change 28% against 29%, -2 [-9, +5]; thanks in the first two sentences 24% against 20%, +4 [-3, +10].

### 2025 against 2026 in the search corpus

Matched comments (text contains "we thank" or "thank the reviewer", the only two 2026 queries) from rebuttal/results/style/author_comments.jsonl; corpus.py block of format_study/output.txt. Shares with Newcombe 95% intervals, medians with a 400-resample bootstrap.

| quantity | 2025 | 2026 | 2026 minus 2025 |
|---|---|---|---|
| reviewer-thread comments | 6,711 | 3,299 | |
| median characters per comment | 3,332 | 3,181 | -151 [-270, -43] |
| table | 15.7% | 21.3% | +5.6 [+4.0, +7.3] |
| part label | 22.7% | 23.5% | +0.8 [-1.0, +2.6] |
| numbered point label | 32.1% | 43.3% | +11.3 [+9.2, +13.3] |
| blockquote | 33.2% | 29.1% | -4.1 [-6.0, -2.2] |
| markdown heading | 15.5% | 23.7% | +8.2 [+6.5, +9.9] |
| bold lead-in line | 43.3% | 50.7% | +7.4 [+5.3, +9.5] |
| line numbers | 21.8% | 14.8% | -7.0 [-8.5, -5.4] |
| revised-document phrase | 38.6% | 36.3% | -2.3 [-4.3, -0.3] |
| colour or highlight named | 10.6% | 8.9% | -1.7 [-2.9, -0.4] |
| general responses | 909 | 170 | |
| median characters per general response | 1,856 | 2,017 | +161 [-292, +583] |
| general response opens "Dear" | 12.4% | 28.2% | +15.8 [+9.2, +23.3] |
| general response names the revised document | 54.6% | 32.4% | -22.2 [-29.5, -14.2] |
