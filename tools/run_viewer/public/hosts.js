/* hosts.js — cluster telemetry for the Fleet board. Reads host_status (one
   snapshot row per node) + host_metrics (time-series) and paints per-host cards:
   RAM meter, cpu/load line, nvitop-flavoured GPU rows, util/RAM sparklines and
   the master's collapsible vLLM log tail. The tables may not exist yet — one
   console.warn, then the Cluster section is simply absent. Shares its meter /
   spark / gpu-row helpers and the single host_metrics realtime channel with
   hoststrip.js (the per-run GPU strip). fleet.js mounts it into .cluster-slot. */
"use strict";

(function () {
  const R = () => window.RENDER;
  const FRESH_MS = 10 * 60e3; // contract: a host is live if updated_at < 10 min
  const SHOW_MS = 45 * 60e3;  // stale hosts linger greyed ("stale Xm") this long, then drop
  const CAP = 200;            // sparkline points kept per host
  const S = { hosts: new Map(), series: new Map(), slot: null, started: false, disabled: false,
    listeners: new Set(), openLogs: new Set() };

  // ---- shared UI helpers (window.Hosts.ui — reused by hoststrip.js) ---------
  const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0));
  const f0 = (v) => (v == null || isNaN(v) ? "?" : String(Math.round(Number(v))));
  const f1 = (v) => (v == null || isNaN(v) ? "?" : String(Math.round(Number(v) * 10) / 10));
  const bar = (pct, cls) => `<span class="hbar${cls ? " " + cls : ""}"><i style="width:${clamp(pct).toFixed(1)}%"></i></span>`;

  function ramHtml(h) {
    const used = Number(h.mem_used_gb), total = Number(h.mem_total_gb);
    if (isNaN(used) || !total) return "";
    return `<div class="hmeter"><span class="hm-l">ram</span>${bar((used / total) * 100, used / total > .95 ? "hot" : "")}` +
      `<span class="hm-v tnum">${f0(used)} / ${f0(total)} GB</span></div>`;
  }
  function sysHtml(h) {
    const bits = [];
    if (h.cpu_pct != null) bits.push(`cpu ${f0(h.cpu_pct)}%`);
    if (h.load1 != null) bits.push(`load ${f1(h.load1)}`);
    return bits.length ? `<div class="hc-sys tnum">${bits.join(" · ")}</div>` : "";
  }
  function gpuRowsHtml(gpus) {
    if (!Array.isArray(gpus) || !gpus.length) return "";
    return `<div class="hgpus">` + gpus.map((g) => {
      const memPct = g.mem_total ? (Number(g.mem) / Number(g.mem_total)) * 100 : 0;
      const x = `${g.power != null ? f0(g.power) + "W" : ""}${g.temp != null ? " " + f0(g.temp) + "°C" : ""}`.trim();
      return `<div class="hg-row tnum"><span class="hg-i">${f0(g.i)}</span>` +
        `${bar(g.util, Number(g.util) > 90 ? "hot" : "")}<span class="hg-v">${f0(g.util)}%</span>` +
        `${bar(memPct, "mem")}<span class="hg-v wide">${f1(g.mem)}/${f0(g.mem_total)}G</span>` +
        `<span class="hg-x">${x}</span></div>`;
    }).join("") + `</div>`;
  }
  function sparkSvg(vals, max, cls) {
    if (!vals || vals.length < 2) return "";
    const W = 120, H = 26, P = 2, hi = max || Math.max(...vals, 1);
    const pts = vals.map((v, i) => {
      const y = Math.max(0, Math.min(hi, Number(v) || 0));
      return `${(P + (i / (vals.length - 1)) * (W - 2 * P)).toFixed(1)},${(H - P - (y / hi) * (H - 2 * P)).toFixed(1)}`;
    }).join(" ");
    return `<svg class="hspark${cls ? " " + cls : ""}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}" fill="none"/></svg>`;
  }

  // ---- host card -------------------------------------------------------------
  function sparksHtml(h) {
    const s = S.series.get(h.host);
    if (!s || s.util.length < 2) return "";
    const ramMax = Number(h.mem_total_gb) || Math.max(...s.ram, 1);
    return `<div class="hsparks"><span class="hs-one"><span class="hs-l">gpu</span>${sparkSvg(s.util, 100, "")}</span>` +
      `<span class="hs-one"><span class="hs-l">ram</span>${sparkSvg(s.ram, ramMax, "ram")}</span></div>`;
  }
  function logHtml(h) {
    if (h.role !== "master" || !h.log_tail) return "";
    return `<details class="hc-log" data-host="${R().esc(h.host)}"${S.openLogs.has(h.host) ? " open" : ""}>` +
      `<summary>vLLM log</summary><pre>${R().esc(h.log_tail)}</pre></details>`;
  }
  function cardHtml(h, now) {
    const RE = R(), age = now - new Date(h.updated_at || 0).getTime();
    const fresh = age < FRESH_MS;
    const ago = fresh ? `<span class="dot running"></span>${RE.fmtAgo(h.updated_at)}` : `stale ${Math.round(age / 60e3)}m`;
    return `<div class="hcard${fresh ? "" : " stale"}">
      <div class="hc-head"><span class="hc-name">${RE.esc(h.host)}</span>
        <span class="hc-role${h.role === "master" ? " master" : ""}">${RE.esc(h.role || "run")}</span>
        <span class="hc-ago${fresh ? " live" : ""}">${ago}</span></div>
      ${ramHtml(h)}${sysHtml(h)}${sparksHtml(h)}${gpuRowsHtml(h.gpus)}${logHtml(h)}</div>`;
  }

  // ---- Cluster section render (into fleet.js's .cluster-slot) ----------------
  function logScrollState(slot) {
    const m = new Map();
    slot.querySelectorAll(".hc-log[open] pre").forEach((p) => m.set(p.closest(".hc-log").dataset.host,
      { top: p.scrollTop, bottom: p.scrollHeight - p.scrollTop - p.clientHeight < 24 }));
    return m;
  }
  function render() {
    const slot = S.slot;
    if (!slot || !slot.isConnected) return;
    const now = Date.now();
    const all = [...S.hosts.values()];
    const fresh = all.filter((h) => now - new Date(h.updated_at || 0).getTime() < FRESH_MS);
    if (S.disabled || !fresh.length) { slot.innerHTML = ""; return; }
    const scroll = logScrollState(slot);
    const shown = all.filter((h) => now - new Date(h.updated_at || 0).getTime() < SHOW_MS)
      .sort((a, b) => (a.role === "master" ? 0 : 1) - (b.role === "master" ? 0 : 1) || String(a.host).localeCompare(String(b.host)));
    slot.innerHTML = `<div class="cluster"><div class="fleet-sub"><span class="fs-title">Cluster</span>
      <span class="fs-note">${fresh.length} host${fresh.length !== 1 ? "s" : ""} live</span></div>
      <div class="hgrid">${shown.map((h) => cardHtml(h, now)).join("")}</div></div>`;
    slot.querySelectorAll(".hc-log[open] pre").forEach((p) => { // follow the tail unless the user scrolled up
      const st = scroll.get(p.closest(".hc-log").dataset.host);
      p.scrollTop = (!st || st.bottom) ? p.scrollHeight : st.top;
    });
  }
  function mountCluster(slot) {
    if (!slot) return;
    S.slot = slot;
    slot.addEventListener("toggle", (e) => { // capture: toggle doesn't bubble
      const d = e.target && e.target.classList && e.target.classList.contains("hc-log") ? e.target : null;
      if (!d) return;
      if (d.open) { S.openLogs.add(d.dataset.host); const p = d.querySelector("pre"); if (p) p.scrollTop = p.scrollHeight; }
      else S.openLogs.delete(d.dataset.host);
    }, true);
    render();
  }

  // ---- data plumbing ----------------------------------------------------------
  function pushMetric(row) {
    if (!row || !row.host) return;
    let s = S.series.get(row.host);
    if (!s) { s = { util: [], ram: [] }; S.series.set(row.host, s); }
    const u = Array.isArray(row.gpus) ? row.gpus.map((g) => Number(g.util)).filter((v) => !isNaN(v)) : [];
    s.util.push(u.length ? u.reduce((a, b) => a + b, 0) / u.length : 0);
    s.ram.push(Number(row.mem_used_gb) || 0);
    if (s.util.length > CAP) { s.util.splice(0, s.util.length - CAP); s.ram.splice(0, s.ram.length - CAP); }
  }
  function onStatus(row) { if (row && row.host) { S.hosts.set(row.host, row); render(); } }
  function onMetric(row) {
    pushMetric(row);
    S.listeners.forEach((fn) => { try { fn(row); } catch (e) {} });
    if (row && S.hosts.has(row.host)) render(); // just the Cluster section — never the whole board
  }
  // hoststrip.js taps the one shared host_metrics channel here; returns off()
  function listen(fn) { S.listeners.add(fn); return () => S.listeners.delete(fn); }

  async function init() {
    const RS = window.RemoteSource;
    if (S.started || !RS || !RS.client) return;
    S.started = true;
    let rows;
    try { rows = await RS.listHosts(); }
    catch (e) { S.disabled = true; console.warn("cluster telemetry unavailable:", (e && e.message) || e); return; }
    rows.forEach((h) => S.hosts.set(h.host, h));
    const now = Date.now();
    const fresh = rows.filter((h) => now - new Date(h.updated_at || 0).getTime() < FRESH_MS);
    try { (await Promise.all(fresh.map((h) => RS.loadHostMetrics({ host: h.host })))).forEach((ms) => ms.forEach(pushMetric)); }
    catch (e) {} // host_metrics missing → cards without sparklines
    RS.subscribeHosts(onStatus);
    RS.subscribeMetrics(onMetric);
    setInterval(render, 60e3); // ages "Xs ago", demotes hosts that go quiet
    render();
  }

  window.Hosts = { init, mountCluster, listen, ui: { bar, ramHtml, sysHtml, gpuRowsHtml, sparkSvg, f0, f1 } };
})();
