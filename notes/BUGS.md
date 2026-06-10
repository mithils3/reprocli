## Fixed bugs 

## Where it enters the pipeline

The prompt header for `2112.02604` literally reads `arxiv_id: 2112.02604` / correct e-print URL / `title: Rethinking Entropy in Test-Time Adaptation...` — a mismatched pair baked in before the run. Tracing back through the chain (`papers.py` → parquet build → download manifest → input CSV), title and arXiv ID travel together from one place: **`fetch_neurips_2025_arxiv.py`**, which maps NeurIPS 2025 proceedings titles to arXiv IDs via OpenAlex fuzzy title search.

The defect is in `openalex_lookup.py:choose_match` (line 97-99): when the best similarity score is **below** `min_score` (0.88), it doesn't drop the row — it returns the best wrong guess with status `batch_low_confidence`. And nothing downstream filters on `match_status` or score (`arxiv_source_inputs.load_jobs` just reads the URL column). So low-confidence garbage matches flowed straight into the download list.

## Measured impact on the original run

Scanning all 500 traces against the authoritative arXiv metadata:

- **117 of 500 prompts (23%) had a title that doesn't belong to their arXiv ID.**
- Of those, **9 are harmless** — same paper, just retitled between arXiv and the NeurIPS camera-ready.
- **108 are genuinely different papers** — e.g. NeurIPS paper "ASGO: Adaptive Structured Gradient Optimization" got matched to a Wolof banking speech dataset paper. For these, the intended NeurIPS paper was *never analyzed*; the model received, downloaded, and extracted a completely different paper.

## The surprisingly good news

The extractions are *internally* consistent. The model works from the downloaded LaTeX, not the title — across all 117 affected traces, only 3 began their web searches from the wrong title, and all 3 self-corrected (their final claims and evidence match the paper they actually read, e.g. `2410.02890` ends up correctly finding the DAWA watermarking repo). So every record in `papers.json` correctly describes its arXiv ID — which is why fixing the titles was the right repair for the verify app, and the signals your team is reviewing are not contaminated.

## What's actually lost

The damage is corpus-level, not record-level: **~108 NeurIPS 2025 papers you intended to process are missing from the dataset**, silently replaced by other papers. If the product claim is "artifact verification of NeurIPS 2025 papers," about 22% of the intended corpus isn't there.

If you want, I can: (1) fix `choose_match` to drop sub-threshold matches, (2) emit the exact list of 108 dropped NeurIPS titles, and (3) re-match them (OpenAlex with author cross-check, or the arXiv API title search) so you can re-run extraction on just those.