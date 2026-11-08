# Author-response advice and evidence on score change (collected 2026-11-08)

Verification key: READ = I fetched the source text itself (via a fetch tool that summarizes pages, so numbers are as reported by that tool, not eyeballed from the PDF). SNIPPET = seen only in search excerpts. NOT READ = could not open.

## 1. Evidence on what changes scores

### 1.1 Kargaran, Nikeghbal, Yang, Ousidhoum (2025), "Insights from the ICLR Peer Review and Rebuttal Process"
URL: https://arxiv.org/abs/2511.15462 (HTML: https://arxiv.org/html/2511.15462). Submitted 19 Nov 2025; data from Paper Copilot / OpenReview, ICLR 2024 and 2025. Status: READ (abstract, Sections 1 to 3, Table 1 to 3, 7, 8, appendix A; Section 4.2 body text NOT READ, the fetch returned only its table captions and annotation prompts).
- Corpus: 2025 has 11,672 papers and 46,748 reviews; 2024 has 7,405 papers and 28,028 reviews.
- Per review, rating after rebuttal (2024 / 2025): same 81% / 75%; increased 17% / 23%; decreased 1% / 1%.
- Mean rating of reviews that rose: 4.64 to 6.34 (2025), 4.58 to 6.30 (2024). Most common changes: 5 to 6, 6 to 8, 3 to 5.
- Acceptance rate by paper group (2024 / 2025): score increased 57.6% / 55.7%; unchanged 12.4% / 7.8%; decreased 6.4% / 8.0%. Still, 42% / 44% of papers with increased scores were not accepted. This is correlational, since strong papers also get raised.
- Rank shuffling: over 40% of the top-5% papers were displaced in both years; nearly 20% of papers left the top 30%.
- Reviewer disagreement falls after rebuttal by 8.92% (2025) and 10.12% (2024); the drop is larger for orals (about 41 to 48%) and spotlights (about 26 to 29%) than for rejected papers (about 6 to 7%). This shows convergence among reviewers, not only author persuasion.
- Predictors of change (Table 8, average absolute regression coefficients): own rating before rebuttal 0.67; other reviewers' mean rating 0.37; reviewer engagement 0.25. Abstract: "initial scores and the ratings of co-reviewers are the strongest predictors of score changes" and rebuttals help borderline papers.
- Timing: for 2025, nearly one third of first messages sent 18 to 24 Nov later led to a score increase (Section 3.2, as reported by the fetch tool).
- Fetch-tool discrepancies in the paper: text says macro F1 0.71 and 0.52 while Table 7 says 0.69 and 0.51; the Introduction's "one in five top papers" and the Conclusion's "about 20% of accepted submissions" are different claims. The rebuttal-strategy taxonomy (coverage, stance, strategy; 81% agreement with humans on 10 papers) is LLM-labelled, so treat strategy results as weak. I could not read what strategies it found helpful.

### 1.2 Gao, Eger, Kuznetsov, Gurevych, Miyao (2019), "Does My Rebuttal Matter? Insights from a Major NLP Conference", NAACL 2019
URLs: https://aclanthology.org/N19-1129/ ; https://arxiv.org/abs/1903.11367 (read through https://ar5iv.labs.arxiv.org/html/1903.11367). Status: READ (abstract plus ar5iv body).
- Data: ACL 2018, 3,870 reviews on 1,538 submissions with before and after scores.
- Overall score after the response: increased 245 reviews (about 6.3%), decreased 248 (about 6.4%), kept 3,377 (about 87.3%). Raised reviews moved from mean 2.65 to 3.76; lowered reviews from 4.17 to 3.04.
- Papers with an increase: 49.8% accepted; with a decrease 7.2%; kept 22.8%.
- Main finding: rebuttals have a "marginal (and statistically significant)" effect, mostly on borderline papers. The biggest predictor of a final score is the gap between a reviewer's own initial score and the other reviewers' mean (conformity), with weight 1.044 for increase and -1.265 for decrease in the full model.
- Response text features (convincingness, specificity, politeness) add little: macro F1 .526 with score only vs .540 with all features on the full set; borderline subset .495 vs .522; majority baseline .301.
- On the borderline subset (590 submissions, 69 raised, 48 lowered), specificity median (0.293), minimum convincingness (0.224) and review-response similarity (0.214) carry more weight than elsewhere. Politeness matters more for keeping a score than raising it there.
- Strong responses averaged 90 tokens vs 53 for weak ones (the fetch tool's summary; check the paper before quoting).
- Caveat: ACL 2018 scale and a different community; scores here are 1 to 5.

## 2. Official ICLR rules

### 2.1 ICLR 2026 Author Guide
URL: https://iclr.cc/Conferences/2026/AuthorGuide (ICLR organizers, 2025). Status: READ via fetch tool; ICLR 2027 guide not checked, so confirm dates and limits there.
- Responses are posted as OpenReview comments once reviews are out (2026: reviews 11 Nov; public discussion 11 Nov to 3 Dec; private reviewer/AC discussion to 10 Dec; decisions 22 Jan).
- Paper can be revised until the end of the public discussion period. Main text limit rises from 9 to 10 pages, "strictly enforced".
- Revisions are checked with a pdfdiff; "Area chairs and reviewers reserve the right to ignore changes that are significantly different from the original paper." Reviewers are not required to read every revision, so communicate changes clearly.
- Each comment has a word limit (number not stated in the fetched text) but the number of comments is unlimited; authors should "remain civil and considerate of the reviewers time."
- Revised abstract must not "read like a different paper"; author set is frozen, order may change.

### 2.2 ICLR 2026 Reviewer Guide
URL: https://iclr.cc/Conferences/2026/ReviewerGuide (ICLR organizers, 2025). Status: READ via fetch tool.
- "It is crucial that you are actively engaged during this phase"; "Maintain a spirit of openness to changing your initial recommendation (either to a more positive or more negative) rating."
- "Update your review, taking into account the new information collected during the discussion phase"; "State your reasoning and what did/didn't change your recommendation."
- Reviewers can change reviews after the response period. Requested new experiments "should not significantly change the content of the submission" and should be limited in scope.
- Borderline papers may get an AC-led virtual meeting; reviewers are told to read other reviewers' feedback first. Practical reading: a response should make it easy for the reviewer to write that "what changed" sentence.

## 3. Practitioner guides

### 3.1 Devi Parikh, Dhruv Batra, Stefan Lee, "How we write rebuttals" (Medium, 27 May 2020)
URL: https://deviparikh.medium.com/how-we-write-rebuttals-dc84742fece1. Status: NOT READ (HTTP 403; one mirror attempt was blocked, so I stopped). Everything below is SNIPPET-level, from search excerpts and secondary quotes.
- Quoted by search excerpt: the reply is aimed at the opponent but "more importantly, we are trying to convince the judges, who will ultimately be making the decisions" (reviewers and area chair).
- Process: keep a spreadsheet of every reviewer comment, draft a response to each, cover every point, then trim and prioritize. Core principle as summarized: thorough, direct, easy for reviewers and AC to follow.
- Recommended by the IJCB 2023 call for papers and cited by Soto Valero. The remaining rules (structure, tone, length) are unverified; fetch it by hand before relying on them.

### 3.2 César Soto Valero, "How to Write a Good Paper Rebuttal" (29 Jan 2022)
URL: http://www.cesarsotovalero.net/blog/how-to-write-a-good-paper-rebuttal.html. Status: READ via fetch tool. Software-engineering venues, not ML, with very short word limits; cites Andreas Zeller, "Patterns for writing good rebuttals" (2012) and the Identify-the-Champion method (NOT READ).
- Typical length 500 to 750 words. Respond only if at least one reviewer clearly favors acceptance (the champion rule).
- About 50 words thanking reviewers and summarizing their positives, then major concerns first (novelty, significance, methodology); skip proofreading-level fixes.
- Add new experiments where allowed, with a link to data; stay respectful and never say a reviewer lacks understanding; end with a summary of concerns shared across reviewers; if several reviewers misread a point, admit the paper is unclear and promise to fix it.

### 3.3 Searched but not read
- Danfeng Yao (Virginia Tech), "Rebuttal Howto" PDF, https://people.cs.vt.edu/~danfeng/papers/Yao-Rebuttal-Howto.pdf: HTTP 403, NOT READ.
- Zihao, "How to Write a Good Rebuttal", zihao-ai.github.io: 404, NOT READ.
- CACM "Rebuttal how-to: strategies, tactics, and the big picture in research": 403, NOT READ; author and year unverified.

## 4. What the evidence supports (synthesis, my reading)
- Roughly 75 to 87% of reviewers keep their score across the two ICLR years and ACL 2018; about 17 to 23% raise it at ICLR, about 6% at ACL 2018. Decreases are rare at ICLR (1%).
- Both large studies find the initial score and distance from co-reviewers dominate; response wording is a second-order effect that matters mainly near the accept line.
- Pattern across guides: address every point, answer major concerns first, be specific and polite, put new evidence in tables or links, and write for the AC as well as the reviewer.

## 5. Unverified claims to avoid repeating
- Any Parikh/Batra rule beyond the quoted lines in 3.1.
- Any claim that a particular rebuttal strategy raises scores at ICLR (Section 4.2 of arXiv 2511.15462 not read).
- ICLR 2027 dates, word limit and page limit (only the 2026 guide was read).
