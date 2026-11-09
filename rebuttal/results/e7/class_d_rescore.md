# E7 class D: do the three uncorrected number-wrong targets change any cell?

Class D is the three targets that the second pass marked as having a wrong number but that the earlier rescore (`rescore_summary.md`, script `scripts/rebuttal/e7_regrade.py`) never corrected: 2510.04136, 2506.01511 and 2505.24864. The question is whether correcting them changes the reproduced verdict of any agent-paper cell. It does not. Each paper has four cells (DeepSeek-V4-Flash, Muse Spark 1.2, MiniMax-M2.7 and Qwen3, the fourth agent), 12 in all. Of those, 2 have no run (dsv4 on 2506.01511 and on 2505.24864) and count as not reproduced under every target, so 10 cells have a run. Only one of the 10 was reproduced, so only that one could fall, and the other nine are checked against the reported number.

Rule applied: the paper's default 5% relative tolerance for a point estimate, and the stated bar for a threshold or direction target, as in `rescore_summary.md`. Old verdicts and reported numbers come from the audit records in `tools/anon_viewer/public/data/runs/` and `results/e6/table.csv`.

## 2510.04136 (WER on LRS2, MoME)

Frozen target: "exact", no usable number (the claim it rests on names a 7B LoRA model, VoxCeleb2 and an LRS3 WER of 3.0, which the paper does not contain). Corrected target: WER 4.3% on LRS2 at audio-visual compression (16,5), MoME-23/4-MHSA with Whisper-small, AV-HuBERT Large and Llama 3.2-3B (`Sections/Experiments.tex:52` and `:70`, `e7_merged.md` item 5). Tier: Reimplement.

| Cell | Reported number | Old verdict (score) | Verdict under corrected target | Basis |
|---|---|---|---|---|
| dsv4 | 28.22% WER, sibling Llama-AVSR checkpoint on LRS3 | partial (6) | not reproduced | (28.22 - 4.3) / 4.3 = 556% relative gap, and the dataset and method differ |
| muse | 1.9211% WER, Whisper-small.en audio-only on an LRS3 mirror | not_reproduced (2) | not reproduced | A different method on a different split, and 1.92 is 55% below 4.3 |
| minimax | none | disqualified (0) | disqualified | No measured number; wrote "reproduced" into report.json against its own fields |
| qwen3 | none | not_reproduced (2) | not reproduced | No forward pass ever ran |

No change.

## 2506.01511 (APA black-box attack success rate)

Frozen target: threshold, above 50% black-box success rate, "paper 77.48% avg across 10 models", no LoRA. Corrected target: the same above-50% bar on MobileNetV2 and Inception-v3 with the ResNet-50 substitute, paper cells APA-SG 89.0 and 83.4 (`paper.tex:295`; APA-GC 97.6 and 93.5 at `:296`; LoRA stage always included, `:67`; `e7_merged.md` item 19). Tier: Run.

| Cell | Reported number | Old verdict (score) | Verdict under corrected target | Basis |
|---|---|---|---|---|
| dsv4 | no run | not reproduced | not reproduced | No cell to grade |
| muse | 65.0% average on MobileNetV2 (75.0) and Inception-v3 (55.0), 20 images | partial (7) | partial | Clears 50% but covers 2% of the images and 2 of 9 targets; a threshold bar does not move when the paper value in the note changes |
| minimax | 79.60% average over 9 models (the log's per-model values give about 87%) | partial (6) | partial | The headline does not reconcile with its own per-model lines |
| qwen3 | MobileNetV2 100%, Inception-v3 80.0%, APA-GC with ResNet-50, 5 images | reproduced (8) | reproduced (8), by re-grade | See below |

The one cell that could fall is qwen3, because its Inception-v3 value of 80.0 is below the paper's APA-SG 83.4 (4.1% relative, inside 5%) and its MobileNetV2 value of 100 is above 89.0 (12.4% relative, outside 5%), so a point-estimate reading would give partial. The bar is a threshold, though, and the rescore left the kind unchanged for threshold targets (as for 2506.18896), so I re-graded the cell with the same script and pinned auditor (claude-sonnet-5, same rubric and prompt) on both the frozen claim and a corrected claim (`class_d_corrected_targets.jsonl`, with the above-50% bar kept and the RN-50 APA-SG and APA-GC cells named in the value). Both grades are score 8, reproduced (`class_d_grades.jsonl`). The auditor read the measured 100% and 80% as clearing the above-50% bar and matching the RN-50 APA-GC row. No change.

## 2505.24864 (ProRL average pass@1 gain)

Frozen target: direction, average pass@1 improvement of 15.7 on six math benchmarks, trained on the DeepScaleR math set alone. Corrected target: the same 15.7 point gain over DeepSeek-R1-Distill-Qwen-1.5B (60.14 against 44.45, `sec_exp.tex:74` and `:78`) for ProRL trained on the 136K five-domain blend (`e7_merged.md` item 36). The number is unchanged and only the training set it belongs to is corrected. Tier: Run.

| Cell | Reported number | Old verdict (score) | Verdict under corrected target | Basis |
|---|---|---|---|---|
| dsv4 | no run | not reproduced | not reproduced | No cell to grade |
| muse | gain of -3.75 points (truncated protocol, 1024 and 2048 tokens) | not_reproduced (4) | not reproduced | Wrong sign against a +15.7 bar |
| minimax | 11.39 points | disqualified (0) | disqualified | Hardcoded 90-item set and no training run, which the target does not affect |
| qwen3 | gain of -1.04 points (max_tokens 4096) | not_reproduced (4) | not reproduced | Wrong sign against a +15.7 bar |

No change.

## Result and spend

Correcting the three class D targets changes 0 reproduced cells, so the all-agent count stays at 73 of 400 and the best Run rate stays at 14 of 34 (dsv4, 41.2%). Combined with the earlier rescore this leaves the corrected-target figures at 71 of 400 and 13 of 34, which come only from 2505.23747.

Spend: 2 grades, $2.33 of Anthropic API (item `E7-class-D` in `rebuttal/results/spend/spend.jsonl`), which brings the total from about $93.6 to about $95.9 of the $200 cap. The estimate before running was about $1.6 to $2.0 from the $0.79 per grade of the first rescore. The script was `scripts/rebuttal/e7_regrade.py` with only the work directory, cell list, corrected-claims path and ledger item name changed.
