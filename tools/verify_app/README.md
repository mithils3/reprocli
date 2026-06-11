# Artifact Verification app

A lightweight, **static** web app for your team to manually verify the
classifier outputs paper-by-paper (currently the **v5 200-paper audit pool**
from `python -m reprocli_vllm.select_pool` — see `notes/Methodology/Dataset Construction.md`): each reviewer reads the model's verdict for
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

## How reviewers use it (guided flow — no choices)

Reviewers **don't pick papers**: the queue feeds them one at a time. There is no
paper list / no filters for non-admins — just the current paper and one button.

1. Open the URL, type your name — you're **dropped straight into the next unlabelled paper**.
   The header shows the real arXiv title, authors, year, and the **abstract** so you know what to search for.
2. **Four steps, unlocked one at a time** — code / dataset / weights / standard-dataset.
   Only the current step is active (later ones show 🔒 until the one
   above is answered; answered steps stay editable). Each shows the model's verdict + evidence;
   **do your own search** with the shortcut buttons, then click **Agree / Disagree / Unsure**,
   optionally paste the link you found and a note. Answering auto-scrolls you to the next step.
   **Keyboard shortcuts:** `a` / `d` / `u` answer the current step, `n` = save & next, `p` = previous.
   (H100 compute bands are audited in code — `gpu_count × wallclock × multiplier` is recomputed
   and adjudicated at selection time — so reviewers don't confirm them by hand.)
3. **The score step is computed automatically** from your four artifact verdicts using the project formula `(no code +2) + (no dataset & non-standard +3) + (no weights +1)`, and shown next to the model's score (✓ matches / ✗ differs). Reviewers never type a score.
4. The footer has **one primary button: "Save & next paper →"**. It stays disabled
   ("Answer all 4 steps to continue (2/4)") until every step is answered, then turns green
   and pulses. Trying to advance early shakes the unanswered step. Small de-emphasized
   links cover the edge cases: **← previous** and **skip for now →** (logs the skip,
   keeps your draft). Switching papers **auto-saves** your draft, and closing the tab
   with unsaved work warns you first.

### The queue (no double-work)

The queue is shared: **the moment any reviewer completes a paper it disappears from everyone's queue**, so people just keep getting the next unprocessed one. Everything updates **live**:

- A red **● live** banner shows when someone else is viewing the same paper *right now* (Supabase Realtime presence).
- **Admins** additionally get the browsable sidebar with filters (**To label / My in-progress / Completed / Disagreements / All**), search, and per-paper ✓N / ⋯N reviewer markers. Your work always reloads by name.

## Telemetry

Every behavioural event is appended to the `activity` table; the `detail` column is a
**JSON string** so you can slice it in SQL or the CSV. Events:

| event | detail |
|---|---|
| `login` / `logout` / `session_end` | admin flag, user-agent / active seconds at exit |
| `paper_opened` / `paper_left` | queue size / **active seconds** (visibility-aware stopwatch) + steps answered |
| `verdict_set` | step, verdict, previous value, `via` click-or-keyboard, **seconds into the paper** |
| `search_click` / `link_click` | which search shortcut / header quick-link they used |
| `evidence_opened` / `context_opened` / `trace_opened` | did they look at the model's evidence before answering |
| `note_edited` / `found_url` | once per step per paper open |
| `saved` / `completed` | active seconds, steps answered, which signals they disagreed on, score match |
| `skipped` / `blocked_next` | bailed on a paper / tried Save & next before finishing |
| `tab_hidden` / `tab_visible` | when they leave to go search (time off-tab is *excluded* from active seconds) |

The "active seconds" stopwatch pauses while the tab is hidden, so time-per-paper
reflects actual attention, not an open background tab.

## Dashboard (admins only)

A **Dashboard** tab appears for names in `ADMIN_NAMES`:

- KPI cards: total papers, papers reviewed ≥1×, fully completed, # reviewers, # disagreements.
- Per-reviewer table: progress, **median active time per paper, search clicks, skips,
  blocked-next attempts**, last-active time.
- Live activity feed (realtime) with the telemetry detail inline.
- Table of every disagreement with the model (which signal, their score, notes).
- **Export CSV** of all verifications.
