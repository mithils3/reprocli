# Reproduction rates by target-audit group

Script: `ev_targets.py`. Per-model tables for both versions: `ev_targets_raw.txt`.

## Checks
- All four yes: 55. Setting or label off: 16. Reproduced cells: 73 (A), 70 (B). All match.

## Cells reproduced

| Group | (A) submission | (B) revision | At least one agent (A / B) |
|---|---|---|---|
| All 100 | 73 of 400 = 18.2% | 70 of 400 = 17.5% | 34 of 100 / 32 of 100 |
| 55 pass all four | 38 of 220 = 17.3% | 36 of 220 = 16.4% | 18 of 55 / 16 of 55 |
| 45 other | 35 of 180 = 19.4% | 34 of 180 = 18.9% | 16 of 45 / 16 of 45 |
| 84 (100 minus 16 off) | 57 of 336 = 17.0% | 53 of 336 = 15.8% | 27 of 84 / 25 of 84 |

Fisher exact, 55 against 45: (A) p = 0.60; (B) p = 0.51.

## Best model per tier (Wilson 95% in brackets)

| Group, version | Run | Retrain | Reimplement |
|---|---|---|---|
| 55, A | dsv4 9 of 19 = 47.4% [27.3, 68.3] | muse 3 of 13 = 23.1% [8.2, 50.3] | muse 4 of 23 = 17.4% [7.0, 37.1] |
| 45, A | dsv4 5 of 15 = 33.3% [15.2, 58.3] | dsv4 7 of 20 = 35.0% [18.1, 56.7] | dsv4, muse 1 of 10 = 10.0% [1.8, 40.4] |
| 55, B | dsv4 9 of 19 = 47.4% [27.3, 68.3] | dsv4, muse, qwen3 2 of 13 = 15.4% [4.3, 42.2] | muse 4 of 23 = 17.4% [7.0, 37.1] |
| 45, B | dsv4, muse 4 of 15 = 26.7% [10.9, 52.0] | dsv4 7 of 20 = 35.0% [18.1, 56.7] | dsv4, muse 1 of 10 = 10.0% [1.8, 40.4] |

Tier order (run > retrain > reimplement, by best rate): kept for all 100 (A, B) and 55 (A); broken for 45 (A, B) and 55 (B).

## Assumptions
- Easy, Medium, Hard mean Run, Retrain, Reimplement.
- A cell is reproduced when its e6 row has index_verdict "reproduced". The 28 cells with no row count as not reproduced.
- (B) removes dsv4 and minimax on 2505.23747, muse on 2508.21046 (retrain), minimax on 2505.12677 (reimplement), and adds muse on 2503.23035 (run). Source: general.md grade-change table, STATUS.md line 14. The added Muse cell has no e6 row. 2510.08177 is partial and adds nothing.
- The 16 papers are the rows marked "setting or label" in `rebuttal/mithil/e7_merged.md`. All 16 lie among the 45 failing papers.
- Model codes as in e6; qwen3's display name is not in the files.
- Fisher treats cells as independent; the four cells of one paper are not, so p is optimistic.
