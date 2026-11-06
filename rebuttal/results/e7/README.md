# E7: blind re-derivation of the 100 eval targets

**What.** gpt-6.1-sol (OpenAI flex, reasoning high) reads each paper's extracted text and returns metric, configuration and value for its claim sentence, with every number masked as [X]. The frozen tuple is never sent.

**Inputs.** `eval_100.jsonl` (HF `Mithilss/reclaim`). The builder's LaTeX fields are not in this file, so paper text is `pdftotext -layout` of arxiv.org/pdf/<id>, cached on DeltaAI under `/work/nvme/bfvr/msalunkhe/rebuttal/e7/papers/`.

**Command (DeltaAI, tmux rb-e7).** `rebuttal/e7_rederive.py` via `run.sh fetch|run|compare`, which loads the key by pointer.

**Headline (denominator 100; Wilson 95%).**
- Agree (metric and configuration match, value within 5%): 0/100, [0.0%, 3.7%].
- Value within 5% with any text: 18/100, [11.7%, 26.7%]. Of 64 numeric re-derived values, 46 fall outside 5%; 36 have no numeric value.
- Cost: $2.908 (run 1 $2.475; run 2 $0.433, nearly all cached input).

**Worked arithmetic (2504.20571).** Frozen 73.6%, re-derived 72.8: |72.8 − 73.6| / 73.6 = 0.8 / 73.6 = 1.09%, inside 5%.

**Caveats.** Text match is token overlap (metric at least 0.8, configuration at least 0.6); configuration is the weak link. The masked sentence does not always pin the frozen row (2505.11483 says "50% less RAM"; the frozen target is 8.56 kB). Four outputs (2505.19713, 2511.00090, 2505.10978, 2508.21046) nested fields under "results".
