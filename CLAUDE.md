# Project Rules

- File size is judged by cohesion, not a fixed cap: a hand-written source file should map to one clear responsibility. Up to ~500 lines is fine; up to ~800 is acceptable when the file is one coherent concern.
- Split a file only when it mixes concerns, and do not merge unrelated concerns just to cut file count. Prefer fewer files that each own one responsibility over many fragments.
- `*.txt`, `*.md`, LaTeX (`*.tex`, `*.bib`), generated data, paper text dumps, binary artifacts, and model outputs are exempt from any size guidance.

# Writing the paper (`paper_latex/`)

- Before editing anything under `paper_latex/`, read `notes/Writing/ICLR Accepted-Paper Writing Lessons.md` — the example-driven playbook distilled from 25 accepted ICLR papers (companion to `notes/Writing/Paper Writing Guide.md` and the doc of record `notes/Writing/ReproBench Paper.md`).
- For the section you are drafting, pull that chapter's `→ ReproBench` moves and apply them; then run the note's TL;DR checklist against the draft before considering the section done.
- Keep the paper finding-first (the *availability cliff* and the *self-claim gap*), carry the one signature claimed-vs-audited pair unchanged across abstract/intro/results, and answer validity objections inline at the claim site rather than deferring them to Limitations.
