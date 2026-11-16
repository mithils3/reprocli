# Second round: what the author's second reply looks like when the reviewer then raises

Threads coded: 320 of 320 sampled (ICLR 2025, public mirror). Each has a review, a first author reply, a reviewer follow-up that states no raise, a second author reply, and a later reviewer comment of 150 characters or more. Half were sampled where a regex found a raise in the later comment and half where it did not.

## Outcome

The outcome is the coder's reading of the reviewer's later comment (the coder saw no author text). It marks a stated raise in 135 of 320 threads, and agrees with the regex flag used for sampling in 285 of 320 (89%).

| Reviewer's later stance | raised | not raised |
|---|---|---|
| unconvinced | 14 | 140 |
| partly | 65 | 29 |
| satisfied | 56 | 10 |
| unclear | 0 | 6 |

## Where the reviewer stood before the second reply

Raised n = 135, not raised n = 185. Gap is raised minus not raised in points, with a 95% interval (Newcombe).

| Reviewer's follow-up | raised | not raised | gap |
|---|---|---|---|
| reviewer stance: question only | 27 (20%) | 16 (9%) | +11 [+4, +20] * |
| reviewer stance: partly | 35 (26%) | 30 (16%) | +10 [+1, +19] * |
| reviewer stance: new concern | 4 (3%) | 0 (0%) | +3 [+0, +7] * |
| reviewer stance: satisfied | 4 (3%) | 5 (3%) | +0 [-4, +5] |
| reviewer asked for a new experiment | 47 (35%) | 80 (43%) | -8 [-19, +2] |
| three or more concerns in the follow-up | 64 (47%) | 104 (56%) | -9 [-20, +2] |
| reviewer stance: unconvinced | 65 (48%) | 134 (72%) | -24 [-34, -13] * |

## All threads

Raised n = 135, not raised n = 185. Gap is raised minus not raised in points, with a 95% interval (Newcombe).

| Feature of the second reply | raised | not raised | gap |
|---|---|---|---|
| tone warm | 75 (56%) | 66 (36%) | +20 [+9, +30] * |
| answers every concern raised | 111 (82%) | 130 (70%) | +12 [+2, +21] * |
| points to revision | 89 (66%) | 104 (56%) | +10 [-1, +20] |
| concedes with change | 68 (50%) | 76 (41%) | +9 [-2, +20] |
| numbers table | 39 (29%) | 42 (23%) | +6 [-3, +16] |
| new result | 68 (50%) | 85 (46%) | +4 [-7, +15] |
| concedes no change | 38 (28%) | 46 (25%) | +3 [-6, +13] |
| promises later | 49 (36%) | 62 (34%) | +3 [-8, +13] |
| restates first reply | 2 (1%) | 4 (2%) | -1 [-4, +3] |
| disagrees without evidence | 10 (7%) | 26 (14%) | -7 [-13, +0] |
| disagrees with evidence | 31 (23%) | 58 (31%) | -8 [-18, +2] |
| tone defensive | 14 (10%) | 42 (23%) | -12 [-20, -4] * |
| clarification only | 30 (22%) | 65 (35%) | -13 [-22, -3] * |
| disagrees | 41 (30%) | 84 (45%) | -15 [-25, -4] * |

## Threads where the reviewer's follow-up was partly satisfied, unconvinced or raised a new concern

Raised n = 104, not raised n = 164. Gap is raised minus not raised in points, with a 95% interval (Newcombe).

| Feature of the second reply | raised | not raised | gap |
|---|---|---|---|
| tone warm | 57 (55%) | 55 (34%) | +21 [+9, +33] * |
| points to revision | 72 (69%) | 93 (57%) | +13 [+1, +24] * |
| concedes with change | 57 (55%) | 70 (43%) | +12 [-0, +24] |
| answers every concern raised | 84 (81%) | 114 (70%) | +11 [+0, +21] * |
| numbers table | 30 (29%) | 37 (23%) | +6 [-4, +17] |
| concedes no change | 34 (33%) | 44 (27%) | +6 [-5, +17] |
| new result | 54 (52%) | 77 (47%) | +5 [-7, +17] |
| promises later | 38 (37%) | 57 (35%) | +2 [-10, +14] |
| restates first reply | 2 (2%) | 4 (2%) | -1 [-4, +5] |
| disagrees with evidence | 30 (29%) | 54 (33%) | -4 [-15, +7] |
| disagrees without evidence | 10 (10%) | 25 (15%) | -6 [-13, +3] |
| disagrees | 40 (38%) | 79 (48%) | -10 [-21, +2] |
| tone defensive | 13 (12%) | 40 (24%) | -12 [-21, -2] * |
| clarification only | 20 (19%) | 57 (35%) | -16 [-25, -5] * |

## Threads where the reviewer's follow-up asked for a new experiment

Raised n = 47, not raised n = 80. Gap is raised minus not raised in points, with a 95% interval (Newcombe).

| Feature of the second reply | raised | not raised | gap |
|---|---|---|---|
| tone warm | 32 (68%) | 28 (35%) | +33 [+15, +48] * |
| numbers table | 24 (51%) | 29 (36%) | +15 [-3, +32] |
| points to revision | 35 (74%) | 48 (60%) | +14 [-3, +29] |
| new result | 37 (79%) | 53 (66%) | +12 [-4, +27] |
| answers every concern raised | 36 (77%) | 52 (65%) | +12 [-5, +26] |
| concedes with change | 26 (55%) | 35 (44%) | +12 [-6, +28] |
| restates first reply | 2 (4%) | 1 (1%) | +3 [-3, +13] |
| concedes no change | 14 (30%) | 23 (29%) | +1 [-14, +18] |
| promises later | 20 (43%) | 35 (44%) | -1 [-18, +16] |
| disagrees without evidence | 1 (2%) | 10 (12%) | -10 [-20, +0] |
| clarification only | 5 (11%) | 18 (22%) | -12 [-24, +2] |
| disagrees with evidence | 10 (21%) | 28 (35%) | -14 [-28, +3] |
| tone defensive | 4 (9%) | 18 (22%) | -14 [-25, -0] * |
| disagrees | 11 (23%) | 38 (48%) | -24 [-39, -7] * |

## Limits

The sample was drawn half and half on the regex flag, so the percentages describe each group and are not raise rates. Every gap is a correlation. About 14 features are tested in each table, so one gap with an interval that excludes zero (marked *) is expected by chance. The coders are Claude Haiku 5.5; the coder of the second reply never saw the reviewer's later comment, and the coder of the later comment never saw the second reply.
