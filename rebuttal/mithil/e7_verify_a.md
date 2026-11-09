# E7 strict second pass, items 1 to 15

Each paper's source is on DeltaAI under /work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/<hours>/<run>/reference/latex, and the file:line references below are relative to that folder. Frozen fields come from the eval_100.jsonl match_target on DeltaAI and from rebuttal/results/e7/v3_failures.csv. The decision rule is the one in the brief: a target is frozen wrong only when the paper states something that contradicts it, frozen right when the frozen value appears for the frozen metric and nothing contradicts the dataset, split or method, and unclear when only a plot image or an ambiguous configuration could settle it.

1. 2505.15201
First pass: frozen wrong. My verdict: unclear.
Quote: "The variance of our estimators is compared in \cref{fig:toyvariance} where $s^{(\textrm{loo}-1)}$ is the strongest." (main.tex:453)
Reason: the toy setup matches (main.tex:445-452, N(θ, 0.1), g(x)=x² on [0,1]), the caption confirms 10,000 estimates at k=4 (figures_tex/toyvariance.tex:4), and nothing in the text states a ratio or contradicts "~10x", so the ratio can only be read from figures/toyvariance.pdf at n=16, which a human must do.

2. 2505.17836
First pass: frozen wrong. My verdict: unclear.
Quote: "figure (b) shows the convergence of \textsc{GoRank} on different graph topologies; figure (c) compares the convergence of the ranking algorithms on a 2D Grid graph." (distributed/files/3b_rank_numerical.tex:3)
Reason: the metric (normalized absolute error), n=500, 100 trials and 8e4 iterations all match the same line, no endpoint value is stated in text, and the figures are PDFs without coordinate data, so a human must read the 2D grid GoRank curve at t=8e4 in Figure fig:main panel (b) or (c) (plot_rank_b.pdf, plot_rank_c.pdf).

3. 2505.23747
First pass: frozen wrong. My verdict: frozen wrong.
Quote: "& 16 & N/A & 51.6 & 42.3 & 47.1 \\" in the "Spatial-MLLM (w/o sa sampling)" block (nips25/tabs/tab-frame-ablation.tex:17)
Corrected target: VSI-Bench micro average 48.4 for Spatial-MLLM-4B, 16 frames, space-aware sampling (nips25/tabs/tab_vsibench.tex:30). If the uniform-sampling config is kept, the paper's value is 47.1 (tab-frame-ablation.tex:17).
Reason: the paper reports 47.1 for the exact frozen configuration (16 frames, uniform sampling) and never mentions the v1.1 model that the 51.13 belongs to, so the value contradicts the paper for that configuration.

4. 2507.02064
First pass: frozen wrong. My verdict: unclear.
Quote: "The network was queried for 5 seconds (100 timesteps), and all models successfully recalled the goal location with high accuracy." (sections/recall.tex:17)
Reason: the metric (L2 distance between decoded and target positions), the 100x100 cm arena and nearest-neighbor decoding all match, nothing contradicts "~0 cm", and the distance appears only in figures/recall.png, so a human must read panel (a) of Figure fig:recall for the r_mask=0.5 curve at the end of the query.

5. 2510.04136
First pass: frozen wrong. My verdict: frozen wrong.
Quote: "We train and evaluate MoME on LRS2 \cite{chung2017lip} and LRS3 \cite{afouras2018lrs3} datasets." (Sections/Experiments.tex:9); backbones are "Llama 3.2-1B, Llama 3.2-3B, and Llama 3.1-8B" (Sections/Experiments.tex:15).
Corrected target: WER 4.3% on LRS2 at audio-visual compression (16,5), MoME-23/4-MHSA with Whisper-small, AV-HuBERT Large and Llama 3.2-3B (Sections/Experiments.tex:52 and :70).
Reason: every frozen field is the placeholder "exact" or "full", and the claim it rests on names a 7B LoRA model, VoxCeleb2 and an LRS3 WER of 3.0, while the paper evaluates only LRS2 and LRS3 with MoME on Llama 3 backbones and its LRS3 row has no 3.0.

6. 2510.05874
First pass: frozen wrong. My verdict: frozen right.
Quote: "4 1.25936028325668e-06" in the MaNGO series (line width=2pt, steelblue) of the Deformable Plate (Easy) panel (figures/results/main_figure/dp_easy_main.tex:245)
Reason: the pgfplots data give 1.259e-6 for MaNGO at context size 4 on DP-easy, the caption names the metric as Full Rollout MSE (figures/results/main_figure.tex:32), and the 100-trajectory test split matches; the only difference is that the paper's value is a five-seed mean while the frozen config says single seed, which is a run detail and not a contradiction of the value.

7. 2510.09485
First pass: frozen right. My verdict: frozen right.
Quote: "The local minimax-optimal sampler consistently outperforms the global minimax-optimal sampler across all \( \varepsilon \) and \( f \)-divergences." (main.tex:833)
Reason: the frozen value is an ordering, the paper states it for the finite space [k] with uniform reference at k=20 and lists total variation among the evaluated divergences (main.tex:824), so the value and metric match; the scope wording should still note that the paper takes the global sampler's worst case over P([k]) and the local one over N_γ(μ_k) (main.tex:832-833).

8. 2511.00090
First pass: frozen wrong. My verdict: frozen wrong.
Quote: "We evaluate our method on representative diffusion-based video models: Open-Sora~\cite{Open-Sora}, Latte~\cite{ma2025latte}, and CogVideoX~\cite{yang2024cogvideox}." (sec/4_experiments.tex:7)
Corrected target: speedup 2.93x, LeMiCa-fast, Latte (16 frames, 512x512) (sec/4_experiments.tex:52), which is the "2.9X speedup on Latte" of sec/1_introduction.tex:36.
Reason: Wan2.1 does not appear in the paper or its supplement PDF, and the one B=17 result the paper gives is 2.45x on Qwen-Image (sec/appendix.tex:338), so the frozen model and the 2.59x both contradict the paper.

9. 2510.22123
First pass: frozen right. My verdict: frozen right.
Quote: "AniDS (Lmax=2) & \textbf{0.102}" in Table tab:md17, captioned "MAE for force prerdiction on MD17's test sets. Forces are reported in units of kcal/mol." (chapters/4_experiment.tex:48 and :22)
Reason: the value, the force MAE metric, the Aspirin column and the MD17 test sets all match, and the only difference is the unit label, which does not change the number.

10. 2410.15392
First pass: frozen wrong. My verdict: frozen wrong.
Quote: "Similar to LocalRF~\cite{localrf}, we adopt 9 scenes, covering large-scale indoor and outdoor scenes." (sec/4_exp.tex:12)
Corrected target: up to 3 dB higher PSNR (3.43 dB over CF-3DGS at 1 FPS) and nearly 40% lower ATE at 1 FPS, EF-3DGS against frame-based methods on the 9-scene Tanks and Temples protocol (sec/4_exp.tex:141 and :146, Tables tab:tnt_photo_results and tab:pose_acc).
Reason: the gain is stated, but only for the 9-scene Tanks and Temples tables, and the paper reports no per-scene result, so the single-scene scope contradicts the setting the number comes from.

11. 2411.06890
First pass: unclear. My verdict: frozen right.
Quote: "\acronym{} (Ours) & \textbf{8.60} & \textbf{1.51} & \textbf{246.6} & \textbf{1.17} & 0.52 & \textbf{6.84}\\" under the Intv. Pong SHD column (experiments.tex:46)
Reason: the value, the SHD metric, Interventional Pong and the SPARTAN method all match, and the paper never names the evaluation split, which the rule counts as no contradiction.

12. 2502.05795
First pass: unclear. My verdict: frozen right.
Quote: "Pre-LN + LayerNorm Scaling  & \textbf{25.76} & \textbf{20.35} & \textbf{18.20} & \textbf{15.71}\\" in Table tab:norm_comparison, captioned "Perplexity (↓) comparison of various layer normalization methods." (Curse_of_Depth.tex:489 and :475)
Reason: 25.76 is the LLaMA-130M perplexity with LayerNorm Scaling, and the paper names no evaluation set and says nothing that conflicts with C4 validation; for the author, the paper lists 2.2B training tokens for LLaMA-130M (Curse_of_Depth.tex:482), while the frozen config's 20K steps at 512 x 256 tokens gives 2.6B, a run detail outside the four checks.

13. 2504.13146
First pass: frozen wrong. My verdict: frozen wrong.
Quote: "consider a reasoning model that achieves 72\% accuracy on MMLU ... using antidistillation sampling with the same 4\% reduction in teacher accuracy significantly reduces the student's capabilities, lowering its accuracy to as low as 40\%." (main.tex:122)
Corrected target: distilled student accuracy as low as 40% on MMLU under antidistillation sampling, teacher at 72% minus about 4% (main.tex:122), with training for 4 epochs (main.tex:362). A GSM8K Platinum student value exists only in Figure fig:lambda (main.tex:301).
Reason: the paper attaches the 40% to MMLU and states 4 epochs where the frozen config says 3, so both the dataset and the configuration contradict the paper.

14. 2505.14827
First pass: unclear. My verdict: frozen right.
Quote: "& \cellcolor{gray!15}57.11 & \cellcolor{gray!15}59.53 & \cellcolor{gray!15}64.65" in the Nemotron-Super-49B MoI row, CountDown4 column (tex/tables/main_results_table.tex:39)
Reason: the value, the accuracy metric, the model and the method match, the dataset is cited to tinyzero (tex/s3.5_settings.tex:19), and the paper says nothing that conflicts with the Hugging Face name or the full-dataset scope, although no bib file is in the folder to confirm the citation entry.

15. 2505.19154
First pass: frozen wrong. My verdict: unclear.
Quote: "we report chamfer distance, PSNR (training-set view), reconstruction time, model size and point number." (neurips_2025.tex:292)
Reason: that label belongs to Table tab:accuracy_completion, where FHGS has PSNR 34.21, whereas the 30.9 comes from Tables tab:scene_comparison_indoor and tab:ablation_study (neurips_2025.tex:248 and :326), which do not say which views they use; a human must decide whether the training-view convention carries over to those two tables, and if it does the target becomes PSNR on training views.

Counts: frozen right 6 (items 6, 7, 9, 11, 12, 14). Frozen wrong 5 (items 3, 5, 8, 10, 13). Unclear 4 (items 1, 2, 4, 15). I disagree with the first pass on 8 items (1, 2, 4, 6, 11, 12, 14, 15).
