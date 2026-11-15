# When reviewers reply: second pass, 2026-11-15

Same data as `reply_timing.md`: 300 public ICLR 2026 forums, 832 review threads in which the authors answered. Scripts: `rebuttal/scripts/reply_timing/` (run each with the folder of cached forum files as its argument). This pass counts 252 reviewer replies where the first pass counted 254.

**Limit of the data.** Reviewer comments stop at 10:57 UTC on 2025-11-28 in every forum, while authors keep posting until 12-04. ICLR's incident page logs the OpenReview identity bug on 11-27, and secondary reports say reviewer discussion was then frozen. The 2026 window therefore ends at an unplanned stop, so the data cannot show how replies bunch before a real deadline, and every total is a floor.

**Time from the author response to the reviewer's first reply** (747 threads answered before the stop; threads still silent at the stop count as unobserved from then on, Kaplan-Meier estimate):

| Within | 12 h | 1 day | 2 days | 3 days | 4 days | 5 days | 6 days | 7 days | 8 days | 10 days |
| :- | -: | -: | -: | -: | -: | -: | -: | -: | -: | -: |
| Reviewers who have replied | 3% | 6% | 10% | 14% | 18% | 26% | 30% | 34% | 41% | 45% |

**Weekday.** Replies per 100 silent thread-days (UTC): Mon 6.0, Tue 6.6, Wed 8.4, Thu 9.1, Fri 6.2, Sat 1.7, Sun 2.1.

**By initial rating** (0 to 10 scale): 2: 47/178 = 26%; 4: 107/338 = 32%; 6: 77/245 = 31%; 8: 20/61 = 33%. The intervals overlap.

**Per paper.** At least one reviewer replied on 149 of 218 papers (68%), and every reviewer replied on 10 (5%). On papers with three answered reviews: 27 of 39 (69%).

**What the first reply says** (keyword match on 252 replies, rough): raises the score 68 (27%), keeps it 78 (31%), both phrasings 10 (4%), a further question 37 (15%), other 59 (23%). Median length 386 characters. Authors answered the reply in 183 of 252 threads (73%), and the reviewer wrote a second time in 37 (15%).

**Threads placed like ours.** Authors answered 6.5 to 8 days before the stop: 88 of 243 reviewers replied (36%), lag quartiles 63, 102 and 130 hours. Of the 215 still silent after 84 hours, 60 replied later (28%), on days 3, 2, 1 and 0 before the stop in 15, 20, 18 and 6 threads. Authors answered 4 to 5.5 days before the stop: 28 of 110 replied (25%), lag quartiles 21, 48 and 64 hours.
