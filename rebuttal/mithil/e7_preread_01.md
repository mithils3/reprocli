# E7 pre-read, items 1 to 9

Paper source is on DeltaAI under /work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/<hours>/<run_id>/reference/latex. File paths below are relative to that latex folder. Figure values were not visible in the source, so a plot read is the only way to settle any value that appears only in a figure.

## 1. 2505.15201
Proposed verdict: frozen wrong
Evidence: main.tex:453: "The variance of our estimators is compared in \cref{fig:toyvariance} where $s^{(\textrm{loo}-1)}$ is the strongest." No ratio such as 10x appears in the text or caption. The toy setup (g(x)=x^2 on 0 to 1, main.tex:447-450) matches the frozen dataset.
Target if wrong: value "s^(loo-1) has the lowest variance of the compared estimators" (qualitative, toy setup, Figure in fig:toyvariance, k=4). Metric and dataset are right.

## 2. 2505.17836
Proposed verdict: frozen wrong
Evidence: distributed/files/3b_rank_numerical.tex:41: "Figure (b) highlights the impact of graph topology: as connectivity decreases, convergence slows, in line with the theoretical bounds." The text gives no endpoint near 0.05. Value search terms: "0.05", "normalized", "absolute error", "80000", "8e4".
Target if wrong: no numeric endpoint in text. Setup is right: normalized absolute error (3b_rank_numerical.tex:3), 100 trials, 8e4 iterations. Read the 2D grid curve in Figure (b) if a number is needed.

## 3. 2505.23747
Proposed verdict: frozen wrong
Evidence: nips25/tabs/tab-frame-ablation.tex:12: "16 & N/A & 52.7 & 43.8 & 48.4 \\". Search terms "51.1", "51.13", "micro", "Spatial-MLLM-4B". 51.13 appears nowhere in the source.
Target if wrong: VSI-Bench micro average (All) = 48.4 for Spatial-MLLM-4B at 16 frames with space-aware sampling (nips25/tabs/tab_vsibench.tex row Spatial-MLLM-4B). The v1.1 uniform-sampling variant named in the frozen config is not reported.

## 4. 2507.02064
Proposed verdict: frozen wrong
Evidence: sections/recall.tex:17: "all models successfully recalled the goal location with high accuracy." The L2 distance is plotted in Figure recall panel a (sections/recall.tex:17). The convergence wording refers to the PCA panel d (sections/recall.tex, later lines), not to distance. No numeric near-zero distance is given.
Target if wrong: metric (L2 distance, decoded vs ground truth) and arena (100x100 cm) are right. Value is qualitative only: "high accuracy" over 100 timesteps (5 s). A number would have to be read from panel a.

## 5. 2510.04136
Proposed verdict: frozen wrong
Evidence: Sections/Experiments.tex:31: "Main results for AVSR on LRS2 and LRS3 in terms of WER (\%)". The row at Sections/Experiments.tex:52 (MoME-23/4-MHSA, 12.7M) carries values 2.9, 3.0, 4.2, 4.3 under the WER header. Search terms "9.1", "WER", "VoxCeleb", "LoRA", "7B". No 9.1 appears.
Target if wrong: metric WER (%), datasets LRS2 and LRS3 (AVSR), method MoME-23/4-MHSA. The frozen fields "exact" and "full" are not targets. The 7B LoRA lip-reading model named in the frozen config is not in the paper.

## 6. 2510.05874
Proposed verdict: frozen wrong (value not in source)
Evidence: value not found anywhere in the paper source. Search terms "1.259", "1\.259", "e-6", "10^{-6}", "Deformable", "95%". The metric and split are in the text: figures/results/main_figure.tex:32: "We report the mean and 95\% confidence interval of the \emph{Full Rollout MSE} over five random seeds." DP-easy split 600/100/100 is in main.tex:626. The MaNGO method is the paper's method.
Target if wrong: metric Full Rollout MSE, dataset DP-easy test (100 trajectories), method MaNGO, 5 seeds with 95% CI. The number is only in the main_figure plots, so a plot read is needed to confirm 1.259e-6. The reason text's "all four failed" is too strict: metric, dataset and method all match the text.

## 7. 2510.09485
Proposed verdict: frozen right
Evidence: main.tex:871: "the local sampler consistently achieves lower worst‐case \( f \)-divergence than its global counterpart across all \( f \)-divergences and privacy levels \( \varepsilon \)." Total variation is one of the f-divergences (main.tex:416). The finite-space figure for k=20 (result_finite_k20.pdf, main.tex around line 847-851) is active and shows the same comparison.
Target if wrong: not wrong. The frozen value is an ordering, not a number, so no TV number is in the text. The frozen dataset (finite space, uniform reference) matches the finite k=20 figure.

## 8. 2511.00090
Proposed verdict: frozen wrong
Evidence: sec/4_experiments.tex:7: "We evaluate our method on representative diffusion-based video models: Open-Sora~\cite{Open-Sora}, Latte~\cite{ma2025latte}, and CogVideoX~\cite{yang2024cogvideox}." Wan is not in the paper. Search terms "Wan", "2.59", "2.9", "Notably" found no Wan and no 2.59. The sentence "a 2.9x speedup on the Latte model" quoted in the review was not found in the source.
Target if wrong: value 2.93x, LeMiCa-fast, Speedup column, Latte block (sec/4_experiments.tex:52). Dataset: Latte (16 frames, 512x512), not Wan2.1 T2V 1.3B. Method: LeMiCa-fast.

## 9. 2510.22123
Proposed verdict: frozen right
Evidence: chapters/4_experiment.tex:22: "Forces are reported in units of kcal/mol." Row at chapters/4_experiment.tex:48: "AniDS (Lmax=2) & \textbf{0.102}". The table is tab:md17, Aspirin column, so the value and the force MAE metric match.
Target if wrong: not needed. The only mismatch is the unit string (the frozen target says kcal/mol/Å, the paper says kcal/mol). Do not confuse this with the rMD17 appendix table in meV/Å (chapters/7_appendix.tex:222), which is a different table.

Counts: frozen right 2 (items 7, 9). Frozen wrong 7 (items 1 to 6, 8). Unclear 0. Items 2, 4 and 6 depend on values that may sit only in plots; the verdicts are wrong because the paper text does not state the frozen value.
