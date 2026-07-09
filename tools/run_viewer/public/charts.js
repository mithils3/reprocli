/* charts.js — dependency-free themed visuals.
   Overview: ArcGauge (reproduced n/N) + a secondary took-vs-predicted scatter.
   Stats: tokens-by-model and compute-by-model bars (unchanged grammar).
   The signature burn-trace + ledger live in trace.js; verdict colours in verdict.js. */
"use strict";

(function () {
  const esc = window.RENDER.esc;
  const fmtK = (n) => n == null ? "—" : n < 1000 ? String(Math.round(n)) : n < 1e6 ? (n / 1e3).toFixed(n < 1e4 ? 1 : 0) + "k" : (n / 1e6).toFixed(2) + "M";
  const fmtH = (n) => n == null ? "—" : (Math.round(n * 1000) / 1000).toLocaleString();

  // ---- ArcGauge: 270° gauge, green progress over a track, numerals centered.
  // opts overrides the centre numeral (num), the sub-label (pct) and the aria-label
  // (label); progress fraction is always numer/denom. ----
  function arcGauge(numer, denom, opts) {
    opts = opts || {};
    const cx = 66, cy = 62, r = 48, A0 = 135, SWEEP = 270;
    const pct = denom ? numer / denom : 0;
    const polar = (deg) => { const a = deg * Math.PI / 180; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
    const arc = (a0, a1) => { const [x0, y0] = polar(a0), [x1, y1] = polar(a1); const large = (a1 - a0) > 180 ? 1 : 0;
      return `M${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`; };
    const prog = A0 + SWEEP * Math.max(0, Math.min(1, pct));
    const numTxt = opts.num ?? `${numer}/${denom}`;
    const pctTxt = opts.pct ?? `${denom ? Math.round(pct * 100) : 0}%`;
    const label = opts.label ?? `${numer} of ${denom} reproduced`;
    return `<svg class="arc-gauge" viewBox="0 0 132 118" role="img" aria-label="${label}">
      <path d="${arc(A0, A0 + SWEEP)}" class="ag-track" fill="none" stroke-width="11" stroke-linecap="round"/>
      ${pct > 0 ? `<path d="${arc(A0, prog)}" class="ag-prog" fill="none" stroke-width="11" stroke-linecap="round"/>` : ""}
      <text x="66" y="64" text-anchor="middle" class="ag-num">${numTxt}</text>
      <text x="66" y="86" text-anchor="middle" class="ag-pct">${pctTxt}</text>
    </svg>`;
  }

  // ---- secondary scatter: took vs predicted, log-log, y=x on-budget diagonal ----
  function scatter(papers) {
    const pts = (papers || []).filter((p) => p.took > 0 && p.predicted > 0);
    if (pts.length < 2) return `<div class="chart-empty">not enough reproduced runs to plot yet</div>`;
    const vals = pts.flatMap((p) => [p.took, p.predicted]);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    lo = Math.pow(10, Math.floor(Math.log10(lo))); hi = Math.pow(10, Math.ceil(Math.log10(hi)));
    if (hi <= lo) hi = lo * 10; // all values in one decade — keep a non-zero log range (no /0 → NaN)
    const W = 340, H = 240, pl = 38, pb = 28, pt = 10, pr = 12;
    const lx = (v) => pl + (Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo)) * (W - pl - pr);
    const ly = (v) => (H - pb) - (Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo)) * (H - pb - pt);
    const ticks = []; for (let e = Math.log10(lo); e <= Math.log10(hi) + 1e-9; e++) ticks.push(Math.pow(10, e));
    const gx = ticks.map((v) => `<line x1="${lx(v).toFixed(1)}" y1="${pt}" x2="${lx(v).toFixed(1)}" y2="${H - pb}" class="sc-grid"/><text x="${lx(v).toFixed(1)}" y="${H - pb + 14}" text-anchor="middle" class="sc-tick">${v}</text>`).join("");
    const gy = ticks.map((v) => `<line x1="${pl}" y1="${ly(v).toFixed(1)}" x2="${W - pr}" y2="${ly(v).toFixed(1)}" class="sc-grid"/><text x="${pl - 6}" y="${(ly(v) + 3).toFixed(1)}" text-anchor="end" class="sc-tick">${v}</text>`).join("");
    const diag = `<line x1="${lx(lo).toFixed(1)}" y1="${ly(lo).toFixed(1)}" x2="${lx(hi).toFixed(1)}" y2="${ly(hi).toFixed(1)}" class="sc-diag"/>`;
    const col = { reproduced: "--yes", miss: "--over", fault: "--no", idle: "--slate", done: "--slate" };
    const dots = pts.map((p) => {
      const c = col[p.verdict] || "--slate";
      return `<circle cx="${lx(p.took).toFixed(1)}" cy="${ly(p.predicted).toFixed(1)}" r="4" style="fill:var(${c});stroke:var(--panel)" fill-opacity=".85" stroke-width="1"><title>${esc(p.claim || p.arxiv_id)} — took ${fmtH(p.took)} vs predicted ${fmtH(p.predicted)} H100·h</title></circle>`;
    }).join("");
    return `<svg class="scatter" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
      ${gx}${gy}${diag}${dots}
      <text x="${(W / 2).toFixed(0)}" y="${H - 2}" text-anchor="middle" class="sc-axis">took H100·h →</text>
      <text x="10" y="${(H / 2).toFixed(0)}" text-anchor="middle" class="sc-axis" transform="rotate(-90 10 ${(H / 2).toFixed(0)})">predicted →</text>
    </svg>`;
  }

  // ---- Stats bars (unchanged) ----------------------------------------------
  function byModel(rows) {
    const m = new Map();
    for (const r of rows) {
      const k = r.model || "—";
      const g = m.get(k) || { model: k, prompt: 0, completion: 0, total: 0, spent: 0, runs: 0 };
      g.prompt += r.prompt || 0; g.completion += r.completion || 0; g.total += r.total || 0; g.spent += r.spent || 0; g.runs += 1;
      m.set(k, g);
    }
    return [...m.values()];
  }
  const card = (title, sub, legend, inner) =>
    `<div class="chart-card"><div class="chart-h"><span class="chart-t">${esc(title)}</span>${sub ? `<span class="chart-s">${esc(sub)}</span>` : ""}</div>${legend || ""}<div class="bars">${inner}</div></div>`;
  const empty = (title) => card(title, "", "", `<div class="chart-empty">no data yet</div>`);
  function barRow(label, runs, segs, valTxt) {
    const segHtml = segs.map((s) => `<span class="seg ${s.cls}" style="width:${s.pct.toFixed(2)}%" title="${esc(s.title)}"></span>`).join("");
    return `<div class="bar-row"><div class="bar-label" title="${esc(label)} · ${runs} run${runs === 1 ? "" : "s"}">${esc(label)}</div><div class="bar-track">${segHtml}</div><div class="bar-val tnum">${valTxt}</div></div>`;
  }
  function tokensByModel(rows) {
    const g = byModel(rows).filter((x) => x.total > 0).sort((a, b) => b.total - a.total);
    if (!g.length) return empty("Tokens by model");
    const max = Math.max(...g.map((x) => x.total)) || 1;
    const legend = `<div class="chart-legend"><span class="lg"><i class="sw seg-prompt"></i>prompt</span><span class="lg"><i class="sw seg-compl"></i>completion</span></div>`;
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
    const bars = g.map((x) => barRow(x.model, x.runs, [{ cls: "seg-compute", pct: (x.spent / max) * 100, title: `${fmtH(x.spent)} H100·h` }], fmtH(x.spent))).join("");
    return card("Compute by model", "H100·h spent, summed over runs", "", bars);
  }
  function statsCharts(rows) { return `<div class="charts-grid">${tokensByModel(rows)}${computeByModel(rows)}</div>`; }

  window.Charts = { arcGauge, scatter, statsCharts, tokensByModel, computeByModel };
})();
