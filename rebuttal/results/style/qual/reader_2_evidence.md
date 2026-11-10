# Reader 2: how evidence is presented and tied to the concern

Raised replies treat each result as bounded: they give its size in modest words, say what it does not cover, and state exactly what a cited paper found, so the reviewer can check every sentence against the numbers beside it. Unchanged replies more often attach a general verdict to numbers too small to carry it, promise or predict results they do not yet have, or point to a table without saying which way it came out. Running the exact experiment the reviewer asked for was common in both groups, so the difference lies in whether the prose claims only what the shown numbers support.

## 1. States the limit of its own evidence

- **Test**: Next to a result the author cites, do they name a specific limit on what it covers (a substitute setting, numbers taken from another paper, preliminary status, a proxy, an untested case) and leave it standing instead of arguing in the next sentence that it does not matter?
- **Counts**: yes in 6 of 10 raised, 2 of 10 unchanged.
- **Raised**: "However, we were unable to find pretrained vocoder models compatible with HuBERT-XL and had to rely on a publicly available release using the smaller HuBERT-base (95M)." (raised-088) "Note that the results of ContextGS are from their paper." (raised-129)
- **Unchanged**: "We agree that it limits the statistical power, but the sample size in our study was sufficient to obtain statistically significant results in many of our comparisons (the small p-values we presented in the paper)." (unchanged-110)
- **Why it might work**: when the authors draw the boundary themselves, the reviewer has less reason to suspect the rest is stretched.
- **Confound**: authors with strong results can afford to name limits, so this may mark a safe paper.

## 2. Cited evidence stated concretely

- **Test**: When the author uses another paper as evidence, do they state that paper's specific finding (its setting and result, a number, or a direct quote)?
- **Counts**: yes in 6 of 10 raised, 1 of 10 unchanged.
- **Raised**: "In Section 4.3 of [1], two models with the same capacity (ResNet-18) were trained on CIFAR-10, one with a standard last-layer size of $d=512$ and the other with a smaller $d=10$ but the same number of classes ($c=10$)." (raised-222) "Llama 7b/13b is among the top three models demonstrating the lowest JSR in response to harmful queries" (raised-214)
- **Unchanged**: "Notable and well-published examples include the papers [A], [B] and [C]." (unchanged-106)
- **Why it might work**: a concrete external finding is a free experiment the reviewer can verify, while a bare citation asks for trust.
- **Confound**: theory papers lean on citations more, and their reviewers may accept argument more readily.

## 3. Size words match the effect

- **Test**: Does the author describe at least one of their own results with a modest size word (marginal, minor, moderate, slight, comparable, roughly, closely aligns, respectably)?
- **Counts**: yes in 3 of 10 raised, 0 of 10 unchanged. The reverse, a strong word on a gap under 1% in the authors' own table, appears in 0 raised and 2 unchanged threads.
- **Raised**: "although the smaller models still perform respectably compared to the baselines" (raised-088) "PCA brings a marginal rate saving (2.2\%)" (raised-129)
- **Unchanged**: "These results, which we have finalized since the initial submission, demonstrate significant improvements in performance across the training epochs when applying our method." (unchanged-150, table shows 58.47 against 58.18)
- **Why it might work**: the reviewer reads the table first, and a word that disagrees with it costs credibility everywhere; the unchanged-150 reviewer answered "the VIT results on Imagenet-1k are not very promising".
- **Confound**: small gains push authors toward strong words, so the word may only mark a weak result.

## 4. Result shown, not promised

- **Test**: Does the author say a requested experiment is still running or will appear in a later version of this paper, or predict its outcome, in place of giving the result?
- **Counts**: yes in 1 of 10 raised, 3 of 10 unchanged.
- **Raised**: "We will include comparisons with such sparse reward-focused baselines in future revised versions to make our results more comprehensive." (raised-177, posted after the reviewer had already raised)
- **Unchanged**: "Based on the current training curve, our proposal is expected to largely improve self KD in this large-scale setting." (unchanged-150)
- **Why it might work**: a forecast sets a bar the delivered number is then judged against, and in unchanged-150 it fell short.
- **Confound**: expensive requests are harder both to finish and to satisfy.

## 5. Pointer says which way it came out

- **Test**: Is there a new result that the author mentions only by its location (table, figure, appendix) with no sentence in the thread saying what it showed?
- **Counts**: yes in 1 of 10 raised, 3 of 10 unchanged.
- **Raised**: the usual form is "We can see in Figure 21 that ICL persists for both datasets after millions of training steps." (raised-022)
- **Unchanged**: "We have added the quantitative ablations in Table 3 of the revised supplementary." (unchanged-081)
- **Why it might work**: a reviewer who must open the PDF to learn a result's direction often does not.
- **Confound**: such replies may be less engaged overall.

## 6. Corrections shown side by side

- **Test**: When the author reports an error in their own earlier numbers or answer, do they show the corrected output itself?
- **Counts**: yes in 2 of 10 raised, 0 of 10 unchanged (one unchanged thread admits an error without showing it).
- **Raised**: "the runtime spent on the rate estimation for coding triplanes was accidentally included, leading to our prolonged decoding time." followed by initial and revised rows (raised-129)
- **Unchanged**: "We are lucky that the conclusions still hold and the advantage of MVFL over VFL becomes even more obvious." with no numbers in the thread (unchanged-159)
- **Why it might work**: old and new numbers together read as care.
- **Confound**: three threads cannot rule out chance.

## Nothing here

- Running the exact comparison the reviewer named happened in both groups; unchanged-042 (constant-δ table) and unchanged-161 (with and without parameter sharing) did so and stayed.
- Stated protocol (hardware, runs averaged, settings held fixed): about 7 raised, 5 unchanged.
- Reporting an unfavourable number with a cause did not separate: raised-129 said "approximately twice the training time of HAC" and moved, while unchanged-161 said "the convergence rate is faster without parameter sharing" and stayed.
