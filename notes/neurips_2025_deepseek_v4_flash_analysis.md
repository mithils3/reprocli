# DeepSeek V4 Flash Output Analysis

Analyzed files:

- `outputs/neurips_2025_deepseek_v4_flash.jsonl`
- `outputs/neurips_2025_deepseek_v4_flash_trace.jsonl`
- `outputs/neurips_2025_deepseek_v4_flash_extracted.jsonl`

## Summary

The run is doing decently on completion and extraction, but it is not yet trustworthy without validators and retries.

All 8 rows completed with HTTP 200 and all 8 produced extractable JSON. Tool use is active: 171 total tool calls, 144 successful, about 84% success. The model used 6-12 tool rounds per paper, with an average of 9.1. Three rows hit the 12-round cap:

- `2506.17220`
- `2509.16170`
- `2502.13119`

The pipeline is promising, but it needs a validation-and-retry layer before these outputs should count as benchmark-grade labels.

## Overall Metrics

- Rows: 8
- Completed responses: 8/8
- Extractable JSON rows: 8/8
- Total tool calls: 171
- Successful tool calls: 144
- Tool success rate: 84.2%
- Average tool rounds: 9.12
- Median tool rounds: 9
- Rows hitting tool-round limit: 3/8
- Average prompt tokens: 117,649
- Prompt token range: 77,716 to 128,000
- Average completion tokens: 2,705
- Total tokens across final rows: 962,832

## Row-Level Status

| custom_id | Score | Tier | Web verification | H100 estimate | Tool rounds | Hit limit | Status |
| --- | ---: | --- | --- | ---: | ---: | --- | --- |
| `2502.08021` | 1 | Medium | available | 15 | 9 | no | usable with spot-checking |
| `2507.13328` | 0 | Easy | available | 2 | 7 | no | usable with spot-checking |
| `2505.11475` | 0 | Easy | available | 48 | 9 | no | usable with spot-checking |
| `2509.15178` | 0 | Easy | available | 10 | 6 | no | usable with spot-checking |
| `2506.17220` | 1 | Artifact-Blocked | unavailable | 0.1 | 12 | yes | failed, rerun needed |
| `2502.16076` | 1 | Medium | available | 0.5 | 6 | no | usable with spot-checking |
| `2509.16170` | 1 | Medium | available | 50 | 12 | yes | needs audit |
| `2502.13119` | 3 | Hard | available | 3 | 12 | yes | needs audit |

My read: 5/8 rows look usable with normal spot-checking, 2/8 need audit, and 1/8 is a clear failure.

## Clear Failure

`2506.17220` failed badly.

After finding DiffTrack evidence, the model started calling nonexistent tools:

- `todowrite`
- `read`
- `file_read`
- `bash`
- `question`
- `search`
- `get_repo_info`
- `list_directory`

Those unknown-tool calls consumed a large fraction of the tool budget. The final answer then emitted a nonsensical central claim:

> The repository requires a clear and comprehensive README file to explain the project, installation, usage, and provide necessary documentation.

Other failure symptoms in this row:

- `mre_config` became `DiffTrack-README-evaluation`
- `agent_task` became `DiffTrack-README-evaluation`
- `web_verification` was set to `unavailable` even though earlier tools worked
- `verified_links` were empty
- `score` was wrong

The extracted booleans for this row imply:

- `code_available = true`
- `dataset_available = false`
- `weights_available = false`
- `dataset_is_standard = false`

Using the prompt formula, the score should be 4:

```text
score = (NOT code_available) * 2
      + (NOT dataset_available) * 3
      + (NOT weights_available) * 1
```

The tier remains `Artifact-Blocked`, but the score field is wrong. This row should be treated as failed and rerun.

## Tool Failure Patterns

Tool counts:

| Tool | Calls | Errors |
| --- | ---: | ---: |
| `github_file_contents` | 38 | 0 |
| `github_search_repositories` | 28 | 0 |
| `fetch_url` | 24 | 2 |
| `huggingface_search` | 20 | 2 |
| `github_search_code` | 14 | 0 |
| `github_repository_tree` | 12 | 1 |
| `github_repo` | 11 | 0 |
| `huggingface_repo` | 6 | 6 |
| `read` | 5 | 5 |
| `file_read` | 5 | 5 |
| other unknown tools | 5 | 5 |

The biggest tool-interface issue is `huggingface_repo`: it was called 6 times and failed all 6 times. The model often recovered through `fetch_url` or `huggingface_search`, but these failed calls wasted rounds.

There were also invalid Hugging Face search calls where arguments collapsed to `{}`.

The `read` and `file_read` failures are hallucinated tool calls from the model, not real file reads. In row `2506.17220`, the model likely wanted to inspect repository or supplemental files after finding DiffTrack, but the runner only exposes web-verification tools such as `github_file_contents`, `github_repository_tree`, `github_repo`, `huggingface_search`, and `fetch_url`. It should have used `github_file_contents` for GitHub files.

That said, the underlying intent is useful. If the paper bundle or OpenReview supplement includes local dataset/supplemental artifacts, the runner should expose a narrow, allowlisted reader for those bundled files. That would let the model inspect supplement files directly without inventing generic local tools such as `read`, `file_read`, or `bash`.

## Format Issues

The raw final response format is inconsistent:

- 4/8 responses start cleanly with `{`
- 3/8 responses are fenced as ```json
- 1/8 response has prose before the JSON fence

The extractor recovered all 8 rows, but the model is not reliably obeying JSON-only output unless the final no-tools pass is forced.

## Quality Concerns

Some outputs are valid JSON but still need audit:

- `2509.16170` hit the 12-round limit and has no dataset URLs in `verified_links`, despite claiming standard dataset verification.
- `2502.13119` hit the 12-round limit after a long search-heavy trace. Its conclusion may be plausible, but the search path was budget-stressed.
- `2505.11475` mentions RM-Bench in evidence and task text, but `verified_links.code` does not include the RM-Bench URL.

These are not necessarily wrong, but they are signs that a post-pass should flag rows for review.

## Recommended Improvements

1. Add a deterministic post-validator.

   Validate:

   - `score`
   - `tier`
   - JSON-only shape
   - clean URLs
   - `web_verification`
   - missing `verified_links` for URLs cited in evidence or task text

2. Auto-rerun rows with bad control-flow signals.

   Rerun when:

   - `hit_tool_round_limit = true`
   - unknown tools were called
   - computed score and emitted score disagree
   - final response has prose or markdown fences

3. Fix or disable `huggingface_repo`.

   In this run, `huggingface_repo` had a 0% success rate. Until its MCP argument mapping is fixed, it wastes rounds and should either be repaired or replaced with `fetch_url` plus `huggingface_search`.

4. Guard unknown tool calls.

   Unknown tool calls should not consume full rounds. The runner could detect non-allowlisted tool names and either:

   - inject one corrective tool result listing the valid tools, or
   - force the final no-tools pass immediately.

5. Add a controlled supplemental-artifact reader.

   If paper bundles include local OpenReview supplement files, dataset manifests, README excerpts, or extracted artifact text, expose them through an explicit tool such as `supplement_file_contents` or `paper_bundle_file_contents`.

   This should be scoped to the current paper's bundle only, with path allowlisting and size limits. It should not expose arbitrary local filesystem access. The model can then satisfy its legitimate need to read bundled supplement files without hallucinating tools like `read`, `file_read`, or `bash`.

6. Force structured final output.

   The final answer should be produced with structured output even when the assistant voluntarily stops with no tool calls. Right now the extractor recovers fenced/prose-wrapped JSON, but benchmark data should not rely on recovery heuristics.

## Bottom Line

This run shows that DeepSeek V4 Flash can use the tool loop and produce usable artifact-classification JSON, but the system needs stronger guardrails. The main weakness is not basic completion; it is reliability under long searches, tool-interface confusion, and missing deterministic validation.

The immediate next move should be a validator plus selective rerun flow. That would likely rescue the good rows, quarantine `2506.17220`, and make the output much closer to benchmark-grade.
