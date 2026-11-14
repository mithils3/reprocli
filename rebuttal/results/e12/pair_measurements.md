# E12 pair measurements: Muse Spark 1.2, run in paper vs second run (10 Reimplement papers)

Sources: paper run from tools/anon_viewer/public/data/runs/muse-reimplement-<paper>.json.gz (final event, audit score). Second run from the repeat_run_dir in muse_pairs.csv, report.json and the grader record in /work/nvme/bfvr/msalunkhe/rebuttal/e12_repeats/<paper>_extracted.jsonl. Second-run scores from e12_grades.csv. Relative difference = |second - paper| / paper, in percent.

| Paper | Target (metric, value) | Run in paper: what it ran; measured value; score | Second run: what it ran; measured value; score | Same experiment? | Rel. diff (%) |
| :- | :- | :- | :- | :- | :- |
| 2402.04579 | Combined cost of CCE on Moons, lowest of CCE and baselines (direction) | Moons, 100 seeds, RBF SVM, CCE vs nearest and random heuristics; 1.1844; 0 | Moons, 100 seeds, RBF SVC, CCE vs Wachter; 1.1890; 4 | yes (baseline set differs: nearest and random vs Wachter) | 0.39 |
| 2503.02809 | Sharpness after T1, about 2/eta = 40 (point) | Width-one linear net, 10000 GD steps, per-step Hessian sharpness; 40.765; 8 | Same net and step count, per-step Hessian sharpness; 40.879; 7 | yes | 0.28 |
| 2505.12677 | LPIPS_e Kelly McKernan, 0.41 (higher is better) | Released erased-kelly checkpoint, 19 prompts, LMS 50 steps; 0.2493; 0 | Same checkpoint, 19 prompts, LMS 50 steps; 0.24928; 6 | yes | 0.01 |
| 2505.19087 | Eq. 5 bound on MNIST, 0.60302 (threshold) | MNIST FC net, Eq. 5 bound from initialization, no SGLD training; 0.588872; 8 | MNIST FC net, Eq. 5 bound from initialization, 60 seeds; 0.588918; 8 | yes | 0.01 |
| 2505.22860 | DDI AUC-ROC (Loss), 0.99 | Three LoRA adapters on Llama-3.1-8B, WMDP, Loss MIA at k=10%; 0.998873; 9 | Same WMDP LoRA setup, Loss MIA, full 4:1 split; 0.999988; 8 | yes | 0.11 |
| 2505.24452 | CIFAR-10 val accuracy, 94.57 (point, 75 epochs) | ResNet-18 CIFAR-10, UBA, 75 epochs, five seeds; 94.68 (5-seed mean); 8 | ResNet-18 CIFAR-10, UBA, 75 epochs, three seeds; 94.58 (3-seed mean); 8 | yes (seed count 5 vs 3) | 0.11 |
| 2509.16950 | Poisoned MVR on MetaDrive Easy, 1.00 (point) | MetaDrive Easy, 100 scenarios, rule-based backdoor proxy; 1.00; 0 | MetaDrive Easy, 100 scenarios, rule-based backdoor proxy; 1.00; 0 | yes | 0.00 |
| 2510.25146 | PSNR on ScanNet, 25.8 dB (point) | Synthetic dummy-frame PSNR smoke test, no ScanNet run; no value for target (smoke 34.08 is not the target); 2 | Artifact audit only, no training or evaluation; no value; 0 | no (neither ran ScanNet PSNR; paper run ran a synthetic smoke test) | blank |
| 2512.02339 | J&F mean on DAVIS-2017 val, 77.6 (%) | I2VGen-XL plus ADM features, full DAVIS val, 30 videos; 44.46; 4 | TED ports on full DAVIS val, corrected 512-pixel port; 48.31; 5 | yes | 8.65 |
| 2602.03066 | NTK availability difference (shortcut minus ground truth) at step 1000, 0.0977 | Colored-MNIST, 5 seeds, availability difference at step 1000; 0.0898 (5-seed mean); 9 | Colored-MNIST, 5 seeds, availability difference at step 1000; 0.0937 (5-seed mean); 8 | yes | 4.31 |

Counts

1. Same route (same experiment = yes): 9 of 10 pairs. The exception is 2510.25146.
2. Both runs report a number for the target: 9 pairs (all except 2510.25146). Relative differences sorted: 0.00, 0.01, 0.01, 0.11, 0.11, 0.28, 0.39, 4.31, 8.65. Median = 0.11%.
3. Large gaps:
   - 2402.04579 (0 vs 4): the paper run was set to 0 by a high-severity other_provenance_break flag. Its scoring compared CCE against two heuristics it wrote itself (nearest-positive and random-positive), not the six CARLA baselines the paper names, although its log shows carla-recourse was installed and never used. The second run compared against Wachter, had no high flag, and measured a combined cost within 0.4% of the paper run.
   - 2505.12677 (0 vs 6): the paper run was set to 0 by a high-severity self_scored_or_fabricated flag. Its report.json said "reproduced" while its own REPORT.md said not reproduced (0.2493 against 0.41). The second run's report said not_reproduced and scored 6 (partial) with no high flag. Both runs measured the same LPIPS_e, so the gap comes from the self-assessment flag, not the number.

Notes
- The second-run folder /work/nvme/bfvr/msalunkhe/rebuttal/e12_repeats/ holds no report.json files. The reports are at the repeat_run_dir paths listed in muse_pairs.csv.
- Second-run report.json values were garbled for 2505.12677, 2505.22860 and 2510.25146. For 2505.12677 and 2505.22860 the value is the one the grader cited from the run's evidence (0.24928 and 0.9999875). 2510.25146 has no target number in either run.
- The paper-run value for 2602.03066 is the 5-seed mean from final_aggregation_5seeds.json as cited in the paper run's events. The paper-run value for 2505.24452 is the 5-seed mean cited in its own report text (94.682).
