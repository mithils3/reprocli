# E7: ten rescore corrections against the second pass's eight

| Paper id | Target | Rescore says | Second pass says | Class |
|---|---|---|---|---|
| 2505.23747 | VSI-Bench micro average, Spatial-MLLM-4B | Frozen 51.13 (v1.1 README) is wrong; corrected to 48.4 (16 frames, space-aware sampling) | Number wrong (item 3): 48.4 | A, number wrong in both. Changes verdict: dsv4-run and minimax-run go from reproduced to partial |
| 2511.00090 | Latte latency speedup | Frozen 2.59x (Wan2.1, not in paper); corrected to 2.93x (LeMiCa-fast on Latte) | Number wrong (item 8): 2.93x | A, number wrong in both |
| 2506.18896 | MATH500 with ReasonFlux-PRM-7B selected data | Frozen above 80% (vs ~73% random); corrected to 84.8 vs 68.4 (Qwen2.5-14B) | Number wrong (item 24): the author must pick which 84.8 setting | A, number wrong in both |
| 2510.10480 | RADiAnce ISM | Frozen 52.15 at Top-10; corrected to Top-20 with 52.15 kept, so only the setting changes | Number wrong (item 40): ISM 52.15 at N = 20 | A, the two passes disagree on the number |
| 2505.16927 | STaPLe IFEval win rate | Frozen 65.6 (constrained); corrected to the unconstrained Iter 1 row with 65.6 kept | Number wrong (item 35): constrained (medoid) 65.1 at 28.2k | A, the two passes disagree on the number |
| 2506.18890 | 4D-LRM PSNR on Consistent4D | Frozen 27.443 at 12 input views; corrected to 24 input views, value kept | Setting or label (item 39): 27.443 at 24 views | B, setting only in second pass |
| 2502.01203 | Multi-reference DPO win rate | Frozen 66.1% with a 1.5B second reference; corrected to the Qwen 2.5 14B second reference | Setting or label (item 29): 66.1% with Qwen 2.5 7B and two references | B, setting only in second pass |
| 2504.13146 | Antidistillation distilled-student accuracy | Frozen ~40% at 3 epochs; corrected to 4 epochs | Setting or label (item 13): 40% on MMLU, 4 epochs | B, setting only in second pass |
| 2505.02391 | GVM-RAFT++ on Math500 | Frozen ~71 to 73% on Llama-3.2-1B; corrected to Qwen2.5-Math-1.5B, 72.90 vs 69.02 | Setting or label (item 34): 72.90 vs 69.02 on Qwen2.5-Math-1.5B | B, setting only in second pass |
| 2410.15392 | EF-3DGS PSNR and ATE gain | Frozen claim on one scene; corrected scope to the 9-scene protocol | Setting or label (item 10): up to 3 dB and about 40% on the 9-scene protocol | B, setting only in second pass |
| 2510.04136 | WER on LRS2 | Not corrected | Number wrong (item 5): WER 4.3 on LRS2 | D, second pass only |
| 2506.01511 | APA-SG on MN-v2 and Inc-v3 | Not corrected | Number wrong (item 19): 89.0 and 83.4 | D, second pass only |
| 2505.24864 | Average gain on the 136K blend | Not corrected | Number wrong (item 36): 15.7 points | D, second pass only |

Class A is number wrong in both passes (5 targets). Class B is corrected in the rescore but setting or label only in the second pass (5 targets). Class C, corrected in the rescore but right or unclear in the second pass, is empty. Class D is a second-pass number-wrong target the rescore did not correct (3 targets).

Under the rescore rule the count is 10, and under the second-pass rule it is 8, so the two rules share 5 targets and differ on 5 in each direction. The only reproduced-cell change comes from 2505.23747, which is class A and sits in both rules: the dsv4 Run best falls from 14 to 13 of 34 (41.2% to 38.2%), overall reproduced cells fall from 73 to 71 of 400, and the Retrain and Reimplement bests do not move. The class D targets were never re-graded, so their cell counts are not known from this rescore.
