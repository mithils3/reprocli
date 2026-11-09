# E7 pre-read, items 19 to 27

Paths below are relative to each paper's `reference/latex` folder on DeltaAI, under `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/<tier>/<run>/reference/latex/`. Quotes are verbatim except that runs of spaces are collapsed. Nothing on DeltaAI was changed.

19. 2506.01511

Proposed verdict: frozen wrong (dataset and method). The ">50%" threshold holds, but the frozen dataset and method do not match the table the 77.48 comes from.

Evidence: "Avg. ASR refers to the average attack success rate on non-substitute models (black-box ASR)." (paper.tex:241, Table 1 caption). The 77.48 sits in the APA-GC row at paper.tex:266. The dataset is 1,000 ImageNet-compatible images (paper.tex:226), and the average runs over 10 non-substitute models (paper.tex:245 header). I did not confirm the substitute name for that row from the table block itself. The CSV reason names MobViT-s.

Correct target: black-box ASR, average over 10 non-substitute models, APA-GC row of Table 1 (77.48), on the 1,000-image ImageNet-compatible set. The frozen "transfer to MobileNetV2 and Inception-v3" is only two of the ten models.

20. 2506.08898

Proposed verdict: unclear. The value 0.6411, the normalized HV metric, and the POCCO-W method on Bi-TSP50 are all in the paper. The "200 instances" count is not.

Evidence: "Bi-TSP50 & \textbf{0.6411} & 0.6400" (appendix.tex:620). Searched for "200 instances", "200 test", "test set", "test instances" and "Bi-TSP50" across arxiv.tex and appendix.tex. No test-set size is stated for Bi-TSP50, so the 200 count is not found anywhere in the paper source.

Correct target: value 0.6411, normalized HV, POCCO-W, Bi-TSP50, with the instance count dropped unless the author can source it elsewhere.

21. 2506.10943

Proposed verdict: frozen wrong (dataset, and the base value).

Evidence: "We evaluate on a 200-passage subset of the SQuAD evaluation set" (neurips_2025.tex:602). The single-passage column of the knowledge table shows base 32.7 and SEAL 47.0 (neurips_2025.tex:335 to 339). The 33.5 is "Train on Passage", not the base (neurips_2025.tex:322 says "33.5\% vs.\ 32.7\%").

Correct target: no-context SQuAD accuracy, Qwen-2.5-7B, single-passage LoRA setting, base 32.7 to SEAL 47.0, evaluated on the 200-passage subset (974 questions). The "full scale" label does not fit this column. The n=2067 column is a different setting.

22. 2506.12025

Proposed verdict: frozen wrong (dataset and method). The 100x figure is in the paper, but it is measured on the IBC cortical-surface data, not the SBM set.

Evidence: "it is up to $100$ times faster than classical solvers and $10$ times" (sections/numerical_experiments.tex:341, in the IBC section that starts at line 287). The SBM training set is 50,000 pairs (numerical_experiments.tex:36). The 14,400-pair set with a 60/20/20 split is the IBC data (numerical_experiments.tex:307). The string "10k pairs" is not in the paper.

Correct target: solver time over ULOT prediction time, 100x, ULOT against the IBPP solver on IBC graph pairs (14,400 pairs, 60/20/20 split). The SBM test set is not the timing dataset.

23. 2506.13717

Proposed verdict: frozen wrong (method: rs). The 90.21 value and the top-1 metric are right. The "validation set" label is not in the paper.

Evidence: "$r_s=8.5$ is applied for CIFAR-10 and ImageNet-100/1K." (main-final.tex:509). The frozen config says rs=7.0, which the paper does not use. The value appears as "\CLAP(ours) &90.21 &99.60" in the CIFAR-10 linear evaluation table (main-final.tex:555). That table has no split label, so "validation" is not supported.

Correct target: top-1 accuracy 90.21 for the proposed method on CIFAR-10, ResNet-18 linear evaluation, with 16 views and rs=8.5. Drop "validation set" unless the author can source the split.

24. 2506.18896

Proposed verdict: frozen wrong (dataset, method, and baseline). The 84.8 value is right, but it comes from a 7B selector, and the "~73%" random baseline is not in the paper.

Evidence: "SFT on 1k \modelname-7B selected data" (tables/RL_results_TAP.tex:14, with "Rule-based & 84.8" on the same row group). This table uses Qwen2.5-7B-Instruct, the setting the frozen target names. The paper's baseline in this table is the original backbone at 74.0 (line 9). I did not find a random-selection row at about 73 for the 7B model. The 73.2 value belongs to a Qwen2.5-Math-PRM-7B row in the 14B table.

Correct target: MATH500 accuracy 84.8, Qwen2.5-7B-Instruct after SFT on 1k ReasonFlux-PRM-7B selected data, rule-based reward. Baseline is 74.0 (Checkpoint 1, original backbone, same table).

25. 2506.20671

Proposed verdict: frozen wrong (dataset label and method label). The value 6.30 and the 815-grid validation split are right.

Evidence: "The dataset comprises 10 training sequences, 1 validation sequence, and 11 test sequences" (sec/6_appendix.tex:10). The paper also says "we perform evaluations on the validation set" (sec/6_appendix.tex:14). It never names the validation sequence as 11. The proposed configuration is "method (r)" (sec/6_appendix.tex:275). The frozen "(j)" is a different ablation row (sec/6_appendix.tex:312). The 6.30 is the "IPFormer (ours)" row (sec/4_experiments.tex:153).

Correct target: PQ-All 6.30, proposed IPFormer (method r), SemanticKITTI validation set (815 voxel grids, sequence not named). Outside the paper: the standard SemanticKITTI validation sequence is 08, so "sequence 11" may be wrong. The author should confirm that before any reply.

26. 2510.15194

Proposed verdict: unclear. The value, metric, and method are right. The paper never states that CUB200-2011 is evaluated on a test split.

Evidence: "Ours & \textbf{89.68}" (sec/4_exp.tex:23, Table 1, RN50, CUB column). The dataset list gives "CUB200-2011~\citep{wah2011caltech}" with no split (sec/4_exp.tex:85). Searched for "test set", "test split", "test images" and "CUB". No CUB test split is named in sec/4_exp.tex or main.tex.

Correct target: downstream top-1 accuracy 89.68 for Ours (RN50) on CUB200-2011. Drop "test set" unless the author can source it.

27. 2510.21363

Proposed verdict: frozen wrong (dataset: development set size). The 0.56 value is right.

Evidence: "We split the dataset into a development set of 20 samples and use the remaining 100 samples as the test set." (main.tex:187). The FairImagen row in the gender table reads "FairImagen & 0.56 & 0.771 & 0.541 & 0.624" (main.tex:252).

Correct target: gender fairness 0.56 for FairImagen (FairPCA-based), with a 20-sample development set and a 100-sample test set. The paper uses "samples", not "prompts". The frozen 30-prompt dev size is not in the paper.

Verdict counts for items 19 to 27: frozen right 0, frozen wrong 7 (19, 21, 22, 23, 24, 25, 27), unclear 2 (20, 26).
