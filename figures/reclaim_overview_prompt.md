# Image-gen prompt: RECLAIM overview figure

One diagram that summarizes the benchmark: construction, task, run, audit, and the
two quantities it measures. Style register is the modern ML technical-report system
diagram (airy, borderless tinted panels, desaturated palette), not a boxed
flowchart and not a cute infographic.

---

## PROMPT

A wide landscape technical system diagram for a machine learning research paper,
aspect ratio 2:1, very high resolution, pure white background, no outer frame, no
caption, no figure number.

**Visual register.** Modern LLM technical-report figure: airy, editorial, and
restrained. Panels are defined by **soft tinted fills with no visible borders**,
generous internal padding, and 14px corner radii. Whitespace does the separating.
Flat 2D vector rendering only. No 3D, no isometric, no gradients, no drop shadows,
no glow, no textures, no skeuomorphism, no rounded speech bubbles, no doodles, no
mascot, no clipart, no dark background.

**Palette.** Page white `#FFFFFF`. Ink `#0F172A` for headings, slate `#475569` for
body text, light slate `#94A3B8` for arrows and secondary labels. Panel tints, each
paired with its own accent used only for that panel's heading, glyph, and rules:
indigo accent `#4C5FD5` on tint `#EEF0FC`; teal accent `#17807A` on tint `#E6F2F1`;
amber accent `#B8791F` on tint `#FBF1E0`; violet accent `#7A4FD5` on tint `#F1ECFD`.
A single rose `#B4453F` reserved for hard scoring rules. Colors stay desaturated and
low-contrast against white; nothing neon, nothing saturated.

**Typography.** A clean grotesque sans-serif throughout (Inter or Helvetica Neue).
Panel headings bold 1.5x body size in the panel's accent color. Section sublabels in
small uppercase with wide letterspacing, light slate. All identifiers, field names,
and values in a monospace face (IBM Plex Mono). Body text left-aligned and generously
line-spaced. **Render every string below exactly as written**, including
underscores, arrows, and capitalization. Add no text that is not listed.

**Icons.** Minimal geometric line glyphs, 1.5px uniform stroke, single accent color,
no fills, one small glyph per panel heading only.

### Layout

Four tinted panels in a single row across the top three quarters of the canvas,
equal height, separated by whitespace and joined by thin light-slate arrows with
small solid triangular heads. Below them, a full-width band split into two tiles.
Nothing overlaps; arrows never cross text.

---

**PANEL 1 — indigo tint.** Glyph: a funnel. Sublabel `STAGE 1`. Heading:
`Construction`

A vertical funnel of six horizontal bars in indigo, each narrower than the one
above, each with its monospace count on the left and its sans label to the right:

```
3,414   NeurIPS 2025 submissions
1,000   sampled
  687   verified
  620   eligible
  200   audit pool
  100   benchmark
```

Between consecutive bars, small light-slate italic gate labels:
`agent classifier, artifact signals checked by tool call`, then
`empirical and unblocked`, then `<= 96 H100-h, stratified`, then `human audit`.

Under the funnel, a horizontal row of three indigo-outlined pills connected left to
right by a thin arrow, each with a small slate sublabel beneath it:

```
Run           execute or evaluate
Retrain       weights withheld
Reimplement   code withheld
```

A small slate caption under the arrow: `artifact availability`

---

**PANEL 2 — teal tint.** Glyph: a target with a pin. Sublabel `STAGE 2`. Heading:
`Task`

Three input rows at the top, each a small line glyph plus a sans label:
`paper LaTeX source`, `OpenReview supplement`, `verified artifact links`.

Below them a white inset block, monospace, aligned in two columns:

```
metric   test accuracy
value    79.42
scope    EuroSAT test set
bar      within tolerance
```

Directly under the block, one rose monospace line: `configuration withheld`
Under that, a slate sans line: `the agent designs the experiment itself`

---

**PANEL 3 — amber tint.** Glyph: a terminal prompt. Sublabel `STAGE 3`. Heading:
`Run`

Under the heading, a slate line: `ReAct tool loop, any chat model, tools only`

A small circular loop arrow sits to the right of that line to signal iteration.

Sublabel `WORKSPACE, CPU`, then four monospace pills laid out compactly:

```
workspace_bash    write_file / edit_file
update_plan       fetch_url
```

Sublabel `CLUSTER, SLURM`, then two monospace pills:

```
list_partitions
run_gpu
```

The `run_gpu` pill is outlined in rose. Beside it, a short slate sans gloss on two
lines: `the only path to a GPU, wall clock metered` / `against the run's H100-h grant`

At the bottom of the panel, a slate footer line:
`~500 GB scratch, round and compute budgets enforced by the harness`

To the right edge of the panel, a small white inset tag in monospace:
`report.json + evidence/`

---

**PANEL 4 — violet tint.** Glyph: a magnifying glass over a document. Sublabel
`STAGE 4`. Heading: `Audit`

Slate line under the heading: `one pinned auditor, rubric frozen before grading`

Three short sans bullets:

```
traces every number to the execution that produced it
checks protocol, split, and scale against the pinned configuration
recomputes metrics from the run's raw outputs
```

Below, a horizontal score ruler: a slim rounded bar with eleven tick marks labeled
`0` through `10` in monospace, shaded from very light violet at the left to full
violet at the right. Verdict labels sit under their segments in small monospace:

```
0  disqualified
1  unverifiable
2  not_reproduced
3  blocked
4-5  not_reproduced
6-7  partial
8-10  reproduced
```

Beneath the ruler, two rose monospace rules on separate lines:

```
high-severity flag  ->  0
genuine artifact wall  ->  capped at 3
```

---

**BOTTOM BAND — very light slate tint `#F6F7F9`, full width, split into two tiles
by whitespace.** Small uppercase letterspaced label above the band:
`WHAT RECLAIM MEASURES`

Left tile. Bold ink heading: `Availability cliff`. Beneath it, one slate sans line:
`reproduction rate across Run, Retrain, and Reimplement`. To its right, a schematic
of three descending indigo bars labeled `Run`, `Retrain`, `Reimplement` on the
x-axis. **Draw no numbers on the bars, no y-axis values, and no gridlines.**

Right tile. Bold ink heading: `Self-claim gap`. Beneath it, one slate sans line:
`runs that claim reproduced against runs the audit confirms`. To its right, a
schematic of two bars, a tall one labeled `claimed` and a short one labeled
`audited`, with a thin bracket between their tops labeled `gap`. **Draw no numbers
on the bars, no y-axis values, and no gridlines.**

---

### Hard constraints

Every label legible at 100% zoom. Nothing clipped, nothing overflowing its panel,
no text touching a panel edge. Consistent left alignment inside each panel.
Consistent panel heights. No placeholder squiggles standing in for words, no
duplicated labels, no invented tool names, no extra panels.

---

## NEGATIVE PROMPT

photorealistic, 3D, isometric, glossy, gradient, neon, saturated, dark background,
heavy borders, thick outlines, drop shadow, bevel, texture, watercolor, sketchy,
hand-drawn, doodle, cartoon, mascot, emoji, clipart, stock icons, human figures,
faces, logo, watermark, signature, caption text, figure number, page number, border
frame, browser window, screenshot, UI chrome, garbled text, misspelled labels, lorem
ipsum, squiggle placeholder text, overlapping text, clipped text, cramped spacing,
numeric values on the bottom bar charts, gridlines

---

## SHORT VARIANT

For models that truncate. Expect to regenerate panels separately.

> Wide flat vector system diagram for an ML paper, 2:1, white background, four
> borderless soft-tinted rounded panels in a row joined by thin gray arrows, airy
> modern tech-report style, desaturated indigo / teal / amber / violet tints, Inter
> headings and IBM Plex Mono identifiers, minimal 1.5px line glyphs.
> Panel 1 `Construction`, indigo, a six-bar funnel reading 3,414 NeurIPS 2025
> submissions, 1,000 sampled, 687 verified, 620 eligible, 200 audit pool, 100
> benchmark, with gate notes `<= 96 H100-h, stratified` and `human audit`, and a
> pill row `Run` / `Retrain` / `Reimplement` under the label `artifact availability`.
> Panel 2 `Task`, teal, inputs `paper LaTeX source`, `OpenReview supplement`,
> `verified artifact links`, and a monospace block `metric test accuracy`,
> `value 79.42`, `scope EuroSAT test set`, `bar within tolerance`, with a rose line
> `configuration withheld`.
> Panel 3 `Run`, amber, `ReAct tool loop` with a small loop arrow and monospace tool
> pills `workspace_bash`, `write_file / edit_file`, `update_plan`, `fetch_url`,
> `list_partitions`, and a rose-outlined `run_gpu` glossed as the only metered path
> to a GPU, ending in a tag `report.json + evidence/`.
> Panel 4 `Audit`, violet, a pinned auditor with a 0 to 10 score ruler whose labels
> read disqualified, unverifiable, not_reproduced, blocked, partial, reproduced, and
> two rose rules `high-severity flag -> 0` and `genuine artifact wall -> capped at 3`.
> A light bottom band `WHAT RECLAIM MEASURES` holds two schematic charts with no
> numeric values: `Availability cliff` as three descending bars Run, Retrain,
> Reimplement, and `Self-claim gap` as a tall `claimed` bar beside a short `audited`
> bar. Render all text exactly as written.

---

## NOTES

- The bottom-band charts carry **no numbers**. The reproduction rates and the
  claimed-vs-audited pair are not frozen; the paper still writes them as `X`.
- Construction counts and the SharpZO match target track Section 3 of
  `iclr2027_conference.tex`. Re-check before shipping.
