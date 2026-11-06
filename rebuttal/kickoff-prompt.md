You are running on claude-vps, an always-on Hetzner box (4 cores, 8 GB, no GPU) with a copy of Mithil's laptop setup. It ran the distillation project until today; that work is paused until Nov 16 and its files under ~/Alingment/Distillation are not yours to change. Keep memory use modest. Heavy work goes to DeltaAI (GPU) and Delta (CPU) as CLAUDE.md says; the Duo links from this box may not be open yet, so check with `ssh -o BatchMode=yes delta true` before relying on them.

Task: draft a plan for replying to our ICLR 2027 reviews (submission 22528, RECLAIM) on OpenReview by 2026-11-14. The three reviews and the PAT pre-submission feedback are in rebuttal/reviews-2026-11-06.md. Ratings are T29u 3, rqBN 3, YGTR 2, so the plan should aim to move YGTR and firm up the two weak accepts.

Before proposing anything, read what we already know. Use all previous memories: this repo's memory (MEMORY.md is loaded), ~/.claude/projects/-home-mithil/memory, and every project's memory under ~/.mstack/memory; search past sessions with `python3 ~/.mstack/bin/msessions.py search "<query>" --context` and settled questions with `python3 ~/.mstack/bin/msearch.py decisions --query "<words>"`. Several reviewer asks touch things the memories settle (for example human-grader-study-lost, baseline-harness-stays-thin, paper-model-roster, reprobench-validity-defenses, h100-weights-eval-only-caveat), so check each ask against them and say where a memory limits what we can claim.

Budget: we can spend up to 600 USD of OpenAI API credits if needed, mainly to answer the frontier-model and harness requests (a frontier model as the agent, or Codex, Claude Code or mini-SWE-agent as the harness, on a stratified subset of papers). Say how many papers and runs that buys, how the cost was estimated, and what GPU-hours it also needs on DeltaAI.

GPU account: all rebuttal GPU work on DeltaAI charges the Slurm account bgnp-dtai-gh (Mithil, 2026-11-06: "let this agent use bgnp-dtai-gh"; its `accounts` row read 1304 and 6367, so check its remaining balance with `accounts` on DeltaAI and budget against that). The repo's run_gpu currently charges bfvr-dtai-gh (memory reprocli-gpu-account-betw, account string in src/reprocli_repro/cluster.py); the plan should say how rebuttal runs get bgnp-dtai-gh without moving the /work/nvme/bfvr/ paths.

The plan should cover, in this order:
1. Every reviewer concern, grouped across reviewers, each marked as new evidence, existing evidence we only need to surface, or a text fix.
2. For each piece of new evidence: what we run, on which machine, the cost in dollars and GPU-hours, the time it takes, and what result would change our reply.
3. The paper revisions, including the PAT checklist errors that are real (verify each against paper_latex/ before listing it).
4. A day-by-day schedule from 2026-11-07 to 2026-11-14 with an owner for each item (Mithil, Haochen, Samridhi), and the cut list if we fall behind.
5. A first draft outline of each reply (one per reviewer plus a general reply), with the key sentence for each concern.

Write the plan to rebuttal/PLAN.md, then commit and push it on the current branch. Do not launch jobs, spend credits, edit paper_latex/, or post anything to OpenReview yet. Stop after the plan and wait for Mithil to review it.
