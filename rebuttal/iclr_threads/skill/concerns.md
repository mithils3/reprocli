# Answer moves by concern type

This file tells you, for each kind of reviewer concern, which answer move went with the reviewer raising the score in ICLR 2025 threads. The data are 441 threads coded blind (244 raised, where the reviewer went from 5 or lower to 6 or higher, and 197 unchanged, where the reviewer replied and stayed at 5 or lower), split into 2,371 reviewer points, with coders blind to group and scores. Numbers come from blind_stats.md unless a line says they were counted from blind_rows.jsonl, and each quote is the first sentence of a real answer.

## How to read a raised share

A raised share is the fraction of points with a given answer move that sit in a raised thread. For example, authors answered 436 points with a new experiment, and 281 of those points sit in raised threads, so the raised share is 281 / 436 = 64% (counted from blind_rows.jsonl; blind_stats.md gives 64% [58, 71]). Compare it with the baseline over all points, 1,282 / 2,371 = 54% [49, 59], so a move at 64% went with raises about ten points more often than the average point. The bracket is a 95% interval from a bootstrap that resamples whole threads, because points in one thread share one outcome. When the intervals of two moves overlap, the data cannot tell them apart, and this file says so. Every gap is a correlation. A concern that the authors can fix may lead both to a new experiment and to the raise, so a high share for a move does not prove that the move caused the raise.

## Findings across all concern types

**Moves.** Running a new experiment (`new_experiment`, 436 points, 64% [58, 71]) is the one move whose interval sits wholly above the 54% baseline. A new analysis of data the authors already had (`new_analysis_existing_data`, 82 points, 63% [52, 74]) has a similar estimate, but its interval reaches below the baseline. Revising the text (`text_revision`, 509 points, 56% [49, 62]) and explaining without changing the paper (`clarification_only`, 558 points, 55% [49, 62]) sit at the baseline. Disagreeing sits below it whether or not evidence backs it: disagreement with evidence is 43% [35, 51] over 328 points, wholly below the baseline, and disagreement without evidence is 43% [33, 54] over 136 points, with an interval that just reaches it. Conceding and narrowing the claim (`concede_and_scope`, 128 points, 49% [39, 59]) and deferring to future work (`defer_future_work`, 101 points, 47% [36, 57]) sit slightly below the baseline, with intervals that include it.

**Numbers.** Answers that contain numbers have a raised share of 63% [57, 69] over 671 addressed points, while answers without numbers have 51% [46, 56] over 1,609. The intervals do not overlap, though much of the gap may come from new experiments, which usually report numbers.

**Location.** Answers that tell the reviewer where the change sits in the paper (a section, line, table or appendix) have 61% [55, 66] over 973 points, against 50% [44, 55] over 1,307 points without a location. The intervals touch at 55, so the gap is suggestive.

**Length.** Answers of 150 words or more have 64% [58, 70] over 762 points, and shorter answers have 49% [44, 55] over 1,518 points, with no overlap. Long answers often carry a new result, so length is likely a sign of substance and padding will not reproduce the gap.

**Major points left unaddressed.** Skipping a major point was rare in both groups: 24 of 852 major points went unaddressed in raised threads (3% [2, 4]) and 32 of 795 in unchanged threads (4% [3, 6]). The intervals overlap, so the data show no effect, and answering every major point stays the default.

At the thread level, dismissive disagreement appeared in 22 of 244 raised threads and 35 of 197 unchanged threads, a gap of -9 points [-15, -2], so a dismissive tone went with unchanged scores.

## clarity_or_presentation

The reviewer says a figure, symbol, section or passage is hard to follow (374 points, raised share 50% [43, 58]).

**Recommended:** revise the text and say where. Text revision has 53% [45, 61] over 226 points. **Avoid:** an explanation that leaves the paper unchanged, at 45% [34, 57] over 108 points. The intervals overlap, so this is a weak preference.

- Raised: "We have discussed practical implications of our main result (see Corollary 3.8), and extended the section Conclusions and Future Work." (https://openreview.net/forum?id=XtY3xYQWcW)
- Raised: "We totally agree that the structure and clarity of the old version of the paper can be significantly improved." (https://openreview.net/forum?id=qKgd7RaAem)
- Unchanged, explanation with no revision: "We explicitly defined $e$ in lines 51-52 as the all-one column vector." (https://openreview.net/forum?id=mBJF0p9yRR)

## evaluation_validity

The reviewer doubts that the evaluation measures what the paper claims, for example a biased judge, too few benchmarks or an unrepresentative setup (306 points, raised share 56% [48, 63]).

**Recommended:** produce new evidence. A new analysis of existing data has 69% [50, 88] over 29 points, a new experiment 63% [52, 74] over 81, and a clear explanation 67% [53, 79] over 57. **Avoid:** conceding and narrowing the claim, which has 21% [5, 42] over 19 points. Its interval sits wholly below the baseline and does not overlap the explanation, new-analysis or new-experiment cells. Disagreement with evidence is in between at 45% [32, 58] over 69 points. Agreeing that the measurement is weak and moving on went with unchanged scores.

- Raised: "To address this limitation, we have added two additional benchmarks to our evaluations of fine-tuned Gemma 2, Phi 3, and Llama 3.1 models that cover both more practical coding scenarios (DS-1000) as well as harder program synthesis problems (CodeContests)." (https://openreview.net/forum?id=AqfUa08PCH)
- Raised: "In response to your query, we have expanded our evaluation to include a variety of judges beyond GPT-4o." (https://openreview.net/forum?id=KZWaxtzIRx)
- Unchanged, concede and scope: "Yes, we don't claim that we have solved this problem completely, but we believe the results outperform VSD's results." (https://openreview.net/forum?id=FtyHMDQSlD)

## missing_experiment_or_ablation

The reviewer asks for an experiment or ablation the paper does not have (206 points, raised share 64% [56, 72], the highest of any type).

**Recommended:** run it. A new experiment has 64% [53, 73] over 132 points, which matches the type's own share. **Avoid:** no move in this type falls below the baseline. Deferring to future work has 68% [47, 89] over 19 points, and disagreeing or conceding together cover only 15 points, 10 of them raised (counted from blind_rows.jsonl). The data support running the experiment and show no penalty for an honest deferral when you cannot.

- Raised: "We conducted additional experiments to compare Impoola and Impala using our group-structured pruning and included them in Section 5.4 Ablations." (https://openreview.net/forum?id=LTdtyzPQoZ)
- Raised: "Following your suggestion, we try removing the convolution." (https://openreview.net/forum?id=E1ML0nEReb)
- Unchanged, arguing the ablation is unnecessary: "The proposed method consists of only two components: TUI and TUI-based CPAda." (https://openreview.net/forum?id=LGIhipNvCQ)

## limitation_or_scope

The reviewer says the method or results cover too narrow a setting, such as one dataset family, one task type or one schedule (189 points, raised share 52% [44, 61]).

**Recommended:** extend the scope with a new experiment (61% [43, 78], 33 points) or explain exactly where the method applies (68% [48, 86], 28 points). **Avoid:** deferring to future work, at 35% [14, 57] over 20 points, and disagreeing with evidence, at 38% [18, 58] over 24 points. All of these intervals overlap, so the ordering is suggestive. Conceding and narrowing the claim sits near the baseline at 53% [36, 71] over 38 points.

- Raised: "In brief, we have added new experiments with cosine, linear, and polynomial schedules in Appendix K." (https://openreview.net/forum?id=JY6P45sFDS)
- Raised: "As a short answer, when the underlying true SCM allows for identifiability of the exogenous variables." (https://openreview.net/forum?id=l11DZY5Nxu)
- Unchanged, deferral: "These are excellent suggestions, and we plan to explore these techniques in future work." (https://openreview.net/forum?id=nR2DHRxWS2)

## reproducibility_or_details

The reviewer cannot find a setting, a data split, a hardware detail or a procedure needed to rerun the work (178 points, raised share 54% [45, 64]).

**Recommended:** give the exact detail, with its numbers, in the answer itself. The two common moves cannot be told apart: explanation has 58% [45, 70] over 83 points and text revision 53% [39, 65] over 68. Answers that contained numbers reached 46 of 65 raised (71%), against 49 of 108 (45%) for answers without numbers (counted from blind_rows.jsonl over addressed points). **Avoid:** a general description that leaves the reviewer still unable to rerun the step.

- Raised: "We ensured no overlap by verifying that for each holo pocket in the test set, the PM-score against any holo pocket in the training set is less than 0.95." (https://openreview.net/forum?id=9qS3HzSDNv)
- Raised: "We recruited 20 independent raters for each of the two surveys (*ref. Line 449, Pg 9*)." (https://openreview.net/forum?id=cC3LxGZasH)
- Unchanged, no numbers: "The experiments were conducted on ETH Euler Clusters, which comprise multiple nodes." (https://openreview.net/forum?id=BfI0D1ci9r)

## theory_or_proof

The reviewer questions an assumption, a step in a proof, or what a theorem implies (169 points, raised share 53% [43, 63]).

**Recommended:** explain the step itself, starting from where the term or bound comes from. Explanation has 66% [51, 79] over 53 points, and text revision 58% [35, 77] over 33. **Avoid:** disagreeing with the reviewer, even with supporting citations, which has 37% [21, 56] over 43 points. The two intervals overlap only between 51 and 56, one of the clearer splits in the file.

- Raised: "The logarithmic factors come from the Chernoff bound, and would be essentially impossible to eliminate." (https://openreview.net/forum?id=RZwtbg3qYD)
- Raised: "In Remark 5.1 of the revised paper, we provide more explanation regarding the degree of nonconvexity defined in Definition 5.2." (https://openreview.net/forum?id=7liN6uHAQZ)
- Unchanged, disagreement: "Here too, we believe there may be a misunderstanding." (https://openreview.net/forum?id=m60n31iYMw)

## missing_baseline

The reviewer names a method the paper should have compared against (160 points, raised share 51% [42, 59]).

**Recommended:** run the named baseline and report the numbers. A new experiment has 65% [53, 76] over 77 points. **Avoid:** deferring the comparison, at 23% [0, 50] over 13 points, and declining it, at 33% [11, 57] without evidence over 15 points and 38% [18, 58] with evidence over 24 points. The new-experiment interval does not overlap the deferral interval, which makes this one of the two clearest splits in the file, although the deferral cell is small. Answers with numbers reached 51 of 77 raised (66%), against 30 of 80 (38%) without numbers (counted from blind_rows.jsonl over addressed points).

- Raised: "Following your suggestion, we added GNS as our baseline method and the detailed results are presented below." (https://openreview.net/forum?id=i1BTP8wFYM)
- Raised: "Following your suggestion, in addition to comparisons with PerSAM, Matcher, and Grounded-SAM, we also evaluate PerSense against C3Det [1], a specialized method for tiny object detection." (https://openreview.net/forum?id=caE5faFVT1)
- Unchanged, declining without evidence: "We understand your expectation for a comparison with more advanced hard negative sample mining algorithms." (https://openreview.net/forum?id=FfHGAAoSVJ)

## novelty

The reviewer says the method resembles prior work or combines known parts (156 points, raised share 49% [41, 58]).

**Recommended:** show the difference with a result, such as a head-to-head run against the prior method, or revise the paper to state the difference. A new experiment has 75% [44, 100] over 12 points and text revision 62% [33, 88] over 13. **Avoid:** an explanation that only asserts the difference, at 41% [24, 59] over 32 points, and disagreement without evidence, at 40% [22, 60] over 25 points. Disagreement with evidence sits at 44% [30, 59] over 52 points. Every interval overlaps and the two best cells are small, so the pattern is suggestive.

- Raised: "We start by comparing with the baselines suggested by the reviewer [1, 2, 3, 4, 5]." (https://openreview.net/forum?id=rMOhA1JNPo)
- Raised: "Unlike the approach in (Tano et al., 2020) which applies DMD predictions to all parameters, our proposed PDT introduces a masking strategy and selectively applies predictions only to those parameters that exhibit ‘good’ prediction performance, hence “differential” training." (https://openreview.net/forum?id=eVsSjNRuAp)
- Unchanged, asserting novelty: "While synthetic data generation and representation editing are well-established methods, **their combination as well as their use in alignment has not, to our knowledge, been explored**." (https://openreview.net/forum?id=8OcM1pTfHm)

## claim_overstated

The reviewer says a claim in the paper goes beyond what the results show, for example a small gain described as a large one (123 points, raised share 55% [45, 65]).

**Recommended:** bring numbers, either from a new run or by rewording the claim to match the numbers. No move in the stats table stands apart: text revision has 55% [35, 73] over 31 points, explanation 52% [30, 76] over 21, conceding and scoping 53% [27, 80] over 15. Counted from blind_rows.jsonl, new experiments reached 9 of 11 raised, and answers with numbers reached 25 of 36 raised (69%) against 39 of 81 (48%) without. **Avoid:** defending the original claim by pointing to results already in the paper. Disagreement with evidence has 47% [29, 66] over 30 points, which overlaps everything else, so this advice rests mainly on the numbers split.

- Raised: "We agree with your comment – we rephrased “competitive performance” to “second-best results”." (https://openreview.net/forum?id=tkqNDbukWW)
- Raised: "We were able to confirm our findings in additional experiments, showing the generalizability of our work." (https://openreview.net/forum?id=AZTdO6JJKt)
- Unchanged, defending with existing results: "We showed the importance of marginalization consistency with the results in Tables 1 and 2." (https://openreview.net/forum?id=ts1F3BVaDI)

## scalability_or_cost

The reviewer worries about runtime, memory or how the method behaves at a larger scale (117 points, raised share 62% [51, 71]).

**Recommended:** measure it. A new experiment, such as a runtime table or a larger-scale run, has 74% [59, 88] over 38 points, and its interval sits wholly above the baseline. A clear explanation has 70% [50, 89] over 20 points. **Avoid:** arguing that cost is not a problem, which has 50% [20, 80] over 16 points. That interval is wide and overlaps the others, so the case against disagreement is weak.

- Raised: "We present the running time comparisons of 1 epoch for each method on all dynamics systems." (https://openreview.net/forum?id=i1BTP8wFYM)
- Raised: "To address scalability concerns, we include an experiment with the LLaVA-Video dataset, which contains significantly more instances and richer temporal information." (https://openreview.net/forum?id=HEXtydywnE)
- Unchanged, arguing cost is fine: "In practice, for many benchmarks, the number of derived Pareto optimal policies is often smaller than the buffer size, meaning that storing them does not require excessive memory resources." (https://openreview.net/forum?id=fDGPIuCdGi)

## related_work

The reviewer says relevant prior work is missing, miscategorized or misdescribed (92 points, raised share 57% [46, 68]).

**Recommended:** add or fix the discussion in the paper and say where. Text revision has 61% [45, 76] over 46 points. **Avoid:** disputing the reviewer's reading of the literature, at 33% [8, 67] over 12 points. The disagreement cell is small and overlaps the revision cell, so the preference is suggestive.

- Raised: "In the updated manuscript, we refined the literature review related to MNO and FNO." (https://openreview.net/forum?id=Llh6CinTiy)
- Raised: "Following reviewer’s recommendation, we have added a category in the related work section for including “protein optimization in the latent space”." (https://openreview.net/forum?id=ua5MHdsbck)
- Unchanged, disputing: "We respectfully disagree with the assertion that we are ignoring others' related work." (https://openreview.net/forum?id=rwAEQWEqkX)
