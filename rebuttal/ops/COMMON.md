# Rebuttal workers: shared facts

Plan of record: `rebuttal/PLAN.md` (read only the section your brief names). Status board: `rebuttal/STATUS.md` (the orchestrator edits it; you do not).

## Machines
- claude-vps (you are here): repo at `~/PyCharmProjects/reprocli`, branch `repro-next`. Light work only: edits, git, one small check at a time, nice 19.
- DeltaAI (GPU, aarch64 GH200): run commands with `delta 'cmd'` (socket already logged in, BatchMode). Repo checkout `~/reprocli` (= /u/msalunkhe/reprocli), branch repro-next; `git -C ~/reprocli pull -q` after you push. Run bundles: `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper_id>/...` (read only). Rebuttal scratch and outputs on DeltaAI: `/work/nvme/bfvr/msalunkhe/rebuttal/` (create subdirs per item).
- GPU account for every new job: `betw-dtai-gh` (`sbatch -A betw-dtai-gh`, and `export REPROCLI_SLURM_ACCOUNT=betw-dtai-gh` for the harness's run_gpu steps). Never touch other jobs in the queue (Distillation f1* jobs, etc.).
- Delta (CPU): heavy CPU analyses go through `delta cpu NAME 'cmd'` (Slurm job on bgnp-delta-cpu; /work/nvme is shared). A scan over a few hundred files on the DeltaAI login node at `nice -n 19` is fine if it finishes in under 10 minutes.
- Secrets live in `~/.bashrc` on each host. Load by pointer: `source <(rg '^export (OPENAI_API_KEY|META_MODEL_KEY|ANTHROPIC_API_KEY|SUPABASE_URL|SUPABASE_SERVICE_KEY|HF_TOKEN)=' ~/.bashrc)`. Never print, echo, log or commit a key value.

## Rules
- Use `rg` for search everywhere, `fd` on DeltaAI. Never `pkill -f`; stop processes by pid. One Bash call waits at most 285 s; longer work runs in tmux or Slurm with a log file, and you report the job id and log path.
- Do not edit `paper_latex/`, the frozen rubric (`rubric_audit.md`), `prompts/prompt_audit.txt`, existing run directories, anything under `~/Alingment/Distillation`, or OpenReview.
- Work in your own git worktree so nothing you do touches another worker's files or the shared index: `git -C ~/PyCharmProjects/reprocli fetch -q && git -C ~/PyCharmProjects/reprocli worktree add --detach ~/wt/<item> origin/repro-next`, edit and test there, commit early and often (`git commit -m "<msg>" -- <paths>`), and publish each commit with `git pull --rebase -q origin repro-next && git push -q origin HEAD:repro-next`. Remove the worktree when done (`git -C ~/PyCharmProjects/reprocli worktree remove ~/wt/<item>`). No Co-Authored-By or other attribution lines in commit messages. Outputs that live only on DeltaAI (/work/...) get a copy of their summary files committed under rebuttal/results/ as soon as they exist.
- Spend ledger: any API call that costs money appends one JSON line per call or per run to `/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl` on DeltaAI: `{"ts":..., "item":"E7", "provider":"openai|meta|anthropic", "model":..., "in":..., "cached":..., "out":..., "usd":...}`. Hard caps across all items: OpenAI $700, Meta $480. Check the ledger total before launching paid work; stop if the cap would be passed.
- Prices per million tokens (input / cached input / output): gpt-6.1-sol flex 1.00/0.05/5.00, gpt-6.1-terra flex 0.50/0.025/2.50, gpt-6-astra flex 5.00/0.50/25.00 (standard = 2x flex), muse-wonder-1.0 4.00/0.20/20.00, muse-spark-1.2 1.25/0.15/4.25.
- Results: one frozen file per item under `rebuttal/results/<item>/` in this repo (JSON or CSV plus a README.md of under 200 words: what was computed, from which files, the command, and the headline numbers with denominators). Exact 95% intervals (Clopper-Pearson or Wilson, say which) on every count.
- Report back in under 200 words: what passed its check, file paths, commit hash, any job ids, and anything that blocked you.
