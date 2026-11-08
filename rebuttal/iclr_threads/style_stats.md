# Surface style of author replies: raised vs unchanged

Threads with author text under the review: raised n=244, unchanged n=197. Share rows: % of threads with at least one match [Wilson 95%]. Rate rows: median matches per 1,000 author words, with a bootstrap 95% interval on the difference of medians. Patterns are in style.py.

## Share of threads with the marker

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

## Medians

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
