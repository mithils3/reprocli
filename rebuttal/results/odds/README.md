# Acceptance odds for 22528 (3, 3, 2) from past ICLR decisions, 2026-11-19

Data: Paper Copilot paperlists (final per-reviewer ratings, confidence, sub-scores, area, decision) for ICLR 2024, 2025 and 2026 main track; the Jasonpicky/openreview_raw dump (~/.cache/openreview_raw) for 2024 and 2025 discussion threads and 2024 meta-reviews; the ICLR 2027 Rebuttal Radar (dipta007.github.io/iclr-2027-rebuttal-radar, data/papers.json, snapshot 2026-11-19 18:22Z) for current 2027 ratings of all 34,456 active papers. Raw files sit in the session scratchpad (`meta/raw/`); `build.py` joins them into `papers.jsonl` (28,008 decided papers). Each `anN.py` takes that folder as its argument and its output is in `anN.out.txt`.

## Which year compares

ICLR 2026 used weak reject 4 and weak accept 6 on a 0-10 scale, so a 2026 6, 6, 4 is a 2027 3, 3, 2. In 2024 and 2025 (scale 1, 3, 5, 6, 8, 10) a 6, 6, 5 ranked near the middle of the field (papers above it were 48% of decided papers in 2025) and was accepted 28-33% of the time, so those years serve only for within-band factors.

ICLR 2026 accepted 5,351 of 19,814 submissions (27.0%). ICLR 2027 has 42,789 submissions (radar site.json).

## Results

| Check | Result |
| :- | :- |
| 2026 papers ending exactly 6, 6, 4 (= 3, 3, 2) | 209 / 282 accepted, 74% [69, 79] |
| 2026 other 2.67 patterns | 4, 2, 2: 46 / 85 (54%); 4, 3, 1: 38 / 54 (70%) |
| 2027 papers at 2.67 now | 5,617, of which 5,049 (90%) are 3, 3, 2 |
| 2027 papers above 2.67 now | 6,270 ahead of the band; band spans top 18.2% to 34.5% of active |
| Model A: 2026 acceptance per mean level, shifted to hit a 2027 acceptance rate | 32% of submissions: 69%; 30%: 65%; 27% (as 2026): 58%; 25%: 52%; 20%: 38% |
| Model A unshifted | 2026 behaviour applied to 2027 scores gives 13,794 accepts = 32.2% of submissions |
| Model B: 2026 acceptance at the same rank | 64% if every active paper reaches a decision, 59% if 15% more withdraw from below |
| 2026 band factors (all-but-one weak accept, n = 887) | 3 reviews 74% against 4 reviews 84%; low reviewer's confidence, area (D&B 87% of 75) and sub-scores show no clear gap |
| 2024+25 engagement, 3-review 6, 6, 5 (n = 238) | low reviewer silent and a positive reviewer posted 37% [26, 48] against 30% overall; nobody positive posted 21% |
| 2024 meta-reviews for this band (146 accepted, 184 rejected) | "insufficient experiments" 4% of accepts against 16% of rejects; "concerns remain" 10% against 17%; "lukewarm" 5% against 12%; novelty complaints and benchmark mentions equal in both |

Estimate stated to Mithil: about 60% (50% to 70%), down from 70%, which had rested on 2024/25 rank histories.

## Our own factors (an6.py, an7.py)

Our values: 3 reviews; positives' confidence 3 and 2; low reviewer (YGTR) confidence 3, review 315 words, informativeness 1, silent in the discussion; rqBN posted ("I maintain my score to support this paper"), T29u silent; area datasets and benchmarks; public author replies of about 3,950 words in 7 comments with a general response, markdown tables, dense numbers and new experiments. Two logistic models over the band (2024+25 with rebuttal and engagement features, n = 850; 2026 with review features, n = 887), each giving our log-odds offset against the average 3-review paper in the band: -0.05 [-0.86, +0.59] and -0.06 [-1.20, +1.11]. Pluses: a positive reviewer posted while the low reviewer stayed silent (+0.60), tables (+0.39). Minuses: positives' confidence at or below 3 (-0.21, -0.17); area coefficient conflicts across years (-0.34 in 2024+25, +0.37 in 2026). Net about zero, so the paper-specific estimate stays at the 3,3,2 base: about 60% (50% to 70%).
