/* charts.js: dependency-free themed visuals. ArcGauge for the headline rate, a
   generic horizontal bar grammar (card + rows + legend) reused by the
   failure-mode stack and the budget row, and a vertical column histogram
   for the 0 to 10 score distribution. All colour goes through the design tokens, so
   dark mode works for free. The burn trace and ledger live in trace.js. */
"use strict";

(function () {
  const esc = window.RENDER.esc;
  const fmtK = (n) => n == null ? "·" : n < 1000 ? String(Math.round(n)) : n < 1e6 ? (n / 1e3).toFixed(n < 1e4 ? 1 : 0) + "k" : (n / 1e6).toFixed(2) + "M";
  const fmtH = (n) => n == null ? "·" : (Math.round(n * 10) / 10).toLocaleString();

  // ---- ArcGauge: 270° gauge, progress over a track, numerals centered --------
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
    const label = opts.label ?? `${numer} of ${denom}`;
    return `<svg class="arc-gauge" viewBox="0 0 132 118" role="img" aria-label="${esc(label)}">
      <path d="${arc(A0, A0 + SWEEP)}" class="ag-track" fill="none" stroke-width="11" stroke-linecap="round"/>
      ${pct > 0 ? `<path d="${arc(A0, prog)}" class="ag-prog" fill="none" stroke-width="11" stroke-linecap="round"/>` : ""}
      <text x="66" y="64" text-anchor="middle" class="ag-num">${esc(numTxt)}</text>
      <text x="66" y="86" text-anchor="middle" class="ag-pct">${esc(pctTxt)}</text>
    </svg>`;
  }

  // ---- horizontal bar grammar ----------------------------------------------
  const card = (title, sub, legend, inner) =>
    `<div class="chart-card"><div class="chart-h"><span class="chart-t">${esc(title)}</span>${sub ? `<span class="chart-s">${esc(sub)}</span>` : ""}</div>${legend || ""}<div class="bars">${inner}</div></div>`;
  const empty = (title) => card(title, "", "", `<div class="chart-empty">no data</div>`);

  // segs: [{cls | colour, pct, title}]. cls picks a token class, colour a css var
  function barRow(label, segs, valTxt, tip) {
    const segHtml = segs.map((s) => {
      const style = s.colour ? `background:var(${s.colour});` : "";
      return `<span class="seg ${s.cls || ""}" style="${style}width:${s.pct.toFixed(2)}%" title="${esc(s.title || "")}"></span>`;
    }).join("");
    return `<div class="bar-row"><div class="bar-label" title="${esc(tip || label)}">${esc(label)}</div>` +
      `<div class="bar-track">${segHtml}</div><div class="bar-val tnum">${esc(valTxt)}</div></div>`;
  }
  function legend(items) {
    return `<div class="chart-legend">${items.map((i) =>
      `<span class="lg"><i class="sw" style="background:var(${i.colour})"></i>${esc(i.label)}</span>`).join("")}</div>`;
  }

  // ---- vertical column histogram (0 to 10 scores) ---------------------------
  function histogram(counts, opts) {
    opts = opts || {};
    const keys = opts.keys || Object.keys(counts);
    const max = Math.max(1, ...keys.map((k) => counts[k] || 0));
    const cols = keys.map((k) => {
      const v = counts[k] || 0;
      const h = (v / max) * 100;
      const cv = opts.colour ? opts.colour(k) : "--accent";
      return `<div class="hg-col" title="${esc(k)}: ${v} run${v === 1 ? "" : "s"}">` +
        `<div class="hg-n tnum">${v || ""}</div>` +
        `<div class="hg-bar"><i style="height:${h.toFixed(1)}%;background:var(${cv})"></i></div>` +
        `<div class="hg-k tnum">${esc(k)}</div></div>`;
    }).join("");
    return `<div class="hgram">${cols}</div>`;
  }

  window.Charts = { arcGauge, card, empty, barRow, legend, histogram, fmtK, fmtH };
})();
