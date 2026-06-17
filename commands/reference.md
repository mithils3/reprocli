# Materialize paper + supplement reference dirs

Stream the paper-bundle dataset and write each row to a per-paper reference
directory the reproduction agent can read:

```
<out-dir>/<arxiv_id>/
  latex/<relative_path>        # paper .tex sources (UTF-8 text)
  supplement/<relative_path>   # every supplement file, raw content bytes
  info.json                    # ids, urls, statuses, file counts
```

Supplement files are written from their raw `content` bytes (so `.py` and binary
files survive — the bundle only fills the `text` field for a narrow extension
set). The stream is lazy, so no shard is fully loaded into memory.

## One paper

The stream stops as soon as the requested id is found.

```bash
PYTHONPATH=src python3 -m reprocli_repro.reference --out-dir refs --arxiv-id 2110.03155
```

## A list of ids

```bash
PYTHONPATH=src python3 -m reprocli_repro.reference --out-dir refs --ids-file ids.txt
```

## First N papers

```bash
PYTHONPATH=src python3 -m reprocli_repro.reference --out-dir refs --limit 50
```

## Flags

- `--out-dir` (required) — destination root.
- `--dataset` — paper-bundle dataset (default `Mithilss/neurips-2025-paper-bundles`).
- `--arxiv-id` — materialize only this id (repeatable).
- `--ids-file` — file of arXiv ids, one per line.
- `--limit` — stop after writing this many papers (ignored with `--arxiv-id`/`--ids-file`).
- `--overwrite` — rewrite an existing paper dir (default: skip).

```bash
PYTHONPATH=src python3 -m reprocli_repro.reference --out-dir /tmp/refs --limit 50
```