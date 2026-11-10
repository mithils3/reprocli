# Reader 1: conceding and holding ground

In the raised threads the authors make their own method the subject of the bad news and fence it in: they name the setting where it breaks, give cost as the reason for what they could not run, and name prior work that shares the gap. In the unchanged threads concessions are softer and rarer, refusals argue the request would not be informative, corrections place the error in the reviewer's reading, and after pushback the authors declare the matter closed and ask for the score. Raised authors make it cheap for the reviewer to have been right, while unchanged authors ask the reviewer to accept having been wrong.

## Features

### 1. Shortfall stated in plain words
- **Test**: Is there a sentence whose subject is the authors' method, experiment or code and whose main predicate is a negative outcome in a named setting (fails, breaks, is worse, is slower, is not enough, "except in X", has a bug)?
- **Counts**: yes in 10 of 10 raised, 3 of 10 unchanged.
- **Quotes**: raised-005: "We observe that WAM shows comparable robustness and breaks when the purification is heavy." raised-068: "We outperfom both across all datasets except in ogbg-arxiv at 0.5% and 1%." unchanged-010: "It can be observed that under lower latency conditions (about 1000 ms), our MonoAttn-Transducer shows no significant difference compared to CAAT." (CAAT is ahead at that latency in the authors' own table.) unchanged-162, after "marginal improvements": "We argue that the improvements are more significant than those on original CIFAR-10."
- **Why it might work**: a loss given with its boundary tells the reviewer that the rest of the table can be trusted.
- **Confound**: only authors whose method mostly wins can afford to name the exception.

### 2. Misreading fixed in the paper
- **Test**: When a reply says a point was already covered or was misunderstood, does that same reply report a change to the paper's text, figure or caption on that point?
- **Counts**: yes in 7 of 10 raised, 3 of 10 unchanged.
- **Quotes**: raised-174: "We realized these points were not explicit in the submission, so we added the following paragraph to the paper." raised-064, after correcting the reviewer's 5x5 reading: "We added the renders of 9x9 and 13x13 environments to the appendix and left a link to them in the caption of Figure 1." unchanged-112, with no change following: "These should also have been clearly revealed in the tables and captions." unchanged-010: "Sorry for the confusion. Actually we provide the LAAL and LAAL-CA results in Table 7, Appendix C."
- **Why it might work**: the edit moves the fault from the reviewer to the manuscript, so accepting the correction costs the reviewer nothing.
- **Confound**: this overlaps the known "pointer to revised text" count; the new part is the self-attribution.

### 3. Limitation shared with named peers
- **Test**: Does the author text admit a limitation of its own method in agreeing words and, in the same paragraph, name prior methods (or "all existing methods") that share it?
- **Counts**: yes in 4 of 10 raised, 0 of 10 unchanged.
- **Quotes**: raised-131: "Assumption 1 is very restrictive indeed, but it is roughly at the same level of simplification performed elsewhere in the community (e.g. Theorem 3.1 in Entezari et al.)." raised-146: "Our evaluation in the table below shows that all existing methods, including ours, face difficulties in such conditions." unchanged-162, using field practice to deny the problem instead: "We trying to make a fair comparison with these methods by following their settings." unchanged-069, on a theory request like 131's: "We demonstrate the theoretical insight of our proposed method as following:"
- **Why it might work**: field practice used to scope an admitted gap reads as calibration; the theory request led to a raise in 131, where the gap was admitted, and not in 069, where an informal paragraph was offered as meeting it.
- **Confound**: the move is only available when peers really do share the limitation.

### 4. Declining on cost grounds
- **Test**: Does the thread decline, or only partly fulfil, a request because of compute, time, difficulty or unavailable code (rather than calling the request unnecessary, weaker or off-scope)?
- **Counts**: yes in 5 of 10 raised, 2 of 10 unchanged.
- **Quotes**: raised-146: "The main reason is that LMD and MultiDiffusion are not available for the 768×768 resolution models, and it is not trivial to reimplement these methods on higher-resolution models due to their complexity." raised-174: "In summary, training and evaluating so many configurations already had a high computational cost, and running multiple repetitions was simply infeasible." unchanged-171: "Therefore, we do not plan to pursue this suggestion further." unchanged-112: "As for DDN [R3-10], it actually only considers $\ell_2$ attack, which is weaker than $\ell_\infty$ attack in general."
- **Why it might work**: a cost reason leaves the request valid in principle; a merit reason calls it a mistake.
- **Confound**: requests in raised threads may have been costlier, though in unchanged-112 the attack declined on merit was run a round later anyway.

### 5. Score asked after pushback
- **Test**: Before any score change, does the author text ask the reviewer to raise the score or assert that the reviewer's concerns are now addressed?
- **Counts**: yes in 1 of 10 raised, 3 of 10 unchanged.
- **Quotes**: raised-197: "We hope we have addressed all of your concerns. If any concerns remain, please do not hesitate to let us know." raised-146: "We hope these clarifications and additional experiments address the reviewer’s concerns." unchanged-135: "Given that this clarification resolves the final point of confusion, we kindly ask you to reconsider your score, as we have addressed all your concerns in full." unchanged-162: "If our responses above address all your concerns, could you kindly increase your score to a higher level."
- **Why it might work**: declaring the objection settled takes the decision from a reviewer who has just said it is not.
- **Confound**: unchanged threads had more rounds after a held score, so more occasions to ask; the one raised case (211, "your concerns shall be addressed") came with a fixed evaluation bug.

## Nothing here
- Reframing the contribution in answer to a criticism ("our main contribution is not X") appears equally often: 4 raised (005, 033, 131, 237) and 4 unchanged (010, 123, 171, 189).
- Bare refusals saying "future work" or "out of scope" with no substitute appear in 4 raised (033, 131, 174, 237) and 3 unchanged (095, 123, 171), so declining is not costly in itself; the reason matters more (feature 4).
- Future-tense promises ("we will add", "we will include") appear in 7 raised and 6 unchanged threads.
