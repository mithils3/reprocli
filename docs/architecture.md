# ReproBench — system architecture (current)

How the dataset is built and consumed today. Two stages produce **the lockfile**
(the band-selected audit pool), which two consumers read: the reproduction agent
and the auditor.

> Verified against: `run_arxiv_prompt_vllm.py`, `output_schema.py`,
> `select_pool.py`, `audit_inputs.py`, `audit.py`, `rubric_audit.md`.
> Status legend: ✅ live · 🚧 not yet wired.

## Pipeline (Mermaid)

```mermaid
flowchart TD
  classDef lock fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#000;

  subgraph S1["STAGE 1 — Dataset construction · classifier pass (mode ≠ audit) ✅"]
    direction TB
    A["NeurIPS 2025 arXiv LaTeX bundles"]
    B["prompt.txt · {PAPER_TEXT}"]
    C["MRE record per paper<br/>output_schema.FINAL_JSON_SCHEMA<br/>central_claim · claim_evidence · mre_config<br/><b>match_bar</b> · agent_task · signals · h100_estimate"]
    D["post-process<br/>normalize_score_and_tier · web_verification · h100 audit"]
    E["&lt;run&gt;_extracted.jsonl<br/>(every classified paper)"]
    A -->|"load_bundle_papers()"| B
    B -->|"vLLM + tool loop · web_tools verify links"| C
    C --> D --> E
  end

  subgraph S2["STAGE 2 — Pool selection · select_pool.py ✅"]
    direction TB
    F{"verified AND<br/>audited H100 ≤ 192 hr"}
    G["audit_pool_extracted.jsonl · ≈200 rows<br/><b>THE LOCKFILE / dataset</b>"]
    F -->|"band-stratified Easy/Medium/Hard<br/>bands 0-8/8-32/32-96/96-192 · cheapest-first"| G
  end
  E --> F

  subgraph CA["CONSUMER A — Repro agent · Haochen / single-agent 🚧 not wired"]
    direction TB
    H["attempt reproduction in sandbox"]
    I["run dir per paper<br/>code · logs · artifacts"]
    H --> I
  end

  subgraph CB["CONSUMER B — Auditor · mode = audit ✅"]
    direction TB
    J["build_audit_prompt<br/>rubric_audit.md + claim_block + run_dir_manifest"]
    K["AUDIT schema · score 0–5 + cheat_flags + citations"]
    L["finalize_audit_row<br/>anti-cheat cap → verdict<br/>reproduced / partial / not_reproduced / unverifiable"]
    J -->|"vLLM + read-only run-dir tools"| K --> L
  end

  G -->|"agent_task"| H
  G -->|"central_claim · mre_config · <b>match_bar</b> (applied verbatim)"| J
  I -. "runs_dir (handoff 🚧 not wired)" .-> J

  class G lock;
```

## Pipeline (ASCII fallback)

```
STAGE 1 — DATASET CONSTRUCTION  (classifier pass, mode != audit)            ✅
   NeurIPS 2025 arXiv LaTeX bundles
        │  load_bundle_papers()  →  Paper(tex_files)
        ▼
   prompt.txt {PAPER_TEXT} ──► vLLM + tool loop ──► web_tools (verify links)
        ▼
   ONE MRE record per paper   (output_schema.FINAL_JSON_SCHEMA)
     ├ central_claim, claim_evidence, paper_kind
     ├ mre_config     — smallest experiment that tests the claim
     ├ match_bar      — {kind, op, reference_value, tolerance, note}   ◄ pinned here
     ├ agent_task     — what the repro agent is told to do
     ├ verified_links, signals   (code / data / weights)
     └ h100_estimate  (compute cost)
        ▼  normalize_score_and_tier · web_verification · h100 audit
   <run>_extracted.jsonl   (every classified paper)

STAGE 2 — POOL SELECTION  (select_pool.py)                                  ✅
   keep if  verified  AND  audited H100 ≤ 192 hr
   band-stratified Easy/Medium/Hard · bands 0-8/8-32/32-96/96-192 · cheapest-first
        ▼
   audit_pool_extracted.jsonl   ◄══ THE LOCKFILE (~200 rows)
   each row = claim + mre_config + match_bar + tier + cost

        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                              ▼
 CONSUMER A — REPRO AGENT            run dir          CONSUMER B — AUDITOR
 (Haochen · single-agent 🚧)      (code/logs/        (mode == audit) ✅
   reads agent_task                 artifacts)         rubric_audit.md
   └► attempts reproduction   ───── runs_dir ─ ─ ─►  + claim_block(claim,
      in a sandbox                  🚧 not wired         mre_config, match_bar)
   writes one run dir per paper                       + run_dir_manifest()
                                                            ▼
                                                      vLLM + read-only run-dir
                                                      tools → AUDIT schema 0–5
                                                            ▼
                                                      finalize_audit_row
                                                      anti-cheat cap → verdict
```

## The `match_bar` through-line

The pinned success bar — "how close counts as a match" — is set once and reused,
so every agent is judged against the same ruler instead of one the auditor
re-infers each run.

```
Stage 1 classifier PINS it  →  lockfile CARRIES it  →  Auditor APPLIES it verbatim
```

| `kind` | what counts as a match | example fields |
|---|---|---|
| `point_estimate` | land near a value | `op=abs_rel_within, ref=25.76, tol=0.05` |
| `threshold` | clear a floor/ceiling | `op=">=", ref=85, tol=null` |
| `direction` | beat a baseline (no tolerance band) | `op="measured_method > measured_baseline", ref=null, tol=null` |
| `magnitude` | the *size* of a delta is the target | `op="delta within tol", ref=+5, tol=0.05` |
| `none` | no checkable scalar/relation (theory/position) | all null |

Rows that predate the field (or `kind = none`) fall back to the rubric defaults in
`rubric_audit.md` C1: ±5 % for a point estimate, direction-only for a comparative.

## Known gap

Consumer A writes run dirs; Consumer B reads `runs_dir`. Nothing connects them yet
— wiring the run-bundle → `runs_dir` handoff is what turns this from an auditor into
an end-to-end benchmark.
