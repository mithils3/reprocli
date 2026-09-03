# Export report

Generated 2026-09-03 by export.py against SPEC.md v2.1.

## Counts per sweep

| sweep | agent | tier | n | mean score | reproduced |
|---|---|---|---|---|---|
| dsv4-run | DeepSeek-V4 | Run | 29 | 6.21 | 14 |
| dsv4-retrain | DeepSeek-V4 | Retrain | 28 | 6.43 | 9 |
| dsv4-reimplement | DeepSeek-V4 | Reimplement | 30 | 5.10 | 4 |
| qwen3-run | Qwen3.6-27B | Run | 34 | 3.91 | 5 |
| qwen3-retrain | Qwen3.6-27B | Retrain | 26 | 4.54 | 6 |
| qwen3-reimplement | Qwen3.6-27B | Reimplement | 30 | 3.27 | 2 |
| minimax-run | MiniMax-M2.7 | Run | 33 | 3.18 | 3 |
| minimax-retrain | MiniMax-M2.7 | Retrain | 32 | 3.41 | 5 |
| minimax-reimplement | MiniMax-M2.7 | Reimplement | 33 | 2.70 | 2 |
| muse-run | Muse Spark 1.2 | Run | 33 | 5.64 | 9 |
| muse-retrain | Muse Spark 1.2 | Retrain | 32 | 6.03 | 9 |
| muse-reimplement | Muse Spark 1.2 | Reimplement | 32 | 3.78 | 5 |

Total 372 runs across 12 sweeps.

## Dropped dissected runs

| sweep | arxiv | reason |
|---|---|---|
| muse-run | 2503.23035 | no pinned claude-sonnet-5 grade (last grader muse-spark-1.2-contributor) | 
| muse-reimplement | 2510.08177 | no pinned claude-sonnet-5 grade (last grader muse-spark-1.2-contributor) | 

## Score disagreements

The score stored on the dissection row against the pinned grade this export uses.

| run | dissection score | Claude Sonnet 5 score | grade source |
|---|---|---|---|
| qwen3-run-2410.18164 | 7 | 0 | pinned auditor pass |
| qwen3-run-2412.11979 | 8 | 4 | pinned auditor pass |
| qwen3-run-2502.05795 | 3 | 4 | pinned auditor pass |
| qwen3-run-2503.23035 | 7 | 8 | pinned auditor pass |
| qwen3-run-2504.20571 | 9 | 8 | pinned auditor pass |
| qwen3-run-2505.11483 | 7 | 6 | pinned auditor pass |
| qwen3-run-2505.14766 | 6 | 4 | pinned auditor pass |
| qwen3-run-2505.14827 | 7 | 0 | pinned auditor pass |
| qwen3-run-2505.19154 | 2 | 0 | pinned auditor pass |
| qwen3-run-2505.24864 | 6 | 4 | pinned auditor pass |
| qwen3-run-2506.02392 | 7 | 6 | pinned auditor pass |
| qwen3-run-2510.21311 | 3 | 0 | pinned auditor pass |
| qwen3-run-2511.16666 | 3 | 2 | pinned auditor pass |
| qwen3-reimplement-2507.06489 | 8 | 7 | pinned auditor pass |
| qwen3-reimplement-2510.08177 | 0 | 4 | pinned auditor pass |
| qwen3-reimplement-2510.25146 | 3 | 1 | pinned auditor pass |
| qwen3-reimplement-2505.12677 | 7 | 4 | pinned auditor pass |
| qwen3-reimplement-2402.04579 | 6 | 4 | pinned auditor pass |
| qwen3-reimplement-2505.16927 | 0 | 4 | pinned auditor pass |
| qwen3-reimplement-2506.00070 | 0 | 2 | pinned auditor pass |
| qwen3-reimplement-2505.22596 | 2 | 4 | pinned auditor pass |
| qwen3-reimplement-2507.02064 | 6 | 5 | pinned auditor pass |
| qwen3-reimplement-2506.02882 | 0 | 2 | pinned auditor pass |
| minimax-run-2506.20990 | 6 | 4 | pinned auditor pass |
| minimax-run-2502.06684 | 10 | 4 | pinned auditor pass |
| minimax-run-2505.11483 | 7 | 6 | pinned auditor pass |
| minimax-run-2510.21311 | 3 | 2 | pinned auditor pass |
| minimax-run-2505.19713 | 1 | 2 | pinned auditor pass |
| minimax-run-2505.14766 | 7 | 4 | pinned auditor pass |
| minimax-run-2511.00090 | 6 | 0 | pinned auditor pass |
| minimax-run-2505.10978 | 4 | 2 | pinned auditor pass |
| minimax-run-2511.16666 | 6 | 4 | pinned auditor pass |
| minimax-run-2505.18456 | 6 | 0 | pinned auditor pass |
| minimax-run-2505.23747 | 8 | 9 | pinned auditor pass |
| minimax-run-2510.23574 | 2 | 4 | pinned auditor pass |
| minimax-run-2410.18164 | 8 | 7 | pinned auditor pass |
| minimax-run-2505.10475 | 3 | 0 | pinned auditor pass |
| minimax-run-2506.01511 | 8 | 6 | pinned auditor pass |
| minimax-run-2412.11979 | 4 | 0 | pinned auditor pass |
| minimax-run-2505.14827 | 4 | 2 | pinned auditor pass |

## Failure-mode mapping

| source slug | mode | n |
|---|---|---|
| near-miss-partial | near-miss-partial | 68 |
| reproduced-clean | reproduced-clean | 58 |
| reimplement-without-validating | reimplement-without-validating | 53 |
| artifact-provenance-mismatch | artifact-provenance-mismatch | 36 |
| scope-substitution | scope-substitution | 34 |
| killed-before-the-number | killed-before-the-number | 23 |
| environment-fights | environment-fights | 22 |
| success | reproduced-clean | 15 |
| reimplement_without_validating | reimplement-without-validating | 8 |
| stale-artifact-reliance | stale-artifact-reliance | 8 |
| killed_before_the_number | killed-before-the-number | 6 |
| near_miss_partial | near-miss-partial | 6 |
| procrastination/wall-kill | procrastination/wall-kill | 5 |
| under-determined-target | other | 5 |
| scope-collapse | other | 4 |
| fabrication_or_provenance_break | other | 3 |
| unavailability-concluded-from-prose | other | 3 |
| quantitative-miss | near-miss-partial | 2 |
| scope_substitution | scope-substitution | 2 |
| context-or-round-exhaustion | other | 1 |
| context_or_round_exhaustion | other | 1 |
| environment_setup_spiral | environment-fights | 1 |
| eval-protocol-shopping | other | 1 |
| fabrication | other | 1 |
| procrastination | procrastination/wall-kill | 1 |
| protocol-drift-direction-flip | other | 1 |
| report-serialization-collapse | other | 1 |
| report-serialization-fault | other | 1 |
| tool-call-format-collapse | other | 1 |
| verified-non-attempt | other | 1 |

Runs displayed as `other`: 25.
Runs whose mode came from the repro_analyses fallback: 0.

## Band-consistency relabels

| run | from | to | pinned score | pinned verdict |
|---|---|---|---|---|
| qwen3-run-2503.23035 | near-miss-partial | reproduced-clean | 8 | reproduced |
| qwen3-run-2505.18809 | near-miss-partial | reproduced-clean | 8 | reproduced |
| minimax-run-2502.06684 | reproduced-clean | other | 4 | not_reproduced |
| minimax-run-2410.18164 | reproduced-clean | near-miss-partial | 7 | partial |
| minimax-run-2506.01511 | reproduced-clean | near-miss-partial | 6 | partial |

## Raw exit_reason values

Listed so the exit_label map can be completed.

| raw value | n | label |
|---|---|---|
| natural | 355 | Finished |
| context_budget | 9 | Context limit |
| budget_exhausted | 8 | Budget exhausted |

## Papers

Included runs whose arxiv is not in eval_100: none

Papers in eval_100 with no runs: 2510.20725

## Facing pass (SPEC 8.1 and 8.2)

Applied to the displayed narrative fields only, never to the transcript. Grades, verdicts, flag kinds and flag severities are untouched.

- characters removed from narrative text: 14176
- rationales with trailing serialization text trimmed: 0

Evidence quotes dropped:

| reason | quotes |
|---|---|
| auditor prose | 7 |

Agent self-report after normalisation:

| value | runs |
|---|---|
| not_reproduced | 208 |
| reproduced | 128 |
| partial | 23 |
| omitted | 13 |

Audit rationales that fell back (under 40 characters):

None.

Rules that fired, with the number of sentences deleted or spans replaced:

| rule | n |
|---|---|
| replace: band citation | 74 |
| replace: sweep | 68 |
| replace: criterion code | 48 |
| replace: srun: | 37 |
| replace: slurm | 37 |
| delete: human spot-check | 28 |
| replace: srun | 27 |
| replace: harness | 26 |
| replace: criterion code list | 17 |
| replace: sweeps | 15 |
| replace: per the rubric | 12 |
| replace: the rubric's | 8 |
| replace: pinned tuple | 6 |
| replace: rubric's band-N | 5 |
| delete: human reviewer should | 5 |
| replace: the frozen rubric | 4 |
| replace: higher band | 3 |
| replace: mre_config | 3 |
| replace: lockfile | 3 |
| replace: match_target | 3 |
| delete: confidence level | 2 |
| replace: srun time limit | 2 |
| replace: frozen eval set | 2 |
| delete: worth flagging for human review | 1 |
| replace: C1 criterion | 1 |
| replace: srun step limit | 1 |
| replace: srun steps | 1 |
| replace: self-graded | 1 |
| replace: criterion code parenthetical | 1 |
| replace: match_bar | 1 |
| replace: methodology_notes | 1 |
| replace: under the frozen rubric | 1 |

## Redactions

Every hide applied, with the characters it removed. `hide_sentences` runs before the facing pass, `hide_fields` after it.

None applied. redactions.json is empty.

## Leak gate

398 files under public/ scanned, 0 hits.

Clean.

### Longer words containing a brand name

Laguna is short enough to sit inside ordinary words, so the gate matches it as a whole token. Every longer word a plain substring `grep -i laguna` over public/ would additionally return is listed here, and there are no others.

| word | occurrences | what it is |
|---|---|---|
| Lagunas | 3 | the surname of an author of a benchmark paper |
| LagunaConfig | 1 | a model-config class in a library listing |

Total bytes of the exported data: 42,517,676 (42.5 MB).

## Concordance with the paper

Checked by concordance.py against public/data/index.json, one row per line of SPEC section 7. A FAIL is reported and never patched in the data.

| check | paper says | computed | |
|---|---|---|---|
| DeepSeek-V4 reproduced by tier | 14/29 (48%), 9/28 (32%), 4/30 (13%) | 14/29 (48%), 9/28 (32%), 4/30 (13%) | PASS |
| Retrain matched-number range | MiniMax-M2.7 5/32 (16%), Qwen3.6-27B 6/26 (23%), Muse Spark 1.2 9/32 (28%), DeepSeek-V4 9/28 (32%) | MiniMax-M2.7 5/32 (16%), Qwen3.6-27B 6/26 (23%), Muse Spark 1.2 9/32 (28%), DeepSeek-V4 9/28 (32%) | PASS |
| Retrain mean audit score range | 3.41 (MiniMax-M2.7) to 6.43 (DeepSeek-V4) | 3.41 (MiniMax-M2.7) to 6.43 (DeepSeek-V4) | PASS |
| Failed-run spend | mean 45%, median 27.4%, n=60 (15+19+26) | mean 45%, median 27.4%, n=60 (15+19+26) | PASS |
| 96 H100-hour band | mean spend 6.5%, 1 of 42 reproduced | mean spend 6.5%, 1 of 42 reproduced | PASS |
| Retrain near-miss | 15 of 28 near-miss-partial, 15 of 19 misses | 15 of 28 near-miss-partial, 15 of 19 misses | PASS |
| Retrain verified partial | 22 of 28 score 6 or better | 22 of 28 score 6 or better | PASS |
| Papers | 100 papers, 34 run / 33 retrain / 33 reimplement | 100 papers, 34 run / 33 retrain / 33 reimplement | PASS |
| Agents | 4 | 4 | PASS |

9 of 9 checks pass.

## Table: primary failure mode by tier

The shape of the paper's tab:failure-modes, from the same data the site shows.

**DeepSeek-V4 (n=87)**

| mode | Run | Retrain | Reimplement | All |
|---|---|---|---|---|
| reproduced-clean | 14 | 9 | 3 | 26 |
| near-miss-partial | 5 | 15 | 6 | 26 |
| reimplement-without-validating | 2 | 1 | 8 | 11 |
| environment-fights | 0 | 0 | 1 | 1 |
| artifact-provenance-mismatch | 4 | 2 | 0 | 6 |
| scope-substitution | 3 | 0 | 6 | 9 |
| stale-artifact-reliance | 1 | 0 | 0 | 1 |
| procrastination/wall-kill | 0 | 1 | 0 | 1 |
| killed-before-the-number | 0 | 0 | 2 | 2 |
| other | 0 | 0 | 4 | 4 |
| **total** | 29 | 28 | 30 | 87 |

**Qwen3.6-27B (n=90)**

| mode | Run | Retrain | Reimplement | All |
|---|---|---|---|---|
| reproduced-clean | 5 | 7 | 3 | 15 |
| near-miss-partial | 8 | 2 | 6 | 16 |
| reimplement-without-validating | 5 | 3 | 8 | 16 |
| environment-fights | 3 | 3 | 1 | 7 |
| artifact-provenance-mismatch | 0 | 2 | 0 | 2 |
| scope-substitution | 2 | 0 | 2 | 4 |
| stale-artifact-reliance | 1 | 0 | 0 | 1 |
| procrastination/wall-kill | 0 | 0 | 0 | 0 |
| killed-before-the-number | 9 | 4 | 6 | 19 |
| other | 1 | 5 | 4 | 10 |
| **total** | 34 | 26 | 30 | 90 |

**MiniMax-M2.7 (n=98)**

| mode | Run | Retrain | Reimplement | All |
|---|---|---|---|---|
| reproduced-clean | 3 | 5 | 1 | 9 |
| near-miss-partial | 2 | 6 | 1 | 9 |
| reimplement-without-validating | 6 | 7 | 14 | 27 |
| environment-fights | 8 | 2 | 1 | 11 |
| artifact-provenance-mismatch | 4 | 1 | 8 | 13 |
| scope-substitution | 2 | 7 | 4 | 13 |
| stale-artifact-reliance | 2 | 1 | 0 | 3 |
| procrastination/wall-kill | 0 | 0 | 3 | 3 |
| killed-before-the-number | 3 | 2 | 0 | 5 |
| other | 3 | 1 | 1 | 5 |
| **total** | 33 | 32 | 33 | 98 |

**Muse Spark 1.2 (n=97)**

| mode | Run | Retrain | Reimplement | All |
|---|---|---|---|---|
| reproduced-clean | 8 | 9 | 5 | 22 |
| near-miss-partial | 8 | 15 | 2 | 25 |
| reimplement-without-validating | 1 | 0 | 6 | 7 |
| environment-fights | 2 | 1 | 1 | 4 |
| artifact-provenance-mismatch | 9 | 3 | 3 | 15 |
| scope-substitution | 0 | 0 | 10 | 10 |
| stale-artifact-reliance | 2 | 1 | 0 | 3 |
| procrastination/wall-kill | 0 | 1 | 1 | 2 |
| killed-before-the-number | 0 | 2 | 1 | 3 |
| other | 3 | 0 | 3 | 6 |
| **total** | 33 | 32 | 32 | 97 |

**All agents pooled (n=372)**

| mode | Run | Retrain | Reimplement | All |
|---|---|---|---|---|
| reproduced-clean | 30 | 30 | 12 | 72 |
| near-miss-partial | 23 | 38 | 15 | 76 |
| reimplement-without-validating | 14 | 11 | 36 | 61 |
| environment-fights | 13 | 6 | 4 | 23 |
| artifact-provenance-mismatch | 17 | 8 | 11 | 36 |
| scope-substitution | 7 | 7 | 22 | 36 |
| stale-artifact-reliance | 6 | 2 | 0 | 8 |
| procrastination/wall-kill | 0 | 2 | 4 | 6 |
| killed-before-the-number | 12 | 8 | 9 | 29 |
| other | 7 | 6 | 12 | 25 |
| **total** | 129 | 118 | 125 | 372 |
