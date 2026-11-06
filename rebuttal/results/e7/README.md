# E7 v2: checking the frozen targets against their papers

**Question.** Were the frozen targets right? Model: gpt-6.1-sol, OpenAI Responses API, flex, reasoning high, strict json_schema. Paper text: `pdftotext -layout` of the arXiv PDF, first 800k characters.

**Step 1 (value-blind lookup).** The model gets the paper plus the frozen metric, dataset/split and configuration, not the frozen value. It returns the number it finds for that cell. Agree when found and within 5% relative.

**Step 2 (tuple check).** The model gets the unmasked claim sentence and the full frozen tuple. It judges metric_ok, config_ok and value_supported, with a quote.

**Headline (n = 100; Wilson 95%).**
- Step 1 value agree: 45/100 [35.6%, 54.8%]; not found: 52/100.
- Step 2: metric_ok 78/100 [68.9%, 85.0%]; config_ok 24/100 [16.7%, 33.2%]; value_supported 36/100 [27.3%, 45.8%].
- All four checks pass: 12/100. Disagreements (either step): 88/100, in `disagreements.csv`.
- By tier, step 1 agree / not found: Easy 12/21, Medium 10/22, Hard 23/9 (of 34, 33, 33).
- Cost: v2 $6.36; E7 ledger total $9.27 including v1.

**Worked arithmetic (2504.20571).** Frozen 73.6%, step 1 finds 74.0%, both printed as percent. |74.0 − 73.6| / 73.6 = 0.4 / 73.6 = 0.54%, inside 5%.

**Caveats.** config_ok fails mostly because the claim sentence seldom names the configuration; Mithil should judge those. One step-1 output was rejected twice for a validator bug (units may be empty); those 20 rows were re-run (commit 9cf1827). v1 is in `v1_masked/`.

Code: `rebuttal/e7_rederive.py` (commit 9cf1827); run as `run.sh fetch|run|compare` on DeltaAI.
