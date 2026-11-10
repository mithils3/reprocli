# ICLR author responses: length and style from OpenReview search hits

Sample of search hits, not the full population. OpenReview's forum and listing endpoints return 403, so every number here comes from the notes search endpoint. Each query returns at most 10,000 hits, so the sample is capped per query.

## Method

Endpoint: `https://api2.openreview.net/notes/search?term=<term>&group=ICLR.cc/<year>/Conference&limit=1000&offset=<0,1000,...>`, paged until a page returned fewer than 1,000 notes. The endpoint rate-limits at 20 requests per window, so requests were retried after a 30 second wait.

Keep rule: the note's invitations end in `Official_Comment`, and its signatures contain a `/Authors` entry. Deduplicated by note id across all queries and years.

Queries run, with raw hits, kept author comments (Official_Comment and Authors), and new unique comments added:

| Query | Year | Raw hits | Kept | New unique |
|---|---|---|---|---|
| we thank | 2025 | 10,000 | 4,026 | 4,012 |
| thank the reviewer | 2025 | 10,000 | 7,950 | 4,825 |
| reviewer for | 2025 | 10,000 | 9,064 | 5,158 |
| we have added | 2025 | 10,000 | 5,796 | 4,317 |
| revised version | 2025 | 10,000 | 7,276 | 5,565 |
| rebuttal | 2025 | 5,000 (partial, fetch stopped) | 3,320 | 2,735 |
| we thank | 2026 | 10,000 | 3,485 | 3,465 |
| thank the reviewer | 2026 | 9,000 | 5,942 | 4,060 |

New unique counts are the comments added by that query after deduplication, so they sum to the 34,137 total only with overlaps removed.

Not run before the time budget ran out: "we appreciate", "thank you for", "we clarify", "additional experiments", "we respectfully" (both years), and "reviewer for", "we have added", "revised version", "rebuttal" for 2026. The 2026 sample is therefore thinner than 2025.

Dropped: raw hits that were not author Official_Comment notes (reviews, decisions, and other notes), and duplicates across queries. Totals: 34,137 unique author comments kept (26,612 from 2025, 7,525 from 2026). 5,592 official reviews on the same forums were saved.

Measures: characters are `len(content.comment)`. A reviewer thread is all author comments that share a forum and a replyto that is not the forum. A general response is a comment whose replyto equals its forum id. "Part" flag: the text or title contains "part 1", "(1/2)", or "continued" (case-insensitive). Table use: at least one line starting with `|`. Bullet use: at least one line starting with `-`, `*`, a bullet character, or a number followed by `.` or `)`. Quartiles use `statistics.quantiles` with the inclusive method.

## Results

Author comments (n = 34,137):
- Characters per comment: Q1 693, median 2,264, Q3 3,896.
- Share flagged as a part (part 1, (1/2), or continued): 8.3%.
- Share with a Markdown table: 15.9%.
- Share with a bullet line: 33.3%.
- Share opening with a "Dear Reviewer" salutation line: 18.2%.

Reviewer threads (n = 26,109 forum and replyto pairs):
- Total author characters per thread: Q1 696, median 2,526, Q3 4,278.

General responses:
- Forums in the sample: 9,642. Forums with at least one general response: 28.2%.
- General responses: 2,976. Characters per general response: Q1 894, median 1,717, Q3 2,792.

Years differ in sample size only; no year split of these medians is reported here.

## Verbatim openings (first sentence after the salutation)

1. (2025) "Thank you for taking the time to review our paper."
2. (2025) "We thank the reviewer for carefully reading our work and proofs."
3. (2025) "We would like to express our sincere appreciate for your thoughtful feedback and kind recognition of our efforts to address your concerns."
4. (2026) "Thank you for the summary comments."
5. (2026) "We sincerely thank the reviewers for their engagement with our work."

## Verbatim examples of reporting a new result (under 60 words each)

A. (2025, 52 words) "We have now updated the submission with a new version of the manuscript which includes the changes mentioned above. We added the new results (Table 4b in Appendix B), referred to from the end of Section 4.3. The fourth and fifth paragraphs of the related work section have been updated (L460ff, L478ff)."

B. (2025, 56 words) "We thank the reviewer 3NzV for the constructive comments. We kindly remind you that we have clarified the issue on the conditional generation experiment, discussed the related work, and added a new experiment on GSM8K (achieving a comparable performance with Llama-2 7B). We look forward to your reply and are happy to address any further comment."

## arXiv 2511.15462 ("Insights from the ICLR Peer Review and Rebuttal Process")

Checked against the HTML version at https://arxiv.org/html/2511.15462.

- Author response length: the paper gives no word or character count for author responses. Its word-count analysis (Section 4.1, Table 4, Table 5, Figure 8) covers reviewer text. Quote: "we use word counts as a strong feature (see next RQ)". Its main finding on length is therefore not stated for author responses.
- Number of responses: the paper counts conversation turns, not responses. Quote (Section 3.1): "Reviews with increased scores show higher engagement, including more conversation turns and stronger author–reviewer participation than in the keep or decrease score cases".
- Timing (Section 3.2): "The rebuttal starts with the first message; usually, authors prepare their entire rebuttal in this initial interaction."
- Introduction: "Rebuttals submitted in the middle of the rebuttal period may be the most effective, while very early or last-minute rebuttals have less impact on engagement and score changes."
- Introduction: "but rebuttals that provide evidence-backed clarifications and avoid generic or vague defenses are more likely to result in positive score changes."
- Section 4.2: "a “generic/vague defense” strategy tends to only help reviewers maintain their original scores".
- Conclusion: "Textual analysis highlights that evidence-backed clarifications and precise responses are most strongly associated with positive changes, whereas vague or defensive rebuttals have little effect."

Reading for us: the paper ties score changes to content and timing, not to response length. This matches the sample, where a general response has a median of 1,717 characters against 2,264 for all comments.

## Files

- Rows: /home/mithil/PyCharmProjects/reprocli/rebuttal/results/style/iclr_author_responses.csv
- Full author text: /home/mithil/PyCharmProjects/reprocli/rebuttal/results/style/author_comments.jsonl (34,137 rows)
- Official reviews on the same forums: /home/mithil/PyCharmProjects/reprocli/rebuttal/results/style/review_comments.jsonl (5,592 rows)
- Processing script and raw pages: /tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/6dbe9a0b-b0fd-4784-933b-d978a99d9c41/scratchpad/ior/process.py

Paper titles: only 644 of the 34,137 author comments have a `paper_title`, because the search returned the submission note for only a few forums.
