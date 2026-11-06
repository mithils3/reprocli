# Frontier arms: Stage-7 grades

What was computed: the pinned auditor (claude-sonnet-5, frozen rubric, eval split) graded each finished frontier-arm run that had a report.json and no VOID file. One line per run in `grades.jsonl`, with arm, model, paper, budget, run_id, score (0 to 10), verdict, reproduced flag, auditor model, and Anthropic cost in USD.

Source runs: `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/<paper>/<budget>h/<run_id>` (read only). Smoke runs and the dev papers 2511.07099 and 2510.21323 were excluded. No miniswe or thin-harness run was gradeable at grading time.

Command: `bash scripts/rebuttal/grade_arms.sh` on DeltaAI (wraps `python scripts/rebuttal/grade_arms.py`, which calls `python -m reprocli_claude --paper-ids <id> --runs-dir <staged dir> --split eval --model claude-sonnet-5`). Re-running grades only runs not yet in the file.

Headline: 15 runs graded, total cost $10.81 (15 ledger rows, item `frontier-grade`). Score counts: 8 (1 run), 6 (2), 4 (1), 2 (5), 1 (6). Three runs scored 6 or more (out of 15). Two first attempts (5554ea, 235777) returned no integer score because the auditor output did not parse; the retry succeeded for both.
