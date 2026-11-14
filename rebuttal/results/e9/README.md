# E9: checkpoint and result-file downloads in agent runs (reviewer YGTR Q2)

Script: `rebuttal/e9_checkpoint_scan.py`. Scan on the Delta CPU login node:
`/usr/bin/python3.9 e9_checkpoint_scan.py --index index.json --out DIR --procs 12 --timeout 240`, then
`--from-hits DIR --review class_review.csv` for classes.

Inputs: 372 runs in `index.json`. Each run maps to one run dir by arxiv id, `spent_h100` and `tool_rounds_used` in `stats.json` (372 of 372 unique). Sources: `evidence/commands.log`, `$` lines in `agent.full.log`, fetch_url URLs, code the agent wrote, and repo code only when an executed command runs it.

Classes (Retrain and Reimplement only): provisional rule for every hit, then manual rows in `class_review.csv` for the 16 reproduced runs with a hit.

Headline counts (scanned / in index; hits = a primary-source match):
- Run: 127/129 scanned, 117 with a hit. Reproduced: 28 of 31 with a hit.
- Retrain: 118/118 scanned, 62 with a hit. Reproduced: 13 of 29.
- Reimplement: 123/125 scanned, 75 with a hit. Reproduced: 3 of 13.
- Reproduced Retrain and Reimplement runs with class c: 2. With a class b hit and no class c hit: 10 (5 with b hits only, 5 with b and d hits). With class d hits only: 4. Counted per run from `class_review.csv` (b = base model, config or tokenizer; d = not a download; c = ready checkpoint of the claimed model). Corrected on 2026-11-14: this line had the 10 and the 4 the other way round.

Not scanned (scan timeout, see `mapping.csv`): dsv4-run-2505.19713, minimax-run-2505.10475, dsv4-reimplement-2511.01463, minimax-reimplement-2511.01463.

Limits: downloads made inside an imported library (no executed .py name) are not traced.
