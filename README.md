# reprocli

Tooling for the NeurIPS paper-bundle reproduction benchmark: a classifier/auditor
agent core that runs over paper bundles on vLLM (MiniMax M2 or Kimi K2.6), the
dataset pipeline that builds the bundles, and the reproduction-agent tooling.

## Commands

Copy-paste command references live in [`commands/`](commands/), one file per task:

- [commands/classification.md](commands/classification.md) — run the
  classifier/auditor over paper bundles on vLLM (MiniMax M2, Kimi K2.6, or
  attaching to an already-running server), plus the tool surface and credentials.
- [commands/dataset.md](commands/dataset.md) — build, stage, and publish the
  paper-bundle dataset.
- [commands/reference.md](commands/reference.md) — materialize a paper +
  supplement into local `latex/` and `supplement/` directories.
- [commands/docs.md](commands/docs.md) — build, serve, and publish the docs site.

## Serving the model

The agents here are **provider-agnostic** — they only make chat-completions
requests to a base URL, so the model is a swappable service, not part of the
runner. Standing that service up lives in a sibling repo, **`../reprocli-serve`**,
which boots a vLLM server on a GPU node (e.g. 4×GH200, TP=4), binds `0.0.0.0`, and
publishes its URL for any other Delta/DeltaAI node to attach to. Point the runner
at it with `--vllm-server-url`, `$REPROCLI_SERVER_URL`, or `$REPROCLI_ENDPOINT_FILE`
(falling back to the embedded local server when none is set). See
[docs/slurm/serve.md](docs/slurm/serve.md) and
`scripts/paper_classification_serve.sbatch`.

## Documentation

Full project documentation lives in [`docs/`](docs/) and is published with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/):
**<https://mithils3.github.io/reprocli/>** (live once GitHub Pages is enabled).
It covers the architecture, the three agent roles, the dataset pipeline, the
lockfile/selection, the tool & schema reference, SLURM recipes, and a complete
CLI flag reference. The reproduction-agent (S6) implementation plan is in
[docs/reproduction-agent-plan.md](docs/reproduction-agent-plan.md).
