# Classifier Redesign: Root-Cause Audit & Plan

Date: 2026-06-10
Status: **implemented** (same day) — prompt v5, run-health/h100-audit/loop-guard
modules, rerun pass (`python -m reprocli_vllm.rerun`), verify-app step 5, and
tests all landed; `rerun select` over the v4 extracted file picks exactly the
152 legacy low-confidence rows (70 unavailable + 80 partial + 2 malformed).
Scope: ASSESSMENT.md findings #3 (30% of rows `unavailable`/`partial`) and #4
(unaudited H100 estimates). Based on a full pass over the 500-row v4 trace
(`outputs/v4/neurips_2025_minimax_m2_trial_trace.jsonl`), the extracted JSONL,
`prompt.txt`, and `src/reprocli_vllm/`.

## Part 1 — Why the failures happen (trace evidence)

### Headline: `web_verification` is not measuring what we think it measures

The prompt defines `unavailable` as "only if tools were unavailable". The traces
say the model uses it to mean "the *artifacts* were unavailable on the web":

| bucket | rows | code_available=false | real tool-error rate | median tool rounds |
|---|---|---|---|---|
| available | 348 | 9% | 3.2% of calls | 6 |
| partial | 80 | 61% | 4.6% | 8 |
| unavailable | 70 | **74%** | 4.9% | 7 |

Tool failure rates are virtually identical across buckets; `unavailable` rows
ran a median of 7 successful tool rounds. The label tracks artifact absence,
not tool health. Reading the final JSONs confirms it: `unavailable` rows have
evidence strings like "No public GitHub repository found … after comprehensive
searches using: title, acronym variants, arXiv ID …" — the tools worked fine.

### Root causes, ranked

**RC1 — Semantic collision in the label (dominant).** A field named
`web_verification` with values `available`/`partial`/`unavailable` reads as
artifact availability. One sentence in a 470-line prompt redefines it as tool
health. The model follows the surface reading. No code validates the claim.

**RC2 — The forced-final message primes "unavailable".** Every row's last user
message before the final JSON is `FINAL_NO_TOOLS_MESSAGE`
(`config.py:64`), which opens with *"Tool use is complete and **no tools are
available in this request**."* Combined with the rule "set `unavailable` only
if tools were unavailable", the literal reading at answer time is `unavailable`.

**RC3 — Silent front-truncation destroys the instructions on big rows.**
`build_chat_completion_request` passes `truncate_prompt_tokens=128000`
(`vllm_io.py:35`), so vLLM silently keeps only the *last* 128K tokens. Meanwhile
`fetch_url` defaults to `TOOL_MAX_CHARS = 2_000_000` chars per result and MCP
results are returned **without any local cap** (the `github_file_contents` tool
description even advertises this). Observed conversations reach **8.1M chars
(~2M tokens)** — when that happens the system message, the entire prompt
(including the `web_verification` definition), and the paper text are dropped,
and the model answers from tool dumps alone.

- Conversations >700K chars: 21% of `unavailable` rows vs 3.4% of `available`.
- Single tool results >400K chars: 16% of `unavailable` vs 3% of `available`.
- Worst case `2503.09617`: a recursive `github_repository_tree` dump; the final
  answer literally says *"No extraction request provided in this message"* —
  and that row was still scored and shipped into the dataset as **Medium**.

**RC4 — No "nothing to verify" path.** 26% of `unavailable` rows are
theory/position papers (vs 4–5% in other buckets). There are no artifacts to
check, the 3-value enum has no correct answer, and the model picks
`unavailable`. Many of these land in Artifact-Blocked, polluting that tier.

**RC5 — Round budget + harsh repeat policy feed `partial`.** 29% of `partial`
rows hit the 12-round limit (vs 4.3% of `available`). `--max-repeated-tool-calls`
defaults to 1: the *second* occurrence of any identical call — including a
retry of a timed-out or rate-limited call — force-finalizes the entire row
(13 rows cut this way). The forced JSON-only pass then has to label an
admittedly incomplete check.

**RC6 — Run health is self-reported, but the harness already knows it.** Which
tools were called, which returned `ok:false`, which artifact categories were
touched, whether the loop exited naturally or was cut — all deterministic
facts available in code, yet we ask the model to summarize them into one enum
and never cross-check.

### Smaller trace findings (cheap fixes)

- **30 calls to hallucinated tool names** (`github_search`, `bash`,
  `github_code_search`, `huggingface_mcp.search_datasets`, …). The error reply
  `Unknown tool: X` doesn't list the valid tools, so models burn more rounds.
- **19× `Unknown supplement file path: README.md`** — `prompt.txt` itself says
  *"Call paper_bundle_file_contents with a manifest path such as README.md"*,
  inviting blind calls; the error doesn't echo the actual manifest.
- **34× "Could not parse GitHub repo" / 22× HF equivalent** — parse errors
  don't show the expected format or the offending input.
- **2 malformed rows** (`2503.05244` content `None`; `2505.19702` non-JSON
  fragment) flow into the extracted JSONL as rows without `signals` — nothing
  downstream flags them.

### Finding #4 evidence (H100 estimates)

- 146/500 (29%) basis strings contain `compute-unspecified`; 64/500 (13%) have
  no recognizable arithmetic at all. Most of both groups sit in the 0–8 band —
  the band that dominates selection.
- `h100_hours_estimate` is a bare number and the basis is free text, so code
  *cannot* recompute or sanity-check the arithmetic even when it is present.
- The verify app audits only the four binary signals; the band is never
  confirmed by a human.

## Part 2 — Redesign plan

Design principle: **the model reports evidence; the code computes status.**
Same principle that moved score/tier out of the model — applied to
verification health and the H100 band.

### A. Prompt changes (`prompt.txt` → v5)

1. **Kill the global `web_verification` enum.** Replace it with a per-signal
   verification state inside each signal object:

   ```json
   "code_available": {
     "value": false,
     "verification": "tool_verified | tool_searched_not_found | tool_failed | paper_text_only | not_applicable",
     "evidence": "..."
   }
   ```

   - `tool_verified` — an ok tool result directly supports `value`.
   - `tool_searched_not_found` — meaningful searches ran and found nothing
     (this is *successful* verification of absence, today's biggest mislabel).
   - `tool_failed` — the needed tool calls errored; value is a best guess.
   - `paper_text_only` — no tool evidence; value comes from the paper text.
   - `not_applicable` — the category does not exist for this paper.

   The row-level status is then **computed in code** (see B4), not asked of
   the model. The word "available" never again describes tool health.

2. **Add a `paper_kind` field**: `empirical | theoretical | position | survey`.
   Non-empirical papers set signals to `not_applicable` and the extractor maps
   them to a new `Out-of-Scope-Non-Empirical` tier instead of letting them
   contaminate Artifact-Blocked/Hard. (~18 of 70 `unavailable` rows.)

3. **Structured H100 estimate** replacing the bare number + free text:

   ```json
   "h100_estimate": {
     "hours": 12,
     "basis_kind": "paper_reported | derived_from_config | comparable_experiment | compute_unspecified",
     "gpu_count": 8, "gpu_type": "A100 80GB", "wallclock_hours": 5,
     "h100_equivalent_multiplier": 0.32,
     "basis": "free-text reasoning"
   }
   ```

   Numeric fields are nullable; when present the extractor recomputes
   `gpu_count × wallclock_hours × multiplier` and flags >20% disagreement with
   `hours`. `basis_kind=compute_unspecified` or missing arithmetic auto-flags
   `needs_human_review`. Compute band is assigned in code.

4. **Rewrite `FINAL_NO_TOOLS_MESSAGE`** (`config.py:64`): remove "no tools are
   available in this request"; say "The tool phase is finished. Produce the
   final JSON from the evidence already gathered. Each signal's `verification`
   field describes what happened during the tool phase, not this message."

5. **Fix the supplement example**: instruct to call
   `paper_bundle_file_contents` only with paths listed in the
   `OPENREVIEW_SUPPLEMENT` manifest; drop the literal `README.md` example.

6. Shorten/sharpen the verification section around the new per-signal states —
   the current 3-value rule text disappears entirely.

### B. Harness/code changes (`src/reprocli_vllm/`)

1. **Context budget enforcement — the highest-impact fix.**
   - Cap every tool result at source: `fetch_url` default down from 2M to
     ~24K chars; wrap all MCP results (repo, file contents, trees, search)
     with a shared truncation helper (~30–50K chars) that appends
     `"[truncated — request a specific path or smaller range]"`.
   - Track cumulative conversation size in `run_tool_loop`; when the estimated
     token count approaches `max_input_tokens`, end the tool phase gracefully
     with an explicit "context budget reached" user message instead of letting
     vLLM silently drop the head. Record `exit_reason=context_budget`.
   - Treat any request where vLLM would front-truncate as a defect: log it and
     mark the row `degraded`.

2. **Retry/repeat policy**: retries of calls whose previous result was
   `ok:false` don't count toward the repeat limit; raise
   `--max-repeated-tool-calls` default to 2. Auto-retry transient network
   failures once in the harness.

3. **Actionable tool errors**: `Unknown tool: X — available tools: …`;
   repo-parse errors echo the input and expected `owner/name` form; unknown
   supplement paths list the manifest's actual paths.

4. **Deterministic run-health in the extractor.** Per row, record telemetry
   from the loop (tool calls with ok/error, exit reason, conversation size,
   truncation flag) and compute:

   ```
   verification_status =
     verified    — every applicable signal is tool_verified / tool_searched_not_found,
                   exit_reason = natural, no degradation
     incomplete  — exit via round limit / repeated-call cutoff / context budget,
                   or any signal tool_failed / paper_text_only
     degraded    — front-truncation, malformed JSON, missing signals,
                   or model-claimed links absent from tool results
   ```

   Keep a derived `web_verification` field only as a compatibility alias for
   the verify app export.

5. **Validation gate**: `degraded` rows get `score=None, tier=None` — they are
   never silently scored (the 2503.09617 failure mode). Malformed rows join
   the same bucket.

6. **Rerun pass** (the pass ASSESSMENT.md already calls for): a small
   `reprocli_vllm/rerun.py` + CLI that reads an extracted JSONL, selects
   `incomplete`/`degraded`/malformed rows (and rows whose recomputed H100
   arithmetic mismatches), requeues exactly those arXiv IDs, and merges
   results into a new extracted file (newest row wins, history preserved).

### C. Verify app

1. **Fifth audit step — H100 band confirmation**: show the structured
   arithmetic and the computed band; reviewer confirms the *band*, not the
   number. Rows flagged `needs_human_review` (compute_unspecified / missing or
   mismatched arithmetic) surface first.
2. Display per-signal `verification` and row `verification_status` so
   reviewers know which verdicts are tool-backed vs paper-text guesses.

### D. Tests

- Extractor: per-signal verification → row status derivation; degraded gate;
  H100 recompute + mismatch flag; band assignment.
- Tool loop: context-budget stop; retry-not-counted-as-repeat; truncation
  helper.
- Rerun: row selection + merge semantics.
- Fixtures cut from real v4 traces (the Factorio row is the regression test).

### Sequencing & dependency

1. B1 + A4 (context caps, budget stop, final-message fix) — stops garbage at
   the source.
2. A1–A3 + B4–B5 (schema v5 + deterministic status + gate) — one coordinated
   change since prompt and extractor move together.
3. B6 rerun pass; rerun v4's `incomplete`/`degraded` rows as the smoke test.
4. C verify-app step 5 + status display.

All of this lands **before** the full 3,414-paper corpus run (ASSESSMENT.md
"Next #3") — running the full corpus on the current design would reproduce the
same ~30% soft-data rate and unauditable estimates at 7× the cost.

### Expected impact

Of today's 150 `unavailable`/`partial` rows, roughly 110 are mislabels
(successful absence-verification or theory papers) that become `verified` or
`Out-of-Scope-Non-Empirical` under the new scheme; the genuinely incomplete
remainder (~38 round-limit/cutoff rows + ~5% transient tool failures) is
exactly what the rerun pass requeues. Every H100 band becomes either
arithmetic-checked in code or explicitly human-flagged.
