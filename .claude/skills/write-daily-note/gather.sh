#!/usr/bin/env bash
# gather.sh — collect the raw material for a daily "What I did" note.
#
# The daily journal lives in the Obsidian vault (NOT in this repo): the repo's
# `notes` symlink points into the vault, and daily notes sit at <vault-root>/Daily/.
# A day's work spans BOTH trees — code in this repo, and writing/figures/analysis
# in the vault (which auto-commits hourly as "vault backup: ..."). This script
# reconstructs the day from both so the agent can write one honest paragraph.
#
# Usage:  gather.sh [YYYY-MM-DD]     (default: today, GNU `date`)
# Output: labeled sections on stdout. Read them, write the paragraph, then save
#         to the path printed under "TARGET FILE". Do NOT git-add the vault.
set -euo pipefail

# Skill dir is <repo>/.claude/skills/write-daily-note ; repo root is 3 levels up.
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"

DATE="${1:-$(date +%F)}"
NEXT="$(date -d "$DATE +1 day" +%F)"
SINCE="$DATE 00:00"
UNTIL="$NEXT 00:00"

VAULT="$(readlink -f "$REPO/notes")"                       # .../Projects/Summer Internship
VROOT="$(git -C "$VAULT" rev-parse --show-toplevel)"       # Obsidian vault root
DAILY="$VROOT/Daily"
TARGET="$DAILY/$DATE.md"

# Vault paths of interest / noise to drop from the file lists.
PROJ_REL="Projects/Summer Internship"
NOISE='\.obsidian/|\.smart-env/|workspace\.json|\.trash/'

hr() { printf '\n===== %s =====\n' "$1"; }

printf 'DATE          %s\n' "$DATE"
printf 'REPO          %s\n' "$REPO"
printf 'VAULT PROJECT %s\n' "$VAULT"
printf 'VAULT ROOT    %s\n' "$VROOT"
printf 'TARGET FILE   %s\n' "$TARGET"
if [ -e "$TARGET" ]; then
  printf 'TARGET EXISTS yes — you are UPDATING an existing note (read it first)\n'
else
  printf 'TARGET EXISTS no  — you are creating a new note\n'
fi

hr "REPO commits ($DATE, all branches, oldest first)"
git -C "$REPO" log --all --since="$SINCE" --until="$UNTIL" --reverse \
    --pretty=format:'%h %ad  %s' --date=format:'%H:%M' 2>/dev/null || true
echo

hr "REPO uncommitted (working tree — finished work may not be committed yet)"
git -C "$REPO" status --short 2>/dev/null | head -40 || true

hr "VAULT commits ($DATE — hourly 'vault backup' auto-commits)"
git -C "$VROOT" log --since="$SINCE" --until="$UNTIL" --reverse \
    --pretty=format:'%h %ad  %s' --date=format:'%H:%M' 2>/dev/null || true
echo

hr "VAULT files touched ($DATE, deduped, noise filtered)"
git -C "$VROOT" log --since="$SINCE" --until="$UNTIL" --name-only --pretty=format: 2>/dev/null \
  | grep -v '^$' | grep -vE "$NOISE" | sort -u || true

hr "VAULT uncommitted (working tree, noise filtered)"
git -C "$VROOT" status --short 2>/dev/null | grep -vE "$NOISE" | head -40 || true

hr "TODO List additions ($DATE — what got planned / ticked off)"
git -C "$VROOT" log --since="$SINCE" --until="$UNTIL" -p -- "$PROJ_REL/TODO List.md" 2>/dev/null \
  | grep -E '^\+' | grep -v '^+++' | sed 's/^+/  /' | head -40 || true

# Most recent EXISTING daily note strictly before DATE — the house-style template.
PREV="$(ls "$DAILY" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$' \
        | sort | awk -v d="$DATE.md" '$0<d' | tail -1)"
hr "FORMAT REFERENCE — most recent prior daily note ($PREV)"
if [ -n "${PREV:-}" ]; then
  cat "$DAILY/$PREV"
else
  echo '(none found — use: "## What I did" heading, one honest paragraph, then #daily)'
fi

hr "NEXT STEPS"
cat <<EOF
1. Read the sections above. The repo half = code; the vault half = writing/analysis/figures.
2. Write ONE tight "## What I did" paragraph (unless the user asks for more), house style
   above: plain declaratives, name the concrete artifacts/sweeps/numbers, honest.
3. Save with the Write tool to:  $TARGET
   - keep the "## What I did" heading, optional "## Connections" wikilinks, trailing #daily
   - if TARGET already exists, Read it and extend rather than clobber.
4. Do NOT run git in the vault (never 'git add' there — it auto-backs-up hourly and a bare
   add stages the whole vault). Just write the file.
EOF
