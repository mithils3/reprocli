# Project Rules

- Keep hand-written source files under 300 lines; `*.txt` and `*.md` files may exceed 300 lines.
- Split code into focused modules before a file crosses that limit.
- Generated data, paper text dumps, binary artifacts, and model outputs are exempt.

# Writing the paper (`paper_latex/`)

- Before editing anything under `paper_latex/`, read `notes/Writing/ICLR Accepted-Paper Writing Lessons.md` — the example-driven playbook distilled from 25 accepted ICLR papers (companion to `notes/Writing/Paper Writing Guide.md` and the doc of record `notes/Writing/ReproBench Paper.md`).
- For the section you are drafting, pull that chapter's `→ ReproBench` moves and apply them; then run the note's TL;DR checklist against the draft before considering the section done.
- Keep the paper finding-first (the *availability cliff* and the *self-claim gap*), carry the one signature claimed-vs-audited pair unchanged across abstract/intro/results, and answer validity objections inline at the claim site rather than deferring them to Limitations.
