# Prompt: build the anonymized RECLAIM code release

Paste everything below this line into a cloud Claude Code session on the reprocli repo.

---

Build the public, anonymized, release-ready copy of this repository under the name RECLAIM, using subagents for the parallel parts. The paper (`paper_latex/`) calls the benchmark RECLAIM and will link the release from footnote 1 via anonymous.4open.science. Nothing under the release may name the author, the university, the cluster, the database, or the development-era project name.

GOAL: a fresh git repository at `../reclaim/` (sibling of this checkout), one squash commit by `RECLAIM Authors <reclaim@anonymous.invalid>`, containing the harness renamed to `reclaim_*`, the frozen splits, the scrubbed run records, the table generators, a static run viewer, tests, and a README a reviewer can follow from clone to a graded run. Then the paper's printed paths and commands match the release.

DONE-WHEN (every line passes):
```bash
cd ../reclaim
git log --oneline | wc -l                                   # 1
git log --format='%an <%ae>' | sort -u                      # RECLAIM Authors <reclaim@anonymous.invalid>
grep -rIiE 'mithil|salunkhe|mithils3|msalunkhe|58468909|outlook\.com|illinois|uiuc|grainger|siebel|ncsa|deltaai|delta\.ncsa|dtai-login|gh-login|ghx4|/u/[a-z]|/work/nv|dltawork|\bbfvr\b|\bbetw\b|rjnkpoxwdslkgxjliakq|supabase|agent-logs|github\.com/mithils3|reprobench|reprocli' . --exclude-dir=.git | wc -l   # 0
PYTHONPATH=src python3 -m pytest tests -q                   # all pass, 0 skipped for anonymity reasons
for m in reclaim_repro reclaim_claude reclaim_serve; do PYTHONPATH=src python3 -m $m --help >/dev/null || echo "FAIL $m"; done
wc -l data/splits/eval_100.jsonl data/splits/dev_14.jsonl   # 100 and 14
python3 -c "import json;m=json.load(open('runs/index.json'));print(len(m['runs']), len(m['sweeps']), len(m['papers']))"   # 372 12 100
PYTHONPATH=src python3 scripts/tables/gen_eval100.py --splits data/splits --runs runs --out /tmp/t.tex && test -s /tmp/t.tex
cd ../reprocli/paper_latex && grep -rn 'reprocli\|REPROCLI' *.tex appendix/*.tex prompts/ | wc -l   # 0
cd ../reprocli/paper_latex && pdflatex -interaction=nonstopmode iclr2027_conference.tex 2>&1 | grep -E '^!|undefined' | wc -l   # 0
```

MUST-NOT-CHANGE: this checkout's `src/`, `tests/`, `scripts/`, `prompts/`, `rubric_audit.md` (the dev repo keeps its names; cluster runbooks and running sweeps depend on them); any audit score, verdict, flag, or transcript text beyond what `tools/anon_viewer/scrub.py` already applied; the wording of the frozen prompts and rubric apart from the benchmark-name substitution; any claim or number in the paper; `tools/anon_viewer/` and the deployed viewer.

## Facts you need

- Packages to rename, one to one: `reprocli_repro` to `reclaim_repro`, `reprocli_claude` to `reclaim_claude`, `reprocli_vllm` to `reclaim_vllm`, `reprocli_serve` to `reclaim_serve`, `reprocli_data` to `reclaim_data`, `reprocli_openai` to `reclaim_openai`. Env vars `REPROCLI_*` become `RECLAIM_*`. `src/run_arxiv_prompt_vllm.py` keeps its name. The invocation style stays `PYTHONPATH=src python3 -m <package>`, which is what the paper prints; add no packaging.
- The benchmark's development name is ReproBench and appears in `prompts/`, `rubric_audit.md`, and many docstrings. Every occurrence becomes RECLAIM. The paper currently discloses this substitution for the printed prompts (grep `substitut` in `paper_latex/appendix/*.tex`); after the release carries the substitution too, reword that disclosure to say the released files carry the public name and the sweeps ran under a development name. Keep the disclosure, do not drop it.
- Lockfile loader: `src/reprocli_repro/dataset.py` defaults to the HF dataset `Mithilss/reprobench-splits`. The release ships the splits as files and defaults to them: `data/splits/eval_100.jsonl` (100 rows, `split=eval`) and `data/splits/dev_14.jsonl` (14 rows). Source them with `huggingface_hub.snapshot_download("Mithilss/reprobench-splits", repo_type="dataset")` (files `eval_100.jsonl`, `dev_split.jsonl`); if that needs a token you do not have, the local cache on his PC is `~/.cache/huggingface/hub/datasets--Mithilss--reprobench-splits/snapshots/*/`. The HF path stays supported behind `--lockfile <owner/name>` with no default id in code. Verify the row counts and that every row has `split` set.
- Run records: the scrubbed, leak-gated export already exists as the static site at https://reclaim-traces.vercel.app (`data/index.json`, `data/runs/*.json`; 372 runs, 12 sweeps, 4 agents, pinned Claude Sonnet 5 grades). `tools/anon_viewer/manifest.json` is committed and carries the counts; `tools/anon_viewer/public/data/` is gitignored and exists only on his PC. Fetch from the site (or copy from the local export if present) into `runs/`, then check the counts against `manifest.json`. Do not re-export from the database and do not touch any record's content.
- The static viewer `tools/anon_viewer/public/` (HTML, JS, CSS, `vercel.json`) is already scrubbed. Copy it to `viewer/`, drop `vercel.json`, point its data path at `../runs/`, and document `python3 -m http.server` from the repo root. If the path change needs more than a few lines, skip the viewer and link the hosted one in the README instead; say which you did.
- Table generators are `paper_latex/tables/{gen_eval100,gen_audit_finalizer,gen_example_row}.py`. Copy them to `scripts/tables/`, make them read `--splits` and `--runs` from the release layout, and confirm the eval-100 table they emit matches the committed `paper_latex/tables/eval100.tex` row for row.
- Telemetry: `src/reprocli_repro/{__main__,audit_upload,event_sink,gpu_usage,live_log,metrics_beacon,postgrest,run_beacon,supabase_sink}.py` and `src/reprocli_vllm/runtime/audit_sink.py` reference the database; `tools/rebuild_splits_from_app.py` and the two `tools/*/public/config.js` files hard-code the project URL `https://rjnkpoxwdslkgxjliakq.supabase.co` and an anon key. In the release, telemetry reads `RECLAIM_TELEMETRY_URL` and `RECLAIM_TELEMETRY_KEY` from the environment and is a no-op when unset. No URL, key, or project ref stays in code, comments, tests, or fixtures.
- Cluster scripts: keep `scripts/serve/{serve_gh200.sbatch,serve_multinode.sbatch}`, `scripts/reproduce/{dsv4_flash,qwen3_27b,minimax_m2,muse_spark}/` (the four agents in the paper), `scripts/reproduce/repro_audit_one.sh`, and `scripts/cluster/build_cuda_sandbox.sh` (the Apptainer sandbox of Appendix A). Slurm account, partition, QOS, reservation, home and scratch paths, module names tied to the site, and login-node hostnames become `<account>`, `<partition>`, `<scratch>` style placeholders with one comment line each. Drop `repair_*`, `dev15*`, `run_dev15.sh`, `glm52/`, `laguna_s21/`, `scripts/minimax_m3/`, `serve_glm52*`, `glm52_2node.sh`, `serve_interactive.md`, and `bench_*.py`. GH200, Slurm, and Apptainer may stay named; the paper names them.
- Exclude from the release entirely: `.claude/`, `tasks/`, `notes` (symlink), `outputs/`, `data/paper_bundle_dataset/`, `commands/`, `tools/` (except the two copies above), `paper_latex/`, `AGENTS.md`, `BASELINE.md`, `PLAN.md`, `REFACTOR_REPORT.md`, `REMOVED.md`, `rubric_audit_v2.md`, `CLAUDE.md`, every zip and `__pycache__`.
- Keep: `src/`, `tests/`, `prompts/`, `rubric_audit.md` (the frozen rubric, 2026-07-16), `requirements.txt`, `ruff.toml`, `.gitignore` (rewritten for the new layout).
- Paper commands of record are in `paper_latex/appendix/h_running.tex` (serve, run one paper, grade one run). Paths the paper prints: `grep -rno 'reprocli[A-Za-z_./-]*' paper_latex/*.tex paper_latex/appendix/*.tex`. Every one of them must exist under the new name in the release.
- Licenses: `LICENSE` is MIT for code and `data/LICENSE` is CC BY 4.0 for the splits and run records, both attributed to "RECLAIM Authors". Flag this in your final report as a decision he can flip.

## README.md

Write it fresh for a reviewer who has not read the paper. Plain English, short sentences, no em dashes, no marketing, no "X, not Y" contrast frames. Numbers only if they appear in the paper (100 papers, the three tiers, the 96 H100-hour cap, four agents, 372 runs); nothing else. Sections, in order:

1. One paragraph: what RECLAIM measures (an agent gets the paper and whatever the authors released, must reproduce the frozen target claim within a numeric tolerance and a metered GPU budget, and a pinned auditor grades the execution evidence).
2. Links: hosted trace viewer, paper (under review, anonymous).
3. Repository layout as a table, one row per top-level directory.
4. Install (Python 3.11, `pip install -r requirements.txt`; vLLM is only needed to serve a model locally).
5. Quickstart: the three commands from Appendix H with the new names, then how to read the verdict file.
6. Dataset: the two split files, the freeze date 2026-07-13, the row fields in a short table derived from the jsonl keys, and what the `match_target` and tolerance mean.
7. Run records: layout of `runs/`, the fields of a run record, the nine failure-mechanism slugs (take them from `paper_latex/appendix/g_taxonomy.tex`, names verbatim), and one worked example of reading a run.
8. Regenerating the paper's tables from `runs/` and `data/splits/`.
9. Running on a cluster: what the Slurm and Apptainer scripts assume and which placeholders to fill.
10. Anonymity note (development name substituted, identifiers redacted in transcripts, records unchanged otherwise), license, citation stub.

## Subagent plan (11 agents, no more)

Phase 0, you alone: create `../reclaim/`, `git init`, set `user.name` and `user.email` to the anonymous author locally in that repo, copy the keep-list with `git ls-files` from this checkout (never `cp -r` of the working tree; it would drag `notes`, `outputs`, and zips). Do not commit until Phase 3. Builders work on disjoint paths in that one tree and never run `git add` or `git commit`; that avoids the shared-index problem.

Phase 1, six builders in parallel, each with the full facts section above and its own path set:
1. Rename and scrub `src/` and `tests/` (package dirs, imports, env vars, strings, docstrings, fixtures; default lockfile to the local splits; telemetry to env-driven no-op). Run the tests before returning.
2. Cluster scripts: keep-list, placeholders, drops.
3. Data and records: splits into `data/splits/`, run records into `runs/`, the viewer into `viewer/`, count checks.
4. `README.md`, `LICENSE`, `data/LICENSE`, `CITATION.cff` (anonymous), `.gitignore`.
5. `scripts/tables/`: port the generators and diff their eval-100 output against `paper_latex/tables/eval100.tex`.
6. Paper: on a branch of this checkout, rename every printed path, module, and env var in `paper_latex/**.tex` and `paper_latex/prompts/` to the release names, reword the substitution disclosure, compile clean, and leave the branch uncommitted for Phase 3. Touch no claim, number, or citation.

Phase 2, four refuters in parallel against the finished tree, each returning `file:line` findings only:
7. Mechanical leak gate: the DONE-WHEN regex over the tree and over `git log`, plus every string that looks like a host, a path under a home directory, a job id, an account string, or a key.
8. Semantic leak read: read every markdown file, comment block, and script header for indirect identifiers (site-specific partition names, node shapes stated as this site's, internal project handles, dates that pair with a public job posting, personal pronouns that reveal a single author).
9. Paper consistency: every path and command printed in the paper resolves in the release; every `--help` in the DONE-WHEN runs; the eval-100 table regenerates row for row; the README's quickstart matches Appendix H exactly.
10. Fresh-clone smoke: `git clone` the tree into a temp dir, new venv, install requirements without vLLM, run the tests, load both splits, regenerate the tables, serve the viewer, and open a run page with Playwright with zero console errors.

Phase 3, one fixer (agent 11) applies every refuter finding, reruns the DONE-WHEN block, and reports. Then you: squash-commit the release with the anonymous author, commit the paper branch here with the usual attribution, and run the DONE-WHEN block one final time yourself before reporting.

## Report

Lead with the DONE-WHEN results verbatim. Then: what was dropped and why, the two license choices, whether the viewer shipped, and any refuter finding you could not fix. Finish with the three manual steps left for him: push `../reclaim/` to a new GitHub repository, mint the link at https://anonymous.4open.science (add the terms from the leak-gate regex, set the expiration after the ICLR 2027 notification date), and paste the minted URL back so the placeholder `RECLAIM-XXXX` in footnote 1 and the README link get filled.
