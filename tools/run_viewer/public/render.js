/* render.js — shared rendering core + the run transcript shell. Turns the
   normalized Run/Round/Call shape (from parser.js OR supabase-data.js) into DOM.
   Pure helpers (esc/el/status) live here and are exported on window.RENDER; the
   round-card / tool-call / json-tree rendering is in render_round.js (300-line
   rule). The transcript is a two-column "strip chart": a vertical burn-trace rail
   (drawn by trace.js, wired by strip.js) beside the rounds. */
"use strict";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
const fmtTime = (t) => t ? new Date(t).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
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

// ---- fuel gauge (burn-down) ------------------------------------------------
function fuelGaugeHtml(run) {
  const total = num(run.total_h100 ?? run.budget);
  let spent = num(run.spent_h100);
  if (spent == null && total != null && run.remaining_h100 != null) spent = num(total - run.remaining_h100);
  if (total == null && spent == null) return "";
  const predicted = predictedOf(run);
  const over = predicted != null && spent != null && spent > predicted;
  const pct = total ? Math.max(0, Math.min(100, (spent / total) * 100)) : 0;
  const predPct = (total && predicted != null) ? Math.max(0, Math.min(100, (predicted / total) * 100)) : null;
  const rem = run.remaining_h100 != null ? num(run.remaining_h100) : (total != null && spent != null ? num(total - spent) : null);
  const fillCls = run.status === "finished" && !over ? "done" : over ? "over" : "";
  return `<div class="fuel"><span class="fuel-l">compute</span>
    <span class="fuel-bar"><i class="fuel-fill ${fillCls}" style="width:${pct.toFixed(1)}%"></i>${predPct != null ? `<i class="fuel-pred" style="left:${predPct.toFixed(1)}%" title="predicted ${predicted} H100·h"></i>` : ""}</span>
    <span class="fuel-v tnum" title="${spent ?? "?"} / ${total ?? "?"} H100·h"><b>${fmtHM(spent)}</b> / ${fmtHM(total)} H100·h${rem != null ? ` · <b>${fmtHM(rem)}</b> left` : ""}${predicted != null ? ` · pred ${fmtHM(predicted)}` : ""}</span></div>`;
}

// ---- run header ------------------------------------------------------------
function runHeaderHtml(run) {
  const fam = V() ? V().ofRun(run) : "done";
  const word = V() ? V().word(run) : (run.status || "");
  const claim = claimOf(run);
  const exit = run.exit_reason ? `<span class="badge ${GOOD_EXIT(run.exit_reason) ? "yes" : "over"}">exit: ${esc(run.exit_reason)}</span>` : "";
  const dl = run.full_log_url ? `<a class="link" href="${esc(run.full_log_url)}" target="_blank" rel="noopener">⬇ full log</a>` : "";
  const tagbar = (window.Tags && run.run_id) ? `<div class="tagbar" data-run="${esc(run.run_id)}"></div>` : "";
  const links = window.Estimates ? window.Estimates.links(run.arxiv_id) : null;
  const lk = links && (links.paper || links.code) ? `<span class="rt-links">${links.paper ? `<a href="${esc(links.paper)}" target="_blank" rel="noopener">paper↗</a>` : ""}${links.code ? `<a href="${esc(links.code)}" target="_blank" rel="noopener">code↗</a>` : ""}</span>` : "";
  return `<div class="rt-head">${V() ? V().inline(fam, word) : ""}
      ${run.model ? `<span class="schip">${esc(run.model)}</span>` : ""}${exit}${lk}${dl}</div>
    <h2 class="rt-claim">${esc(claim || run.run_id || run.arxiv_id || "transcript")}</h2>
    <div class="rt-meta"><span class="pid">${esc(run.arxiv_id || "")}</span>${run.run_id && claim ? ` · <span class="s-rid">${esc(run.run_id)}</span>` : ""}${run.started_at || run.updated_at ? ` · started ${fmtTime(run.started_at)} · updated ${fmtTime(run.updated_at)}` : ""}${run.host ? ` · ${esc(run.host)}` : ""}</div>
    ${tagbar}${fuelGaugeHtml(run)}`;
}
const topHtml = (run) => runHeaderHtml(run);

// ---- transcript shell ------------------------------------------------------
function setSpike(run, rounds) { if (window.Trace) run.__spike = window.Trace.cumulative(rounds || []).maxDelta; }
function renderRun(rootEl, run, rounds) {
  const RR = window.RENDER;
  setSpike(run, rounds);
  rootEl.innerHTML = `<div class="run-detail">
    <div class="run-top">${topHtml(run)}</div>
    <div class="run-body"><div class="strip-rail" aria-hidden="true"></div>
      <div class="rounds">${(rounds || []).map((r) => RR.roundCardHtml(r, run.arxiv_id, run)).join("")}</div></div>
  </div>`;
  if (window.Strip) window.Strip.mount(rootEl, run, rounds);
}
function appendRound(rootEl, round, run, rounds) {
  const RR = window.RENDER, roundsEl = rootEl.querySelector(".rounds");
  if (!roundsEl) return;
  setSpike(run, rounds);
  const key = `${round.kind}:${round.round_index}`;
  const html = RR.roundCardHtml(round, run.arxiv_id, run);
  const ex = roundsEl.querySelector(`[data-key="${CSS.escape(key)}"]`);
  if (ex) ex.outerHTML = html; else roundsEl.insertAdjacentHTML("beforeend", html);
  if (window.Strip) window.Strip.redraw(rootEl, run, rounds);
}

// ---- run-list item (Live sidebar) -----------------------------------------
function renderRunListItem(run) {
  const si = statusInfo(run), fam = V() ? V().ofRun(run) : "done", m = V() ? V().meta(fam) : { glyph: "·" };
  const live = effectiveStatus(run) === "running";
  const claim = claimOf(run) || run.arxiv_id;
  const took = num(run.spent_h100), budget = num(run.budget ?? run.total_h100);
  return el(`<button class="plitem ${si.cls === "dead" ? "dead" : ""}" data-run="${esc(run.run_id)}">
    <span class="pl-vg vd ${fam}" title="${esc(V() ? V().word(run) : "")}">${m.glyph}</span>
    <span class="pmeta"><span class="pl-claim">${esc(claim)}</span>
      <span class="pl-sub"><span class="pid">${esc(run.arxiv_id)}</span>
        <span class="schip">${esc(run.model || "—")}</span>
        ${live ? '<span class="live-tag">● live</span>' : ""}
        <span class="schip tnum">${took ?? "·"}/${budget ?? "?"}h</span>
        <span class="schip">${fmtTime(run.updated_at)}</span></span>
      ${window.Tags ? window.Tags.chipsHtml(run.run_id) : ""}</span></button>`);
}

window.RENDER = { esc, el, fmtTime, num, fmtHM, claimOf, predictedOf, GOOD_EXIT,
  statusInfo, statusBadgeClass, isDead, isRoundLimit, effectiveStatus, ageHours,
  renderRun, renderRunListItem, appendRound, topHtml, fuelGaugeHtml, DEAD_AFTER_HOURS };
