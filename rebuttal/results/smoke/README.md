# Smoke runs (development papers, not eval)

Purpose: push one real paper through each new arm before any eval paper is spent, and measure per-run cost and GPU use.

| Arm | Paper | Budget (H100-h) | Prediction (written before launch, 2026-11-06) |
| :- | :- | :- | :- |
| gpt-6.1-terra, thin harness, flex | 2511.07099, 2510.21323 (dev, Run, 0-8) | 8 each | 85%: both finish with a schema-valid report.json; cost $1 to $6 per run; GPU use under 3 H100-hours per run |
| muse-wonder-1.0, thin harness | 2511.07099 (dev, Run, 0-8) | 8 | 85%: finishes with report.json; cost $10 to $35 |

Pass rule: report.json exists and validates, the ledger line is priced from real token counts, no 4xx from the API in the run log, and run_gpu charged betw-dtai-gh. A failure stops the arm until fixed.
