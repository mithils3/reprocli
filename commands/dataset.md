# Dataset pipeline

One command builds the paper-bundle dataset end to end: arXiv ids and titles
come pre-matched from the
[`ai-conferences/NeurIPS2025`](https://huggingface.co/datasets/ai-conferences/NeurIPS2025)
dataset (papers without an arxiv id are dropped — no fuzzy title matching),
arXiv e-print sources and OpenReview supplements are downloaded, and a
one-row-per-paper Parquet dataset is written.

## Build the full dataset

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset --data-dir data --workers 8
```

## Smoke test (5 papers into a scratch dir)

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset \
  --limit 5 --data-dir data/smoke --workers 2 --allow-failures
```

## Run a subset of stages

Stages run in order `index,sources,supplements,bundle[,upload]` and are
resume-friendly (already-downloaded papers are skipped). Use `--stages` to run a
subset, `--force` to refetch/replace, and `--upload` to push the bundle to
`Mithilss/neurips-2025-paper-bundles`:

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset --stages bundle --force
PYTHONPATH=src python3 -m reprocli_data.build_dataset --stages upload
```

## Rebuild the Parquet bundle and publish

Once sources and supplements are downloaded, rebuild the Parquet bundle and push
it to the Hub in one step (replaces any existing bundle output):

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset --stages bundle,upload --force
```

## Notes

Supplements are matched to OpenReview notes by the forum id from `paper_url`
(never by title). Optional env vars: `OPENREVIEW_USERNAME`/`OPENREVIEW_PASSWORD`
for OpenReview, `HF_TOKEN` for upload.

Bundle columns: `arxiv_id`, `title`, `openreview_id`, `arxiv_id_source`,
`paper_source_url`, `paper_status`, `paper_tex_files`, `paper_tex_text`,
`supplement_source_url`, `supplement_status`, `supplement_files`. The builder
batches paper rows before writing Parquet; lower `--batch-size-mb` or
`--batch-rows` if a shared filesystem run is memory constrained.

The intermediate file-level dataset (`Mithilss/neurips-2025-arxiv-latex-sources`)
is no longer produced; bundles are built directly from the extracted source
directories under `<data-dir>/arxiv_sources/`.
