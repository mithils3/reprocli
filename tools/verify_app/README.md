# Artifact Verification app

A lightweight, **static** web app for your team to manually verify the v4
extraction outputs paper-by-paper: each reviewer reads the model's verdict for
an artifact (code / dataset / weights / standard-dataset) and the score, does
their **own** Google / GitHub / Hugging Face search, and records agree /
disagree / unsure + a note. You get an admin **dashboard** of who did what,
where reviewers disagree with the model, and a live activity feed.

- **Frontend:** plain HTML/CSS/JS (no build step) → deploys to Vercel as static files.
- **Backend:** Supabase (free Postgres) — stores every verification + an activity log.
- **Auth:** name only (each reviewer types their name once). Your name unlocks the dashboard.
- **Traces:** the 220 MB conversation trace is split per-paper and served on demand from Supabase Storage (optional — the app works without it).

> **Setup & deployment instructions live in [`SETUP.md`](SETUP.md).**

```
tools/verify_app/
  build_data.py         # one-time: makes public/papers.json + splits traces
  fetch_arxiv_meta.py   # patches papers.json with real arXiv titles/authors/abstracts
  arxiv_meta.json       # cached arXiv metadata (build_data.py merges it on rebuild)
  supabase_schema.sql   # paste into Supabase SQL editor
  SETUP.md              # setup + Vercel deploy steps
  public/               # <-- this folder is the website you deploy
    index.html
    config.js           # the 4 values you edit
    app.js  styles.css
    papers.json         # generated (2.7 MB, ships with the site)
  traces_out/           # generated (49 MB, NOT committed; upload to Storage)
```

> **Why `fetch_arxiv_meta.py` exists:** titles scraped from the model traces were
> misaligned for ~25% of papers (wrong title shown next to the right claim). This
> script pulls the authoritative title, authors, year, and abstract from the arXiv
> API, keyed by arXiv id, and `build_data.py` re-merges the cache on every rebuild.

## How reviewers use it

1. Open the URL, type your name — you're **dropped straight into the first unlabelled paper**.
   The header shows the real arXiv title, authors, year, and the **abstract** so you know what to search for.
2. **Four artifact steps** — code / dataset / weights / standard-dataset. Each shows the model's verdict + evidence; **do your own search** with the shortcut buttons, then click **Agree / Disagree / Unsure**, optionally paste the link you found and a note. After you answer, the step spells out what your verdict means (e.g. "Your answer: code is available — NO").
   **Keyboard shortcuts:** `a` / `d` / `u` answer the first open step, `n` = save & next, `p` = previous (active when you're not typing in a field).
3. **Step 5 is the score — it is computed automatically** from your four verdicts using the project formula `(no code +2) + (no dataset & non-standard +3) + (no weights +1)`, and shown next to the model's score (✓ matches / ✗ differs). Reviewers never type a score.
4. **Save & next** moves you to the next paper in the queue. A paper turns green once all four steps are answered. Switching papers **auto-saves** your draft, and closing the tab with unsaved work warns you first.

### The queue (no double-work)

The default **To label** list is a shared work queue: **the moment any reviewer completes a paper it disappears from everyone's queue**, so people just keep grabbing the next unprocessed one. Everything updates **live**:

- A red **● live** marker + banner show when someone else is viewing a paper *right now* (Supabase Realtime presence).
- Green **✓N** / amber **⋯N** markers show how many *other* reviewers have completed / started a paper (names on hover).
- Other filters: **My in-progress** (resume your half-done ones), **Completed**, **Disagreements**, and **All** (see everything, including finished papers). Your work always reloads by name.

## Dashboard (admins only)

A **Dashboard** tab appears for names in `ADMIN_NAMES`:

- KPI cards: total papers, papers reviewed ≥1×, fully completed, # reviewers, # disagreements.
- Per-reviewer progress + last-active time.
- Live activity feed (realtime).
- Table of every disagreement with the model (which signal, their score, notes).
- **Export CSV** of all verifications.
