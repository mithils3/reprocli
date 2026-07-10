/* render.js — shared rendering core + the run transcript shell. Turns the
   normalized Run/Round/Call shape (from parser.js OR supabase-data.js) into DOM.
   Pure helpers (esc/el/status/fmt*) live here and are exported on window.RENDER;
   round-card rendering is in render_round.js and the sidebar/card helpers in
   runcard.js (300-line rule). The run detail is an instrument panel (tile strip +
   horizontal burn trace) over a two-column strip chart: a vertical burn-trace
   rail (trace.js/strip.js) beside collapsible timeline round cards. */
"use strict";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
const fmtTime = (t) => t ? new Date(t).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
// relative recency for sidebar/tiles ("12s ago" / "3m ago" / "2h ago" / "4d ago")
function fmtAgo(ts) {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (isNaN(ms)) return "—";
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return s + "s ago";
  const m = Math.round(s / 60); if (m < 60) return m + "m ago";
  const h = Math.round(m / 60); if (h < 24) return h + "h ago";
  return Math.round(h / 24) + "d ago";
}
const num = (v) => (v == null ? null : (Math.round(v * 10000) / 10000));
// H100·h as a readable Hh MMm / MMm SSs / SSs (compute, so "minutes" = H100·minutes)
function fmtHM(h) {
  if (h == null || isNaN(h)) return "—";
  const neg = h < 0, sec = Math.round(Math.abs(h) * 3600);
  const hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60), ss = sec % 60;
  const s = hh > 0 ? `${hh}h ${String(mm).padStart(2, "0")}m`
    : mm > 0 ? `${mm}m ${String(ss).padStart(2, "0")}s` : `${ss}s`;
  return (neg ? "−" : "") + s;
}

// ---- status / dead-run logic ----------------------------------------------
const GOOD_EXIT = (e) => e === "natural" || e === "completed";
const DEAD_AFTER_HOURS = (window.APP_CONFIG && window.APP_CONFIG.DEAD_AFTER_HOURS) || 12;
function ageHours(t) { if (!t) return Infinity; const ms = new Date(t).getTime(); return isNaN(ms) ? Infinity : (Date.now() - ms) / 3.6e6; }
function isDead(run) { return run.status === "running" && !!run.updated_at && ageHours(run.updated_at) > DEAD_AFTER_HOURS; }
const effectiveStatus = (run) => (isDead(run) ? "dead" : run.status || "running");
const isRoundLimit = (run) => run.exit_reason === "round_limit";
const statusBadgeClass = (cls) => cls === "finished" ? "yes" : cls === "error" ? "no" : cls === "dead" ? "slate" : "accent";
function statusInfo(run) {
  const s = effectiveStatus(run);
  if (s === "dead") return { cls: "dead", label: "dead" };
  if (s === "finished") return { cls: "finished", label: "done" };
  if (s === "error") return { cls: "error", label: "error" };
  if (s === "partial") return { cls: "running", label: "partial" };
  return { cls: "running", label: "running" };
}

// ---- lockfile joins --------------------------------------------------------
const claimOf = (run) => (window.Estimates && run && window.Estimates.claim(run.arxiv_id)) || null;
function predictedOf(run) {
  const p = window.Estimates ? window.Estimates.get(run.arxiv_id) : null;
  return (p != null && p > 0) ? p : num(run.total_h100 ?? run.budget);
}
const V = () => window.Verdict;

// spent / total / remaining / predicted from a run row (single source for gauges)
function fuelNums(run) {
  const total = num(run.total_h100 ?? run.budget);
  let spent = num(run.spent_h100);
  if (spent == null && total != null && run.remaining_h100 != null) spent = num(total - run.remaining_h100);
  const predicted = predictedOf(run);
  const rem = run.remaining_h100 != null ? num(run.remaining_h100)
    : (total != null && spent != null ? num(total - spent) : null);
  return { total, spent, predicted, rem };
}

// ---- fuel gauge (burn-down) — kept for source-compat (RENDER.fuelGaugeHtml) --
function fuelGaugeHtml(run) {
  const { total, spent, predicted, rem } = fuelNums(run);
  if (total == null && spent == null) return "";
  const over = predicted != null && spent != null && spent > predicted;
  const pct = total ? Math.max(0, Math.min(100, (spent / total) * 100)) : 0;
  const predPct = (total && predicted != null) ? Math.max(0, Math.min(100, (predicted / total) * 100)) : null;
  const fillCls = run.status === "finished" && !over ? "done" : over ? "over" : "";
  return `<div class="fuel"><span class="fuel-l">compute</span>
    <span class="fuel-bar"><i class="fuel-fill ${fillCls}" style="width:${pct.toFixed(1)}%"></i>${predPct != null ? `<i class="fuel-pred" style="left:${predPct.toFixed(1)}%" title="predicted ${predicted} H100·h"></i>` : ""}</span>
    <span class="fuel-v tnum" title="${spent ?? "?"} / ${total ?? "?"} H100·h"><b>${fmtHM(spent)}</b> / ${fmtHM(total)} H100·h${rem != null ? ` · <b>${fmtHM(rem)}</b> left` : ""}${predicted != null ? ` · pred ${fmtHM(predicted)}` : ""}</span></div>`;
}

// ---- run header → instrument panel (tile strip) ---------------------------
function itile(label, value, sub, cls) {
  return `<div class="itile ${cls || ""}"><div class="it-l">${label}</div><div class="it-v tnum">${value}</div>${sub ? `<div class="it-sub">${sub}</div>` : ""}</div>`;
}
function runTilesHtml(run, extra) {
  const { total, spent, predicted, rem } = fuelNums(run);
  const pct = (total && spent != null) ? `${Math.round((spent / total) * 100)}%` : "";
  const rounds = (extra && extra.rounds != null) ? String(extra.rounds) : "—";
  const live = effectiveStatus(run) === "running";
  const bal = (predicted != null && spent != null && V()) ? V().balance(spent, predicted) : "";
  const lastVal = live ? `<span class="dot running"></span>${fmtAgo(run.updated_at)}` : fmtAgo(run.updated_at);
  return `<div class="itiles">` +
    itile("SPENT", fmtHM(spent), "", "big") +
    itile("BUDGET", fmtHM(total), pct, "") +
    itile("LEFT", fmtHM(rem), "", "") +
    (predicted != null ? itile("PREDICTED", fmtHM(predicted), bal, "") : "") +
    itile("ROUNDS", rounds, "", "") +
    itile("LAST EVENT", lastVal, "", live ? "live" : "") +
    `</div>`;
}
// compact GPU-efficiency chip from the run-finish host_metrics rollup; omitted
// until the sink has written gpu_util_avg_pct (older / still-running runs)
function gpuChipHtml(run) {
  if (run.gpu_util_avg_pct == null) return "";
  const bits = [`avg ${Math.round(run.gpu_util_avg_pct)}%`];
  if (run.gpu_active_pct != null) bits.push(`active ${Math.round(run.gpu_active_pct)}%`);
  if (run.gpu_mem_peak_gb != null) bits.push(`peak ${Number(run.gpu_mem_peak_gb).toFixed(1)} GB`);
  const tip = run.gpu_samples != null ? ` title="GPU rollup over ${run.gpu_samples} samples"` : "";
  return `<span class="schip"${tip}>GPU: ${esc(bits.join(" · "))}</span>`;
}
function runHeaderHtml(run, extra) {
  const fam = V() ? V().ofRun(run) : "done";
  const word = V() ? V().word(run) : (run.status || "");
  const claim = claimOf(run);
  const exit = run.exit_reason ? `<span class="badge ${GOOD_EXIT(run.exit_reason) ? "yes" : "over"}">exit: ${esc(run.exit_reason)}</span>` : "";
  const dl = run.full_log_url ? `<a class="link" href="${esc(run.full_log_url)}" target="_blank" rel="noopener">⬇ full log</a>` : "";
  const tagbar = (window.Tags && run.run_id) ? `<div class="tagbar" data-run="${esc(run.run_id)}"></div>` : "";
  const links = window.Estimates ? window.Estimates.links(run.arxiv_id) : null;
  const lk = links && (links.paper || links.code) ? `<span class="rt-links">${links.paper ? `<a href="${esc(links.paper)}" target="_blank" rel="noopener">paper↗</a>` : ""}${links.code ? `<a href="${esc(links.code)}" target="_blank" rel="noopener">code↗</a>` : ""}</span>` : "";
  return `<div class="rt-head">${V() ? V().inline(fam, word) : ""}
      ${run.model ? `<span class="schip">${esc(run.model)}</span>` : ""}${exit}${gpuChipHtml(run)}${lk}${dl}</div>
    <h2 class="rt-claim">${esc(claim || run.run_id || run.arxiv_id || "transcript")}</h2>
    <div class="rt-meta"><span class="pid">${esc(run.arxiv_id || "")}</span>${run.run_id && claim ? ` · <span class="s-rid">${esc(run.run_id)}</span>` : ""}${run.started_at || run.updated_at ? ` · started ${fmtTime(run.started_at)} · updated ${fmtTime(run.updated_at)}` : ""}${run.host ? ` · ${esc(run.host)}` : ""}${run.batch_id ? ` · <span class="s-rid" title="batch ${esc(run.batch_id)}">⛁ ${esc(run.batch_label || run.batch_id)}</span>` : ""}</div>
    ${tagbar}${runTilesHtml(run, extra)}`;
}
const topHtml = (run, extra) => runHeaderHtml(run, extra);

// ---- horizontal burn trace (lives OUTSIDE .run-top so patches don't wipe it) --
function traceSvg(run, rounds) {
  if (!window.Trace || !rounds || !rounds.length) return "";
  const predicted = predictedOf(run);
  const family = V() ? V().ofRun(run) : "done";
  const live = effectiveStatus(run) === "running";
  return window.Trace.draw(rounds, { orientation: "h", vbW: 720, vbH: 72, fill: true, markers: true, predicted, family, live });
}
const tracePanelHtml = (run, rounds) => (rounds && rounds.length) ? `<div class="run-trace">${traceSvg(run, rounds)}</div>` : "";

// ---- transcript shell ------------------------------------------------------
function setSpike(run, rounds) { if (window.Trace) run.__spike = window.Trace.cumulative(rounds || []).maxDelta; }
// default collapse on a full render: everything collapsed except the last two + finals
const collapseDefault = (round, i, n) => round.kind !== "final" && i < n - 2;
const roundsCtlHtml = () => `<div class="rounds-ctl"><button class="link" type="button" data-act="expand">expand all</button><button class="link" type="button" data-act="collapse">collapse all</button></div>`;
function wireRounds(rootEl) {
  const roundsEl = rootEl.querySelector(".rounds");
  if (!roundsEl || roundsEl.__wired) return;
  roundsEl.__wired = true;
  roundsEl.addEventListener("click", (e) => {
    const ctl = e.target.closest(".rounds-ctl [data-act]");
    if (ctl) { const expand = ctl.dataset.act === "expand"; roundsEl.querySelectorAll(".rcard").forEach((c) => c.classList.toggle("collapsed", !expand)); return; }
    const h = e.target.closest(".rcard-h");
    if (h && roundsEl.contains(h)) { const card = h.closest(".rcard"); const c = card.classList.toggle("collapsed"); h.setAttribute("aria-expanded", String(!c)); }
  });
}
function renderRun(rootEl, run, rounds) {
  const RR = window.RENDER;
  rounds = rounds || [];
  setSpike(run, rounds);
  const n = rounds.length;
  rootEl.innerHTML = `<div class="run-detail">
    <div class="run-top">${topHtml(run, { rounds: n })}</div>
    ${tracePanelHtml(run, rounds)}
    <div class="run-body"><div class="strip-rail" aria-hidden="true"></div>
      <div class="rounds">${roundsCtlHtml()}${rounds.map((r, i) => RR.roundCardHtml(r, run.arxiv_id, run, collapseDefault(r, i, n))).join("")}</div></div>
  </div>`;
  wireRounds(rootEl);
  if (window.Strip) window.Strip.mount(rootEl, run, rounds);
}
function appendRound(rootEl, round, run, rounds) {
  const RR = window.RENDER, roundsEl = rootEl.querySelector(".rounds");
  if (!roundsEl) return;
  setSpike(run, rounds);
  const key = `${round.kind}:${round.round_index}`;
  const ex = roundsEl.querySelector(`[data-key="${CSS.escape(key)}"]`);
  const keepCollapsed = ex ? ex.classList.contains("collapsed") : false; // new cards arrive expanded
  const html = RR.roundCardHtml(round, run.arxiv_id, run, keepCollapsed);
  if (ex) ex.outerHTML = html; else roundsEl.insertAdjacentHTML("beforeend", html);
  const rd = rootEl.querySelector(".run-detail"), tp = rootEl.querySelector(".run-trace");
  if (rounds && rounds.length) {
    if (tp) tp.innerHTML = traceSvg(run, rounds);
    else if (rd) { const top = rd.querySelector(".run-top"); if (top) top.insertAdjacentHTML("afterend", tracePanelHtml(run, rounds)); }
  }
  if (window.Strip) window.Strip.redraw(rootEl, run, rounds);
}

window.RENDER = { esc, el, fmtTime, fmtAgo, num, fmtHM, claimOf, predictedOf, GOOD_EXIT,
  statusInfo, statusBadgeClass, isDead, isRoundLimit, effectiveStatus, ageHours, fuelNums,
  renderRun, appendRound, topHtml, fuelGaugeHtml, DEAD_AFTER_HOURS };
