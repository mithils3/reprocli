# E7 pre-read, items 10 to 18

Paper sources are on DeltaAI under /work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/8h/<run>/reference/latex/. File names below are relative to that folder. Read only; nothing on DeltaAI or in the repo was changed except this file.

10. 2410.15392

Proposed verdict: frozen wrong (dataset)

Evidence: "Similar to LocalRF~\cite{localrf}, we adopt 9 scenes, covering large-scale indoor and outdoor scenes." (sec/4_exp.tex:12). The 3 dB and 40 percent claims appear in sec/0_abstract.tex:9 and sec/4_exp.tex:141, so the value is in the paper. The paper does not report it for one scene.

Should be: value "up to 3 dB higher PSNR and 40% lower ATE" at 1 FPS, metric PSNR and ATE, dataset Tanks and Temples with 9 scenes (tabs/table_1.tex, caption "Quantitative evaluations on Tanks and Temples dataset"), method comparison against frame-based baselines.

11. 2411.06890

Proposed verdict: unclear (value, metric and method match; the split label is not in the paper)

Evidence: "\acronym{} (Ours) & \textbf{8.60} & \textbf{1.51} & \textbf{246.6}" (experiments.tex:46, prediction and graph table). Searches for "test set", "held-out", "test split" and "evaluat" found no split named for Interventional Pong. The text says only "We evaluate our model in three domains" (experiments.tex:17).

Should be: if the label must stay, drop "test set" and use "Interventional Pong, SHD column of the prediction and graph table (experiments.tex:44-46)".

12. 2502.05795

Proposed verdict: unclear (value and metric match; the C4 validation label is not in the paper)

Evidence: "Comparison against other normalization methods on LLaMA-130M. All methods use the identical configurations. Perplexity (↓) is reported." (Curse_of_Depth.tex:741). The value 25.76 is the last column of that table (line 748). The only C4 mention is for angular distance: "sampled from the C4 dataset" (line 235). Searches for "validation" and "perplexity" found no C4 validation label for the perplexity.

Should be: perplexity, LLaMA-130M, LayerNorm Scaling, comparison table (Curse_of_Depth.tex:741-748). The dataset field should say the paper does not name the evaluation split.

13. 2504.13146

Proposed verdict: frozen wrong (dataset and method)

Evidence: "lowering its accuracy to as low as 40\%." (main.tex:122). The 40 percent figure is part of a hypothetical example: "consider a reasoning model that achieves 72\% accuracy on MMLU." The GSM8K Platinum test set is described at main.tex:323.

Should be: student accuracy, MMLU, antidistillation sampling, illustrative example with a 72 percent teacher and a 52 percent greedy-distilled student (main.tex:122). It is not a measured GSM8K Platinum result.

14. 2505.14827

Proposed verdict: unclear (value and method match; the dataset identifier is not in the paper)

Evidence: "\textbf{Count Down 4}~\citep{tinyzero} is a synthetic numerical reasoning task that presents models with arithmetic puzzles." (tex/s3.5_settings.tex:19). The 59.53 value is in the Nemotron-Super-49B block, CountDown4 column, gray method row (tex/tables/main_results_table.tex:39).

Correction to the review file: the re-derivation says the paper does not name the TinyZero source. It does cite \citep{tinyzero}. The Hugging Face name yzhuang/tinyzero-Countdown-Tasks-4 and the phrase "full dataset" do not appear. The bib file is not in the folder, so the cited entry could not be checked.

Should be: keep the tinyzero citation and drop the Hugging Face path unless the author confirms it.

15. 2505.19154

Proposed verdict: frozen wrong (metric and dataset split)

Evidence: "we report chamfer distance, PSNR (training-set view), reconstruction time, model size and point number." (neurips_2025.tex:292, caption of the DTU table). The ablation table header is "Methods & PSNR$\uparrow$" (neurips_2025.tex:324). A search for "novel" and "test view" found no novel or test views in the DTU experiments.

Should be: PSNR on training-set views, DTU scan24, 10,000 iterations, FHGS row of the ablation table (neurips_2025.tex:326, value 30.9).

16. 2505.24452

Proposed verdict: unclear (value and metric match; the split is in conflict)

Evidence: "Validation accuracy for vision classification tasks." (neurips_2025_arxiv.tex:458, Table 2 caption). The value 94.57$\pm$0.3281 is the UBA row for CIFAR10 ResNet18, first budget column, 75 epochs (25%) (line 472, header at line 462). The paper gives a CIFAR10 test split size (line 1782), but it never says the table uses that split.

Should be: validation accuracy, CIFAR10, ResNet18, UBA, 75 epochs (25% budget). Remove "test set" unless the author confirms the split.

17. 2506.17475

Proposed verdict: unclear (value and method match; the split is not named)

Evidence: "Results on Cifar10 with VGG16 using low-rank Heavyball SGD. Compression rate (c.r.) is reported in percent." (neurips2025_camera_ready.tex:909, Table tab:heavyball). The 79.01 is the Acc. [%] column for the Heavy Ball DLRT row (line 919). The baseline is 78.98. No "test set" label appears in the paper.

Should be: Acc. [%] on CIFAR10, VGG16, low-rank Heavy Ball DLRT, transfer learning from ImageNet weights (line 485), 79.01 against baseline 78.98.

18. 2505.24873

Proposed verdict: frozen wrong (config and dataset label)

Evidence: "We set the evaluate frame length as 32." (main.tex:492). The 81-frame, 480p, 6-step setting in the frozen config is the latency setting (main.tex:490). The 0.9842 SSIM is the "Ours (6 steps)" row of Table tab:quantitative_results (main.tex:522). The paper says "all 90 DAVIS videos" (main.tex:533) and never uses "validation".

Should be: SSIM 0.9842, DAVIS (90 videos), MiniMax-Remover 6 steps, no CFG (main.tex:310), evaluated at frame length 32 (main.tex:492). Drop "validation set" and the 81-frame setting.

Verdict counts: frozen right 0, frozen wrong 4 (items 10, 13, 15, 18), unclear 5 (items 11, 12, 14, 16, 17).
