/* hoststrip.js — per-run GPU telemetry strip in the Live run detail. app.js
   mounts it from openRun: query host_metrics for the run_id and, if any rows
   exist, render a compact strip (worker host RAM/CPU + nvitop GPU rows + a mean
   util sparkline) right after .run-top, following realtime inserts through the
   single channel hosts.js owns (listen/off — no channel leaks). Runs live on
   JIT GPU nodes that come and go: a latest sample older than 3 min renders as
   "last seen Xm ago" instead of live bars. No rows at all (telemetry off /
   older run) → nothing is rendered. closeRun/openRun call unmount(). */
"use strict";

(function () {
  const R = () => window.RENDER;
  const STALE_MS = 3 * 60e3, CAP = 200;
  let cur = null; // { runId, rootEl, rows, off, timer }

  function unmount() {
    if (!cur) return;
    if (cur.off) cur.off();
    if (cur.timer) clearInterval(cur.timer);
    const el = cur.rootEl && cur.rootEl.querySelector(".hoststrip");
    if (el) el.remove();
    cur = null;
  }

  function utilSeries(rows) {
    return rows.map((m) => {
      const u = Array.isArray(m.gpus) ? m.gpus.map((g) => Number(g.util)).filter((v) => !isNaN(v)) : [];
      return u.length ? u.reduce((a, b) => a + b, 0) / u.length : 0;
    });
  }

  function html(rows) {
    const RE = R(), U = window.Hosts.ui;
    const last = rows[rows.length - 1];
    const stale = Date.now() - new Date(last.created_at || 0).getTime() > STALE_MS;
    const ago = stale
      ? `<span class="hc-ago">last seen ${RE.fmtAgo(last.created_at)}</span>`
      : `<span class="hc-ago live"><span class="dot running"></span>${RE.fmtAgo(last.created_at)}</span>`;
    const head = `<div class="hs-head"><span class="hs-t">gpu node</span><span class="hc-name">${RE.esc(last.host || "?")}</span>${ago}</div>`;
    if (stale) return `<div class="hoststrip stale">${head}</div>`;
    const u = utilSeries(rows);
    const spark = u.length > 1 ? `<div class="hsparks"><span class="hs-one"><span class="hs-l">gpu</span>${U.sparkSvg(u, 100, "")}</span></div>` : "";
    return `<div class="hoststrip">${head}<div class="hs-body">
      <div class="hs-col">${U.ramHtml(last)}${U.sysHtml(last)}${spark}</div>
      <div class="hs-col grow">${U.gpuRowsHtml(last.gpus)}</div></div></div>`;
  }

  function render() {
    if (!cur || !cur.rootEl) return;
    const top = cur.rootEl.querySelector(".run-top");
    const el = cur.rootEl.querySelector(".hoststrip");
    if (!cur.rows.length || !top) { if (el) el.remove(); return; } // no telemetry → render nothing at all
    const fresh = R().el(html(cur.rows));
    if (el) el.replaceWith(fresh);
    else top.insertAdjacentElement("afterend", fresh);
  }

  async function mount(rootEl, runId) {
    unmount();
    if (!window.Hosts || !window.RemoteSource || !window.RemoteSource.client) return;
    const my = cur = { runId, rootEl, rows: [], off: null, timer: null };
    my.off = window.Hosts.listen((row) => { // realtime inserts, filtered by run_id
      if (cur !== my || !row || row.run_id !== my.runId) return;
      my.rows.push(row);
      if (my.rows.length > CAP) my.rows.splice(0, my.rows.length - CAP);
      render();
    });
    my.timer = setInterval(() => { if (cur === my) render(); }, 60e3); // ages live dot → "last seen Xm ago"
    let rows = [];
    try { rows = await window.RemoteSource.loadHostMetrics({ run_id: runId }); }
    catch (e) { return; } // host_metrics table missing → strip simply absent (realtime may still arrive)
    if (cur !== my) return;
    my.rows = rows.concat(my.rows).slice(-CAP);
    render();
  }

  window.HostStrip = { mount, unmount };
})();
