# Export report

Generated 2026-08-31 by export.py against SPEC.md v2.1.

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

Total 275 runs across 9 sweeps.

## Dropped dissected runs

None. Every dissected run has a pinned Claude Sonnet 5 grade.

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
| reimplement-without-validating | reimplement-without-validating | 46 |
| near-miss-partial | near-miss-partial | 43 |
| reproduced-clean | reproduced-clean | 36 |
| scope-substitution | scope-substitution | 24 |
| artifact-provenance-mismatch | artifact-provenance-mismatch | 21 |
| killed-before-the-number | killed-before-the-number | 20 |
| environment-fights | environment-fights | 18 |
| success | reproduced-clean | 15 |
| reimplement_without_validating | reimplement-without-validating | 8 |
| killed_before_the_number | killed-before-the-number | 6 |
| near_miss_partial | near-miss-partial | 6 |
| stale-artifact-reliance | stale-artifact-reliance | 5 |
| procrastination/wall-kill | procrastination/wall-kill | 4 |
| scope-collapse | other | 4 |
| fabrication_or_provenance_break | other | 3 |
| under-determined-target | other | 3 |
| quantitative-miss | near-miss-partial | 2 |
| scope_substitution | scope-substitution | 2 |
| context-or-round-exhaustion | other | 1 |
| context_or_round_exhaustion | other | 1 |
| environment_setup_spiral | environment-fights | 1 |
| eval-protocol-shopping | other | 1 |
| fabrication | other | 1 |
| protocol-drift-direction-flip | other | 1 |
| report-serialization-fault | other | 1 |
| tool-call-format-collapse | other | 1 |
| verified-non-attempt | other | 1 |

Runs displayed as `other`: 19.
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
| natural | 261 | Finished |
| context_budget | 9 | Context limit |
| budget_exhausted | 5 | Budget exhausted |

## Papers

Included runs whose arxiv is not in eval_100: none

Papers in eval_100 with no runs: 2510.20725

## Facing pass (SPEC 8.1 and 8.2)

Applied to the displayed narrative fields only, never to the transcript. Grades, verdicts, flag kinds and flag severities are untouched.

- characters removed from narrative text: 61749
- rationales with trailing serialization text trimmed: 3

Evidence quotes dropped:

| reason | quotes |
|---|---|
| round outside the transcript | 35 |
| auditor prose | 24 |

Agent self-report after normalisation:

| value | runs |
|---|---|
| not_reproduced | 163 |
| reproduced | 84 |
| partial | 15 |
| omitted | 13 |

Audit rationales that fell back (under 40 characters):

| run | fallback |
|---|---|
| qwen3-run-2506.10351 | the dissection rationale_gist |

Rules that fired, with the number of sentences deleted or spans replaced:

| rule | n |
|---|---|
| replace: band citation | 201 |
| replace: criterion code | 178 |
| delete: human spot-check | 81 |
| replace: harness | 80 |
| replace: sweep | 65 |
| replace: slurm | 61 |
| replace: criterion code list | 49 |
| replace: per the rubric | 49 |
| replace: the rubric's | 32 |
| replace: rubric's band-N | 27 |
| delete: human reviewer should | 20 |
| replace: criterion code parenthetical | 13 |
| replace: sweeps | 11 |
| replace: sweep wall | 11 |
| delete: confidence is moderate | 10 |
| replace: the frozen rubric | 9 |
| delete: confidence level | 8 |
| replace: mre_config | 6 |
| replace: higher band | 5 |
| replace: pinned tuple | 5 |
| replace: srun time limit | 5 |
| replace: srun: | 5 |
| replace: lower band | 4 |
| delete: Invalid partition name specified | 4 |
| replace: sibling quantity, long form | 3 |
| replace: self-graded | 3 |
| replace: methodology_notes | 2 |
| replace: match_bar | 2 |
| replace: [tier]-tier residue | 2 |
| delete: a spot-check of/should/would | 2 |
| replace: srun | 2 |
| replace: C1 criterion | 2 |
| replace: srun steps | 2 |
| replace: though it should be human spot-checked | 1 |
| delete: human review of | 1 |
| replace: criterion criteria list | 1 |
| delete: shared SLURM job hosting | 1 |
| delete: at zero, EVERYTHING dies | 1 |
| replace: srun wrapper | 1 |
| replace: under the frozen rubric | 1 |
| delete: worth flagging for human review | 1 |
| replace: should be independently spot-checked in | 1 |
| delete: stateless resend architecture | 1 |
| delete: the (self-)auditor | 1 |
| delete: propose tracking this as a new sub-mode | 1 |
| replace: harness/formatting failure | 1 |
| delete: which the audit rationale's phrase | 1 |
| replace: srun error | 1 |
| replace: harness artifact | 1 |
| delete: see suspected_grading_error | 1 |
| delete: the previous agent ran | 1 |
| replace: lockfile | 1 |
| replace: Stage-7 auditor | 1 |
| delete: metering behavior | 1 |
| delete: OOM cascade incident | 1 |
| delete: outbound git protocol blocked | 1 |
| replace: srun/GPU-session | 1 |
| delete: worth flagging for tuple-quality review | 1 |
| delete: run_gpu tool bug | 1 |
| replace: sbatch | 1 |
| replace: srun step limit | 1 |
| replace: srun step | 1 |

## Redactions

Every hide applied, with the characters it removed. `hide_sentences` runs before the facing pass, `hide_fields` after it.

| kind | run | field or substrings | removed |
|---|---|---|---|
| hide_fields | dsv4-retrain-2504.12463 | analysis.evidence_quotes | 904 characters |
| hide_sentences | dsv4-reimplement-2510.04136 | corresponds to no table | 294 characters |
| hide_sentences | qwen3-run-2410.18164 | audit_result.json | 206 characters |
| hide_fields | qwen3-run-2503.18430 | analysis.failure_mode_detail | 1565 characters |
| hide_fields | qwen3-run-2504.12397 | analysis.failure_mode_detail | 2310 characters |
| hide_fields | qwen3-run-2505.10475 | analysis.failure_mode_detail | 2056 characters |
| hide_fields | qwen3-run-2505.10475 | analysis.evidence_quotes | 1151 characters |
| hide_sentences | qwen3-run-2505.11483 | mis-specified | 327 characters |
| hide_fields | qwen3-run-2506.01511 | analysis.failure_mode_detail | 1712 characters |
| hide_sentences | qwen3-run-2506.02392 | should have been pinned | 222 characters |
| hide_sentences | qwen3-run-2506.12025 | worth flagging | 617 characters |
| hide_sentences | qwen3-retrain-2502.01203 | mis-specification | 184 characters |
| hide_sentences | qwen3-retrain-2505.17836 | read off a log-log figure | 482 characters |
| hide_fields | qwen3-retrain-2509.16391 | analysis.agent_trajectory_summary | 1349 characters |
| hide_sentences | qwen3-retrain-2510.09485 | garbled; flagged for human review | 298 characters |
| hide_fields | qwen3-reimplement-2503.02809 | analysis.agent_trajectory_summary | 2181 characters |
| hide_sentences | qwen3-reimplement-2510.25146 | should have been excluded | 484 characters |
| hide_sentences | qwen3-reimplement-2505.24452 | curation-level | 459 characters |
| hide_fields | qwen3-reimplement-2502.08924 | analysis.agent_trajectory_summary | 2764 characters |
| hide_fields | qwen3-reimplement-2511.20906 | analysis.agent_trajectory_summary | 2916 characters |
| hide_sentences | qwen3-reimplement-2510.04136 | needs correction; stale audit_result; fabricated | 1033 characters |
| hide_fields | qwen3-reimplement-2506.00070 | analysis.evidence_quotes | 316 characters |
| hide_fields | qwen3-reimplement-2506.00070 | analysis.agent_trajectory_summary | 2498 characters |
| hide_fields | minimax-run-2503.18430 | analysis.evidence_quotes | 520 characters |
| hide_fields | minimax-run-2505.18809 | analysis.failure_mode_detail | 606 characters |
| hide_fields | minimax-run-2505.18809 | analysis.agent_trajectory_summary | 905 characters |
| hide_fields | minimax-run-2505.18809 | analysis.evidence_quotes | 771 characters |
| hide_sentences | minimax-run-2505.14827 | diverges from a prior | 358 characters |
| hide_sentences | minimax-retrain-2510.09485 | garbled | 360 characters |
| hide_fields | minimax-retrain-2506.20233 | analysis.evidence_quotes | 1094 characters |
| hide_fields | minimax-retrain-2506.13717 | analysis.agent_trajectory_summary | 1599 characters |
| hide_sentences | minimax-retrain-2510.22123 | I diverge | 573 characters |

## Leak gate

301 files under public/ scanned, 0 hits.

Clean.

### Longer words containing a brand name

Muse and Laguna are short enough to sit inside ordinary words, so the gate matches them as whole tokens. Every longer word a plain substring `grep -i muse` or `grep -i laguna` over public/ would additionally return is listed here, and there are no others.

| word | occurrences | what it is |
|---|---|---|
| Museum | 28 | a Tanks-and-Temples scene named in a benchmark paper |
| nMuseum | 3 | the same scene name, after an escaped newline in the JSON |
| Lagunas | 2 | the surname of an author of a benchmark paper |
| muse_glimmer | 2 | a model architecture in a library listing |
| 1muser | 1 | an ANSI colour code abutting the word user |
| LagunaConfig | 1 | a model-config class in a library listing |

Total bytes of the exported data: 31,054,840 (31.1 MB).

## Concordance with the paper

Checked by concordance.py against public/data/index.json, one row per line of SPEC section 7. A FAIL is reported and never patched in the data.

| check | paper says | computed | |
|---|---|---|---|
| DeepSeek-V4 reproduced by tier | 14/29 (48%), 9/28 (32%), 4/30 (13%) | 14/29 (48%), 9/28 (32%), 4/30 (13%) | PASS |
| Retrain matched-number range | MiniMax-M2.7 5/32 (16%), Qwen3.6-27B 6/26 (23%), DeepSeek-V4 9/28 (32%) | MiniMax-M2.7 5/32 (16%), Qwen3.6-27B 6/26 (23%), DeepSeek-V4 9/28 (32%) | PASS |
| Retrain mean audit score range | 3.41 (MiniMax-M2.7) to 6.43 (DeepSeek-V4) | 3.41 (MiniMax-M2.7) to 6.43 (DeepSeek-V4) | PASS |
| Failed-run spend | mean 45%, median 27.4%, n=60 (15+19+26) | mean 45%, median 27.4%, n=60 (15+19+26) | PASS |
| 96 H100-hour band | mean spend 13.1%, 0 of 11 reproduced | mean spend 6.7%, 0 of 30 reproduced | **FAIL** |
| Retrain near-miss | 15 of 28 near-miss-partial, 15 of 19 misses | 15 of 28 near-miss-partial, 15 of 19 misses | PASS |
| Retrain verified partial | 22 of 28 score 6 or better | 22 of 28 score 6 or better | PASS |
| Papers | 100 papers, 34 run / 33 retrain / 33 reimplement | 100 papers, 34 run / 33 retrain / 33 reimplement | PASS |
| Agents | 3 | 3 | PASS |

- 96 H100-hour band: the paper pools 11 runs at this band and the export pools every run of the nine sweeps whose budget is 96, so the denominators differ; both find no reproduction

8 of 9 checks pass.

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

**All agents pooled (n=275)**

| mode | Run | Retrain | Reimplement | All |
|---|---|---|---|---|
| reproduced-clean | 22 | 21 | 7 | 50 |
| near-miss-partial | 15 | 23 | 13 | 51 |
| reimplement-without-validating | 13 | 11 | 30 | 54 |
| environment-fights | 11 | 5 | 3 | 19 |
| artifact-provenance-mismatch | 8 | 5 | 8 | 21 |
| scope-substitution | 7 | 7 | 12 | 26 |
| stale-artifact-reliance | 4 | 1 | 0 | 5 |
| procrastination/wall-kill | 0 | 1 | 3 | 4 |
| killed-before-the-number | 12 | 6 | 8 | 26 |
| other | 4 | 6 | 9 | 19 |
| **total** | 96 | 86 | 93 | 275 |
