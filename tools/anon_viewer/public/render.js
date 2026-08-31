/* render.js: shared rendering core + the run transcript shell. Turns the
   normalized Run/Round/Call shape into DOM. Pure helpers (esc/el/fmt*) live here
   and are exported on window.RENDER; round-card rendering is in render_round.js
   and the small card helpers in runcard.js. The run detail is an instrument panel
   (tile strip + horizontal burn trace) over a two-column strip chart: a vertical
   burn-trace rail (trace.js/strip.js) beside collapsible timeline round cards. */
"use strict";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; }
const num = (v) => (v == null ? null : (Math.round(v * 10000) / 10000));

// H100·h as a readable Hh MMm / MMm SSs / SSs (compute, so "minutes" = H100·minutes)
function fmtHM(h) {
  if (h == null || isNaN(h)) return "·";
  const neg = h < 0, sec = Math.round(Math.abs(h) * 3600);
  const hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60), ss = sec % 60;
  const s = hh > 0 ? `${hh}h ${String(mm).padStart(2, "0")}m`
    : mm > 0 ? `${mm}m ${String(ss).padStart(2, "0")}s` : `${ss}s`;
  return (neg ? "−" : "") + s;
}
// wall duration in seconds -> "3d 04h" / "8h 40m" / "12m 30s"
function fmtDur(s) {
  if (s == null || isNaN(s)) return "·";
  const t = Math.max(0, Math.round(s));
  const d = Math.floor(t / 86400), h = Math.floor((t % 86400) / 3600);
  const m = Math.floor((t % 3600) / 60), ss = t % 60;
  if (d > 0) return `${d}d ${String(h).padStart(2, "0")}h`;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m > 0) return `${m}m ${String(ss).padStart(2, "0")}s`;
  return `${ss}s`;
}
const fmtTok = (n) => n == null ? "·" : n >= 1e6 ? (n / 1e6).toFixed(2) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "k" : String(n);
const fmtTime = () => "";

// ---- how a run ended -------------------------------------------------------
// The index carries the reader-facing exit_label. A round event still carries the
// raw word, so the same map turns it into the same label on the final card.
const EXIT_LABEL = {
  natural: "Finished", completed: "Finished",
  budget_exhausted: "Budget exhausted",
  context_budget: "Context limit",
  round_limit: "Round limit",
  wall_clock: "Time limit", timeout: "Time limit",
  error: "Ended with error",
};
const exitLabel = (raw) => (raw ? (EXIT_LABEL[String(raw)] || "Ended") : null);
const GOOD_EXIT = (e) => e === "natural" || e === "completed";

// ---- paper joins (carried on the run row by data.js) ------------------------
const claimOf = (run) => (run && run.claim) || null;
function predictedOf(run) {
  if (!run) return null;
  const p = num(run.predicted_h100);
  return (p != null && p > 0) ? p : num(run.budget_h100);
}
const V = () => window.Verdict;

// spent / total / predicted from a run row (single source for the tiles and bars)
function fuelNums(run) {
  const total = num(run.budget_h100);
  const spent = num(run.spent_h100);
  const predicted = predictedOf(run);
  return { total, spent, predicted };
}

// ---- run header → instrument panel (tile strip) ----------------------------
function itile(label, value, sub, cls) {
  return `<div class="itile ${cls || ""}"><div class="it-l">${label}</div><div class="it-v tnum">${value}</div>${sub ? `<div class="it-sub">${sub}</div>` : ""}</div>`;
}
function runTilesHtml(run, extra) {
  const { total, spent } = fuelNums(run);
  const pct = (total && spent != null) ? `${Math.round((spent / total) * 100)}% of budget` : "";
  const rounds = (extra && extra.rounds != null) ? String(extra.rounds) : (run.rounds != null ? String(run.rounds) : "·");
  const tok = run.tokens || {};
  // the paper's own compute estimate, never the budget fallback: the tile is
  // omitted when the record carries no estimate for this paper
  const est = num(run.predicted_h100);
  return `<div class="itiles">` +
    itile("SPENT", fmtHM(spent), pct, "big") +
    itile("BUDGET", fmtHM(total), "H100·h", "") +
    ((est != null && est > 0) ? itile("ESTIMATED NEED", fmtHM(est), "paper&#39;s estimate", "") : "") +
    itile("ROUNDS", rounds, run.tool_calls != null ? `${run.tool_calls} tool calls` : "", "") +
    itile("TOKENS", fmtTok(tok.total), tok.cached != null ? `${fmtTok(tok.cached)} cached` : "", "") +
    itile("DURATION", fmtDur(run.duration_s), "wall clock", "") +
    `</div>`;
}

function runHeaderHtml(run, extra) {
  const fam = V() ? V().ofRun(run) : "done";
  const word = V() ? V().word(run) : "";
  const claim = claimOf(run);
  const target = (typeof run.target === "string" && run.target.trim()) ? run.target.trim() : null;
  const a = run.audit || {};
  const exit = run.exit_label
    ? `<span class="badge ${run.exit_label === "Finished" ? "yes" : "over"}">${esc(run.exit_label)}</span>` : "";
  const score = a.score != null
    ? `<span class="an-score ${a.score >= 8 ? "yes" : a.score >= 6 ? "over" : a.score <= 0 ? "no" : "slate"}">${esc(a.score)}<span>/10</span></span>` : "";
  const mode = (run.mode && window.Modes) ? window.Modes.chip(run.mode) : "";
  const tierName = window.Data ? window.Data.tierName(run.tier) : run.tier;
  const tier = run.tier ? `<span class="badge ${({ run: "yes", retrain: "over", reimplement: "no" })[run.tier] || "slate"}">${esc(tierName)}</span>` : "";
  const model = run.model_name ? `<span class="schip">${esc(run.model_name)}</span>` : "";
  const p = run.paper || {};
  const lk = (p.paper_url || p.code_url)
    ? `<span class="rt-links">${p.paper_url ? `<a href="${esc(p.paper_url)}" target="_blank" rel="noopener">paper↗</a>` : ""}${p.code_url ? `<a href="${esc(p.code_url)}" target="_blank" rel="noopener">code↗</a>` : ""}</span>` : "";
  const arx = run.arxiv_id
    ? `<a class="pid" href="https://arxiv.org/abs/${esc(run.arxiv_id)}" target="_blank" rel="noopener">${esc(run.arxiv_id)} ↗</a>` : "";
  return `<div class="rt-head">${V() ? V().stamp(fam, word ? String(word).replace(/_/g, " ").toUpperCase() : null) : ""}
      ${tier}${model}${score}${mode}${exit}${lk}</div>
    <h2 class="rt-claim">${esc(claim || run.arxiv_id || "transcript")}</h2>
    ${target ? `<div class="rt-target"><span class="rt-target-l">TARGET</span><span class="rt-target-v">${esc(target)}</span></div>` : ""}
    <div class="rt-meta">${arx}</div>
    ${runTilesHtml(run, extra)}`;
}
const topHtml = (run, extra) => runHeaderHtml(run, extra);

// ---- horizontal burn trace (lives OUTSIDE .run-top so patches don't wipe it) --
function traceSvg(run, rounds) {
  if (!window.Trace || !rounds || !rounds.length) return "";
  const predicted = predictedOf(run);
  const family = V() ? V().ofRun(run) : "done";
  return window.Trace.draw(rounds, { orientation: "h", vbW: 720, vbH: 72, fill: true, markers: true, predicted, family });
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
// opts.head === false renders the trace + rail + rounds only, so a caller can
// place its own header and the audit / dissection cards above the transcript.
function renderRun(rootEl, run, rounds, opts) {
  const RR = window.RENDER;
  opts = opts || {};
  rounds = rounds || [];
  setSpike(run, rounds);
  const n = rounds.length;
  const head = opts.head === false ? "" : `<div class="run-top">${topHtml(run, { rounds: n })}</div>`;
  rootEl.innerHTML = `<div class="run-detail">
    ${head}
    ${tracePanelHtml(run, rounds)}
    <div class="run-body"><div class="strip-rail" aria-hidden="true"></div>
      <div class="rounds">${roundsCtlHtml()}${rounds.map((r, i) => RR.roundCardHtml(r, run.arxiv_id, run, collapseDefault(r, i, n))).join("")}</div></div>
  </div>`;
  wireRounds(rootEl);
  if (window.Strip) window.Strip.mount(rootEl, run, rounds);
}

window.RENDER = { esc, el, num, fmtHM, fmtDur, fmtTok, fmtTime, claimOf, predictedOf,
  GOOD_EXIT, exitLabel, fuelNums, renderRun, topHtml, runTilesHtml };
