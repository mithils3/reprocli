#!/usr/bin/env python3
"""Render figure HTML to PDF at its own body size. Usage: build.py [name ...]"""
import re
import sys
import pathlib
from playwright.sync_api import sync_playwright

FIGS = pathlib.Path(__file__).parent


def main(names):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for n in names:
            page.goto((FIGS / f"{n}.html").as_uri())
            page.wait_for_timeout(400)
            # scrollHeight rounds down; a fractional body spills onto a second PDF page
            w, h = page.evaluate(
                "[document.body.scrollWidth, Math.ceil(document.body.getBoundingClientRect().height)]"
            )
            pdf = FIGS / f"{n}.pdf"
            page.pdf(
                path=str(pdf),
                width=f"{w}px",
                height=f"{h}px",
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            pages = max(int(c) for c in re.findall(rb"/Count (\d+)", pdf.read_bytes()))
            if pages != 1:
                sys.exit(f"{n}: PDF has {pages} pages, expected 1")
            page.screenshot(path=str(FIGS / f"{n}.png"), full_page=True, scale="css")
            print(f"{n} {w}x{h}")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(p.stem for p in FIGS.glob("*.html")))
