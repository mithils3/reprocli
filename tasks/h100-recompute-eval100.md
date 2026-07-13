# Task: Recompute H100-hour estimates for all 100 eval-100 papers

> **Runbook / durable spec.** Saved so it survives context compaction. Re-read this
> before resuming. Status: **DONE 2026-07-01** — recomputed all 100, uploaded to HF
> (commit `21047e20`). 90/100 rows moved (65 down, 11 up), total audited H100-h
> 4426→1922 (−57%), median 35→2.5h. Final bands 0-8:63 / 8-32:20 / 32-96:14 / 96-192:3 /
> >192:0. Note: `signals.weights_available=true` is often only the BASE model — 4 rows
> (2504.12397 aLoRA, 2506.20990 SharpZO, 2502.08924 boosting, 2505.23305 MGE-LDM) kept as
> small training runs because the paper's contributed artifact isn't released, so
> eval-only is impossible. 2506.23589 (DTM, weights+code unavailable) re-scoped to a
> reduced-scale training MRE (61.44h) instead of full-scale.

## One change from the original spec
- **Subagent model/thinking:** use **Sonnet 5** (`model: 'sonnet'` → resolves to
  `claude-sonnet-5`) with **low thinking** (`effort: 'low'`) on every Workflow `agent()`
  call. `agentType: 'general-purpose'`.

## Goal
Recompute each paper's H100-hour figure for the eval-100 split of the HF dataset
`Mithilss/reprobench-splits` (test split = `eval_100.jsonl`, 100 rows), then reupload the
corrected `eval_100.jsonl` to that same HF repo (write auth, user `Mithilss`).

## What the number means (load-bearing definition)
Each paper's H100-hour figure = compute to run its **Minimal Reproducible Experiment
(MRE)** = the **minimum compute to PROVE the paper's central claim**. NOT the paper's
largest run, NOT the full-paper training run, NOT human debugging/engineering time.

- **Key on `signals.weights_available.value` FIRST.**
  - If weights are released (`== true`) → MRE is **EVAL-ONLY**. Never retrain. Cost =
    running the released checkpoint on the eval that demonstrates the central claim.
  - If weights are NOT released → MRE is the **smallest training run that demonstrates
    the central effect** (smallest model / shortest schedule / one seed that shows the
    claim), NOT full-paper scale.
- This is the correction the first pass got wrong: it over-corrected several rows UP to
  full-paper training scale (e.g. ProRL `2505.24864` blew up to ~16000h; `2510.04136`,
  `2506.23589`, `2505.18456` also inflated). Released weights ⇒ eval-only.

## Formula & multiplier table
```
H100_hours = gpu_count × wallclock_hours × h100_equivalent_multiplier
```
- `gpu_count`       = GPUs running concurrently for the MRE.
- `wallclock_hours` = TRUE wall-clock time, NOT total GPU-hours. If a source gives total
  GPU-hours G across N GPUs, `wallclock = G / N`, so `gpu_count × wallclock = G`.
- `multiplier`      = the card's value from the CANONICAL table in `prompts/prompt.txt`
  (~lines 424–483; authoritative — read it from the file, don't guess).
  Examples: H100 SXM 1.00, A100/A800 0.32, L40S 0.37, A40 0.15, B200 2.27.
- Equivalently: `H100_hours = (total GPU-hours for the MRE) × multiplier`.

## Systematic bugs to fix (check every row)
1. **double_count_gpu_hours**: wallclock filled with a TOTAL-GPU-hours figure, then
   ×gpu_count again → ~Nx too high.
2. **unit_error**: s/ms/hours mistakes (e.g. treating ms as s → ~1000x).
3. **wrong_multiplier**: multiplier doesn't match the table for the stated gpu_type
   (e.g. A100 using 1.0 instead of 0.32).
4. **noncompute_inflation**: hours padded with "+Nx for debugging/tuning". Compute only.
5. **internally_inconsistent**: the basis's own numbers contradict the hours.
6. **scope_error**: estimate covers the full paper, not the MRE (or vice-versa) — the
   main thing this redo fixes; apply the weights→eval-only rule above.

Keep the SAME underlying source observations the original basis used (paper-stated GPU
count, steps, per-step/per-frame times, paper-reported GPU-hours). Only correct
arithmetic / units / multiplier / non-compute padding / scope. Do NOT invent a new
experiment.

## Bands & cap
- Bands: `0-8`, `8-32`, `32-96`, `96-192`, `>192`.
- Cap hours at **192** (over-cap band `>192`).
- **UPDATE 2026-07-09:** cap lowered to **96**. The three `96-192` rows
  (2505.17315, 2512.13837, 2510.20261 — 432 H100-h, 26% of eval compute for n=3)
  were swapped for the deterministic next-in-line cheap rows of the same tier:
  2506.10943 SEAL (Medium, 12h), 2510.19784 DynaInfer (Medium, 12h),
  2602.03066 NTK-shortcut (Hard, 4h). No 0-8 Medium candidates remained in the
  pool, so the two Medium replacements come from 8-32 cheapest-first. New
  composition: 0-8:59 / 8-32:27 / 32-96:14, total 1247.1 H100-h, max 96.0.
  Incoming rows carry pre-recompute hour estimates and hand-authored
  match_targets → both need the recompute/repin treatment.
- **UPDATE 2026-07-10:** dropped **2506.04536 NOBLE** (Easy, 0-8, 0.5h) — genuine
  availability wall: weights released but the HoF simulation ground-truth voltage
  traces needed for the 2.18% rel-L2 target are not released (empty `data/`,
  empty `data_path` in `noble.yaml`), so the metric is not producible. Swapped in
  the deterministic next-cheapest Easy 0-8 row **2505.19154 FHGS** (0.028h,
  `paper_reported` basis). Composition unchanged (34/33/33, bands 59/27/14, total
  1246.6→"1,247"); paper `paper_reported` basis count 18→19. FHGS carries a
  hand-authored provisional PSNR point-estimate match_target (30.9 on DTU scan24)
  → needs the repin/human-freeze treatment. Two other Qwen3.6 "blocked" audits
  (2505.18456 ADLM, 2503.17482 Steerability) were NOT dropped: their artifacts are
  public (sibling checkpoints / released data), so they are re-audit cases, not
  availability walls.
- **UPDATE 2026-07-11:** dropped **four Medium rows** under the same
  hard-wall / never-released principle and swapped in the four next-cheapest
  audited-pool Medium rows (cheapest-first, 8-32 band; no 0-8 Medium candidates
  remained). Composition held at 34/33/33; overall bands 59/27/14 → **57/29/14**
  (Medium 0-8 18→16, 8-32 11→13); total ~1246.6 → **~1259 H100-h**. Dropped:
  - **2503.17482 Steerability** — the paper's own released CSV contradicts its
    Table 1 number by 2×, and the SD1.4 data behind the claim exists nowhere
    (internally-contradicted + source data never released). Was Medium 0-8, 0.0h.
    Previously a "blocked" re-audit case (07-10); the CSV contradiction is a
    genuine construct wall, so it is now a drop, not a re-audit.
  - **2505.17685 FSDrive** — checkpoint never released + ToS-gated nuScenes with
    no complete mirror. Was Medium 8-32, 20.64h.
  - **2505.20425 OSVI-WM** — `mujoco_py` has no aarch64 build, ever. **Caveat:
    this is a harness-specific aarch64 wall, NOT a paper defect** — if the
    harness ever leaves aarch64, this paper should RETURN rather than count as a
    permanent wall. Was Medium 8-32, 12.8h.
  - **2110.03155 Categorical-DRL** — dropped for consistency: same
    aarch64/`mujoco_py` mechanism as OSVI-WM (it was DQ'd over that mechanism in
    sweep 2640098 but marked passable and never adjudicated). Carries the same
    harness-specific-return caveat. Was Medium 0-8, 3.75h.
  Added (provisional match_targets + provisional H100 fields → all four owe the
  repin/human-freeze treatment, flagged `h100_needs_human_review=true`):
  **2510.24940 SemCoT** (12.0h, SVAMP acc ~46% point-estimate),
  **2511.00119 GeneFlow** (12.0h, RF FID « diffusion, direction),
  **2505.24089 BASE-MIA** (12.8h, Cora GCN AUC ~82.45% point-estimate),
  **2410.19933 RePO** (13.0h, safety rate >90% threshold). Uploaded
  `eval_100.jsonl` to HF (commit `6feda9cb`).
- **UPDATE 2026-07-13:** dropped **two Hard rows with NO replacement** (user
  decision) after the prospective host-probe adjudication of all 33 Hard papers
  (no agent sweep exists for Hard; one adversarial prober + two independent
  refuters per claimed wall; report `Analysis/Repro-Agent Runs/Hard-Tier
  Genuine-Wall Adjudication (prospective probe, 2026-07-13).md`). Composition
  now **34/33/31, test=98**; Hard bands 14/9/10 → **13/8/10**; total ~1259 →
  **~1235 H100-h**. Dropped:
  - **2506.07104 REO-RL** — implementation + trained checkpoints never released
    (single stale "Init" commit, empty Releases, unanswered code-request issue,
    zero HF hits); the lockfile agent_task's base-model-only proxy cannot test
    the actual ≥50% REG-reduction claim, and REO-RL training from scratch does
    not fit the 8 H100-h band. Was Hard 0-8, 6.0h.
  - **2505.19516 DiffE2E** — anchor (Driving Score 83, CARLA Longest6
    closed-loop) requires the CARLA simulator, which has never shipped an
    aarch64 build across its release history (x86-only SSE in the UE4 toolchain,
    no maintained aarch64 fork). **Harness-specific wall, NOT a paper defect —
    RETURN if the harness leaves aarch64** (same caveat class as OSVI-WM /
    Categorical-DRL). Was Hard 8-32, 18.0h.
  Adjudication cleared the other 31 Hard rows as reproducible-in-principle
  (boundary cases and verified lockfile link corrections listed in the report).
- **UPDATE 2026-07-13 (later):** refilled the two Hard slots (user decision,
  cheapest-first from the remaining 23 audited Hard pool rows, each host-probed
  before insertion). Composition back to **34/33/33, test=100**; Hard bands
  13/8/10 → **15/8/10**; total ~1238 H100-h. Added (provisional match_targets,
  `h100_needs_human_review=true`, owe the repin/human-freeze treatment):
  - **2505.12677 CURE** (0.6h, Hard 0-8) — eval-only route: the paper's own
    pre-erased UNet checkpoints are on a public ungated Google Drive folder
    linked from the repo; anchor LPIPS_e=0.41 (Table 1, Kelly McKernan row,
    threshold bar). Unlearning training code itself is unreleased.
  - **2410.15392 EF-3DGS** (2.0h, Hard 0-8) — no code, but fully open pipeline:
    Tanks and Temples public, events synthesized with open V2E, 3DGS
    source-buildable on aarch64; direction anchor "up to 3dB higher PSNR /
    40% lower ATE at 1 FPS" (v1 abstract + Tables 1-2; v2 abstract says 2dB —
    repin must pin scene-level numbers).
  **Four cheaper candidates were REJECTED on host-probe for latent paid-API
  dependence the pool signals do not capture**: 2505.15101 CaMVo (5 of 7
  ensemble models are Claude/GPT/o-series APIs), 2503.02863 SteerConf (headline
  models GPT-3.5/GPT-4, ~$1500 API spend; on the open LLaMA3-70B the paper's own
  Table 2 shows ECE worsening 5.0→7.8), 2602.20296 Decomp (decomposition teacher
  is GPT-4o, decomposed data unreleased), 2512.00762 Seeing-the-Wind (material
  estimation via GPT-4o-Vision is in the MRE). Screen remaining pool rows for
  API-in-the-loop before any future swap-in.
- Band edges inclusive → a value on the boundary lands in the LOWER band.
- Reference impls:
  - `src/reprocli_vllm/audit/h100.py` — `recomputed_hours`, `h100_band`,
    `arithmetic_mismatch`, `H100_BANDS`, `MISMATCH_TOLERANCE = 0.2`.
  - `src/reprocli_vllm/audit/select_pool.py` — `H100_CAP = 192.0`,
    `selection_band = h100_band(...)`.
- Expected: the `96-192` band may lose ~5–6 papers after correction. Fine.

## Per-row fields to update (only on rows that actually move; preserve all others)
```
audited_h100_hours
h100_estimate.{hours, gpu_count, wallclock_hours, gpu_type, multiplier, basis_kind, basis}
h100_hours_estimate
h100_estimate_basis
h100_recomputed_hours
h100_arithmetic_mismatch
h100_band
selection_band
h100_needs_human_review
h100_hours_adjudicated
```
Availability signals live under
`signals.{weights_available, code_available, dataset_available, dataset_is_standard}.value`.

## Orchestration (Workflow, per paper)
- **Stage 1 — recompute** (Sonnet 5, low thinking): read a per-paper file
  (`central_claim`, MRE config, current h100 fields, AND the 4 availability signals),
  emit a recomputed record. Scope decision keys on `weights_available` (eval-only if
  released).
- **Stage 2 — adversarial verify** (Sonnet 5, low thinking): writes the final record.
- **Stage 3 — adjudicate** (Sonnet 5, low thinking): contested / low-confidence rows only.
- Structured output via JSON schema on every stage. One paper per agent.
- Prior script to reuse for structure:
  `.claude/workflows/scripts/remake-h100-hours-wf_2df8999d-da7.js` — reuse its structure,
  but make the scope decision key on `weights_available` (eval-only if released).
- **Pre-run:** enrich each per-paper row file with the 4 availability signals.

## Deliverable
1. Download `eval_100.jsonl` from HF (back it up).
2. Run the workflow over all 100 ids.
3. Validate: no row exceeds 192h without justification; every weights-released paper is
   eval-only; recompute `h100_band` / `selection_band` from the corrected hours.
4. Assemble corrected `eval_100.jsonl` (change only moved rows; preserve everything else).
5. Diff summary: old→new hours, band migrations, biggest movers, and flag any
   `selection_band` vs `h100_band` mismatch.
6. Reupload `eval_100.jsonl` to `Mithilss/reprobench-splits` (HF write auth, user
   `Mithilss`).
