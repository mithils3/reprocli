# E7: are the frozen targets the paper's reported results?

Model: gpt-6.1-sol, OpenAI Responses API, flex, reasoning high, strict json_schema. Paper text: `pdftotext -layout` of the arXiv PDF, first 800k characters. Code: `rebuttal/e7_rederive.py`, run on DeltaAI as `run.sh fetch|run|run3|compare`. Ledger: item E7.

**v3 (answer to rqBN: is the target the paper's reported result?).** Step 3 gets the claim sentence and the frozen metric, dataset/split, configuration and value, and asks four yes/no questions with a quote each: (a) the paper reports this value within rounding, (b) for this metric, (c) on this dataset/split, (d) for this method or variant. Released-code details (checkpoint names, steps, seeds, hardware) are declared out of scope.
- All four yes: 55/100 [45.2%, 64.4%].
- (a) 92/100 [85.0%, 95.9%]; (b) 95/100 [88.8%, 97.9%]; (c) 76/100 [66.8%, 83.3%]; (d) 69/100 [59.4%, 77.2%].
- By tier (all four yes): see `summary.json` `step3.by_tier`; Easy, Medium and Hard counts for (a) to (d) are 32/29/31, 32/30/33, 24/25/27 and 22/18/29 (of 34, 33, 33).
- Failures (any of a to d not yes): 45, with quotes and reasons in `v3_failures.csv`. The most common failure is (d) alone (18).
- Frozen value check for 2506.18890: the lockfile row has value 27.443 (PSNR, Consistent4D, 12 input views). Step 3 finds 27.443 in Table 1 for 4D-LRM-Base but with 24 input views, so (d) fails. The "4" that appeared in earlier outputs came from the model reading "4D", not from the frozen target.

**v2 (step 1 lookup and step 2 tuple check).** Step 1 value agree 45/100 [35.6%, 54.8%], not found 52/100. Step 2 metric_ok 78/100, config_ok 24/100, value_supported 36/100. The step-2 config failures are mostly the implementation-level details v3 excludes. Files: `comparison.csv`, `disagreements.csv`, `rederived.jsonl` (v2 and v3 columns merged in `comparison.csv`). Arithmetic example: frozen 73.6% against 74.0% found, |74.0 − 73.6| / 73.6 = 0.54%, inside 5%.

**Cost.** E7 ledger total $12.70 (v1 $2.91, v2 $6.36, v3 $3.43), cap $20.

v1 (masked claim, superseded) is in `v1_masked/`.
