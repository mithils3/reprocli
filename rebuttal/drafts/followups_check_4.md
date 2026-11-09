# Fact-check of followups.md contradictions 11, 12, 13

Checked 2026-11-08. No file was edited and nothing on DeltaAI was changed.

## Item 11: repeat runs described as done

Verdict: CONFIRMED. The sacct check shows job 3540624 RUNNING and jobs 3540625 to 3540633 PENDING, so no repeat run has finished.

Sentences that state the runs as done:

- rebuttal/drafts/replies.md:25: "We also ran DeepSeek-V4-Flash twice more on 12 of those papers"
- rebuttal/drafts/replies.md:56: "we ran DeepSeek-V4-Flash, the best agent at Run, twice more on 12 papers"
- rebuttal/drafts/replies.md:228: "and we ran DeepSeek-V4-Flash twice more on 12 papers"

Smallest edit (each sentence, "ran" becomes "queued"):

- replies.md:25, old "We also ran DeepSeek-V4-Flash twice more" new "We also queued DeepSeek-V4-Flash twice more"
- replies.md:56, old "we ran DeepSeek-V4-Flash, the best agent at Run, twice more" new "we queued DeepSeek-V4-Flash, the best agent at Run, twice more"
- replies.md:228, old "and we ran DeepSeek-V4-Flash twice more" new "and we queued DeepSeek-V4-Flash twice more"

replies.md:50 ("DeepSeek-V4-Flash run twice more on 12 papers") is a plan line and needs no change. The bracketed slots at replies.md:56 and :228 and the "[We reran the other 20 cells ...]" slot are fine as written.

## Item 12: three unmatched log entries shown as reconciled

Verdict: PARTLY. The reply never uses the word "reconciled". Its table at replies.md:155 to 159 lists the three entries as a plain count, under a total of 45,861, with no unmatched label. The E5 files class them as unmatched.

- rebuttal/drafts/replies.md:159: "| Remaining budget within 0.0003 GPU-hours, cost equal | 3 |"
- rebuttal/results/e5/README.md:11: "Unmatched: 3 (see below)."
- rebuttal/results/e5/README.md:18: "2. Unmatched (value, 0.0002 to 0.0003 h, cost equal): `qwen3-retrain-2510.22123` trajectory.jsonl:24; `muse-run-2504.12397` trajectory.jsonl:52; `muse-run-2505.23305` trajectory.jsonl:18."

The other rows (100, 60, 25) are the explained class in E5 (185 in total), so they match the file. Only the three-entry row differs.

Smallest edit: replies.md:159, old "| Remaining budget within 0.0003 GPU-hours, cost equal | 3 |" new "| Unmatched: remaining budget within 0.0003 GPU-hours, cost equal | 3 |".

Author decision: whether the reply also says these three are unexplained. The sentence at replies.md:150 onward says "This check catches any edit", which the three open entries do not settle.

## Item 13: claim kinds

Verdict: CONFIRMED. The lockfile gives 62 point_estimate, 21 direction, 14 threshold, 1 range, 1 magnitude and 1 with no kind (match_bar_kind absent). Direction plus threshold is 35, not 38. The 38 in the replies is the count of all non-point claims.

Lockfile: /home/mithil/PyCharmProjects/reclaim/data/splits/eval_100.jsonl (md5 ab205529, as recorded in rebuttal/results/e6/README.md:3). The on-disk count is also in rebuttal/results/e6/summary.json lines 9 to 16 (lockfile_kinds).

Wrong sentences:

- rebuttal/drafts/replies.md:83: "Of the 100 claims, 62 are point estimates and 38 are tested by direction or by a threshold (for example "beats the strongest baseline"), which a tolerance does not affect."
- rebuttal/drafts/replies.md:182: "The other 38 are tested by direction or threshold."

Smallest edits:

- replies.md:83, old "62 are point estimates and 38 are tested by direction or by a threshold (for example "beats the strongest baseline"), which a tolerance does not affect." new "62 are point estimates, 35 are tested by direction or by a threshold (for example "beats the strongest baseline"), and 3 are a range, a magnitude or have no kind; a tolerance does not affect these 38."
- replies.md:182, old "The other 38 are tested by direction or threshold." new "The other 38 are 35 tested by direction or threshold, plus one range, one magnitude and one with no kind."

replies.md:115 and :195 ("38 without a number test", "38 others") are correct as written and need no change.
