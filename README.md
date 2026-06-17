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

## Documentation

Full project documentation lives in [`docs/`](docs/) and is published with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/):
**<https://mithils3.github.io/reprocli/>** (live once GitHub Pages is enabled).
It covers the architecture, the three agent roles, the dataset pipeline, the
lockfile/selection, the tool & schema reference, SLURM recipes, and a complete
CLI flag reference. The reproduction-agent (S6) implementation plan is in
[docs/reproduction-agent-plan.md](docs/reproduction-agent-plan.md).
