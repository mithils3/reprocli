# Mirror examples for the ICLR rebuttal points

Each example is a verbatim author reply from the two sources. Forum ids are OpenReview forum ids. Excerpts are cut to the relevant part and keep their Markdown.

## 1. One run per cell, no seeds or variance

**Example 1.** 2026, forum PjIK38mwKm. Shape: bold label with a backtick tag, a one-line answer that states the variance bound ("<2%"), then a request to confirm.

* **Performance variance** `Question3` We have supplemented the main results with standard deviations across three independent runs, showing variances <2% in most cases, confirming that the performance improvements from ReSum are meaningful.

**Example 2.** 2025, forum VT4Ovqg0BW. Shape: answer in the body, a sentence naming the mean and standard deviation over 3 runs, a five-row table with the spread in subscripts, and a promise to add it as an ablation.

For the number of top gate routers, we performed an exploration from 1 to 5 experts and found that 2 is the optimal. The performance comparison on the OBQA dataset with Llama2-7B is given as following, we report the mean and standard deviation of the performance under 3 random runs:

| Top-K | ACC $\uparrow$ | ECE $\downarrow$ |
|---|---|---|
| Top-1 | $74.8_{0.62}$ | $7.69_{1.96}$ |
| Top-2 | $\mathbf{77.3_{1.36}}$ | $\mathbf{5.0_{1.15}}$ |
| Top-3 | $75.2_{0.8}$ | $5.8_{0.81}$ |
| Top-4 | $75.8_{0.53}$ | $7.67_{0.46}$ |
| Top-5 | $75.3_{0.5}$ | $6.29_{0.61}$ |

## 2. LLM judge or auto-grader validity and agreement with humans

**Example 1.** 2025, forum bhK7U37VW8 (AutoDAN-Turbo). Shape: "A3:" opener, a numbered first point that gives a Cohen's kappa for each judge model with a word for its level, then a second point tied to attack success.

A3: We also add alignment evaluations of summarizer LLM in Appendix F. Our analysis shows the following:
1. The summarizer LLMs also align well with human evaluators, though the level of agreement differs across models. Specifically, Gemma-7B-it achieves a high Cohen’s Kappa score of 0.8125, indicating substantial agreement with human-selected summaries and reliable performance in reflecting human judgments. Meanwhile, Llama-2-70B-chat achieves a moderate Cohen’s Kappa score of 0.6250, suggesting that while its summaries are generally consistent with human evaluations, there remains room for improvement.

**Example 2.** 2025, forum 9D2QvO1uWj. Shape: a "Q:" heading, then bullets that say what the agreement number measures (ROC-AUC against human labels), how many annotators there were, and whether the judge leaks annotator identity.

Q: Human evaluation of VideoCon-Physics
- We clarify that Table 4 indicates the agreement (ROC-AUC) between the videocon-physics predictions and the human annotations on the unseen prompts and videos in the test set. The results highlight that the agreement of Videocon-physics is high in comparison to the other baselines.
- Table 5 highlights that the VideoCon-physics is not biased towards annotations that were taken for specific video models. Specifically, we show that the Videocon-physics can reliably perform judgments for the video models that were unseen in the training on the unseen prompts and videos.
- Further, we highlight that the videophy annotations were performed by 14 workers where the load was shared uniformly across the annotators. It is unlikely that the model will be biased towards the judgments of a specific annotator.

## 3. Logs or results the agent could tamper with

None found. Searches of both sources for tamper, overwrite, log file, reward hacking and cheating returned no reply about agent-writable logs or results. The cheating hits were about attacks on LLM judges and were left out.

## 4. No human baseline

**Example 1.** 2025, forum DSsSPr0RZJ. Shape: an opening thank-you, a short paragraph that defines the human number (average of the top-3 public solutions), then a closing request to adjust the score.

Thank you for your thoughtful feedback. For the human expert performance in our study, we collected and evaluated the top-3 performing codes from the Kaggle website for each competition (e.g., https://www.kaggle.com/competitions/santa-2024/code). The human expert performance on our split dataset is then calculated as the average performance of these top-3 codes.

**Example 2.** 2026, forum hzf23XSDcs. Shape: a numbered list of bold items, the third one giving the human score next to the model score with two bold numbers.

3.  **Integrated the SPL metric as per your constructive suggestion** across models and the human baseline. This new data (Human SPL: **21.23%** vs. SOTA VLM: **~13%**) provides a crucial, holistic view of navigation efficiency and further validates the benchmark's difficulty.

## 5. How targets or labels were validated

**Example 1.** 2025, forum 996aKQIom0. Shape: a numbered list of bold labels, each a one-line commitment (annotator count, a table to complete, a motivation sentence), with no new numbers beyond the annotator count.

We appreciate these detailed comments about our evaluation methodology. We acknowledge several limitations in the current version and are implementing substantial improvements:
1. **Annotation process**. We are expanding from 1 to 5 annotators. The revised version will include detailed annotator profiles (background, expertise), complete annotation instructions in supplementary materials, time and cost details.
2. **Version comparison**. We will complete the empty cells in Tables 1 and 2 to provide a thorough comparison across all models for both versions.

**Example 2.** 2025, forum jw2fC6REUB. Shape: a short list of what was added to the appendix, with the agreement numbers moved there rather than stated in the reply. Weaker match: it reports agreement but does not validate targets.

We have added additional details to the appendix based on your suggestions. In particular,

* Numbers for the inter-annotator agreement for retrieval tasks.
* Appendix Tables 3 and 4, consolidating the tasks, number of examples, input and output lengths, brief description of tasks, assessed capabilities, and metrics.

## 6. Tolerance or threshold choice

**Example 1.** 2025, forum 7mlvOHL6qJ. Shape: a bullet list of revisions, each ending with an appendix letter. The threshold sweep is one bullet pointing to Appendix N.

- Included a further discussion on the principles of choosing the similarity threshold, together with additional experimental results with varying thresholds, in Appendix N;

**Example 2.** 2025, forum NUD03NBDOE. Shape: the reviewer question quoted in a Markdown heading block, a pointer to Appendix F, and a short reason why a threshold is hard to set. No number is given.

## Questions
> Have you considered incorporating a combination of automatic evaluation metrics (e.g., BertScore) alongside the current evaluation?

We appreciate the reviewer’s suggestion. We have added F1-BERTScores in Appendix F for comparison. While traditional metrics like F1-BERTScore provide additional insights, our manual analysis reveals cases where they give high scores to incorrect responses and low scores to correct ones, making thresholding difficult. A combination of LLM-based evaluation and automatic methods (like BERTScore) could yield a better metric, but that is out of the scope of this paper. (Refer to Weakness 1 for details)

## 7. Frontier models or production agents not evaluated

**Example 1.** 2025, forum 0K1OaL6XuK. Shape: a follow-up that restates the earlier GPT-4 check, adds three new tasks, and reports an optimal rate over 10 queries per task.

In our last response, we show LLMFP does not necessarily need stronger models by testing it with GPT-4 for two multi-step tasks, Blocksworld and Gripper. We would like to provide some more experiments to support this claim. We performed additional experiments to test it with GPT-4 on three more multi-constraint tasks, Workforce, Task Allocation, and Warehouse. We tested 10 queries from each domain and got an optimal rate of 80%, 70%  and 70% respectively.

**Example 2.** 2025, forum 7H1jbTaOIn. Shape: the reviewer's question quoted in bold-underscore, a one-sentence answer, and a single-row table. It answers with GPT-3.5 rather than the Claude 3.5 or GPT-4o the reviewer named, so it is a partial match.

__3.  paper only uses small open-sourced LLMs, such as GPT-Neo-1.3B GPT-Neo-2.7B Llama-2-7B. Is that possible to provide results using larger ones, such 70B LLama-3.1 and other close-sourced ones, such as Claude 3.5 and GPT-4o?__

Thank you for the valuable suggestion. We conduct all baselines for Subj. As shown in following table, our method still outperforms other baselines using large scale model GPT-3.5. We have also added these results in Table 3 in  revised version.

## 8. Hardware or environment confounds

**Example 1.** 2025, forum 5Jc7r5aqHJ. Shape: bold labels per topic, with the hardware named in one sentence (GPU and CPU model) and a pointer to Section 5.1 for the rest.

**Deployment Details**: We have provided implementation details in the manuscript (Sec 5.1) and anonymous code to facilitate understanding and reproducibility.  The experiments use NVIDIA GeForce RTX 3090 GPUs as the hardware platform, coupled with Intel(R) Xeon(R) Gold 6240 CPU @ 2.60GHz.

**Example 2.** 2025, forum xyfb9HHvMe. Shape: a bold question, a bold answer that names the single GPU, a two-row table of memory and time per step, and a one-line conclusion. Weaker match: it reports cost, not a confound.

**A11.** Thanks for your suggestions! We compare our method with Diffusion-DPO by fine-tuning SD15, using a batch size of 16 and 128 gradient accumulation steps on a single A100 GPU. The table below presents the average time per optimization step for DSPO and DPO:

|           | GPU Memory | Time for each step | 
|-----------|----------|-------|
| Diffusion-DPO   |  60.5G |   4.14min    |
| DSPO   | 60.2G | 4.18min     |

We observe that our models have similar GPU memory and time for each optimization step compared with Diffusion-DPO.

## 9. Checkpoint or data leakage (agent downloading results)

No example of an agent downloading a checkpoint was found. The two examples below are the nearest matches on data leakage.

**Example 1.** 2025, forum 9EBSEkFSje. Shape: a closing summary with one bullet per reviewer weakness (W1, W2, and so on), each stating what was clarified. The leakage answer is one bullet with no number.

- (W1): We highlighted the inherent challenges of completely avoiding data leakage in large benchmarks (and its similar practice in NLP benchmarks), and emphasized our effort to minimize leakage while ensuring diversity and generalizability.

**Example 2.** 2025, forum o9SuQXZvNA. Shape: a quoted reviewer sentence, then a short "Thanks for the comment!" reply that defers the leakage question to future work. Weaker match: it concedes rather than measures.

Thanks for the comment! We will further study the reasons for the under-performance of LLMs and the impact of potential data leakage in the future.

## 10. Failures caused by the infrastructure

None found. Searches of both sources for timeout, out of memory, job killed, time limit and infrastructure returned no reply about failed runs.

## 11. General response listing revisions

**Example 1.** 2025, forum l11DZY5Nxu. Shape: a one-sentence opener, then bold area labels (Datasets, Writing, Limitations, Timing), each with one sentence and an appendix pointer.

**Dear Reviewers,**  

Thank you for your comprehensive and constructive feedback on our work. Below, we summarize the key revisions made during the rebuttal:  

- **Datasets:**  We clarify that the Petshop dataset is a recently released, state-of-the-art RCD benchmark, and not created by us. Details about Petshop and other synthetic datasets have been added to `Appendix C`.  
- **Writing:**    We streamlined the paper by removing redundant points and updated the caption of `Fig. 1` to clarify the OOD behavior specific to the RCD problem. Additionally, we introduced `Fig. 2` to illustrate the training and inference procedures of IDI.  
- **Limitations of IDI:**  To analyze the pros and cons of IDI compared to other counterfactual RCD approaches, we conducted new experiments (see `Appendix E`) to evaluate IDI’s sensitivity to training size and variance ($\epsilon_i$). These limitations have been explicitly discussed in `Sec. 7`.  
- **Timing Analysis:**   We performed a timing analysis of IDI and other baselines, now included in `Appendix D`.  

**Example 2.** 2025, forum Il5DjZmLzp. Shape: a numbered list of four added items, with a closing sentence that compares the method with a prior work on that work's own benchmark.

During this rebuttal process, we have:

1. Added a subsection to the paper discussing foundation model choice.
2. Provided sample complexity results for the color setting, demonstrating a significant advantage compared to brute-force.
3. Provided ablations for the energy functions on segmentation.
4. Shown preliminary results on **3 different realistic transformations**: CO3D viewpoint shifts, day-night, and embodied vision in a virtual environment. Our method demonstrates promising canonicalization performance in these experiments, and we plan to do large-scale testing for the camera-ready draft.
