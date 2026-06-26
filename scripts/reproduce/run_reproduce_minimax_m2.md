# Run one arXiv id through the reproduction agent (brain = MiniMax-M2.7)

End-to-end runbook for driving **one paper** through the S6 reproduction agent
(`reprocli_repro`) on DeltaAI, using **MiniMax-M2.7** as the brain — the same model
we serve for the classifier (`scripts/minimax_m2/paper_classification.sbatch`).

The key idea is the **orchestrator / GPU split**: the brain is one persistent
serve job, the reproduction agent is a *cheap CPU process* that attaches to it by
URL and **never holds a GPU**; it `salloc`s a GPU *just in time* for each
`run_gpu` step and releases it the instant the command exits. So three things are
in play:

| layer | where it runs | GPUs held |
|---|---|---|
| **Brain** — `reprocli_serve` MiniMax-M2.7 | one `ghx4` job (TP=4) | 4×GH200, the whole time |
| **Orchestrator** — `python -m reprocli_repro` | a **login node** (or small CPU alloc) | none |
| **Experiment** — each `run_gpu` step | a JIT `salloc … srun …` | K GPUs, only while the step runs |

---

## 0. Prerequisites (once)

- Repo + venv on the cluster: `/u/msalunkhe/reprocli` with `.venv` (has `vllm`,
  `datasets`, `huggingface_hub`). The orchestrator itself only needs
  `datasets` + stdlib HTTP, but the same venv works.
- `uv` on `PATH` (the agent builds a per-paper `uv` venv in each workspace).
- MiniMax-M2.7 weights reachable (HF id `MiniMaxAI/MiniMax-M2.7` or the local
  mirror `/work/nvme/bfvr/msalunkhe/MiniMax-M2.7`).
- `HF_TOKEN` exported (the lockfile dataset and the paper bundle come from the Hub).
- Point the HF cache at the NVMe work dir, not `$HOME` — the paper bundle is large
  and is downloaded in full (non-streaming) on first use, then cached:
  `export HF_HOME=/work/nvme/bfvr/msalunkhe/hf_cache`

Pick a sample paper from the **dev-15** split (`validation`), **not** the eval-100
benchmark: running the agent against eval-100 during development would leak into /
contaminate the frozen benchmark. dev-15 is the disjoint development split kept for
exactly this. Easy tier is the cheapest first run:

```bash
# 2506.09045 is an Easy dev-15 paper — a good smoke target that never touches eval.
ARXIV_ID=2506.09045
```

---

## 1. Serve the brain (MiniMax-M2.7)

Submit the dedicated serve job. It stands up vLLM on one 4×GH200 node (TP=4 from
the model profile) and publishes an **endpoint file** with the routable URL once
`/health` is green.

```bash
cd /u/msalunkhe/reprocli
sbatch scripts/serve/serve_gh200.sbatch
# default ENDPOINT_FILE = /work/nvme/bfvr/msalunkhe/endpoints/minimax_m2.json
```

Wait for it, then sanity-check from a login node:

```bash
ENDPOINT_FILE=/work/nvme/bfvr/msalunkhe/endpoints/minimax_m2.json
until [[ -f "$ENDPOINT_FILE" ]]; do sleep 5; done
curl -f "$(jq -r .base_url "$ENDPOINT_FILE")/health" && echo "  brain up"
```

> Prefer an interactive server you can poke at? Use the single-node block in
> `scripts/serve/serve_interactive.md` — same `reprocli_serve` invocation, same
> endpoint file.

---

## 2. Run the paper through the reproduction agent

From a **login node** (so the agent can `salloc` its own GPU steps — do *not* run
the orchestrator inside another GPU job):

```bash
cd /u/msalunkhe/reprocli
module load python/3.11.9
source .venv/bin/activate
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

# Attach to the brain by URL (zero-flag: the runner auto-discovers it from this).
export REPROCLI_ENDPOINT_FILE=/work/nvme/bfvr/msalunkhe/endpoints/minimax_m2.json

python -m reprocli_repro \
  --paper-id "$ARXIV_ID" \
  --split dev \
  --cluster deltaai \
  --budget-h100-hours 8 \
  --tool-rounds 40
```

Run bundles default to `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs` (the NVMe
work dir, **not** the repo) — override the root with `$REPRO_WORK_ROOT`, or the
exact path with `--runs-dir`.

What each flag does:

- `--paper-id` / `--split dev` — load this one row from the lockfile dataset
  `Mithilss/reprobench-splits`. `--split dev` is the 14-paper `validation`
  (development) split; `--split eval` is the frozen 100-paper `test` benchmark —
  reserve it for final scoring so development never contaminates it.
- `--cluster deltaai` — the JIT GPU substrate `run_gpu` allocates on: account
  `betw-dtai-gh`, partition `ghx4`, `hw=gh200`, 4 GPU/node, `module load
  python/3.11.9`. (Default, shown for clarity.)
- `--budget-h100-hours 8` — the compute ceiling, in H100-equivalent hours. GH200
  is Hopper-class (multiplier 1.0). `run_gpu` refuses a step whose worst case
  (`gpus × minutes × multiplier`) would overspend, and the loop force-finals when
  the budget hits zero.
- The model id is auto-resolved from the server's `/v1/models`. To pin it
  explicitly: `--served-model-name MiniMaxAI/MiniMax-M2.7`.

Equivalent explicit-URL form (instead of the env var):

```bash
python -m reprocli_repro --paper-id "$ARXIV_ID" --split dev \
  --vllm-server-url "$(jq -r .base_url "$ENDPOINT_FILE")" \
  --served-model-name MiniMaxAI/MiniMax-M2.7
```

---

## 3. What the agent does and what you get

The agent loops against the brain through its toolset:

- **`workspace_bash`** — clone the released code, build/populate the per-paper
  `uv` venv, install deps, run CPU work (cwd-confined to the workspace). The tool
  wraps every command to `module load` the cluster's CUDA modules (`cuda cudnn
  nccl` on deltaai), so installs see CUDA — the agent never writes `module load` or
  `srun` itself. The per-paper venv is **clean** (no `--system-site-packages`), so
  the agent installs the paper's own deps (incl. a CUDA torch wheel), not the
  host's CPU packages.
- **`read_file` / `write_file` / `apply_patch`** — inspect and edit, path-confined
  to the workspace; `reference/` (paper LaTeX + supplement) is read-only.
- **`run_gpu`** — the one metered path to a GPU: a JIT `salloc -A betw-dtai-gh -p
  ghx4 --gpus=K --time=MIN srun … bash -lc 'cd <ws> && module load … && <cmd>'`,
  charged on the command's **run time** (queue wait excluded), released on exit.
  The **agent chooses K** (1–4 on deltaai, capped at the node's GPU count) and the
  wall cap per step; the operator only sets the entitlements (account / partition /
  node type) via `--cluster`.

Everything lands under the run bundle (the S6→S7 contract the auditor reads):

```
/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<arxiv_id>/8h/<run_id>/
  workspace/            # the editable code clone + per-paper .venv
  reference/            # read-only paper LaTeX + every supplement file
  evidence/
    commands.log        # one line per shell / GPU command (cmd, rc, cwd, duration)
    trajectory.jsonl    # one structured row per run_gpu step: gpus, run_seconds,
                        #   cost_h100_hours, remaining_h100_hours
    env.lock            # uv pip freeze
    patches/            # every diff applied, verbatim
```

The agent's raw responses go to
`/work/nvme/bfvr/msalunkhe/reprocli/reproduce.jsonl` (override with `--output`;
add `--save-round-jsonl` for a per-round trace).

---

## 4. Sanity-check offline first (no brain, no GPU)

Before burning cluster time, confirm the inputs render. With **no** server
configured the command does a dry run: it prepares the bundle and prints the
rendered prompt, nothing more.

```bash
unset REPROCLI_ENDPOINT_FILE REPROCLI_SERVER_URL
python -m reprocli_repro --paper-id "$ARXIV_ID" --split dev \
  --no-reference --no-build-venv --runs-dir /tmp/repro_dryrun
```

You should see the `[<id>] tier=… band=… budget=8h run_dir=…` summary and the full
reproduction prompt, ending with a "dry run: no brain attached" notice.

---

## 5. Status / caveats

- **Built and exercised (Phases 0–4):** input pipeline, per-paper
  workspace/reference/evidence, the budget meter + JIT-SLURM substrate, the full
  toolset, and the loop that drives one paper to a stop (natural, round limit, or
  `budget_exhausted`).
- **Not yet wired (Phases 5–6):** the post-loop harness re-execution that writes
  the graded `result.json`, and the auditor bundle. For now a run leaves you the
  evidence dir + the agent's final response — not a pass/fail verdict.
- **Executor:** SLURM only. `run_gpu` always goes through a JIT `salloc`, so the
  orchestrator must run somewhere it can submit jobs (a login node). There is no
  `--executor local`.
- If `ghx4` batch queueing makes JIT steps slow, override the substrate to the
  interactive partition: `--partition ghx4-interactive`.
- The brain serve job and the agent's `run_gpu` steps consume GPUs independently
  (4 for the brain, K per experiment step) — size your allocations accordingly.
```
