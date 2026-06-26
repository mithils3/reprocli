/* charts.js — tiny, dependency-free bar charts for the Stats tab. Rendered as
   themed HTML (flex bars whose widths are %), so they track dark mode and resize
   for free — no SVG coordinate math, no charting library. Two builders today:
   tokens-by-model (stacked prompt + completion) and compute-by-model (H100·h).
   Both take the same row shape stats.js builds and return an HTML string. */
"use strict";

(function () {
  const esc = window.RENDER.esc;
  const fmtK = (n) => {
    if (n == null) return "—";
    if (n < 1000) return String(Math.round(n));
    if (n < 1e6) return (n / 1e3).toFixed(n < 1e4 ? 1 : 0) + "k";
    return (n / 1e6).toFixed(2) + "M";
  };
  const fmtH = (n) => (n == null ? "—" : (Math.round(n * 1000) / 1000).toLocaleString());

  // sum the per-run rows into one bucket per model
  function byModel(rows) {
    const m = new Map();
    for (const r of rows) {
      const k = r.model || "—";
      const g = m.get(k) || { model: k, prompt: 0, completion: 0, total: 0, spent: 0, runs: 0 };
      g.prompt += r.prompt || 0; g.completion += r.completion || 0;
      g.total += r.total || 0; g.spent += r.spent || 0; g.runs += 1;
      m.set(k, g);
    }
    return [...m.values()];
  }

  const card = (title, sub, legend, inner) =>
    `<div class="chart-card"><div class="chart-h"><span class="chart-t">${esc(title)}</span>` +
    `${sub ? `<span class="chart-s">${esc(sub)}</span>` : ""}</div>${legend || ""}` +
    `<div class="bars">${inner}</div></div>`;
  const empty = (title) => card(title, "", "", `<div class="chart-empty">no data yet</div>`);

  function barRow(label, runs, segs, valTxt) {
    const segHtml = segs.map((s) =>
      `<span class="seg ${s.cls}" style="width:${s.pct.toFixed(2)}%" title="${esc(s.title)}"></span>`).join("");
    return `<div class="bar-row">
      <div class="bar-label" title="${esc(label)} · ${runs} run${runs === 1 ? "" : "s"}">${esc(label)}</div>
      <div class="bar-track">${segHtml}</div>
      <div class="bar-val">${valTxt}</div></div>`;
  }

  function tokensByModel(rows) {
    const g = byModel(rows).filter((x) => x.total > 0).sort((a, b) => b.total - a.total);
    if (!g.length) return empty("Tokens by model");
    const max = Math.max(...g.map((x) => x.total)) || 1;
    const legend = `<div class="chart-legend">` +
      `<span class="lg"><i class="sw seg-prompt"></i>prompt</span>` +
      `<span class="lg"><i class="sw seg-compl"></i>completion</span></div>`;
    const bars = g.map((x) => barRow(x.model, x.runs, [
      { cls: "seg-prompt", pct: (x.prompt / max) * 100, title: `prompt ${fmtK(x.prompt)}` },
      { cls: "seg-compl", pct: (x.completion / max) * 100, title: `completion ${fmtK(x.completion)}` },
    ], fmtK(x.total))).join("");
    return card("Tokens by model", "stacked prompt + completion, summed over runs", legend, bars);
  }

  function computeByModel(rows) {
    const g = byModel(rows).filter((x) => x.spent > 0).sort((a, b) => b.spent - a.spent);
    if (!g.length) return empty("Compute by model");
    const max = Math.max(...g.map((x) => x.spent)) || 1;
    const bars = g.map((x) => barRow(x.model, x.runs,
      [{ cls: "seg-compute", pct: (x.spent / max) * 100, title: `${fmtH(x.spent)} H100·h` }],
      fmtH(x.spent))).join("");
    return card("Compute by model", "H100·h spent, summed over runs", "", bars);
  }

  function render(rows) {
    return `<div class="charts-grid">${tokensByModel(rows)}${computeByModel(rows)}</div>`;
  }

  window.Charts = { render, tokensByModel, computeByModel };
})();
