# E7 pre-read, items 37 to 45

Paper sources were read on DeltaAI under /work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/.../reference/latex. Line numbers are in the file named in each evidence line, relative to that latex folder. Nothing was changed.

## 37. 2506.06991

- Proposed verdict: frozen wrong (config only). The value and scope are supported.
- Evidence: neurips_2025.tex:588, "Toxicity & 0.60 (0.40) & 0.89 (0.83) & 0.89 (0.82) & 0.85 (0.79) & \textbf{0.91}". The average is over every combination, per neurips_2025.tex:573. The fixed composition (0.1, 0.05, 0.05) appears only in the figure caption at neurips_2025.tex:500, not in the table.
- Target if wrong: CA_Z (ours), Toxicity, GPT-4-reliant agents, AUC averaged over all tested (alpha_llm, alpha_r, alpha_b), Table 1 (tab:detect_gpt4). Drop the fixed-composition config.

## 38. 2506.07673

- Proposed verdict: frozen wrong (scope and run settings). The value 37.2 is supported.
- Evidence: experiment.tex:91, "With a 37.2\% reduction in estimation gap, it performs comparably to". The table row at experiment.tex:384 reads "Random-Sampling-Learn & 2.9 & -37.2", in the Interpolation block with n=50 (header at experiment.tex:350-357). The text says "repeated over 100 random trials" at experiment.tex:65.
- Target if wrong: Random-Sampling-Learn, interpolation split, coreset n=50, estimation-gap reduction against Random-Sampling averaged over all 19 benchmarks, 100 random trials. Not MMLU only, not one run.

## 39. 2506.18890

- Proposed verdict: frozen wrong (input view count only). The value and method are supported.
- Evidence: floatings/tab_full_const4d.tex:42, "4D-LRM-Base & No & 27.443 & 0.062 & 0.952", in the 256 block under the Alter. Canonical Views column group. The setup text at sec/4_experiment.tex:94 reads "The above experiments use 24 input views over a 24-frame motion sequence."
- Target if wrong: Alternating Canonical Views with 24 input views (4 poses, 24 of 24 timestamps). The 12 input views belong to training only (sec/4_experiment.tex:144).

## 40. 2510.10480

- Proposed verdict: frozen wrong (retrieval setting). The value 52.15 is supported in the main table.
- Evidence: tables/peptide.tex:14, "RADiAnce & \textbf{39.42} & \textbf{2.29}& \textbf{1.963} & \textbf{41.94} & \textbf{52.15}". The Top-N 20 row at tables/retrieval_number.tex:14 gives 39.42 and 2.29. The Top-10 row at line 13 gives 39.12 and 2.31. tables/adaptive.tex:18 pairs 39.42, 2.29 and 52.15 in a "Fixed Top-N" row.
- Target if wrong: RADiAnce, Top-N with N=20, LNR peptide benchmark, ISM (%) 52.15. The text does not name N=20, so this rests on matching numbers. The 100 samples per complex were not checked.

## 41. 2510.19314

- Proposed verdict: frozen wrong (seed count). The value 0.7923 is supported for Freeway.
- Evidence: main.tex:320, "We conduct experiments using 10 different random seeds to ensure the robustness and reliability of the results." The value appears at main.tex:462, "\textbf{0.7923} &\textbf{0.7429}", in the Freeway forgetting table with pool size 5 (main.tex:378).
- Target if wrong: CKA-RL, Freeway 8-mode sequence, PERF averaged over 10 seeds, pool size 5.

## 42. 2510.20725

- Proposed verdict: frozen wrong (dataset). The paper makes the sublinear claim for GP-sampled environments, not for navigation.
- Evidence: 5_experiments.tex:15, "Across all kernels, cumulative regret grows sublinearly, which is consistent with our theoretical analysis." The caption at 5_experiments.tex:10 names GP-sampled environments over 200 trials. The navigation caption at 5_experiments.tex:48 gives regret over 200 random trials with no sublinear statement.
- Target if wrong: cumulative regret on GP-sampled environments (fig:fixed_gp_regret_plot), 200 trials, sublinear growth. The single-trial navigation run is not reported in the paper.

## 43. 2510.23577

- Proposed verdict: frozen wrong (config). The value 98.89 is supported.
- Evidence: contents/Appendix.tex:153, "For consistency, we adopt the optimal hyperparameter settings reported in \cite{DyGFormer} for all baseline methods." The 98.89 sits in the Wikipedia (WK) column of the "w/ TAMI" row at contents/experiments.tex:159, under the rnd block.
- Target if wrong: GraphMixer + TAMI, Wikipedia, random negative sampling, AP, 5 runs, with DyGFormer's optimal hyperparameters rather than defaults.
- Check first: the row at contents/experiments.tex:159 matches the GraphMixer baseline row at contents/experiments.tex:51 in all 13 values. Confirm that line 159 is not a copy error.

## 44. 2511.00119

- Proposed verdict: frozen wrong (training config). The qualitative FID claim is supported.
- Evidence: neurips_2025.tex:258, "single & \textbf{20.73$\pm$8.45} & 0.24$\pm$0.04 & 14.90$\pm$2.55 & 171.06$\pm$81.98", the Xenium_C1 single-cell row with the diffusion baseline. The config is at neurips_2025.tex:203, "We trained our models for 100 epochs using the AdamW optimizer with a batch size of 96."
- Target if wrong: Xenium_C1 single-cell Rectified Flow against the diffusion baseline, 100 epochs, batch size 96. The 3-fold cross-validation claim was not confirmed in the text.

## 45. 2511.02225

- Proposed verdict: unclear. The value and dataset are supported. The variant label is not stated in the table.
- Evidence: appendix.tex:216, "{Gym Fetch (Task 1)} & $0.95_{\pm 0.03}$ & $\bf{0.98}_{\pm 0.02}$", in the single-task block of the policy table (appendix.tex:200-216). Its column is labeled only "FIOC". experiment.tex:94 says "the variational masks with categorical distributions perform best". Steps and seeds match: appendix.tex:487 "All tasks are with 2M training steps," and checklist.tex:126 "either 5 or 10 random seeds."
- Target if wrong: none found. The author should confirm from the run config which FIOC variant fills the FIOC column.

Counts: frozen wrong 8 (37 to 44), frozen right 0, unclear 1 (45).
