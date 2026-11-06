# E7 review sheet: 45 failing targets

E7 asked a second model, gpt-6.1-sol from OpenAI, to re-derive the target for each of the 100 evaluation papers from the paper text alone, blind to the frozen value. Each re-derived target was checked against the frozen one on four points: value (the paper reports the frozen number), metric, dataset or split, and method or variant. In the failure letters below, a means value, b metric, c dataset and d method. 55 of 100 targets pass all four. The 45 entries here are the rest, sorted so that value failures come first, then metric, then dataset, and method-only failures last. Verdicts go in `e7_verdicts.csv`.

1. 2505.15201 (Medium). Frozen: value "~10x lower variance than alternatives"; metric "empirical variance of gradient estimator"; dataset "toy Gaussian policy, g(x)=x², 0≤x≤1". Re-derived: no matching value; Figure 4 compares the estimators on this toy setup. Failed: value, metric, dataset, method. Look at: Figure 4.

   Verdict: ______ (frozen right / frozen wrong / unclear)

2. 2505.17836 (Medium). Frozen: value "~0.05"; metric "average normalized absolute error"; dataset "GoRank at t=80000, 100 trials". Re-derived: no endpoint near 0.05; the paper shows convergence plots and qualitative discussion. Failed: value. Look at: passage "Figure (b) highlights the impact of graph topology".

   Verdict: ______ (frozen right / frozen wrong / unclear)

3. 2505.23747 (Easy). Frozen: value "51.13%"; metric "VSI-Bench micro average accuracy (All)"; dataset "VSI-Bench test set". Re-derived: 51.13% appears nowhere; the reported micro average for Spatial-MLLM-4B (16 frames, space-aware sampling) is 48.4. Failed: all four. Look at: VSI-Bench results table, row "Spatial-MLLM-4B 65.3 34.8".

   Verdict: ______ (frozen right / frozen wrong / unclear)

4. 2507.02064 (Hard). Frozen: value "~0 cm after convergence"; metric "L2 distance from decoded position to target"; dataset "100x100 cm arena, nearest-neighbor decoding". Re-derived: metric and arena match, but the paper describes convergence without a numeric near-zero distance. Failed: value. Look at: Figure 2d, passage "In Figure 2d, the recall trajectories".

   Verdict: ______ (frozen right / frozen wrong / unclear)

5. 2510.04136 (Hard). Frozen: value "exact"; metric "exact"; dataset "full". The frozen fields hold no numbers. Re-derived: the paper reports 3.0 and 4.3 under the WER metric and no 9.1. Failed: value, dataset, method. Look at: row "MoME-23/4-MHSA 12.7M 2.9 3.0 4.2 4.3".

   Verdict: ______ (frozen right / frozen wrong / unclear)

6. 2510.05874 (Medium). Frozen: value "1.259e-6"; metric "full rollout MSE"; dataset "Deformable Plate Easy test split". Re-derived: no matching value. The reason text says metric, dataset and method are evaluated, yet all four checks failed; recheck it. Failed: all four. Look at: passage "We report the mean and 95% confidence interval".

   Verdict: ______ (frozen right / frozen wrong / unclear)

7. 2510.09485 (Medium). Frozen: value "local sampler TV below global sampler TV"; metric "worst-case total variation distance"; dataset "finite space with uniform reference". Re-derived: the ordering is stated in words, with no numbers to match. Failed: value, dataset. Look at: passage "The local minimax-optimal sampler consistently outperforms the global".

   Verdict: ______ (frozen right / frozen wrong / unclear)

8. 2511.00090 (Easy). Frozen: value "2.59x"; metric "latency speedup ratio"; dataset "Wan2.1 T2V 1.3B, 480p, single-video generation". Re-derived: 2.59x is not reported; the text gives a 2.9x speedup. Failed: all four. Look at: passage "Notably, our method achieves a 2.9× speedup".

   Verdict: ______ (frozen right / frozen wrong / unclear)

9. 2510.22123 (Medium). Frozen: value "0.102"; metric "Force MAE (kcal/mol/Å)"; dataset "MD17 aspirin test set". Re-derived: 0.102 kcal/mol in Table 1, so the value agrees. Failed: metric only, though the value matches. Look at: Table 1, check the row is force MAE.

   Verdict: ______ (frozen right / frozen wrong / unclear)

10. 2410.15392 (Hard). Frozen: value "up to 3 dB higher PSNR" (a gain claim); metric "PSNR and ATE"; dataset "one Tanks and Temples scene". Re-derived: no matching row; the gains are reported on a multi-scene protocol. Failed: dataset. Look at: passage "Similar to LocalRF [8], we adopt 9 scenes".

    Verdict: ______ (frozen right / frozen wrong / unclear)

11. 2411.06890 (Hard). Frozen: value "1.51"; metric "SHD of learned graph"; dataset "Interventional Pong test set". Re-derived: 1.51 is reported for SPARTAN in Table 1, but the paper does not call the evaluation split a test set. Failed: dataset. Look at: Table 1.

    Verdict: ______ (frozen right / frozen wrong / unclear)

12. 2502.05795 (Easy). Frozen: value "25.76"; metric "validation perplexity"; dataset "C4 validation set". Re-derived: no matching row; 25.76 is reported for LLaMA-130M with LayerNorm Scaling, with no C4 validation label. Failed: dataset. Look at: passage "To reduce variance, we report the average distance".

    Verdict: ______ (frozen right / frozen wrong / unclear)

13. 2504.13146 (Medium). Frozen: value "~40%"; metric "distilled student accuracy"; dataset "GSM8K Platinum test set". Re-derived: 40% is reported, but for MMLU, not GSM8K Platinum. Failed: dataset, method. Look at: passage "To illustrate our empirical results, consider a reasoning".

    Verdict: ______ (frozen right / frozen wrong / unclear)

14. 2505.14827 (Easy). Frozen: value "59.53%"; metric "accuracy (%)"; dataset "yzhuang/tinyzero-Countdown-Tasks-4, full dataset". Re-derived: 59.53 is reported for MoI with Nemotron-Super-49B on Count Down 4, but the paper does not name the tinyzero repo. Failed: dataset. Look at: passage "Count Down 4 [27] is a synthetic numerical".

    Verdict: ______ (frozen right / frozen wrong / unclear)

15. 2505.19154 (Easy). Frozen: value "30.9"; metric "PSNR on rendered novel views"; dataset "DTU scan24 test views". Re-derived: 30.9 is reported for FHGS on DTU scan24; the views are not labeled test or novel. Failed: dataset. Look at: passage "The ablation study is conducted on the scan24 of DTU".

    Verdict: ______ (frozen right / frozen wrong / unclear)

16. 2505.24452 (Hard). Frozen: value "94.57±0.33"; metric "validation accuracy (%)"; dataset "CIFAR10 test set". Re-derived: 94.57±0.3281 is in Table 2 as validation accuracy. The frozen metric and split contradict each other. Failed: dataset. Look at: Table 2.

    Verdict: ______ (frozen right / frozen wrong / unclear)

17. 2506.17475 (Hard). Frozen: value "79.01%"; metric "test accuracy"; dataset "CIFAR-10 test set". Re-derived: 79.01% is in Table 8. Failed: dataset. Look at: Table 8, check its split label.

    Verdict: ______ (frozen right / frozen wrong / unclear)

18. 2505.24873 (Easy). Frozen: value "0.9842"; metric "SSIM"; dataset "DAVIS validation set, 90 videos". Re-derived: 0.9842 is reported for 6-step MiniMax-Remover on DAVIS, with no validation label. Failed: dataset, method. Look at: passage "As show in Table 2, our method outperforms".

    Verdict: ______ (frozen right / frozen wrong / unclear)

19. 2506.01511 (Easy). Frozen: value ">50% black-box ASR"; metric "black-box attack success rate"; dataset "transfer to MobileNetV2 and Inception-v3". Re-derived: 77.48% average is reported, but Table 1 assigns it to LoRA-aligned APA-GC. Failed: dataset, method. Look at: Table 1; passage "We choose the widely used ImageNet-compatible Dataset".

    Verdict: ______ (frozen right / frozen wrong / unclear)

20. 2506.08898 (Medium). Frozen: value "0.6411"; metric "normalized hypervolume (HV)"; dataset "Bi-TSP50 test set, 200 instances". Re-derived: 0.6411 is reported for POCCO-W on Bi-TSP50, but the 200-instance split is not established. Failed: dataset, method. Look at: Table 1 (BiTSP and MOCVRP).

    Verdict: ______ (frozen right / frozen wrong / unclear)

21. 2506.10943 (Medium). Frozen: value "33.5% base to SEAL, full scale"; metric "no-context SQuAD QA accuracy"; dataset "50 SQuAD passages, reduced scale". Re-derived: 33.5% is the passage-only baseline; the frozen base scores 32.7%. SEAL values come from a 200-passage subset. Failed: dataset. Look at: passage "We evaluate on a 200-passage subset".

    Verdict: ______ (frozen right / frozen wrong / unclear)

22. 2506.12025 (Easy). Frozen: value "100x prediction speedup"; metric "solver time / ULOT time"; dataset "SBM graph pairs, test set". Re-derived: 100x is stated, but timed against IBC; SBM training uses 50,000 pairs, not 10k. Failed: dataset, method. Look at: passage "We construct a dataset of the 14400 different".

    Verdict: ______ (frozen right / frozen wrong / unclear)

23. 2506.13717 (Medium). Frozen: value "90.21%"; metric "top-1 classification accuracy"; dataset "CIFAR-10 validation set". Re-derived: 90.21 is reported, but not labeled validation, and the paper uses rs = 8.5. Failed: dataset, method. Look at: Table 7 (linear evaluation on CIFAR10).

    Verdict: ______ (frozen right / frozen wrong / unclear)

24. 2506.18896 (Easy). Frozen: value ">80% (vs ~73% random-selection baseline)"; metric "MATH500 accuracy"; dataset "Qwen2.5-7B-Instruct on ReasonFlux-PRM-selected data". Re-derived: 84.8 is reported, but from an SFT result the re-derivation says has a different data setup. Failed: dataset, method. Look at: Table 2 (SFT results).

    Verdict: ______ (frozen right / frozen wrong / unclear)

25. 2506.20671 (Easy). Frozen: value "6.30"; metric "PQ-All (%)"; dataset "SemanticKITTI validation sequence 11, 815 voxel grids". Re-derived: 6.30 is reported as PQ-All, but not tied to sequence 11. Failed: dataset, method. Look at: passage "The dataset comprises 10 training sequences, 1 validation".

    Verdict: ______ (frozen right / frozen wrong / unclear)

26. 2510.15194 (Hard). Frozen: value "89.68"; metric "downstream top-1 accuracy (%)"; dataset "CUB200-2011 test set". Re-derived: 89.68% is in Table 1. Failed: dataset. Look at: Table 1, check its split label.

    Verdict: ______ (frozen right / frozen wrong / unclear)

27. 2510.21363 (Medium). Frozen: value "0.560"; metric "gender fairness score (0-1)"; dataset "100-prompt test set, 30-prompt dev set". Re-derived: 0.56 is reported for FairImagen's FairPCA method, with 20 dev and 100 test samples, not 30 dev. Failed: dataset. Look at: passage "We split the dataset into a development set".

    Verdict: ______ (frozen right / frozen wrong / unclear)

28. 2402.04579 (Hard). Frozen: value "CCE achieves best combined cost"; metric "combined cost (modification cost plus λ₂ χ²-divergence)"; dataset "average over 100 experiments on Moons". Re-derived: paper reports CCE best on this trade-off; the method check fails. Failed: method. Look at: passage "Two non-linear methods, Multilayer Perceptron or Random Forest".

    Verdict: ______ (frozen right / frozen wrong / unclear)

29. 2502.01203 (Medium). Frozen: value "66.1%"; metric "win rate against preferred answer (%)"; dataset "UltraFeedback, 10% held-out". Re-derived: 66.1% is reported for DPO on Qwen 2.5 7B, not the 0.5B-Instruct model in the frozen config. Failed: method. Look at: passage "To validate that our algorithm works at a".

    Verdict: ______ (frozen right / frozen wrong / unclear)

30. 2502.06684 (Easy). Frozen: value "77.0 ± 1.8%"; metric "mean accuracy (%)"; dataset "10 TabZilla datasets with over 10 classes". Re-derived: 77.0 ± 1.8 is in Table 5. The frozen config has 6 self-attention layers; the text describes 12. Failed: method. Look at: Table 5; architecture passage.

    Verdict: ______ (frozen right / frozen wrong / unclear)

31. 2503.23035 (Easy). Frozen: value "27.69"; metric "PSNR (dB)"; dataset "PIE benchmark, 700 images at 512x512". Re-derived: Table 6 gives 27.64. The gap is |27.64 − 27.69| / 27.69 = 0.18%, inside the 5% tolerance. Failed: method. Look at: Table 6.

    Verdict: ______ (frozen right / frozen wrong / unclear)

32. 2504.12397 (Easy). Frozen: value "79.30% (LoRA) vs 81.94% (aLoRA)"; metric "classification accuracy (%)"; dataset "Bengali hate speech test split". Re-derived: both numbers are reported, but as validation-selected grid-search results, and rank 8 is not shown for both. Failed: method. Look at: passage "Following typical LoRA SFT best practices".

    Verdict: ______ (frozen right / frozen wrong / unclear)

33. 2504.12463 (Medium). Frozen: value "23.48"; metric "validation perplexity"; dataset "FineWeb validation set". Re-derived: 23.48 is reported on FineWeb for Default MoE with 8c1, a variant the re-derivation says does not match. Failed: method. Look at: passage "We train on FineWeb-Edu".

    Verdict: ______ (frozen right / frozen wrong / unclear)

34. 2505.02391 (Medium). Frozen: value "~71-73%"; metric "average@8 accuracy on MATH500"; dataset "MATH500 test set". Re-derived: 72.90 for GVM-RAFT++ is in the frozen range; the baseline is 69.02. Failed: method. Look at: passage "The experiments are conducted with Qwen series base".

    Verdict: ______ (frozen right / frozen wrong / unclear)

35. 2505.16927 (Hard). Frozen: value "65.6%"; metric "IFEval principle-following win-rate"; dataset "IFEval, 541 prompts, Prometheus-8x7B-v2.0 judge". Re-derived: 65.6% belongs to the unconstrained STaPLe Iter 1 model; the constrained version gives 65.1%. Failed: method. Look at: iteration table, row "Unconstrained Iter 1 (28.2k)".

    Verdict: ______ (frozen right / frozen wrong / unclear)

36. 2505.24864 (Easy). Frozen: value "15.7%"; metric "average pass@1 improvement on math benchmarks"; dataset "six math benchmarks". Re-derived: 15.7% is reported on these benchmarks. The frozen config says 16k training steps; the paper says about 16k GPU hours. Failed: method. Look at: passage "We conduct training on 4 8×H100-80GB".

    Verdict: ______ (frozen right / frozen wrong / unclear)

37. 2506.06991 (Medium). Frozen: value "0.91"; metric "AUC"; dataset "toxicity labeling set with GPT-4 samples, averaged". Re-derived: Table 1 gives 0.91 for the conditioned CA mechanism, a variant the frozen config does not name. Failed: method. Look at: Table 1; passage "For each value of αllm ranging from 0".

    Verdict: ______ (frozen right / frozen wrong / unclear)

38. 2506.07673 (Medium). Frozen: value "37.2%"; metric "estimation gap reduction vs Random-Sampling (%)"; dataset "average across 19 benchmarks". Re-derived: 37.2% is reported for Random-Sampling-Learn under interpolation over 19 benchmarks. The reason says the frozen variant is MMLU-only and single-run. Failed: method. Look at: the results table for Random-Sampling-Learn.

    Verdict: ______ (frozen right / frozen wrong / unclear)

39. 2506.18890 (Easy). Frozen: value "27.443 PSNR"; metric "PSNR (dB)"; dataset "Consistent4D (re-rendered), 4D-LRM-Base, 256x256, 12 input views". Re-derived: 27.443 is taken from the 24-view row (Alternating Canonical Views, 24 input views over 24 frames). Failed: method. Look at: Table 1, Alternating Canonical Views row for 4D-LRM-Base.

    Verdict: ______ (frozen right / frozen wrong / unclear)

40. 2510.10480 (Medium). Frozen: value "52.15%"; metric "ISM (%)"; dataset "LNR test benchmark, 93 complexes". Re-derived: 52.15 sits in the 20-template rows of Table 4 (AAR 39.42, RMSD 2.29); Top-10 gives 39.12 and 2.31. Failed: method. Look at: Table 4.

    Verdict: ______ (frozen right / frozen wrong / unclear)

41. 2510.19314 (Medium). Frozen: value "0.7923"; metric "average performance (PERF.)"; dataset "Freeway, 8-mode task sequence". Re-derived: 0.7923 is reported for CKA-RL over 10 seeds; the frozen target is a single-seed run. Failed: method. Look at: passage "We conduct experiments using 10 different random seeds".

    Verdict: ______ (frozen right / frozen wrong / unclear)

42. 2510.20725 (Medium). Frozen: value "sublinear regret growth"; metric "cumulative regret growth pattern"; dataset "synthetic navigation MDP". Re-derived: the paper reports sublinear growth over 200 trials, not for the single-trial RBF navigation run. Failed: method. Look at: passage "The results over 200 trials are shown in".

    Verdict: ______ (frozen right / frozen wrong / unclear)

43. 2510.23577 (Medium). Frozen: value "98.89"; metric "average precision (AP) in percent"; dataset "Wikipedia test set, 5 runs, random negative sampling". Re-derived: 98.89 is reported for GraphMixer + TAMI under optimal baseline settings, not the frozen default hyperparameters. Failed: method. Look at: passage "For consistency, we adopt the optimal hyperparameter settings".

    Verdict: ______ (frozen right / frozen wrong / unclear)

44. 2511.00119 (Medium). Frozen: value "Rectified Flow FID below baseline" (no number); metric "FID"; dataset "Xenium_C1 held-out cells". Re-derived: Table 2 gives the FIDs under 3-fold CV. The paper uses 100 epochs and batch 96, not 50 epochs and batch 16. Failed: method. Look at: Table 2.

    Verdict: ______ (frozen right / frozen wrong / unclear)

45. 2511.02225 (Hard). Frozen: value "0.95 ± 0.03"; metric "policy learning success rate"; dataset "OpenAI Gym Fetch Task 1 (2-push), 5-10 seeds". Re-derived: 0.95 ± 0.03 is in Table A2. Failed: method. Look at: Table A2.

    Verdict: ______ (frozen right / frozen wrong / unclear)
