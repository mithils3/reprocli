#!/usr/bin/env python3
"""Geometry audit for figure HTML: text collisions, margin overflow, clipped text.
Usage: audit.py <name> [...]. Exit 1 if any figure reports hits."""
import sys
import pathlib
from playwright.sync_api import sync_playwright

FIGS = pathlib.Path(__file__).parent

JS = """
() => {
  const problems = [];
  const body = document.body.getBoundingClientRect();
  const els = [...document.querySelectorAll('*')];

  // tight boxes for every visible text node
  const textBoxes = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.textContent.trim()) continue;
    const el = node.parentElement;
    if (!el) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none') continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    for (const r of range.getClientRects()) {
      if (r.width > 0 && r.height > 0)
        textBoxes.push({ el, text: node.textContent.trim().slice(0, 32), r });
    }
  }

  const overlap = (a, b) => {
    const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return x > 2 && y > 2 ? [x, y] : null;
  };

  // 1. text-vs-text collisions (skip same element, ancestor chains)
  for (let i = 0; i < textBoxes.length; i++)
    for (let j = i + 1; j < textBoxes.length; j++) {
      const A = textBoxes[i], B = textBoxes[j];
      if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) continue;
      const o = overlap(A.r, B.r);
      if (o) problems.push(`TEXT-HIT "${A.text}" x "${B.text}" ${o[0].toFixed(0)}x${o[1].toFixed(0)}px`);
    }

  // 2. text-vs-image collisions
  for (const img of document.querySelectorAll('img')) {
    const ir = img.getBoundingClientRect();
    for (const T of textBoxes) {
      if (img.parentElement && img.parentElement.contains(T.el) &&
          img.parentElement.children.length <= 3) continue;
      const o = overlap(ir, T.r);
      if (o && o[0] > 4 && o[1] > 4)
        problems.push(`IMG-HIT ${img.getAttribute('src')} x "${T.text}" ${o[0].toFixed(0)}x${o[1].toFixed(0)}px`);
    }
  }

  // 3. margin overflow: anything outside the body box
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.left < body.left - 1 || r.right > body.right + 1 ||
        r.top < body.top - 1 || r.bottom > body.bottom + 1)
      problems.push(`OVERFLOW <${el.tagName.toLowerCase()} class="${el.className}"> ` +
        `[${r.left.toFixed(0)},${r.top.toFixed(0)},${r.right.toFixed(0)},${r.bottom.toFixed(0)}] ` +
        `body [0,0,${body.right.toFixed(0)},${body.bottom.toFixed(0)}]`);
  }

  // 4a. text clipped by an overflow-hidden ancestor (catches inline leaves too)
  for (const T of textBoxes) {
    for (let anc = T.el.parentElement; anc && anc !== document.body; anc = anc.parentElement) {
      const st = getComputedStyle(anc);
      if (st.overflow === 'visible' && st.overflowX === 'visible') continue;
      const ar = anc.getBoundingClientRect();
      const cl = ar.left + anc.clientLeft, ct = ar.top + anc.clientTop;
      if (T.r.right > cl + anc.clientWidth + 1 || T.r.left < cl - 1 ||
          T.r.bottom > ct + anc.clientHeight + 1 || T.r.top < ct - 1)
        problems.push(`ANCESTOR-CLIP "${T.text}" exceeds <${anc.tagName.toLowerCase()} class="${anc.className}">`);
      break;
    }
  }

  // 4b. clipped nowrap text
  for (const el of els) {
    if (!el.childElementCount && el.textContent.trim() &&
        (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2)) {
      const st = getComputedStyle(el);
      if (st.overflow !== 'visible' || st.whiteSpace === 'nowrap' || st.whiteSpace === 'pre')
        problems.push(`CLIP <${el.tagName.toLowerCase()} class="${el.className}"> ` +
          `"${el.textContent.trim().slice(0, 32)}" scroll ${el.scrollWidth}x${el.scrollHeight} ` +
          `client ${el.clientWidth}x${el.clientHeight}`);
    }
  }
  return problems;
}
"""


def main(names):
    bad = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for n in names:
            page.goto((FIGS / f"{n}.html").as_uri())
            page.wait_for_timeout(400)
            problems = page.evaluate(JS)
            print(f"{n}: {len(problems)} problem(s)")
            for pr in problems:
                print(f"  {pr}")
            bad = bad or bool(problems)
        browser.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(p.stem for p in FIGS.glob("*.html")))
