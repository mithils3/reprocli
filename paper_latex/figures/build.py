#!/usr/bin/env python3
"""Render figure HTML to PDF at its own body size. Usage: build.py [name ...]"""
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
            w, h = page.evaluate("[document.body.scrollWidth, document.body.scrollHeight]")
            page.pdf(
                path=str(FIGS / f"{n}.pdf"),
                width=f"{w}px",
                height=f"{h}px",
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            page.screenshot(path=str(FIGS / f"{n}.png"), full_page=True, scale="css")
            print(f"{n} {w}x{h}")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(p.stem for p in FIGS.glob("*.html")))
