# E7 merged verdict sheet

The first pass was a fast model's check of each frozen target against its paper, and the second pass was a stronger model that called a target wrong only when the paper itself contradicts the frozen field. The author's verdict decides, and this sheet does not replace the Verdict lines in `e7_review.md`.

Paths in the evidence column are relative to each paper's `reference/latex` folder on DeltaAI. The verify files are in `rebuttal/mithil/`.

## Counts (second pass)

| Second-pass verdict | Count | Items |
|---|---|---|
| Right | 14 | 6, 7, 9, 11, 12, 14, 16, 17, 25, 26, 32, 41, 43, 44 |
| Wrong | 24 | 3, 5, 8, 10, 13, 18, 19, 20, 21, 22, 23, 24, 27, 29, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40 |
| Unclear | 7 | 1, 2, 4, 15, 28, 42, 45 |

Of the 24 wrong items, 8 have the frozen number wrong (3, 5, 8, 19, 24, 35, 36, 40). The other 16 have the number right and only a setting, label, split or dataset name off (10, 13, 18, 20, 21, 22, 23, 27, 29, 30, 31, 33, 34, 37, 38, 39). The split was made from each item's reason text. Where the reason does not say the frozen number is right, the item counts as number wrong.

## Look at these first

1. **Item 1, 2505.15201 (unclear).** Figure `fig:toyvariance` (`figures/toyvariance.pdf`, n = 16). Read whether the strongest estimator's variance is about 10 times lower than the alternatives.
2. **Item 2, 2505.17836 (unclear).** Figure `fig:main`, panels (b) and (c) (`plot_rank_b.pdf`, `plot_rank_c.pdf`). Read the GoRank curve on the 2D grid at t = 8e4 and check whether it sits near 0.05.
3. **Item 4, 2507.02064 (unclear).** Figure `fig:recall`, panel (a) (`figures/recall.png`). Read the r_mask = 0.5 curve at the end of the 5 second query and check for a value near 0 cm.
4. **Item 15, 2505.19154 (unclear).** Tables `tab:scene_comparison_indoor` (line 248) and `tab:ablation_study` (line 326). Decide whether they use training views. If they do, the target becomes PSNR on training views, not the 30.9 now in the frozen field.
5. **Item 18, 2505.24873 (wrong, needs a human).** The 32-frame sentence at `main.tex:492`. Decide whether it covers MiniMax-Remover as well as the baselines in the row at `main.tex:522`.
6. **Item 24, 2506.18896 (wrong, needs a human).** Table `tab:TAP_offline_select` (68.4 random, 84.8 selected) against `tables/RL_results_TAP.tex:10` and `:14` (84.8 for Qwen2.5-7B, no random baseline). Choose which 84.8 setting the target should name.
7. **Item 28, 2402.04579 (unclear).** Figure 4, `fig:cost` (`figs/final.pdf`, not in the source folder). Check whether the 100-run bars are for the Moons dataset.
8. **Item 42, 2510.20725 (unclear).** Top-right panel of `fig:other_problems` (`figures/navigation.png`). Check whether an RBF curve is plotted and bends below linear. The supplement at `7_appendix.tex:600` says that set used a Matérn kernel with nu = 1.5.
9. **Item 45, 2511.02225 (unclear).** Table `tab:policy_learning_app`, column "FIOC", value 0.95 ± 0.03 for Gym Fetch Task 1. Check the run configuration or the authors' code for whether the categorical or codebook mask variant filled that column.

## Full sheet (45 items)

Kind of error: "number" means the frozen number is wrong. "setting or label" means the number is right and a dataset, model, split, label or config value is off. "none" means the item is right or unclear.

| Item | Paper | First pass | Second pass | Kind of error | Corrected target (short) | Evidence (file:line) |
|---|---|---|---|---|---|---|
| 1 | 2505.15201 | wrong | unclear | none | n/a, see look-first 1 | main.tex:453; figures/toyvariance.pdf |
| 2 | 2505.17836 | wrong | unclear | none | n/a, see look-first 2 | distributed/files/3b_rank_numerical.tex:3 |
| 3 | 2505.23747 | wrong | wrong | number | 48.4 micro avg (space-aware); 47.1 for uniform 16 frames | nips25/tabs/tab-frame-ablation.tex:17; nips25/tabs/tab_vsibench.tex:30 |
| 4 | 2507.02064 | wrong | unclear | none | n/a, see look-first 3 | sections/recall.tex:17; figures/recall.png |
| 5 | 2510.04136 | wrong | wrong | number | WER 4.3 on LRS2, MoME-23/4-MHSA | Sections/Experiments.tex:9, :15, :52, :70 |
| 6 | 2510.05874 | wrong | right | none | n/a | figures/results/main_figure/dp_easy_main.tex:245; figures/results/main_figure.tex:32 |
| 7 | 2510.09485 | right | right | none | n/a | main.tex:824, :832-833 |
| 8 | 2511.00090 | wrong | wrong | number | 2.93x speedup, LeMiCa-fast, Latte | sec/4_experiments.tex:52; sec/1_introduction.tex:36 |
| 9 | 2510.22123 | right | right | none | n/a | chapters/4_experiment.tex:48, :22 |
| 10 | 2410.15392 | wrong | wrong | setting or label | up to 3 dB PSNR and about 40% lower ATE on the 9-scene protocol | sec/4_exp.tex:12, :141, :146 |
| 11 | 2411.06890 | unclear | right | none | n/a | experiments.tex:46 |
| 12 | 2502.05795 | unclear | right | none | n/a | Curse_of_Depth.tex:475, :482, :489 |
| 13 | 2504.13146 | wrong | wrong | setting or label | 40% on MMLU, 4 epochs | main.tex:122, :362; GSM8K value only in fig:lambda (main.tex:301) |
| 14 | 2505.14827 | unclear | right | none | n/a | tex/tables/main_results_table.tex:39; tex/s3.5_settings.tex:19 |
| 15 | 2505.19154 | wrong | unclear | none | n/a, see look-first 4 | neurips_2025.tex:248, :292, :326 |
| 16 | 2505.24452 | unclear | right | none | n/a | neurips_2025_arxiv.tex:472, :1782 |
| 17 | 2506.17475 | unclear | right | none | n/a | neurips2025_camera_ready.tex:856; line 919 |
| 18 | 2505.24873 | wrong | wrong | setting or label | SSIM 0.9842 on DAVIS, 32-frame evaluation, 6 steps | main.tex:492, :522 |
| 19 | 2506.01511 | wrong | wrong | number | APA-SG 89.0 and 83.4 on MN-v2 and Inc-v3 (RN-50 substitute) | paper.tex:67, :266, :295, :296 |
| 20 | 2506.08898 | unclear | wrong | setting or label | normalized HV 0.6411, POCCO-W on Bi-TSP50, trained across sizes 20 to 100 | arxiv.tex:142, :415, :574 |
| 21 | 2506.10943 | wrong | wrong | setting or label | base model is 32.7 (33.5 is train on passage) | neurips_2025.tex:111, :322, :335-336 |
| 22 | 2506.12025 | wrong | wrong | setting or label | up to 100x faster than classical solvers on IBC, 14,400 pairs | sections/numerical_experiments.tex:341; lines 300-302; sections/apppendix.tex:35-40 |
| 23 | 2506.13717 | wrong | wrong | setting or label | rs = 8.5 for CIFAR-10 | main-final.tex:509; lines 228, 534, 555 |
| 24 | 2506.18896 | wrong | wrong | number | 84.8 (Qwen2.5-14B, 1k selected) vs 68.4 random; see look-first 6 | tables/SFT_results.tex:17, :26; tables/RL_results_TAP.tex:10, :14 |
| 25 | 2506.20671 | wrong | right | none | n/a | sec/4_experiments.tex:153, :345; sec/6_appendix.tex:10, :328 |
| 26 | 2510.15194 | unclear | right | none | n/a | sec/4_exp.tex:23, :75 |
| 27 | 2510.21363 | wrong | wrong | setting or label | development set 20 samples, test set 100 | main.tex:187; line 252 |
| 28 | 2402.04579 | unclear | unclear | none | n/a, see look-first 7 | main.tex:384, :388-404 |
| 29 | 2502.01203 | wrong | wrong | setting or label | 66.1% win rate, Qwen 2.5 7B, two references | _NIPS_2025_-RLHF-MF.tex:653, :656, :670 |
| 30 | 2502.06684 | wrong | wrong | setting or label | 12 layers (6 SelfAtt_c, 6 SelfAtt_b); mean accuracy 77.0 | neurips_2025.tex:521, :699; figures/TabZilla_metric_Accuracy_datasets_ood.tex:6 |
| 31 | 2503.23035 | unclear | wrong | setting or label (wrong label, number within tolerance) | PSNR 27.69 for combination; 27.64 for random rotation | neurips_2025.tex:528, :535, :568, :569 |
| 32 | 2504.12397 | unclear | right | none | n/a | main_neurips.tex:378, :1134 |
| 33 | 2504.12463 | wrong | wrong | setting or label | validation perplexity 23.48, FineWeb, 10B tokens | common/sections/04-experimental_setup.tex:29-30; common/sections/05-evaluation.tex:49 |
| 34 | 2505.02391 | wrong | wrong | setting or label | GVM-RAFT++ on Qwen2.5-Math-1.5B, 72.90 vs 69.02 | contents/experiments.tex:6, :127, :131 |
| 35 | 2505.16927 | wrong | wrong | number | constrained (medoid) IFEval win rate 65.1 at 28.2k | Sections/appendix.tex:648-649 |
| 36 | 2505.24864 | wrong | wrong | number | 15.7 point average gain on the 136K five-domain blend | sec_exp.tex:10, :74, :78; neurips_2025.tex:221 |
| 37 | 2506.06991 | wrong | wrong | setting or label | CA_Z average AUC 0.91 over all tested compositions | neurips_2025.tex:500, :544, :573, :588 |
| 38 | 2506.07673 | wrong | wrong | setting or label | 37.2% estimation gap reduction over all 19 benchmarks | sections/experiment.tex:65, :384, :399 |
| 39 | 2506.18890 | wrong | wrong | setting or label | PSNR 27.443, 24 input views | floatings/fig_evaluation.tex:5; floatings/tab_full_const4d.tex:42; sec/4_experiment.tex:94, :144 |
| 40 | 2510.10480 | wrong | wrong | number | RADiAnce Top-N at N = 20, ISM 52.15, AAR 39.42, RMSD 2.29 | tables/retrieval_number.tex:13-14; tables/peptide.tex:14; tables/adaptive.tex:18; neurips_2025.tex:390 |
| 41 | 2510.19314 | wrong | right | none | n/a | main.tex:301, :317, :320, :388 |
| 42 | 2510.20725 | wrong | unclear | none | n/a, see look-first 8 | 5_experiments.tex:31, :52; 7_appendix.tex:600 |
| 43 | 2510.23577 | wrong | right | none | n/a | contents/experiments.tex:42, :51; contents/Appendix.tex:145, :153 |
| 44 | 2511.00119 | wrong | right | none | n/a | neurips_2025.tex:203, :239, :258 |
| 45 | 2511.02225 | unclear | unclear | none | n/a, see look-first 9 | sections/appendix.tex:117, :213-216; checklist.tex:126 |

## Item 31 note

The second pass calls item 31 (2503.23035) wrong. It also says the two values in the paper, 27.64 for random rotation and 27.69 for the combination, differ by 0.18%, which sits inside the 5% grading tolerance. The mismatch is therefore a wrong label, number within tolerance: the frozen pairing of 27.69 with random rotation is a label error, not a number error.
