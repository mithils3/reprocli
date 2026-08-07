---
name: write-daily-note
description: Write today's daily journal paragraph ("what I did today", "daily note", "## What I did") and save it to the Obsidian vault's Daily/ folder. Reconstructs the day from BOTH the repo git log and the notes-vault git log, then writes one honest paragraph in house style. Use when asked to "write what I did today", "daily paragraph", "update my daily note", or "log today".
---

# write-daily-note

The daily journal is one paragraph a day under a `## What I did` heading, ending
with `#daily`. It lives in the **Obsidian vault, not this repo**: the repo's
`notes` symlink points into the vault, and the notes sit at
`<vault-root>/Daily/YYYY-MM-DD.md`. A day's work spans **both** trees — code
committed here, and writing/analysis/figures in the vault (which auto-commits
hourly as `vault backup: ...`). The repo git log alone misses half the day.

Paths below are relative to the repo root (`<unit>/`).

## Run (agent path) — do this

1. **Gather the day's material** with the driver (default = today; pass a date
   for backfill):

   ```bash
   .claude/skills/write-daily-note/gather.sh            # today
   .claude/skills/write-daily-note/gather.sh 2026-07-16 # a specific day
   ```

   It prints, in order: the resolved paths + **TARGET FILE** to write, repo
   commits for the day, repo uncommitted changes, vault backup commits, the
   deduped list of vault files touched, vault uncommitted changes, the day's
   `TODO List.md` additions, the **most recent prior daily note as a format
   reference**, and a NEXT STEPS reminder.

2. **Write the paragraph.** Read the gathered material, then compose one tight
   `## What I did` paragraph (unless the user asks for more/less). House style,
   matching the format-reference note the driver printed:
   - plain declarative sentences ("Closed out X", "Wrote Y", "Most of the hours went to Z");
   - name the concrete artifacts — sweep IDs, file names, quant/serve flags, the actual numbers;
   - split the day into its real halves (e.g. morning analysis / afternoon serving) inside the one paragraph;
   - be honest about dead ends and reverts — they are the interesting part.

3. **Save with the Write tool** to the exact `TARGET FILE` path the driver
   printed (e.g. `/mnt/c/Users/.../Obsidian Vault/Daily/2026-07-21.md`). Keep the
   `## What I did` heading, an optional `## Connections` block of `[[wikilinks]]`
   to the notes you touched, and a trailing `#daily`.
   - If **TARGET EXISTS** says yes, Read the file first and extend it — don't clobber.

## Gotchas

- **The note is NOT in this repo.** Never write it under `notes/…` in the repo
  tree — that's the *project* subfolder of the vault. Daily notes live at the
  vault **root**'s `Daily/`, which the driver resolves via
  `git -C "$(readlink -f notes)" rev-parse --show-toplevel`.
- **Never `git add` in the vault.** The vault is its own git repo with hourly
  auto-backup; a bare `git add`/`git add -A` there stages the *entire* Obsidian
  vault. Just Write the file and stop — the next hourly backup commits it. (This
  repo's "commit + push every change" rule is for the *repo*, not the vault.)
- **Vault path has a space** (`.../OneDrive/Obsidian Vault/...`). Always quote it.
- **The vault half is where the writing/figures live.** If you only report repo
  commits you'll miss the analysis, LaTeX, and TODO progress — the driver's
  "VAULT files touched" and "TODO List additions" sections are half the story.
- **Finished-but-uncommitted work counts.** The driver prints repo + vault
  working-tree status so an ABANDONED-banner tweak or an unstaged figure still
  makes the note.

## Troubleshooting

- **`gather.sh: command not found` / permission denied** — run it with an
  explicit path: `bash .claude/skills/write-daily-note/gather.sh` (it's already
  `chmod +x`, but `bash …` always works).
- **Empty repo/vault sections** — expected on a quiet day; the driver still
  exits 0 and prints every section header. Cross-check the TODO additions and
  the prior note before concluding "nothing happened".
- **`date: invalid date`** — the driver uses GNU `date -d` (Linux). Pass the
  date as `YYYY-MM-DD`.
