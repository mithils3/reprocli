# E7 strict second pass, items 16 to 30

File paths are relative to each paper's `reference/latex` folder on DeltaAI (`/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/<tier>/<run>/reference/latex`). Every verdict follows the literal rule: frozen wrong only when the paper states something that contradicts a frozen field, frozen right when the value is there and nothing in the paper contradicts the rest, unclear when only a plot image or an ambiguous passage could settle it. Nothing from outside the paper was used.

16. 2505.24452

First pass: unclear. This pass: frozen right.

Quote: "CIFAR10 consists of a training split of 50000 examples and a test split of 10000 examples." (neurips_2025_arxiv.tex:1782). The value is the UBA row, 75 epochs (25%) column, "94.57$\pm$0.3281" (line 472).

Reason: the paper describes only a training split and a test split for CIFAR10, so the 10,000-image test split is the only held-out set the "validation accuracy" can come from; nothing contradicts "CIFAR10 test set", and the config (lr 0.1, batch 128, weight decay 5e-4) matches lines 1787 to 1789.

17. 2506.17475

First pass: unclear. This pass: frozen right.

Quote: "We apply standard data augmentation techniques to the training set ... The test set is only normalized." (neurips2025_camera_ready.tex:856). The value is "\Cref{alg:heavy_ball_dlrt} & 94.35 & \textbf{79.01}" (line 919).

Reason: the paper names only a training set and a test set for CIFAR-10, and the config (tau 0.1, initial rank 150, 20 epochs, batch 128, lr 0.001, gamma 0.9) matches lines 822 to 834 and 926, so nothing contradicts the target.

18. 2505.24873

First pass: frozen wrong. This pass: frozen wrong (config only).

Quote: "We set the evaluate frame length as 32. To evaluate with same frame length, we expand input frame length for VideoComposer and FloED." (main.tex:492). The 480p and 81-frame setting is the latency measurement at line 490.

Corrected target: SSIM 0.9842, DAVIS (all 90 videos, split not named), MiniMax-Remover with 6 sampling steps and no CFG, evaluation frame length 32 ("Ours (6 steps)" row, main.tex:522).

Reason: the paper states a 32-frame evaluation length for the comparison table, which contradicts the frozen 81-frame config; the value, metric and dataset are right, and the missing "validation" label is not a contradiction.

19. 2506.01511

First pass: frozen wrong. This pass: frozen wrong.

Quote: "& APA-SG(Ours) & 89.0 & 83.4 & 99.6* & ... & 75.32" in the RN-50 substitute block, while 77.48 is the APA-GC row of the MobViT-s block (paper.tex:295 and paper.tex:266).

Corrected target: black-box ASR above 50% on MN-v2 and Inc-v3 with the RN-50 substitute, APA-SG (LoRA visual consistency stage included): 89.0 and 83.4 (paper.tex:295); with APA-GC the same cells are 97.6 and 93.5 (line 296).

Reason: the frozen value says the paper number is 77.48 averaged over 10 models, but the paper gives 77.48 for a different substitute and attack (MobViT-s, APA-GC) averaged over the 9 non-substitute models, and APA always includes the LoRA stage (paper.tex:67), so "no LoRA" is not the paper's method. The first-pass correction (77.48 over 10 models) keeps the wrong substitute and the wrong model count.

20. 2506.08898

First pass: unclear. This pass: frozen wrong (config only).

Quote: "All neural methods are trained on Bi-TSP100, except for CNH, WE-CA, and POCCO, which are trained across varying sizes $n \in \{20, 21, \dots, 100\}$." (arxiv.tex:574).

Corrected target: normalized HV 0.6411, POCCO-W on Bi-TSP50 (Table 1, arxiv.tex:415), one model trained across sizes 20 to 100 for 200 epochs, batch 64, beta 3.5, 4 FF experts plus 1 ID expert, Top-2, N = 101 weight vectors, reference point (35, 35); test-instance count not stated.

Reason: the paper says POCCO is trained across problem sizes 20 to 100 (and builds on WE-CA, "a unified model that generalizes across various problem sizes", line 142), which contradicts "trained on Bi-TSP50"; the 200-instance count is absent, which by itself would not count against the target.

21. 2506.10943

First pass: frozen wrong. This pass: frozen wrong (base value label).

Quote: "finetuning directly on the passage yields a negligible gain over the frozen base model (33.5\% vs.\ 32.7\%)" (neurips_2025.tex:322); the table rows read "Base model & 32.7" and "Train on Passage & 33.5" (lines 335 and 336).

Corrected target: full-scale single-passage (LoRA) no-context SQuAD accuracy, Qwen2.5-7B, base 32.7 to SEAL 47.0, evaluated on the 200-passage subset with 974 questions (line 602); the reduced-scale anchor (SEAL beats base) is unchanged.

Reason: the frozen field calls 33.5 the base score, which the table contradicts; the intro line 111 does say "from 33.5\% to 47.0\%", which is likely where the frozen reading came from, so this is a label fix and the direction anchor still holds.

22. 2506.12025

First pass: frozen wrong. This pass: frozen wrong.

Quote: "even though ULOT makes errors, it is up to $100$ times faster than classical solvers" (sections/numerical_experiments.tex:341, in the IBC section); SBM training is "$50000$ simulated pairs" (line 36).

Corrected target: up to 100x lower time than classical solvers (IBPP, MM, LBFGSB, Sinkhorn), ULOT on IBC fMRI graph pairs of 1000 nodes, 14,400 pairs with a 60/20/20 train/val/test split (lines 300 to 302), IBC model config (3 layers, MLP hidden 256, GCN hidden 128, temperature 5, sections/apppendix.tex:35 to 40).

Reason: the only measured 100x speedup is on IBC, and the frozen SBM config's 10k training pairs contradicts the paper's 50,000.

23. 2506.13717

First pass: frozen wrong. This pass: frozen wrong (config only).

Quote: "We use $m=16$ views for CIFAR-10 dataset ... $r_s=8.5$ is applied for CIFAR-10 and ImageNet-100/1K." (main-final.tex:509). The value is "\CLAP(ours) &90.21 &99.60" (line 555).

Corrected target: top-1 linear-evaluation accuracy 90.21 on CIFAR-10, ResNet-18, 16 views, rs = 8.5, 1000 pretraining epochs and 100 linear-probe epochs (lines 228 and 534); split not named.

Reason: the paper states rs = 8.5 for CIFAR-10, which contradicts the frozen rs = 7.0; the missing "validation" label is not a contradiction.

24. 2506.18896

First pass: frozen wrong. This pass: frozen wrong.

Quote: "Random & 16.7 ... & 20.0 ... & 68.4 ... & 34.8" in the offline data selection table, where ReasonFlux-PRM-7B selection gives 84.8 on MATH500 (tables/SFT_results.tex:17 and :26).

Corrected target: MATH500 84.8 for Qwen2.5-14B-Instruct fine-tuned on 1k ReasonFlux-PRM-7B selected samples against 68.4 for random selection (tab:TAP_offline_select). The only Qwen2.5-7B-Instruct 84.8 is Checkpoint 2 (SFT on 1k ReasonFlux-PRM-7B data) under rule-based GRPO against 74.0 for the original backbone (tables/RL_results_TAP.tex:10 and :14), and it has no random-selection baseline.

Reason: the paper's only random-selection baseline is 68.4, which contradicts the frozen "~73%", and the paper never runs SFT selection with ReasonFlux-PRM-1.5B; the author has to choose which of the two 84.8 settings the target should name.

25. 2506.20671

First pass: frozen wrong. This pass: frozen right.

Quote: "The dataset comprises 10 training sequences, 1 validation sequence, and 11 test sequences, with our experiments adhering to the standard split [44] of 3834 training and 815 validation grids." (sec/6_appendix.tex:10).

Reason: PQ-All 6.30 is the IPFormer row (sec/4_experiments.tex:153), the dual-head two-stage design is the final config (called (j) in the main ablation, sec/4_experiments.tex:345, and (r) in the appendix, sec/6_appendix.tex:328, both 6.30), and the paper never numbers the sequences, so "sequence 11" and "00-09" are unnamed details that nothing in the paper contradicts. The first pass relied on outside knowledge (sequence 08) and on a (j) label the frozen config does not use. The author may still want to drop the sequence numbers since the paper does not give them.

26. 2510.15194

First pass: unclear. This pass: frozen right.

Quote: "&          Ours & \textbf{89.68} &     \textbf{91.31} &   \textbf{99.59}" (sec/4_exp.tex:23, RN50 block, CUB column); "The synthetic dataset pool consists of approximately \(K\)=5 times the number of original training samples." (line 75).

Reason: the value, metric, RN50 backbone, SDXL synthesis and K = 5 pool all match, and the paper names no CUB split at all, so nothing contradicts "test set".

27. 2510.21363

First pass: frozen wrong. This pass: frozen wrong.

Quote: "We split the dataset into a development set of 20 samples and use the remaining 100 samples as the test set." (main.tex:187). The value is "FairImagen & 0.56 & 0.771 & 0.541 & 0.624" (line 252).

Corrected target: gender fairness 0.56 for FairImagen (FairPCA), 20-sample development set, 100-sample test set, 12 images per prompt, SD3 pipeline.

Reason: the paper's development set has 20 samples, which contradicts the frozen 30.

28. 2402.04579

First pass: unclear. This pass: unclear.

Quote: "Comparison of modification and competition costs across 100 experiments with different random seeds ... when considering the combined metric of modification cost and competition efficiency, it outperforms baselines" (main.tex:384, fig:cost).

Reason: the combined-cost claim is in the text, and "ANN" fits the paper's "Multilayer Perceptron" (line 390), but neither the caption nor lines 388 to 404 say which dataset the 100-run bars cover, and the figure file (figs/final.pdf) is not in the source folder. A human must open Figure 4 (fig:cost; it is the fourth figure in source order, so the frozen "Figure 5" points at the lambda_2 trade-off figure) and check whether the bars are for Moons.

29. 2502.01203

First pass: frozen wrong. This pass: frozen wrong.

Quote: "To validate that our algorithm works at a larger scale, we also applied it to the Qwen 2.5 7B model ... As a second reference, we used Qwen 2.5 14B Instruct." (_NIPS_2025_-RLHF-MF.tex:656). The value is "Ours (DPO with both references) & 66.1\%" (line 670).

Corrected target: win rate 66.1% against the preferred UltraFeedback answer, judged by GPT-4o, Qwen 2.5 7B after SFT, DPO with two references (the SFT model and Qwen 2.5 14B Instruct), alpha = 0.5; the held-out fraction is not stated.

Reason: the 0.5B-Instruct model with a 1.5B second reference belongs to the offline experiment scored by a reward model (line 653), while 66.1% comes from the separate 7B win-rate experiment.

30. 2502.06684

First pass: frozen wrong. This pass: frozen wrong (config only).

Quote: "We use an \methodname{} network with $12$ self-attention layers alternating between both type of attention ...: 6 blocks SelfAtt_c and 6 blocks SelfAtt_b." (neurips_2025.tex:699).

Corrected target: mean accuracy 77.0 +/- 1.8 on the 10 TabZilla datasets with more than 10 classes over 10 splits (figures/TabZilla_metric_Accuracy_datasets_ood.tex:6), EquiTabPFN with 12 self-attention layers (6 SelfAtt_c, 6 SelfAtt_b), 4 heads, dimension 512, hidden 1024, about 25M parameters, no ensembling (neurips_2025.tex:521).

Reason: the paper states 12 layers, which contradicts the frozen 6; since the run loads the released checkpoint, the fix is to the description and the value stands.

## Counts

Frozen right 4 (16, 17, 25, 26). Frozen wrong 10 (18, 19, 20, 21, 22, 23, 24, 27, 29, 30). Unclear 1 (28).

Against the first pass: 16, 17 and 26 move from unclear to frozen right, 25 moves from frozen wrong to frozen right, and 20 moves from unclear to frozen wrong. Item 19 keeps its verdict but gets a different correction. In 6 of the 10 frozen-wrong items (18, 20, 21, 23, 27, 30) the value is right and only a config detail or a label needs fixing.

Items a human must look at: 28 (Figure 4, which dataset the bars show), 24 (which 84.8 setting the target should name), and 18 (whether the 32-frame evaluation sentence covers MiniMax-Remover as well as the baselines).
