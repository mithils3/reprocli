# reprocli

Tooling for the NeurIPS paper-bundle reproduction benchmark: the S6 reproduction
agent that runs a paper's experiment on the cluster (`reprocli_repro`), the S7
auditor that grades the run against the lockfile (`run_arxiv_prompt_vllm.py --mode
audit`), a shared vLLM serving layer both attach to by URL (`reprocli_serve`), and
the dataset pipeline that builds the paper bundles.

## Commands

Copy-paste command references live in [`commands/`](commands/), one file per task:

- [commands/dataset.md](commands/dataset.md) — build, stage, and publish the
  paper-bundle dataset.

## CC and serving

The repo splits into two decoupled halves that talk only over a published URL:

- **CC (the agent half)** — `reprocli_vllm` (auditor core), `reprocli_repro`
  (reproduction agent), and `run_arxiv_prompt_vllm.py`. These are
  **URL-only, provider-agnostic brains**: like Codex / Claude Code / opencode they
  host no model, they only make chat-completions requests to a base URL. There is
  no embedded in-process server.
- **Serving** — `src/reprocli_serve/` boots a vLLM server on a GPU node (e.g.
  4×GH200, TP=4), binds `0.0.0.0`, and publishes its URL for any other
  Delta/DeltaAI node to attach to (`scripts/serve/serve_gh200.sbatch`,
  `scripts/serve/serve_multinode.sbatch`). It owns the per-model serve profiles
  (`reprocli_serve/profiles.py`) — the single source of vLLM launch flags.

Point the runner at a server with `--vllm-server-url`, `$REPROCLI_SERVER_URL`, or
`$REPROCLI_ENDPOINT_FILE` — so swapping the model is a URL change. With no endpoint
configured the reproduction agent renders prompts as a dry run and the auditor
runner exits with an error; neither self-hosts a model.

When the base URL is OpenRouter, set `$REPROCLI_OPENROUTER_PROVIDER` to a provider
slug (e.g. `deepseek`) to pin every request to that upstream with fallbacks off, so
a cache-read-dominated run is billed at that provider's own cache pricing instead of
being silently routed to a pricier host. A comma-separated list sets a preference
order (still no fallback beyond the list). Unset → OpenRouter's default routing, and
a no-op against a local vLLM (which ignores the field).
