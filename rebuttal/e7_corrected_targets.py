#!/usr/bin/env python3
"""Build rebuttal/results/e7/corrected_targets.jsonl: frozen claim rows for the 10 papers E7 marked
value_wrong, with only match_target config/value/scope (and nothing else) changed to what the paper
reports. Also checks that every number new to a changed field appears in the paper text.

Usage: python3 rebuttal/e7_corrected_targets.py FROZEN_EVAL_100.jsonl PAPERS_DIR [OUT.jsonl]
"""
import json, re, sys
from pathlib import Path

FROZEN, PAPERS = Path(sys.argv[1]), Path(sys.argv[2])
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parent / "results/e7/corrected_targets.jsonl"

# paper -> (changes to match_target, note, evidence line/quote)
FIX = {
"2410.15392": (
  {"config": "EF-3DGS reimplemented from the paper (no code released) on the 9 Tanks and Temples scenes at the 1 FPS protocol: upsample the scene video (frame interpolation per paper Sec V-A), synthesize events with the open V2E simulator, then jointly optimize poses + 3DGS with the EGM/CMax/LEGM/PBA losses; compare against the paper's 3DGS/pose-free baselines per Tables 1-2",
   "value": "up to 3dB higher PSNR and nearly 40% lower trajectory error at 1FPS than state-of-the-art; Tables 1-2 at 1 FPS: EF-3DGS 23.96 PSNR vs CF-3DGS 20.53 (+3.43dB), ATE 0.3753 vs 0.8972",
   "scope": "Tanks and Temples, 9 scenes, 1 FPS event-frame hybrid protocol"},
  "Scope changed from a single scene to the paper's 9-scene protocol; value now carries the 1 FPS rows of Tables 1-2 (EF-3DGS vs CF-3DGS) next to the abstract headline. Metric and match_bar_kind (direction) unchanged.",
  "484: Similar to LocalRF [8], we adopt 9 scenes, covering large-scale indoor and outdoor scenes. | 426/431: CF-3DGS ... 20.53 0.65 0.46; EF-3DGS(Ours) ... 23.96 0.72 0.36 | 494/496: ATE 0.8972 vs 0.3753 | 620/629: up to 3dB higher PSNR and nearly 40% lower trajectory error at 1FPS ... 3.43dB at 1FPS"),
"2502.01203": (
  {"config": "DPO with Qwen 2.5 7B (SFT first), two reference models (SFT model + Qwen 2.5 14B Instruct, geometric ensemble, alpha=0.5), RKL, gamma=1.0, UltraFeedback dataset, GPT-4o as judge",
   "scope": "UltraFeedback dataset (10% held-out for evaluation); Table 2 of the paper (Qwen 2.5 7B)"},
  "Model changed from Qwen 2.5 0.5B-Instruct (second reference 1.5B) to Qwen 2.5 7B with Qwen 2.5 14B Instruct as second reference, the only setting where 66.1% appears (Table 2). Value, metric and match_bar_kind (direction) unchanged. The paper's 0.5B experiment is scored with Skywork-Reward and has no 66.1%.",
  "638: Ours (DPO with both references) 66.1% | 628: As a second reference, we used Qwen 2.5 14B Instruct. | 'we also applied it to the Qwen 2.5 7B model ... GPT-4o as LLM-as-a-Judge'"),
"2504.13146": (
  {"config": "lambda=0.15 (antidistillation), tau=0.6, epsilon=0.01, teacher DeepSeek-R1-Distill-Qwen-7B, proxy Qwen2.5-3B, student Llama-3.2-3B, LoRA rank 128, lr=5e-4, 4 epochs, batch size 32, GSM8K",
   "value": "25% distilled student accuracy on GSM8K with antidistillation sampling (Figure 1 bar; standard-sampling student 61%)"},
  "The ~40% is the paper's MMLU illustration (teacher 72%, student 52% to 40%), not GSM8K. The only printed GSM8K antidistilled-student value is the Figure 1 bar, 25% (standard-sampling student 61%); epochs corrected 3 to 4 (paper: 4 epochs). Figure 1 does not state lambda, and its teacher accuracy differs from the 4% drop in the MMLU example; the Figure 3 GSM8K curve has no printed value, so Figure 1 is the only candidate. Scope and match_bar_kind (point_estimate) unchanged.",
  "47,48: To illustrate our empirical results, consider a reasoning model that achieves 72% accuracy on MMLU. | 83-88: Antidistillation ... Teacher 70% ... Student Base 31% ... Student Poisoned 25% (Figure 1); standard sampling Student Distilled 61% | 524-525: batch size 32, for 4 epochs"),
"2505.02391": (
  {"config": "GVM-RAFT++ on Qwen2.5-Math-1.5B (the smaller of the two models the paper trains) with N'=8, N=8n samples per prompt, 10 iterations with 9 gradient steps each, batch size 1024, learning rate 1e-6, clip_higher_ratio=0.3, alpha=0.001, beta=2.0",
   "value": "Table 1 Math500 Average @ 8 on Qwen2.5-Math-1.5B: GVM-RAFT++ 72.90 vs RAFT++ 69.02"},
  "Model changed from Llama-3.2-1B-Instruct (not trained in the paper) to Qwen2.5-Math-1.5B, the smaller of the two trained models (the other, Qwen2.5-Math-7B, is 81.00 vs 81.68 and is not used). Value 72.90 vs 69.02 replaces the unreported ~71-73 vs ~66-69 ranges. Metric and match_bar_kind (direction) unchanged; remaining config hyperparameters are as frozen.",
  "821-824: Qwen2.5 Math-1.5B ... RAFT++ 69.02 ... GVM-RAFT++ 72.90 | 976-977: The experiments are conducted with Qwen series base models"),
"2505.16927": (
  {"config": "STaPLe Iteration 1, Llama-3.1-8B-Instruct, unconstrained version, N=16, Rouge-L similarity, 3 epochs SFT on 28.2k accepted samples"},
  "Constrained (clustered) and ~5k accepted samples replaced by unconstrained and 28.2k: Table 2 STaPLe Iter 1 (28.2k) is 65.6%; the paper reports the constrained run only at Iter 4 (69.1%). Value, metric, scope and match_bar_kind (threshold) unchanged.",
  "1232: STaPLe Iter 1 (28.2k) 7.66 8.15 7.16 32.2 65.6% | 408-414: Table 1 unconstrained STaPLe Iter 4 68.9%, Constrained STaPLe Iter 4 69.1%"),
"2505.23747": (
  {"config": "Spatial-MLLM-4B, 16 frames input, space-aware frame sampling (Nm=128, Nk=16), temperature=0.1, top_p=0.001",
   "value": "48.4%"},
  "51.13% (v1.1 release README, not in the paper) replaced by the paper's Spatial-MLLM-4B micro average 48.4 (Table 1, VSI-Bench, 16 frames). Config now follows the paper's inference details (space-aware sampling, temperature 0.1, top-p 0.001) instead of the v1.1 checkpoint and uniform sampling. Metric, scope and match_bar_kind (point_estimate) unchanged.",
  "505: Spatial-MLLM-4B 65.3 34.8 63.1 45.1 41.3 46.2 33.5 46.3 48.4 | 534-536: we set Nm = 128 and Nk = 16 ... temperature to 0.1 and the top-p to 0.001"),
"2506.18890": (
  {"config": "4D-LRM-Base, 256x256 resolution, Alternating Canonical Views (24 input views, 24 frames), single A100 forward pass inference"},
  "Input views corrected from 12 to 24: the paper defines Alternating Canonical Views as 4 camera poses, 24/24 timestamps seen, 24 input views in total. Value 27.443, metric, scope and match_bar_kind unchanged.",
  "366: 256 4D-LRM-Base No 27.443 0.062 0.952 [Alter. Canonical Views] | 304-305 (Figure 4): Alternating Canonical Views (4 camera poses, 24/24 timestamps seen, 24 input views in total)"),
"2506.18896": (
  {"config": "ReasonFlux-PRM-7B scores trajectory-response pairs -> top-1K -> SFT Qwen2.5-14B-Instruct generator (5 epochs, lr=1e-5)",
   "value": "84.8% (ReasonFlux-PRM-7B-selected data) vs 68.4% (random-selection baseline)",
   "scope": "Qwen2.5-14B-Instruct fine-tuned on ReasonFlux-PRM-7B-selected data (Table 2)"},
  "Generator changed from Qwen2.5-7B-Instruct to Qwen2.5-14B-Instruct and the selecting PRM from 1.5B to 7B; value from '>80% vs ~73% random' to Table 2's 84.8 vs 68.4. The paper has no SFT-only Qwen2.5-7B-Instruct number (84.8 on 7B appears only after SFT plus RL, Table 7). The '>80' threshold is not in the paper and is dropped; match_bar_kind (threshold) left unchanged, so the auditor reads 84.8 as the bar.",
  "411: ReasonFlux-PRM-7B 40.0 33.3 84.8 (up 6.0) 47.5; Random ... 68.4 | 396-397: generator model Qwen2.5-14B-Instruct | 891: fine-tune the model for 5 epochs using a learning rate of 1e-5"),
"2510.10480": (
  {"config": "RADiAnce with full cross-domain training (Ab + Pep + ProtFrag), Top-20 retrieval (Fixed Top-N), 100 samples per test complex on LNR peptide benchmark"},
  "Retrieval changed from Top-10 to Top-20: Table 4 ties 39.42 AAR / 2.29 RMSD (the row of the 52.15 ISM in Table 5, Fixed Top-N) to N=20; N=10 gives 39.12 / 2.31. Value 52.15%, metric, scope and match_bar_kind unchanged.",
  "598: Top-N 20 50.43+-4.8 54.63 0.9682 0.0485 50.24+-3.3 39.42 2.29 0.5227 | 610: Fixed Top-N 39.42 2.29 0.5227 1.963 -7.99 52.15 0.7698 | 597: N=10 39.12 2.31"),
"2511.00090": (
  {"config": "LeMiCa-fast on Latte (16 frames, 512x512), Table 1 latency speedup over the original model",
   "value": "2.93x (Latte, LeMiCa-fast)",
   "scope": "Latte (16 frames, 512x512) video generation, Table 1"},
  "Wan2.1 T2V 1.3B is not evaluated in the paper (2.59x was the repo README ratio 1.76/0.68 min). Re-pinned to the row the frozen claim sentence names, 2.9x on Latte: Table 1 LeMiCa-fast 2.93x. Table 1 states no budget B for it, so B=17 is dropped. The other B=17 reading in the verdict (Qwen-Image 2.45x) is not in the paper text (2.45x there is TeaCache-fast on CogVideoX), so it was not used. Metric and match_bar_kind (point_estimate) unchanged.",
  "337: LeMiCa-fast 1.00 2.93x 3.81 76.75% 0.273 0.70 19.43 (Latte, 16 frames, 512x512) | 29: our method achieves a 2.9x speedup on the Latte"),
}

NUM = re.compile(r"\d+(?:\.\d+)?")
rows, bad = [], []
for line in FROZEN.read_text().splitlines():
    r = json.loads(line)
    pid = r["custom_id"]
    if pid not in FIX:
        continue
    change, note, ev = FIX[pid]
    text = (PAPERS / f"{pid}.txt").read_text()
    flat = re.sub(r"[ \t]+", " ", text)
    new = dict(r)
    mt = dict(r["match_target"])
    for k, v in change.items():
        old_nums = set(NUM.findall(mt.get(k, "")))
        for n in set(NUM.findall(v)) - old_nums:
            if n not in flat:
                bad.append((pid, k, n))
        mt[k] = v
    new["match_target"] = mt
    new["e7_correction_note"] = note
    new["e7_evidence_line"] = ev
    rows.append(new)
assert len(rows) == 10, len(rows)
assert not bad, bad
OUT.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
print(f"wrote {len(rows)} rows to {OUT}; all new numbers found in paper text")
