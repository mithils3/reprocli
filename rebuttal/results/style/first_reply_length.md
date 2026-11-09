## Method
- Data: format_sample.jsonl, 240 threads (group values: raised, unchanged). Raised n=120, unchanged n=120.
- First reply: post 1, plus following posts when post 1 title or first 80 chars has (1/N) or "Part 1" (then the next N-1 posts), otherwise the following posts whose title or first 80 chars has (k/N), "Part k", or "continued", stopping at the first post without one.
- Labelled answers: QLAB label lines (W/Q/C/Point/Issue + number), first occurrence per id, from fmt_study.py; blockquote lines excluded; words per answer = answer words; per-thread ratio = first-reply words / labels, 0-label threads excluded.
- Reviewer points: items (numbered/bulleted) under the "weaknesses:" and "questions:" keys of review_text; if none, paragraphs in those sections.
- Quartiles: statistics.quantiles, method inclusive. Table rows = pipe lines minus separator lines. Numbers = numeric tokens after removing reference labels (Table 2, Q1, Section 3). Result answer = markdown table or 3+ numbers.

## Item 2: first reply, quartiles Q1 / median / Q3
| Group | Chars | Words | Posts | Labelled answers | Words per labelled answer |
|---|---|---|---|---|---|
| All | 3229 / 4436 / 5521 (n=240) | 488 / 658 / 825 (n=240) | 1 / 1 / 2 (n=240) | 0 / 0 / 4 (n=240) | 135 / 206 / 341 (n=115) |
| raised | 3746 / 4789 / 6351 (n=120) | 551 / 689 / 914 (n=120) | 1 / 1 / 2 (n=120) | 0 / 1 / 4 (n=120) | 148 / 221 / 368 (n=68) |
| other (unchanged) | 3032 / 4160 / 4972 (n=120) | 429 / 589 / 749 (n=120) | 1 / 1 / 1 (n=120) | 0 / 0 / 3 (n=120) | 116 / 184 / 288 (n=47) |

## Item 3: reviewer points vs first reply (threads with points in bin)
Points counted by: Counter({'items': 196, 'paragraph fallback': 44}); points Q1/median/Q3 = 4 / 6 / 8 (n=240)
| Points bin | Chars Q1 / med / Q3 | Words Q1 / med / Q3 |
|---|---|---|
| 1-3 | 2886 / 4129 / 5277 (n=54) | 423 / 586 / 816 (n=54) |
| 4-5 | 3046 / 4298 / 6023 (n=62) | 425 / 624 / 862 (n=62) |
| 6-8 | 3407 / 4552 / 5233 (n=70) | 525 / 674 / 838 (n=70) |
| 9+ | 3723 / 4542 / 5402 (n=54) | 567 / 676 / 803 (n=54) |

## Item 4: markdown table in first reply
- Share with a table: 67/240 = 27.9%
- Table rows among those with a table: median 8 (Q1/Q3 5/14, n=67)

## Item 5: posts in first reply
- one post: 176/240 = 73.3%
- two posts: 38/240 = 15.8%
- three or more: 26/240 = 10.8%

## Item 6: words per labelled answer, result vs rest
- Labelled answers total: 478
| Answer type | Words Q1 / med / Q3 |
|---|---|
| reports a result (table or 3+ numbers) | 119 / 192 / 322 (n=282) |
| rest | 45 / 80 / 121 (n=196) |

## Model answers (group raised, 90-180 words, result with numbers)
Candidates: 8 answers across 7 threads; first five in sort order (first sentence with a number first, then thread id).

### 1. thread_id t062, 170 words, answers 'Q3: The reliability of the summarizer LLM is also unclear. A comparison with human-generated summaries would be beneficial.'

> : The reliability of the summarizer LLM is also unclear. A comparison with human-generated summaries would be beneficial.
> 
> A3: We also add alignment evaluations of summarizer LLM in Appendix F. Our analysis shows the following:
> 1. The summarizer LLMs also align well with human evaluators, though the level of agreement differs across models. Specifically, Gemma-7B-it achieves a high Cohen’s Kappa score of 0.8125, indicating substantial agreement with human-selected summaries and reliable performance in reflecting human judgments. Meanwhile, Llama-2-70B-chat achieves a moderate Cohen’s Kappa score of 0.6250, suggesting that while its summaries are generally consistent with human evaluations, there remains room for improvement.
> 
> 2. While the alignment of different LLMs in jailbreak strategy summarization varies, all the evaluated LLMs achieve higher jailbreak ASR compared to baseline methods. This demonstrates that using LLMs as summarizers is both reasonable and practical in our method. For instance, as shown in Table 3, even the relatively small Llama-2-7B-chat model, which has weaker alignment and helpfulness capabilities, achieves a 48.0% ASR when attacking Gemini Pro.

### 2. thread_id t190, 111 words, answers '> **Q2.** Omission captioning details in ground-truth annotation'

> .** Omission captioning details in ground-truth annotation
> 
> **A2.** As we explained to Reviewer DgKk, we compensate for the missing fine-grained details in the ground-truth captions that are present in the model's predictions when computing recall score $s_r$ for DCScore. In concrete, in step 3, we would use GPT-4o to identify the units that are correct but not presented in reference captions. By incorporating the correct additional information from the model's captions into the ground-truth caption, we make the evaluation metric more robust to the omission details in ground-truth captions.
> 
> | Considering Omission in Ground-truth  | PCC ($\rho$) | $1-R^2$ | KD $\tau$ |  Sp $\tau$ |
> |---|---|---|---|---|
> | No | 0.6151 | **0.72** | 0.5111 | 0.5916 |
> | Yes (DCScore) | **0.6605** | 1.54 | **0.5328** | **0.6166** |

### 3. thread_id t259, 112 words, answers '> **Q4.** The performance metrics for GraphSAGE are absent from Table 2. There is a discrepancy between the methodology description and experimental results regarding GraphSAGE (line 420)'

> .** The performance metrics for GraphSAGE are absent from Table 2. There is a discrepancy between the methodology description and experimental results regarding GraphSAGE (line 420)
> 
> **A4.** We believe there has been a misunderstanding. Line 420 states that **in our framework**, the GNNs used for **generating prototypes** (Eq. 6) and **classifier guidance** (Eq. 9) are GraphSAGE. In other words, GraphSAGE is used in all variants of our AugGLM model (T5-small/base/large).
> 
> However, we appreciate the suggestion to include GraphSAGE as a baseline in Table 2. To address this, we report its performance on Cora/Pubmed/ogbn-arxiv/ogbn-products as follows: 86.51/89.08/73.88/76.04. They have been incorporated into the revised Table 1.

### 4. thread_id t365, 157 words, answers '> **Q1**: The semantic preservation of the proposed method is inferior compared to GPT Paraphraser.'

> **: The semantic preservation of the proposed method is inferior compared to GPT Paraphraser.
> 
> A1: We agree with the reviewer’s opinion that  our method preserves semantics when using llama3-8b. However, we clarify that the attack method involves a trade-off between resource consumption, attack effectiveness, and semantic preservation. We would like to highlight that our attack performance significantly surpasses that of other baseline methods. 
> 
> In our experiment, we find that the performance of semantic preservation is highly influenced by the capabilities of the paraphrasing model. We use a lightweight Llam3-8b model to reduce resource requirements. As noted in Section E, replacing Llama3-8b with Llama3-70b in our setup increases the Semantic Preservation score by 16%. 
> 
> To further address the reviewer’s concerns, we conducted an additional experiment using GPT-4o as the paraphrasing model using our method while keeping all other settings unchanged. This adjustment resulted in a semantic preservation score of 8.02 which closely aligns with GPT Paraphraser(8.25).

### 5. thread_id t402, 147 words, answers '### Weakness 1.'

> .
> The proposed model, Vec2Face, which can convert vectors to images while preserving the ID information, is the reason we can generate an unlimited number of identities, not PCA. The reason we use PCA is that we found it can sample better/stronger identity vectors, resulting in accuracy improvement.
> |       Vector sampling          | Accuracy |
> | :-------------: | :------: |
> |  with PCA   |  92.00   |
> | without PCA |  91.24   |
> 
> Unlike Arc2Face, which fine-tunes a stable-diffusion-v1.5 on WebFace42M, we train our model with only 1M images and we can achieve higher accuracy, showcasing the efficacy of the proposed work.
> 
> As for ID3, we added its result because we saw that literature before the full version submission. We will add it to the related work, but it is impossible for us to borrow ideas from it because we trained our model for over 1000 epochs and the HSFace400K has 20M images. Both are non-trivial to be achieved in this short period.
