## 28. 2402.04579

Proposed verdict: unclear

Evidence: main.tex line 404: "our method outperforms the baselines, offering the most balanced trade-off." The 100-run comparison (fig:cost, lines 385 to 403) names no dataset, so the Moons tie is not in the text. Line 390 says "Two non-linear methods, Multilayer Perceptron or Random Forest"; the text never says ANN for Moons. Line 94 calls the Moons classifier an SVM.

What the target should be: if the author keeps Moons, the combined-cost claim has no dataset to attach to in the paper. The figure number (4 in the CSV reason) was not checked.

## 29. 2502.01203

Proposed verdict: frozen wrong

Evidence: _NIPS_2025_-RLHF-MF.tex line 656: "To validate that our algorithm works at a larger scale, we also applied it to the Qwen 2.5 7B model." The win-rate table at line 670 reads "Ours (DPO with both references) & \textbf{66.1\%}". The 0.5B experiment (line 651) is offline RL scored by a reward model, not a win rate. The 10% held-out split was not checked.

What the target should be: 66.1% win rate against the preferred answer, Qwen 2.5 7B, UltraFeedback, DPO with both references (SFT model and Qwen 2.5 14B Instruct), GPT-4o as judge (lines 656 and 662). The 0.5B config in the frozen target uses a 1.5B second reference, which is not the 14B used for the 66.1% row.

## 30. 2502.06684

Proposed verdict: frozen wrong (configuration only; value is right)

Evidence: neurips_2025.tex line 699: "We use an \methodname{} network with $12$ self-attention layers alternating between both type of attention". The value 77.0 +/- 1.8 is the EquiTabPFN row in the Mean Acc column of figures/TabZilla_metric_Accuracy_datasets_ood.tex line 6, which feeds the >10-class table (neurips_2025.tex around line 838).

What the target should be: 12 self-attention layers alternating between the two attention types, not 6. Value, metric and dataset (more than 10 classes, 10 splits) match.

## 31. 2503.23035

Proposed verdict: unclear

Evidence: neurips_2025.tex line 552: "as well as the combination of these transformations for comparison." The transformation table (lines 559 to 569) gives rotation 27.64 at line 568 and combination 27.69 at line 569. The main-table "Ours" row at line 341 is 27.69, and the text does not say which transformation that row uses.

What the target should be: 27.69 is the main-table value. If the author wants the rotation-only setting, the value is 27.64 (line 568), 0.18% away, so either passes the tolerance. The method text uses rotation as its example (line 307), which is not the same as saying the reported run used rotation.

## 32. 2504.12397

Proposed verdict: unclear

Evidence: main_neurips.tex line 1134: "and searched over ranks $[6, 8, 16, 32]$ and learning rates". The 79.30% and 81.94% cells are in the Llama 3.2 1B column of the table at line 378. Line 1134 to 1135 also says "reported performance was computed on the test set for those selected models."

What the target should be: the value, metric, dataset and test split are supported. The paper does not fix rank 8 for either adapter. Rank was chosen per run on validation, so "rank=8 vs rank=8" is not in the paper. The author should either drop the rank or state "validation-selected rank."

## 33. 2504.12463

Proposed verdict: frozen wrong (dataset in the configuration)

Evidence: common/sections/05-evaluation.tex line 49: "after training the 8c1 MoE for 10B tokens, Loss-Free Balancing obtains a validation perplexity of \(24.22\), whereas our Default MoE obtains \(23.48\)." Dataset rule, common/sections/04-experimental_setup.tex line 30: FineWeb-Edu is for the benchmark table and the tokens-to-target figure, and "FineWeb ... (for all other plots and results)".

What the target should be: 23.48 is validation perplexity on FineWeb, not FineWeb-Edu, for Default MoE with 8c1 after 10B tokens. The paragraph does not name the dataset, so this follows from the dataset rule at line 30.

## 34. 2505.02391

Proposed verdict: frozen wrong (model)

Evidence: contents/experiments.tex line 6: "we conduct experiments with Qwen2.5-Math-1.5B and Qwen2.5-Math-7B". Llama-3.2-1B-Instruct does not appear in the paper source. The live row at line 131 is "\dibs-RAFT++ & {72.90}", and the RAFT++ baseline at line 127 is 69.02. The macro \dibs is GVM (main.tex line 47).

What the target should be: GVM-RAFT++ (\dibs-RAFT++) on Qwen2.5-Math-1.5B, Math500 accuracy 72.90 against 69.02 for RAFT++ (lines 127 and 131). The frozen range 71 to 73 and baseline range 66 to 69 both hold. The live row shows no sample size. The n=32, iteration 4 label goes with 72.90 only in commented-out tables (lines 34, 69 and 100).

## 35. 2505.16927

Proposed verdict: frozen wrong (variant and value)

Evidence: Sections/appendix.tex line 649: "Medoids Iter 1 (28.2k) & 7.63 & 8.14 & 7.11 & 31.9 & 65.1\%". Line 648 gives "Unconstrained Iter 1 (28.2k)" with 65.6\%. The constrained variant is defined in Sections/results.tex line 74 as "the version of the algorithm with agglomerative clustering following the E-step during each iteration".

What the target should be: 65.1% (Medoids Iter 1, constrained, Llama-3.1-8B-Instruct, IFEval win rate, appendix.tex line 649). The frozen "~5k accepted samples" does not match Iter 1, which the table lists as 28.2k. The main-text table (Tables/self-improvement-multi-iters.tex line 15) labels the 65.6% run "STaPLe Iter 1", which is the unconstrained run. The "N=16, Rouge-L" settings were not checked.

## 36. 2505.24864

Proposed verdict: frozen wrong (training configuration; value is right)

Evidence: Sections/sec_exp.tex line 142: "our model consistently outperforms the base model across benchmarks, showing an average improvement of 15.7". The six benchmarks are listed at sec_exp.tex line 72 (AIME24, AIME25, AMC, Math, Minerva, Olympiad). Line 32: "the whole training runs for approximately 16k GPUs hours."

What the target should be: 15.7% average improvement over the six math benchmarks, which matches. The training length is not 16k steps. The live text says "It enables more than 2k training steps" (neurips_2025.tex line 221). The phrase "16k training steps" appears only on a commented-out line (neurips_2025.tex line 234). The compute figure is about 16k GPU hours.
