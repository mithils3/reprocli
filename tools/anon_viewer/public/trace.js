/* trace.js: the signature visual. One dependency-free inline-SVG primitive: a run's
   cumulative compute (H100·h) plotted against its round arc, raced against the
   indigo dashed "predicted" ceiling. The cyan curve recolours to amber the instant
   cumulative spend crosses that ceiling, and is capped by a verdict glyph. The
   same draw fn renders a card thumbnail and the full vertical transcript rail
   (which doubles as the minimap). Also the dual-track took/predicted ledger bar.
   Colours go through style="" (var() is unreliable in SVG presentation
   attributes). */
"use strict";

(function () {
  const fill = (v) => `style="fill:var(${v})"`;
  const stroke = (v, extra) => `style="stroke:var(${v})${extra || ""}"`;

  function cumulative(rounds) {
    let cum = 0, maxDelta = 0;
    const pts = [];
    (rounds || []).forEach((r, i) => {
      let d = 0, fault = false;
      for (const c of (r.calls || [])) {
        if (typeof c.cost_h100 === "number") d += c.cost_h100;
        if (c.ok === false || c.error) fault = true;
      }
      cum = Math.round((cum + d) * 1e6) / 1e6;
      if (d > maxDelta) maxDelta = d;
      pts.push({ i, y: cum, delta: d, fault, kind: r.kind });
    });
    return { pts, total: cum, maxDelta };
  }

  function splitAt(pts, pred) {
    if (pred == null || !pts.length) return { before: pts, after: [] };
    const before = [], after = [];
    for (let k = 0; k < pts.length; k++) {
      const p = pts[k];
      (p.y <= pred ? before : after).push(p);
      const q = pts[k + 1];
      if (q && (p.y <= pred) !== (q.y <= pred)) {
        const f = (pred - p.y) / (q.y - p.y);
        const cx = { i: p.i + (q.i - p.i) * f, y: pred };
        before.push(cx); after.unshift(cx);
      }
    }
    return { before, after };
  }

  function capSvg(fam, x, y, r, live) {
    const cv = { reproduced: "--yes", miss: "--over", fault: "--no", idle: "--slate", done: "--slate", running: "--accent" }[fam] || "--slate";
    const ember = live ? `<circle cx="${x}" cy="${y}" r="${r + 1.5}" class="trace-ember" ${fill(cv)}/>` : "";
    if (fam === "fault")
      return `${ember}<g ${stroke(cv)} stroke-width="${(r * .72).toFixed(1)}" stroke-linecap="round"><line x1="${x - r}" y1="${y - r}" x2="${x + r}" y2="${y + r}"/><line x1="${x - r}" y1="${y + r}" x2="${x + r}" y2="${y - r}"/></g>`;
    if (fam === "idle" || fam === "done")
      return `${ember}<circle cx="${x}" cy="${y}" r="${r}" style="fill:var(--panel);stroke:var(${cv})" stroke-width="1.3"/>`;
    if (fam === "miss")
      return `${ember}<circle cx="${x}" cy="${y}" r="${r}" ${fill(cv)}/><path d="M${x} ${y - r} A ${r} ${r} 0 0 1 ${x} ${y + r} Z" style="fill:var(--panel);opacity:.55"/>`;
    return `${ember}<circle cx="${x}" cy="${y}" r="${r}" ${fill(cv)}/>`;
  }

  function draw(rounds, opts) {
    opts = opts || {};
    const horiz = opts.orientation !== "v";
    const vbW = opts.vbW || (horiz ? 240 : 60);
    const vbH = opts.vbH || (horiz ? 80 : 320);
    const pad = opts.pad || (horiz ? 6 : 7);
    const { pts, total } = cumulative(rounds);
    const pred = (typeof opts.predicted === "number" && opts.predicted > 0) ? opts.predicted : null;
    const n = pts.length;
    if (!n) return `<svg class="trace empty-trace" viewBox="0 0 ${vbW} ${vbH}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"></svg>`;
    const yMax = Math.max(total, pred || 0, 1e-9) * 1.12;
    const aMin = pad, aW = vbW - 2 * pad, aH = vbH - 2 * pad;
    const t = (i) => (n === 1 ? 0.5 : i / (n - 1));
    const map = horiz
      ? (i, y) => [aMin + t(i) * aW, aMin + aH - (y / yMax) * aH]
      : (i, y) => [aMin + (y / yMax) * aW, aMin + t(i) * aH];
    const poly = (arr) => arr.map((p) => map(p.i, p.y).map((v) => Math.round(v * 10) / 10).join(",")).join(" ");
    const sw = opts.sw || (horiz ? 2 : 2.2);

    let predSvg = "";
    if (pred != null) {
      const [px, py] = map(0, pred);
      predSvg = horiz
        ? `<line x1="${aMin}" y1="${py.toFixed(1)}" x2="${vbW - pad}" y2="${py.toFixed(1)}" ${stroke("--predicted", ";opacity:.85")} stroke-width="1" stroke-dasharray="3 3"/>`
        : `<line x1="${px.toFixed(1)}" y1="${aMin}" x2="${px.toFixed(1)}" y2="${vbH - pad}" ${stroke("--predicted", ";opacity:.85")} stroke-width="1" stroke-dasharray="3 3"/>`;
    }
    let fillSvg = "";
    if (opts.fill) {
      const base = horiz ? `${aMin + aW},${aMin + aH} ${aMin},${aMin + aH}` : `${aMin},${aMin + aH} ${aMin},${aMin}`;
      fillSvg = `<polygon points="${poly(pts)} ${base}" ${fill("--accent-tint")}/>`;
    }
    const { before, after } = splitAt(pts, pred);
    const cyan = before.length > 1 ? `<polyline points="${poly(before)}" fill="none" ${stroke("--accent")} stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round"/>` : "";
    const amber = after.length > 1 ? `<polyline points="${poly(after)}" fill="none" ${stroke("--over")} stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round"/>` : "";
    let marks = "";
    if (opts.markers) {
      marks = pts.map((p) => {
        const [mx, my] = map(p.i, p.y);
        const cv = p.fault ? "--no" : (p.y > (pred || Infinity) ? "--over" : "--accent");
        return `<circle class="trace-mark" data-round="${p.i}" cx="${Math.round(mx * 10) / 10}" cy="${Math.round(my * 10) / 10}" r="${opts.markerR || 2}" ${fill(cv)}/>`;
      }).join("");
    }
    const last = pts[n - 1], [lx, ly] = map(last.i, last.y);
    const cap = capSvg(opts.family || "done", Math.round(lx * 10) / 10, Math.round(ly * 10) / 10, opts.capR || (horiz ? 3 : 3.4), opts.live);
    return `<svg class="trace ${horiz ? "trace-h" : "trace-v"}" viewBox="0 0 ${vbW} ${vbH}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${predSvg}${fillSvg}${cyan}${amber}${marks}${cap}</svg>`;
  }

  function ledger(took, predicted, opts) {
    opts = opts || {};
    if (took == null && predicted == null) return "";
    const tk = took || 0, pr = predicted || 0;
    const max = Math.max(tk, pr, 1e-9);
    const predPct = (pr / max) * 100, tookPct = (tk / max) * 100;
    const overPct = Math.max(0, tookPct - predPct), basePct = Math.min(tookPct, predPct);
    const tick = pr > 0 ? `<i class="lg-tick" style="left:${predPct.toFixed(1)}%"></i>` : "";
    let label = "";
    if (opts.pct && pr > 0 && took != null) {
      const r = Math.round((tk / pr) * 100);
      label = `<span class="lg-pct tnum ${tk > pr ? "over" : "under"}">${r}%</span>`;
    }
    return `<span class="ledger ${opts.size || ""}"><span class="lg-track">` +
      (pr > 0 ? `<i class="lg-pred" style="width:${predPct.toFixed(1)}%"></i>` : "") +
      `<i class="lg-took" style="width:${basePct.toFixed(1)}%"></i>` +
      (overPct > 0 ? `<i class="lg-over" style="left:${predPct.toFixed(1)}%;width:${overPct.toFixed(1)}%"></i>` : "") +
      `${tick}</span>${label}</span>`;
  }

  window.Trace = { cumulative, draw, ledger };
})();
