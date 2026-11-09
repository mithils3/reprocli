#!/usr/bin/env python3
"""Export rebuttal reply parts from replies.md to paste-ready files, with a readiness check."""
import argparse
import re
import sys
from pathlib import Path

MAX_CHARS = 5000
PART_RE = re.compile(r"^General reply \(one part, ([\d,]+) characters\)")
REPLY_RE = re.compile(r"^Reply to (\w+), part (\d+) of (\d+) \(([\d,]+) characters\)")
AUTHOR_RE = re.compile(r"[ ]*\[AUTHOR:[^\]]*\][ ]*")
SLOT_RE = re.compile(r"\[[^\[\]]*\](?!\()")
HEADING_RE = re.compile(r"^#{1,3} ")


def parse_parts(text):
    parts, current = [], None
    for lineno, line in enumerate(text.split("\n"), 1):
        if HEADING_RE.match(line):
            current = None
            m = PART_RE.match(line[4:])
            if m:
                current = {"stem": "general", "reviewer": "general",
                           "claimed": int(m.group(1).replace(",", "")), "lines": []}
            m = REPLY_RE.match(line[4:])
            if m:
                rev, n = m.group(1), m.group(2)
                current = {"stem": f"{rev}_{n}", "reviewer": rev,
                           "claimed": int(m.group(4).replace(",", "")), "lines": []}
            if current:
                parts.append(current)
        elif current is not None:
            current["lines"].append((lineno, line))
    return parts


def clean_body(lines):
    raw = "\n".join(line for _, line in lines)
    clean = AUTHOR_RE.sub(" ", raw)
    clean = re.sub(r"(?m)^[ ]+(?=\S)|[ ]+$", "", clean)
    return clean.strip() + "\n"


def bad_tables(clean):
    bad, block = [], []

    def check(block):
        expected = None
        for lineno, row in block:
            cells = len(row.strip().strip("|").split("|"))
            if expected is None:
                expected = cells
            elif cells != expected:
                bad.append((lineno, cells, expected))

    for lineno, line in enumerate(clean.split("\n"), 1):
        if line.lstrip().startswith("|"):
            block.append((lineno, line.strip()))
        else:
            if block:
                check(block)
            block = []
    if block:
        check(block)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input")
    ap.add_argument("--out", default="rebuttal/post/")
    ap.add_argument("--part", help="limit to one reviewer, e.g. T29u")
    args = ap.parse_args()

    parts = parse_parts(Path(args.input).read_text(encoding="utf-8"))
    if args.part:
        parts = [p for p in parts if p["reviewer"] == args.part]
    if not parts:
        print("no reply parts matched", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, not_ready = [], []
    for p in parts:
        body = clean_body(p["lines"])
        (out / f"{p['stem']}.md").write_text(body, encoding="utf-8")
        chars = len(body.strip())
        slots = []
        for lineno, text in enumerate(body.split("\n"), 1):
            for m in SLOT_RE.finditer(text):
                slots.append((lineno, m.group(0)))
        dashes = body.count("—")
        tables = bad_tables(body)
        ready = not slots and dashes == 0 and chars <= MAX_CHARS
        rows.append((p["stem"], chars, p["claimed"], chars - p["claimed"],
                     len(slots), dashes, len(tables), "READY" if ready else "NOT READY"))
        if not ready:
            not_ready.append((p["stem"], slots))
        for lineno, cells, expected in tables:
            print(f"  table row mismatch {p['stem']} line {lineno}: {cells} cells, header has {expected}")

    print(f"{'part':<10}{'chars':>7}{'heading':>9}{'diff':>6}{'slots':>7}{'emdash':>8}{'badtbl':>8}  status")
    for stem, chars, claimed, diff, ns, nd, nt, status in rows:
        print(f"{stem:<10}{chars:>7}{claimed:>9}{diff:>6}{ns:>7}{nd:>8}{nt:>8}  {status}")

    for stem, slots in not_ready:
        if slots:
            print(f"\nNOT READY {stem}: remaining slots")
            for lineno, text in slots:
                print(f"  line {lineno}: {text[:70]}")

    print(f"\nexported {len(parts)} file(s) to {out}")
    return 0 if all(r[-1] == "READY" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
