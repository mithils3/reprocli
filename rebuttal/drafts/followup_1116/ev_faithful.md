# Faithful misses in RECLAIM: definition, count, and rates without them

The paper never uses the term "faithful miss." Its closest term is the Appendix G mode "Ran, outside tolerance" (slug `near-miss-partial`), which the Section 5 text describes as a run that executes a faithful pipeline and lands outside tolerance.

**Definition quotes**
- Section 5, paper line 415 (`paper_latex/paper.txt`: line 637): "a run outside tolerance executes a faithful pipeline and lands short of the bar."
- Appendix G, `paper_latex/appendix/g_taxonomy.tex` lines 93-95: "The agent runs the right pipeline and measures a number that misses the bar."

**Source of per-run labels:** `~/sweeps/paper-table-2026-09-05/resolved_modes.json` (`mode` field, joined to `tools/anon_viewer/public/data/index.json` by run id). Grades: `rebuttal/results/e6/table.csv`, which agrees with index.json on every score.

**Count rebuilt: yes, 76 of 400 cells.** By tier: Run 24, Retrain 37, Reimplement 15 (matches Figure 5). By model: dsv4 26, qwen3 16, minimax 7, muse 27 (matches `g_taxonomy.tex` line 40).

**Baseline, all 400 cells** (reproduced = score 8 or more)

| Tier | dsv4 | qwen3 | minimax | muse |
|---|---|---|---|---|
| Run | 14 of 34 = 41.2% | 5 of 34 = 14.7% | 3 of 34 = 8.8% | 9 of 34 = 26.5% |
| Retrain | 9 of 33 = 27.3% | 6 of 33 = 18.2% | 5 of 33 = 15.2% | 9 of 33 = 27.3% |
| Reimplement | 4 of 33 = 12.1% | 2 of 33 = 6.1% | 2 of 33 = 6.1% | 5 of 33 = 15.2% |

Overall: 73 of 400 = 18.2% (Wilson 95%: 14.8-22.3).

**After removing faithful-miss cells from each denominator**

| Tier | dsv4 | qwen3 | minimax | muse |
|---|---|---|---|---|
| Run | 14 of 29 = 48.3% | 5 of 28 = 17.9% | 3 of 31 = 9.7% | 9 of 24 = 37.5% |
| Retrain | 9 of 18 = 50.0% | 6 of 30 = 20.0% | 5 of 29 = 17.2% | 9 of 18 = 50.0% |
| Reimplement | 4 of 27 = 14.8% | 2 of 26 = 7.7% | 2 of 33 = 6.1% | 5 of 31 = 16.1% |

Overall: 73 of 324 = 22.5% (Wilson 95%: 18.3-27.4).

**Best model per tier, Wilson 95%**

| Tier | Before | After |
|---|---|---|
| Run | dsv4, 14 of 34 = 41.2% (26.4-57.8) | dsv4, 14 of 29 = 48.3% (31.4-65.6) |
| Retrain | muse, 9 of 33 = 27.3% (15.1-44.2); tied with dsv4 | muse, 9 of 18 = 50.0% (29.0-71.0); tied with dsv4 |
| Reimplement | muse, 5 of 33 = 15.2% (6.7-30.9) | muse, 5 of 31 = 16.1% (7.1-32.6) |

**Checks**
- Reproduced total 73 at submission: pass (score 8 or more). Figure 5 shows 72 because one run, `muse-run-2505.18456` (score 8), is labeled `artifact-provenance-mismatch`, not `reproduced-clean`.
- Three of the 76 cells (Reimplement muse 2505.12677 and 2506.02882; Retrain minimax 2506.13717) carry a `disqualified` verdict with score 0. These are the three near-miss labels the Appendix G relabel pass kept on disqualified runs. They are counted as faithful misses here, as the paper counts them.

**Script and outputs** (same folder)
- `/tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/ee88b5cc-f222-456d-9de1-997a82c38396/scratchpad/followup_1116/ev_faithful/faithful_rates.py`
- `/tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/ee88b5cc-f222-456d-9de1-997a82c38396/scratchpad/followup_1116/ev_faithful/results.txt`
