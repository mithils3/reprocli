# Image-gen prompt: RECLAIM overview figure (Figure 1)

Target style reference: PaperCoder Figure 2. Intended replacement for
`harness_overview` as the one-diagram summary of the paper.

---

## PROMPT

Create a clean, flat **vector-style academic figure** for a machine learning
conference paper (ICLR two-column, full text width). Landscape, aspect ratio
16:9, very high resolution, pure white background, no border frame around the
whole image. The look is a friendly hand-drawn-infographic: rounded rectangles
with thin 1.5px medium-gray strokes, soft pastel fills, small doodle-style line
icons, and a light playful feel while staying publication-serious. No
photorealism, no 3D, no gradients, no heavy drop shadows, no glow, no textures.

**Color system.** White page. Card fills: pale warm yellow `#FDF3D0` for stage
1, near-black `#1E1E20` for stage 2, pale blue `#E4EDFB` for stage 3, pale green
`#E6F3E6` for the outcome strip, light gray `#F2F2F3` for the left rail and for
all icon trays. Strokes and body text charcoal `#2B2B2E`. Monospace code text
purple `#6B3FA0` and teal `#0F7B7B`. One accent red `#D93025` used only for
failure marks and for the two hard scoring rules. One accent green `#1E8E3E`
used only for the success check.

**Typography.** Headings and labels in a clean geometric sans-serif (Inter or
Nunito), bold for headings. All identifiers, field names, and values in a
monospace font (JetBrains Mono or Menlo). Render **every string below exactly as
written**, including underscores, punctuation, arrows, and capitalization.
Spelling accuracy matters more than decoration. Do not invent, translate,
paraphrase, or add any text that is not listed here.

### Overall layout

A narrow **left rail** occupying about 20% of the width, separated from the rest
by a single thin vertical gray rule. The remaining 80% on the right holds the
RECLAIM pipeline as three numbered stage groups: stage 1 spans the full width of
the right region on the top row, stages 2 and 3 sit side by side on the bottom
row (stage 2 about 45% of the right region, stage 3 about 55%), and a slim
outcome strip runs along the very bottom of the right region.

---

### LEFT RAIL — the naive setup

Header at the top of the rail, bold sans, black: `Self-report`

Below it, a light-gray rounded card containing, top to bottom:

1. A doodle icon of a stack of paper sheets, with the label `Paper` beside it.
2. A small white card with a thin border showing, in serif, centered, stacked:
   `SharpZO`, then a thin horizontal rule, then `EuroSAT, 16-shot` and
   `test accuracy 79.42%`.
3. A downward black arrow.
4. A small gray pill labeled `Agent`.
5. A downward black arrow.
6. A white card with a thin border, monospace, left aligned:
   `report.json`, then `agent_assessment:` and on the next line, indented,
   `"reproduced"`, then `observed_value: 79.42`.
   A red circled ✗ badge overlaps the top-right corner of this card.
7. Two soft-yellow rounded callout pills stacked below the card, bold black
   text: `Number echoed from the paper!` and `No execution evidence!`

---

### RIGHT REGION — header

Top-left of the right region: a cute hand-drawn doodle mascot of a single paper
document sheet holding a large magnifying glass over a small printed number, with
a tiny GPU card doodle tucked beside it. To its right, in large bold rounded
sans-serif: `RECLAIM`

---

### STAGE 1 — top row, full width of the right region

A large light-gray rounded container. Centered at its top edge, straddling the
border, a white pill with a black outline and bold black text: `1. Construction`

Inside, three pale-yellow rounded cards left to right, equal width, each with a
small line icon and a bold heading at its top, and a white inner card holding the
body text.

**Card 1.1** — icon: a document with a pin. Heading: `1.1 Match Target`
White inner card, monospace, left aligned, one item per line:

```
claim:  zeroth-order prompt tuning
        beats the baseline
metric: test accuracy
value:  79.42
scope:  EuroSAT test set
bar:    within tolerance
```

Then a red monospace line at the bottom of the inner card:
`config withheld from the agent`

**Card 1.2** — icon: a small checklist with a magnifying glass. Heading:
`1.2 Availability Audit`
White inner card with four rows, each a checkbox and a monospace label:

```
[x] code
[x] data
[ ] weights
[x] standard benchmark
```

A small gray stamp badge to the right of the rows reading `tool-verified`.
Below the rows, a horizontal three-step ladder of small rounded chips, connected
left to right by a thin gray arrow: `Run` then `Retrain` then `Reimplement`.
Under the arrow, in small gray italic sans: `more for the agent to rebuild`

**Card 1.3** — icon: a funnel. Heading: `1.3 Cap and Select`
White inner card holding a vertical funnel of five stacked bars, each narrower
than the one above it, each labeled in monospace on its right:

```
3,414 NeurIPS 2025 submissions
1,000 sampled
687 verified
620 eligible
200 audit pool
100 released
```

Two small gray tags pinned to the funnel's side, at the level of the third and
fifth bars: `<= 96 H100-h` and `human audit`

Thin dashed gray arrows run from the top of the stage 1 container down into each
of the three cards, and short gray icon trays sit above each card showing the
inputs accumulating: above 1.1 a paper icon; above 1.2 a paper icon plus a link
icon; above 1.3 a paper icon plus a link icon plus a GPU icon.

---

### STAGE 2 — bottom row, left

A light-gray rounded container. Centered at its top edge, a white pill with a
black outline and bold black text: `2. Run`

Inside, one large near-black rounded card with white text. At its top, bold
white: `ReAct tool loop`, and to the right in smaller gray: `any chat model, tools-only`

Below, a small-caps gray section label: `WORKSPACE - CPU NODE`, and under it a
vertical list of dark rounded pills with white monospace labels, each followed by
a short gray sans gloss on the same line:

```
workspace_bash    cwd-confined shell
write_file / edit_file    author code and configs
update_plan    running checklist
fetch_url    public URLs only
```

Then a second small-caps gray section label: `CLUSTER - SLURM`, and under it:

```
list_partitions    node pools via sinfo
run_gpu    the only path to a GPU; wall clock metered
           against the H100-h grant
```

The `run_gpu` pill is outlined in accent red to mark it as the metered tool.

At the bottom of the dark card, a thin gray monospace footer line:
`~500 GB scratch - round and H100-h budgets harness-enforced`

---

### STAGE 3 — bottom row, right

A light-gray rounded container. Centered at its top edge, a white pill with a
black outline and bold black text: `3. Audit`

Inside, two pale-blue rounded cards side by side.

**Left card** — icon: a folder. Heading: `report.json + evidence/`
White inner card, monospace, left aligned:

```
paper_id, claim, what_ran, scoring_command
measurements[] {metric, observed_value,
  reference_value, scope, evidence}
agent_assessment in {reproduced, partial,
  not_reproduced, could_not_run}
```

Below it a small gray sub-card with a folder icon:
`evidence/  REPORT.md - commands.log - plan.md - run stdout`

**Right card** — icon: a lightning bolt inside a shield. Heading:
`Provenance auditor`
Small gray line under the heading: `Claude Sonnet 5, pinned; rubric frozen`
White inner card with three short bullet lines in sans:

```
traces every number to the execution that produced it
checks protocol, split, and scale against the pinned config
recomputes metrics from the run's raw outputs
```

Below, a horizontal score ruler: a thin bar segmented from `0` on the left to
`10` on the right with tick labels, and verdict chips sitting under their
segments, left to right:
`disqualified`, `unverifiable`, `not_reproduced`, `blocked`, `partial`,
`reproduced`. The `disqualified` chip is filled accent red, the `reproduced`
chip is filled accent green, the rest are light gray.

Under the ruler, two short red monospace rules on their own lines:

```
high-severity flag  ->  score 0
genuine artifact wall  ->  capped at 3
```

---

### OUTCOME STRIP — bottom of the right region

A slim pale-green rounded band spanning the full width of the right region,
split into two halves by a thin vertical gray rule.

**Left half.** Bold sans heading: `Availability cliff`. Beside it a tiny bar
chart of three descending bars with the x-axis labels `Run`, `Retrain`,
`Reimplement` and the y-axis label `reproduction rate`. **Draw no numbers on or
near the bars and no y-axis tick values.**

**Right half.** Bold sans heading: `Self-claim gap`. Beside it a tiny bar chart
of exactly two bars, a tall one labeled `claimed` and a much shorter one labeled
`audited`, with a bracket between their tops labeled `gap`. **Draw no numbers on
or near the bars and no y-axis tick values.**

A green circled ✓ badge sits at the far right end of the strip, visually
answering the red ✗ badge in the left rail.

---

### Connectors

Solid black arrows carry the main flow: from the stage 1 container down and right
into stage 2, and from stage 2 right into stage 3, and from stage 3 down into the
outcome strip. Thin dashed gray arrows carry the secondary flow: from the left
rail's paper card across the vertical rule into stage 1, and from stage 1's card
1.1 down into stage 3's auditor card. Arrows must not cross any text.

### Hard constraints

Every card and every label must be fully legible at 100% zoom. Nothing may
overflow or clip its container. No lorem ipsum, no placeholder squiggles standing
in for words, no repeated or duplicated labels, no extra panels, no caption text
under the figure, no figure number, no title bar, no watermark, no signature, no
UI chrome, no browser window, no photographic elements, no people, no cartoon
faces on the mascot beyond simple line features.

---

## NEGATIVE PROMPT

photorealistic, 3D render, isometric, glossy, gradient mesh, neon, dark mode
background, textured paper, watercolor, sketchy crosshatching, blurry text,
garbled text, misspelled labels, lorem ipsum, squiggle placeholder text,
duplicated panels, overlapping text, clipped text, cramped margins, drop shadows,
bevels, stock-photo icons, corporate clipart, human figures, faces, logos,
watermark, signature, caption, figure number, page number, border frame,
screenshot, browser chrome, numeric values on the outcome bar charts

---

## SHORT VARIANT

For models that truncate long prompts, use this and expect to regenerate panels
separately.

> Flat vector academic figure for an ML paper, 16:9, white background, rounded
> rectangle cards with thin gray strokes, pastel fills, doodle line icons, sans
> headings and monospace code labels. Left narrow rail titled `Self-report`: a
> paper icon, an `Agent` pill, and a `report.json` card claiming
> `agent_assessment: "reproduced"` with a red ✗ and two yellow callouts
> `Number echoed from the paper!` and `No execution evidence!`. Right side titled
> `RECLAIM` with a doodle of a paper sheet holding a magnifying glass over a
> number, laid out as three numbered stages in white outlined pills:
> `1. Construction` (three pale-yellow cards: `1.1 Match Target` with
> metric/value/scope and a red `config withheld from the agent`;
> `1.2 Availability Audit` with checkboxes for code, data, weights, standard
> benchmark and a `Run -> Retrain -> Reimplement` ladder; `1.3 Cap and Select`
> with a funnel 3,414 to 1,000 to 687 to 620 to 200 to 100 and tags
> `<= 96 H100-h` and `human audit`), `2. Run` (one near-black card titled
> `ReAct tool loop` listing tool pills `workspace_bash`, `write_file / edit_file`,
> `update_plan`, `fetch_url`, `list_partitions`, and a red-outlined `run_gpu`
> marked as the only metered path to a GPU), and `3. Audit` (two pale-blue cards:
> a `report.json + evidence/` schema card, and a `Provenance auditor` card with a
> 0 to 10 score ruler whose chips read disqualified, unverifiable,
> not_reproduced, blocked, partial, reproduced, plus red rules
> `high-severity flag -> score 0` and `genuine artifact wall -> capped at 3`).
> A pale-green bottom strip shows two tiny unlabeled-value bar charts,
> `Availability cliff` with three descending bars Run, Retrain, Reimplement, and
> `Self-claim gap` with a tall `claimed` bar next to a short `audited` bar, ending
> in a green ✓. Render all text exactly as written.

---

## NOTES

- The outcome-strip bar charts deliberately carry **no numeric values**. The
  reproduction rates and the claimed-vs-audited pair are not frozen yet, and the
  paper still writes them as `X`. Add the numbers only when the sweeps that back
  them are final.
- The construction numbers (3,414 / 1,000 / 687 / 620 / 200 / 100, the 96 H100-h
  cap) and the SharpZO match target match Section 3 of
  `iclr2027_conference.tex` as of this writing. Re-check them before shipping.
