# E7 second pass, items 31 to 45

Each paper was read on DeltaAI under /work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/.../reference/latex, and file:line references are relative to that folder. The decision rule was applied literally. A target is frozen wrong only when the paper states a different value for the same metric, dataset and method, a different dataset or split (training or evaluation) for that number, or a model or variant that the paper does not have. Run budget settings in the frozen configuration (seed count, number of runs, epochs, batch size, step count, hardware, and where the hyperparameters come from) are not dataset, split or method, so a paper that states different ones leaves the verdict at frozen right, and the mismatch is recorded as a config note with the paper's values.

31. 2503.23035
- First pass: unclear. Second pass: frozen wrong.
- Quote: neurips_2025.tex:568-569, "rotation & 27.64 & \textbf{5.14} & \textbf{2.45} & \textbf{0.81} \\ combination & \textbf{27.69} & \textbf{5.14} & \textbf{2.45} & \textbf{0.81}".
- Corrected target: PSNR 27.69 on PIE for FreeInv with the combination of transformations (line 569), or keep random rotation and use 27.64 (lines 528, 535 and 568).
- Reason: the paper gives random rotation as 27.64 three times and gives 27.69 only to the combination row, so the frozen pairing of 27.69 with random rotation contradicts the paper, although the 0.18% gap sits inside the 5% grading tolerance.

32. 2504.12397
- First pass: unclear. Second pass: frozen right.
- Quote: main_neurips.tex:1134, "Hyperparameters were selected by taking the configuration that performed best on the validation set, and reported performance was computed on the test set for those selected models."
- Reason: 79.30% and 81.94% are the Llama 3.2 1B test accuracies (line 378), rank 8 is inside the searched grid [6, 8, 16, 32], and the paper never states the selected rank for this cell, so nothing contradicts the frozen rank (it is unsupported, and the author may prefer to write "validation-selected rank").

33. 2504.12463
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: common/sections/04-experimental_setup.tex:29-30, "We train on FineWeb-Edu (for Table 2 and Figure 11) and FineWeb (for all other plots and results)".
- Corrected target: validation perplexity 23.48 for Default MoE 8c1 after 10B tokens, trained and validated on FineWeb (common/sections/05-evaluation.tex:49).
- Reason: the Loss-Free Balancing comparison is outside Table 2 and Figure 11 and carries no exception (the ReMoE paragraph at line 45 names its FineWeb-Edu exception explicitly), so the paper's own dataset rule contradicts the frozen FineWeb-Edu training corpus while the frozen FineWeb validation scope is right.

34. 2505.02391
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: contents/experiments.tex:6, "we conduct experiments with Qwen2.5-Math-1.5B and Qwen2.5-Math-7B".
- Corrected target: GVM-RAFT++ on Qwen2.5-Math-1.5B, Math500 Average@8 of 72.90 against 69.02 for RAFT++ (contents/experiments.tex:127 and 131).
- Reason: Llama-3.2-1B-Instruct appears nowhere in the source, so the frozen base model is not in the paper, while the frozen value ranges 71 to 73 and 66 to 69 do hold for the Qwen 1.5B rows.

35. 2505.16927
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: Sections/appendix.tex:648-649, "Unconstrained Iter 1 (28.2k) & 7.66 & 8.15 & 7.16 & 32.2 & 65.6\% ... Medoids Iter 1 (28.2k) & 7.63 & 8.14 & 7.11 & 31.9 & 65.1\%".
- Corrected target: IFEval win rate 65.1% for constrained (medoid clustering) STaPLe Iter 1 on Llama-3.1-8B-Instruct with 28.2k training samples, or keep 65.6% and change the variant to unconstrained.
- Reason: the paper reports a different number (65.1%) for the frozen constrained variant, and its Iter 1 training set is 28.2k samples where the frozen configuration says about 5k.

36. 2505.24864
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: sec_exp.tex:10, "a generalist model trained via reinforcement learning on a diverse, verifiable dataset of 136K problems across math, code, STEM, logic puzzles, and instruction following."
- Corrected target: 15.7 point average pass@1 gain over DeepSeek-R1-Distill-Qwen-1.5B on the six math benchmarks (60.14 against 44.45, sec_exp.tex:74 and 78), for ProRL trained on the 136K five-domain blend, about 16k GPU hours on four 8xH100 nodes.
- Reason: the frozen configuration trains on the DeepScaleR math set alone, which is only the 40k math part of the paper's training data (sec_experiment_details.tex:16), so that model is not in the paper. Config note: the paper speaks of "more than 2k training steps" (neurips_2025.tex:221), and the intro gives 14.7% for math (same line), which conflicts with the 15.7% that the table supports.

37. 2506.06991
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: neurips_2025.tex:573, "reporting the average AUC score and the bottom 10\% quantile for each method on each dataset, where the average is w.r.t. every tested combination of (alpha_llm, alpha_r, alpha_b)."
- Corrected target: CA_Z average AUC 0.91 on Toxicity with GPT-4-reliant agents, averaged over all tested compositions (Table tab:detect_gpt4, line 588), with the fixed composition (0.1, 0.05, 0.05) removed.
- Reason: the frozen configuration places 0.91 at one fixed worker composition, but the paper states that 0.91 averages over every tested composition with alpha_r and alpha_b sampled at random (line 544), and the fixed composition appears only in a score-distribution caption (line 500).

38. 2506.07673
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: sections/experiment.tex:399, "EGR stands for the estimation gap reduction compared with Random-Sampling, averaged over all benchmarks."
- Corrected target: Random-Sampling-Learn, interpolation split, n=50, estimation gap reduction of 37.2% averaged over all 19 benchmarks (row at line 384), with the MMLU restriction removed.
- Reason: the frozen configuration names the MMLU benchmark, while the paper gives 37.2% only as the all-benchmark average, which is what the frozen scope already says. Config note: the paper repeats each experiment over 100 random trials (line 65), where the frozen configuration says one run with seed 0.

39. 2506.18890
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: floatings/fig_evaluation.tex:5, "Alternating Canonical Views (4 camera poses, 24/24 timestamps seen, 24 input views in total)".
- Corrected target: PSNR 27.443 for 4D-LRM-Base at 256x256 on Consistent4D (re-rendered), Alternating Canonical Views with 24 input views over 24 frames (floatings/tab_full_const4d.tex:42).
- Reason: the paper states 24 input views for this evaluation setup (also sec/4_experiment.tex:94), and 12 input views is the training setting (sec/4_experiment.tex:144).

40. 2510.10480
- First pass: frozen wrong. Second pass: frozen wrong.
- Quote: tables/retrieval_number.tex:13-14, "Top-N & 10 & ... & 51.67±3.6 & 39.12 & 2.31 & 0.5129 ... Top-N & 20 & ... & 50.24±3.3 & 39.42 & 2.29 & 0.5227".
- Corrected target: RADiAnce with Top-N retrieval at N=20, LNR peptide benchmark, ISM 52.15%, 100 samples per test complex (tables/peptide.tex:14; neurips_2025.tex:390).
- Reason: the run that produced 52.15 has AAR 39.42, RMSD 2.29 and diversity 0.5227 (tables/adaptive.tex:18), which are the paper's Top-20 values, while the paper reports different AAR and RMSD (39.12 and 2.31) for Top-10.

41. 2510.19314
- First pass: frozen wrong. Second pass: frozen right.
- Quote: main.tex:301, "\textbf{0.7923{\tiny $\pm$0.10}} & \textbf{0.7429{\tiny $\pm$0.07}}", the CKA-RL row in the Freeway columns.
- Reason: the value, metric, Freeway eight-mode sequence, PPO, 1M steps per task and pool size 5 all match (lines 317 and 388). Config note: the paper averages over 10 seeds (main.tex:320), where the frozen configuration says one seed, which is a run budget difference.

42. 2510.20725
- First pass: frozen wrong. Second pass: unclear.
- Quote: 5_experiments.tex:52, "The results over 200 trials are shown in Figure~\ref{fig:other_problems} and demonstrate sublinear regret growth, consistent with our theory. Notably, in these sparse, less smooth environments, the RBF kernel accumulates regret more rapidly".
- Reason: the first pass was wrong to say the paper makes no sublinear claim for navigation, because line 52 makes it for the sparse navigation task, but the kernel is ambiguous: the main text implies an RBF run on navigation while 7_appendix.tex:600 says that set of experiments used a Matérn kernel with nu=1.5. The supplement config.yaml sets navigation with an RBF kernel and 200 trials. A human should look at the top-right panel of Figure fig:other_problems (figures/navigation.png, 5_experiments.tex:31) and check whether an RBF curve is plotted and bends below linear. Config note: one trial against the paper's 200 is a run budget difference.

43. 2510.23577
- First pass: frozen wrong. Second pass: frozen right.
- Quote: contents/experiments.tex:51, "& {GraphMixer} & 78.38 & 95.26 & ... & 71.57 & 98.89 \\", the GraphMixer row under "with TAMI" in the rnd block, WK column.
- Reason: 98.89 is the transductive Wikipedia AP for GraphMixer plus TAMI under random negative sampling, averaged over five runs (contents/Appendix.tex:145), and gamma 0.9 for Wikipedia matches the paper. The first pass's copy-error worry is unfounded because line 51 is the with-TAMI row, while the plain GraphMixer baseline at line 42 reads 97.23. Config note: the paper adopts DyGFormer's optimal hyperparameters (contents/Appendix.tex:153), where the frozen configuration says defaults.

44. 2511.00119
- First pass: frozen wrong. Second pass: frozen right.
- Quote: neurips_2025.tex:258, "& single & \textbf{20.73$\pm$8.45} & 0.24$\pm$0.04 & 14.90$\pm$2.55 & 171.06$\pm$81.98".
- Reason: the Xenium_C1 single-cell rectified flow FID (20.73) is far under the diffusion baseline (171.06), and 3-fold cross-validation is stated at line 239, so the qualitative claim, metric and sample match. Config note: the paper trains for 100 epochs with batch size 96 (line 203), where the frozen configuration says 50 epochs and batch size 16.

45. 2511.02225
- First pass: unclear. Second pass: unclear.
- Quote: sections/appendix.tex:117, "In policy learning tasks, we only use the variational masks for learning the regime variables."
- Reason: 0.95 ± 0.03 for Gym Fetch Task 1 sits in a column labelled only "FIOC" (sections/appendix.tex:213-216), and the paper defines two variational mask variants (categorical and codebook, line 77) without saying which one fills that column. A human should check the run configuration or the authors' code for which mask variant produced Table tab:policy_learning_app. Steps (2M, line 487) and seeds (5 or 10, checklist.tex:126) match.

Counts: frozen wrong 9 (31, 33, 34, 35, 36, 37, 38, 39, 40), frozen right 4 (32, 41, 43, 44), unclear 2 (42, 45). The second pass disagrees with the first pass on 6 items (31, 32, 41, 42, 43, 44).
