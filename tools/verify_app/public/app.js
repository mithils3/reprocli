/* Artifact Verification — static SPA backed by Supabase (name-only auth). */
"use strict";

const CFG = window.APP_CONFIG || {};
const sb = (CFG.SUPABASE_URL && CFG.SUPABASE_ANON_KEY && window.supabase)
  ? window.supabase.createClient(CFG.SUPABASE_URL, CFG.SUPABASE_ANON_KEY)
  : null;

const ADMINS = (CFG.ADMIN_NAMES || []).map((s) => String(s).toLowerCase());

// ---- state ---------------------------------------------------------------
const state = {
  reviewer: null,
  papers: [],
  byId: {},
  drafts: {},        // paper_id -> editable verification fields (mine)
  saved: {},         // paper_id -> last-saved row (for dirty checks)
  others: {},        // paper_id -> { done: [names], progress: [names] } (everyone else)
  othersFull: {},    // paper_id -> [full verification rows] (everyone else, for the compare panel)
  presence: {},      // paper_id -> [names] viewing RIGHT NOW (everyone else)
  current: null,     // paper_id
  filter: "queue",
  tierFilter: "all",
  scoreFilter: "all",
  search: "",
  dirty: false,
  noted: new Set(),  // once-per-paper telemetry keys (note edits, evidence opens…)
};

// each artifact step is data-driven so the UI and DB stay in lock-step
const STEPS = [
  {
    key: "code", signal: "code_available", linkKey: "code", foundKey: "found_code_url",
    noun: "code is available",
    q: "Is the code available?",
    guide: "Find the official repo with the actual method/MRE code. A repo that only hosts the PDF, slides, or a paper list does NOT count.",
    searches: (p) => [
      ["GitHub", ghSearch(p)],
      ["Google", gSearch(`${shortTitle(p)} github code`)],
    ],
  },
  {
    key: "dataset", signal: "dataset_available", linkKey: "dataset", foundKey: "found_dataset_url",
    noun: "dataset is available",
    q: "Is the dataset available?",
    guide: "Can you actually download the data used for the main experiment (direct link, HF dataset, Zenodo, etc.)? 'Available on request' = not available.",
    searches: (p) => [
      ["Google", gSearch(`${shortTitle(p)} dataset download`)],
      ["HF datasets", `https://huggingface.co/datasets?search=${enc(shortTitle(p))}`],
      ["Papers w/ Code", `https://paperswithcode.com/search?q=${enc(shortTitle(p))}`],
    ],
  },
  {
    key: "weights", signal: "weights_available", linkKey: "weights", foundKey: "found_weights_url",
    noun: "weights are available",
    q: "Are the trained model weights / checkpoints available?",
    guide: "Look for downloadable checkpoints (HF model repo, Google Drive, release assets). Training code alone is NOT weights.",
    searches: (p) => [
      ["HF models", `https://huggingface.co/models?search=${enc(shortTitle(p))}`],
      ["Google", gSearch(`${shortTitle(p)} pretrained checkpoint weights`)],
    ],
  },
  {
    key: "dataset_standard", signal: "dataset_is_standard", linkKey: null, foundKey: null,
    noun: "dataset is a standard benchmark",
    q: "Is the dataset a standard / well-known public benchmark?",
    guide: "e.g. ImageNet, GLUE, COCO, C4. A new dataset introduced by this paper is NOT standard.",
    searches: (p) => [
      ["Google", gSearch(`${shortTitle(p)} benchmark dataset`)],
    ],
  },
];
const VERDICTS = ["agree", "disagree", "unsure"];

// ---- url helpers ----------------------------------------------------------
const enc = encodeURIComponent;
function shortTitle(p) {
  const t = (p.title || "").replace(/\(title unavailable\).*/, "").trim();
  return t.split(/\s+/).slice(0, 10).join(" ");
}
const gSearch = (q) => `https://www.google.com/search?q=${enc(q)}`;
function tierClass(tier) {
  const t = String(tier || "").toLowerCase();
  if (t.startsWith("easy")) return "t-easy";
  if (t.startsWith("medium")) return "t-medium";
  if (t.startsWith("hard")) return "t-hard";
  if (t.startsWith("artifact")) return "t-blocked";
  return "t-none";
}
function authorsLine(p) {
  const a = p.authors || [];
  if (!a.length) return "";
  const names = a.slice(0, 3).join(", ") + (a.length > 3 ? " et al." : "");
  return `${names}${p.year ? " · " + p.year : ""}`;
}
const arxivAbs = (p) => `https://arxiv.org/abs/${p.custom_id}`;
function ghSearch(p) {
  return `https://github.com/search?q=${enc(shortTitle(p))}&type=repositories`;
}

// ---- telemetry -------------------------------------------------------------
// Every behavioural event lands in the `activity` table; `detail` is a JSON
// string so the dashboard (or SQL) can slice time-on-paper, search usage,
// hesitation, skips, etc.
function track(action, paperId, detail) {
  if (!sb) return;
  sb.from("activity")
    .insert({ reviewer: state.reviewer, paper_id: paperId, action, detail: detail ? JSON.stringify(detail) : null })
    .then(({ error }) => { if (error) console.warn("telemetry:", error.message); });
}

// fire the same event once per paper-open (e.g. "edited the code note")
function trackOnce(action, key, detail) {
  const k = `${action}:${key}`;
  if (state.noted.has(k)) return;
  state.noted.add(k);
  track(action, state.current, detail);
}

// telemetry that must survive the page going away (sign-out, tab close)
function beacon(action, detail) {
  if (!CFG.SUPABASE_URL || !CFG.SUPABASE_ANON_KEY || !state.reviewer || !navigator.sendBeacon) return;
  const row = { reviewer: state.reviewer, paper_id: state.current, action, detail: detail ? JSON.stringify(detail) : null };
  navigator.sendBeacon(
    `${CFG.SUPABASE_URL}/rest/v1/activity?apikey=${CFG.SUPABASE_ANON_KEY}`,
    new Blob([JSON.stringify(row)], { type: "application/json" }));
}

// visibility-aware stopwatch: how long the reviewer ACTIVELY had this paper open
const ptimer = { segStart: null, accMs: 0 };
function timerReset() { ptimer.segStart = document.hidden ? null : Date.now(); ptimer.accMs = 0; }
function timerSeconds() {
  const run = ptimer.segStart ? Date.now() - ptimer.segStart : 0;
  return Math.round((ptimer.accMs + run) / 1000);
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    if (ptimer.segStart) { ptimer.accMs += Date.now() - ptimer.segStart; ptimer.segStart = null; }
    if (state.reviewer && state.current) track("tab_hidden", state.current, { active_seconds: timerSeconds() });
  } else {
    if (!ptimer.segStart) ptimer.segStart = Date.now();
    if (state.reviewer && state.current) track("tab_visible", state.current, null);
  }
});
window.addEventListener("pagehide", () => {
  if (state.current) beacon("session_end", { active_seconds: timerSeconds(), steps_answered: answeredCount(state.current) });
});

// ---- dom helpers ----------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

// ===========================================================================
// boot
// ===========================================================================
window.addEventListener("DOMContentLoaded", init);

async function init() {
  if (!sb) {
    $("#gate-hint").textContent =
      "⚠ Supabase is not configured. Edit config.js with your project URL and anon key.";
  }
  const saved = localStorage.getItem("reviewer");
  $("#gate-go").addEventListener("click", () => signIn($("#gate-name").value));
  $("#gate-name").addEventListener("keydown", (e) => { if (e.key === "Enter") signIn($("#gate-name").value); });
  $("#gate-name").value = saved || "";
  $("#signout").addEventListener("click", signOut);
  $$(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  $("#search").addEventListener("input", (e) => { state.search = e.target.value.toLowerCase(); renderList(); });

  await loadPapers();
  if (saved) signIn(saved);
}

async function loadPapers() {
  const res = await fetch("papers.json");
  state.papers = await res.json();
  state.byId = Object.fromEntries(state.papers.map((p) => [p.custom_id, p]));
}

async function signIn(name) {
  name = (name || "").trim();
  if (!name) { $("#gate-hint").textContent = "Please enter a name."; return; }
  state.reviewer = name;
  localStorage.setItem("reviewer", name);
  $("#who-name").textContent = name;
  const isAdmin = ADMINS.includes(name.toLowerCase());
  $$(".admin-only").forEach((e) => e.classList.toggle("hidden", !isAdmin));
  // guided flow: reviewers don't pick papers — the queue does. Admins keep the sidebar.
  document.body.classList.toggle("is-admin", isAdmin);
  $("#gate").classList.add("hidden");
  $("#app").classList.remove("hidden");

  await loadMyVerifications();
  await loadAllVerifications();
  startLiveSync();
  track("login", null, { admin: isAdmin, ua: navigator.userAgent.slice(0, 120) });
  buildFilters();
  renderList();
  setView("verify");
  const first = visiblePapers()[0];     // drop the reviewer straight into the next unprocessed paper
  if (first) openPaper(first.custom_id);
}

function signOut() {
  beacon("logout", { active_seconds: timerSeconds() });
  localStorage.removeItem("reviewer");
  location.reload();
}

async function loadMyVerifications() {
  state.drafts = {};
  state.saved = {};
  if (!sb) return;
  const { data, error } = await sb.from("verifications").select("*").eq("reviewer", state.reviewer);
  if (error) { console.error(error); return; }
  for (const row of data || []) {
    state.saved[row.paper_id] = row;
    state.drafts[row.paper_id] = { ...row };
  }
}

function draft(id) {
  if (!state.drafts[id]) state.drafts[id] = { paper_id: id, reviewer: state.reviewer };
  return state.drafts[id];
}

// --- everyone else's status (so two people don't redo the same paper) ------
async function loadAllVerifications() {
  state.others = {};
  state.othersFull = {};
  if (!sb) return;
  const { data, error } = await sb.from("verifications").select("*");
  if (error) { console.error(error); return; }
  for (const r of data || []) {
    if (r.reviewer === state.reviewer) continue;
    const m = state.others[r.paper_id] || (state.others[r.paper_id] = { done: [], progress: [] });
    (r.status === "completed" ? m.done : m.progress).push(r.reviewer);
    (state.othersFull[r.paper_id] || (state.othersFull[r.paper_id] = [])).push(r);
  }
}

function debounce(fn, ms) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

// --- realtime: live updates of saved work + who is viewing what ------------
let liveStarted = false;
let presenceChannel = null;
function startLiveSync() {
  if (!sb || liveStarted) return;
  liveStarted = true;

  // (a) any reviewer saves -> refresh cross-reviewer status live
  const refresh = debounce(async () => {
    await loadAllVerifications();
    renderList();
    refreshConflictBanner();
    refreshOthersPanel();
  }, 400);
  sb.channel("verifs-live")
    .on("postgres_changes", { event: "*", schema: "public", table: "verifications" }, refresh)
    .subscribe();

  // (b) presence: broadcast which paper I'm currently viewing
  presenceChannel = sb.channel("reviewers", { config: { presence: { key: state.reviewer } } });
  presenceChannel.on("presence", { event: "sync" }, () => {
    const raw = presenceChannel.presenceState();
    const map = {};
    for (const key in raw) {
      for (const meta of raw[key]) {
        if (!meta.paper_id || meta.name === state.reviewer) continue;
        (map[meta.paper_id] || (map[meta.paper_id] = new Set())).add(meta.name);
      }
    }
    state.presence = Object.fromEntries(Object.entries(map).map(([k, v]) => [k, [...v]]));
    renderList();
    refreshConflictBanner();
  });
  presenceChannel.subscribe((status) => {
    if (status === "SUBSCRIBED") trackPresence();
  });
}

function trackPresence() {
  if (presenceChannel) presenceChannel.track({ name: state.reviewer, paper_id: state.current });
}

// ===========================================================================
// status / progress
// ===========================================================================
// completion = the four artifact signals (the H100 band is trusted from the code audit)
// (the score is computed from the artifact verdicts)
const VERDICT_FIELDS = ["code_verdict", "dataset_verdict", "weights_verdict", "dataset_standard_verdict"];

// deterministic scoring formula (mirrors tools/v3_viewer/quality.py)
function scoreFromSignals(code, data, weights, standard) {
  let s = 0;
  if (!code) s += 2;
  if (!standard && !data) s += 3;
  if (!weights) s += 1;
  return s;
}
function tierFromScore(s, data, standard) {
  if (s === 0) return "Easy";
  if (s === 1) return "Medium";
  if (s === 2) return "Hard";
  if (s === 3 && (data || standard)) return "Hard";
  return "Artifact-Blocked";
}

// turn each agree/disagree verdict into the reviewer's effective boolean
// (agree -> model's value, disagree -> flipped, unsure/unset -> null)
function reviewerSignals(p, d = draft(p.custom_id)) {
  const sig = p.signals || {};
  const out = {};
  for (const step of STEPS) {
    if (!step.signal) continue;
    const mv = (sig[step.signal] || {}).value;
    const v = d[`${step.key}_verdict`];
    out[step.key] = typeof mv === "boolean"
      ? (v === "agree" ? mv : v === "disagree" ? !mv : null)
      : null;
  }
  return out;
}

// reviewer's computed score/tier, or null if any signal is unsure/unanswered
function reviewerScore(p, d = draft(p.custom_id)) {
  const e = reviewerSignals(p, d);
  if ([e.code, e.dataset, e.weights, e.dataset_standard].some((x) => x === null)) return null;
  const score = scoreFromSignals(e.code, e.dataset, e.weights, e.dataset_standard);
  return { score, tier: tierFromScore(score, e.dataset, e.dataset_standard) };
}

function answeredCount(id) {
  const d = state.drafts[id] || {};
  return VERDICT_FIELDS.filter((f) => d[f]).length;
}
function paperStatus(id) {
  const d = state.drafts[id];
  if (!d) return "todo";
  const set = VERDICT_FIELDS.filter((f) => d[f]);
  if (set.length === 0) return "todo";
  if (set.length === VERDICT_FIELDS.length) return "done";
  return "progress";
}
function hasDisagreement(id) {
  const d = state.drafts[id];
  return d && VERDICT_FIELDS.some((f) => d[f] === "disagree");
}
// a paper leaves the working queue as soon as ANYONE completes it
function completedByAnyone(id) {
  return paperStatus(id) === "done" || (state.others[id]?.done.length || 0) > 0;
}
function myDoneCount() {
  return state.papers.filter((p) => paperStatus(p.custom_id) === "done").length;
}
function queueCount() {
  return state.papers.filter((p) => !completedByAnyone(p.custom_id)).length;
}

// ===========================================================================
// sidebar
// ===========================================================================
function buildFilters() {
  const counts = {
    queue: queueCount(),
    mine: state.papers.filter((p) => paperStatus(p.custom_id) === "progress").length,
    done: state.papers.filter((p) => completedByAnyone(p.custom_id)).length,
    disagree: state.papers.filter((p) => hasDisagreement(p.custom_id)).length,
    all: state.papers.length,
  };
  const filters = [
    ["queue", "To label"], ["mine", "My in-progress"],
    ["done", "Completed"], ["disagree", "Disagreements"], ["all", "All"],
  ];
  const root = $("#filters");
  root.innerHTML = "";
  for (const [key, label] of filters) {
    const b = el(`<button class="filt ${key === state.filter ? "active" : ""}" data-f="${key}">${label} <span class="fcount">${counts[key]}</span></button>`);
    b.addEventListener("click", () => { state.filter = key; renderList(); });
    root.appendChild(b);
  }
  root.appendChild(facetSelects());
}

function optionList(values, current, allLabel) {
  return [`<option value="all">${esc(allLabel)}</option>`]
    .concat(values.map((v) =>
      `<option value="${esc(v)}" ${v === current ? "selected" : ""}>${esc(v)}</option>`))
    .join("");
}

function facetSelects() {
  const tierOrder = ["Easy", "Medium", "Hard", "Artifact-Blocked"];
  const tiers = tierOrder.filter((t) => state.papers.some((p) => p.tier === t));
  const scores = [...new Set(state.papers.map((p) => String(p.score ?? "—")))]
    .sort((a, b) => Number(a) - Number(b));
  const box = el(`
    <div class="facet-filters">
      <select id="tier-filter" aria-label="Tier filter">${optionList(tiers, state.tierFilter, "All tiers")}</select>
      <select id="score-filter" aria-label="Score filter">${optionList(scores, state.scoreFilter, "All scores")}</select>
    </div>`);
  $("#tier-filter", box).addEventListener("change", (e) => {
    state.tierFilter = e.target.value;
    renderList();
  });
  $("#score-filter", box).addEventListener("change", (e) => {
    state.scoreFilter = e.target.value;
    renderList();
  });
  return box;
}

function visiblePapers() {
  const items = state.papers.filter((p) => {
    const id = p.custom_id;
    const st = paperStatus(id);
    // default queue: anything not yet completed by anyone (just keep labelling)
    if (state.filter === "queue" && completedByAnyone(id)) return false;
    if (state.filter === "mine" && st !== "progress") return false;
    if (state.filter === "done" && !completedByAnyone(id)) return false;
    if (state.filter === "disagree" && !hasDisagreement(id)) return false;
    if (state.tierFilter !== "all" && String(p.tier ?? "") !== state.tierFilter) return false;
    if (state.scoreFilter !== "all" && String(p.score ?? "—") !== state.scoreFilter) return false;
    // "all" applies no status filter
    if (state.search) {
      const hay = (id + " " + (p.title || "")).toLowerCase();
      if (!hay.includes(state.search)) return false;
    }
    return true;
  });
  return items;
}

function renderList() {
  const total = state.papers.length;
  const teamDone = total - queueCount();
  $("#who-progress").innerHTML =
    `<span class="bar"><span class="bar-fill" style="width:${total ? Math.round(100 * teamDone / total) : 0}%"></span></span>` +
    `${teamDone}/${total} done · ${myDoneCount()} by you`;
  buildFilters();
  const list = $("#paper-list");
  list.innerHTML = "";
  const items = visiblePapers();
  if (!items.length) {
    const msg = state.filter === "queue"
      ? "🎉 Nothing left to label — every paper has been completed."
      : "No papers match.";
    list.appendChild(el(`<div class="empty small">${msg}</div>`));
    return;
  }
  for (const p of items) {
    const st = paperStatus(p.custom_id);
    const dis = hasDisagreement(p.custom_id);
    const o = state.others[p.custom_id] || { done: [], progress: [] };
    const live = state.presence[p.custom_id] || [];
    const others = [];
    if (live.length) others.push(`<span class="live" title="Viewing now: ${esc(live.join(", "))}">● live</span>`);
    if (o.done.length) others.push(`<span class="oth done" title="Completed by: ${esc(o.done.join(", "))}">✓${o.done.length}</span>`);
    if (o.progress.length) others.push(`<span class="oth prog" title="In progress: ${esc(o.progress.join(", "))}">⋯${o.progress.length}</span>`);
    const item = el(`
      <button class="plitem ${p.custom_id === state.current ? "active" : ""} ${live.length ? "is-live" : ""}" data-id="${p.custom_id}">
        <span class="dot ${st}"></span>
        <span class="pmeta">
          <span class="pid">${esc(p.custom_id)} <span class="tchip ${tierClass(p.tier)}">${esc(p.tier ?? "?")}</span> <span class="schip">score ${esc(p.score ?? "—")}</span> ${dis ? '<span class="flag">⚠</span>' : ""}</span>
          <span class="ptitle">${esc(p.title || "")}</span>
        </span>
        ${others.length ? `<span class="others">${others.join("")}</span>` : ""}
      </button>`);
    item.addEventListener("click", () => openPaper(p.custom_id));
    list.appendChild(item);
  }
}

// ===========================================================================
// detail / step-by-step
// ===========================================================================
async function openPaper(id) {
  // never lose work: silently save the current draft before switching papers
  if (state.dirty && state.current && state.current !== id) await saveCurrent(false);
  if (state.current && state.current !== id) {
    track("paper_left", state.current, { active_seconds: timerSeconds(), steps_answered: answeredCount(state.current) });
  }
  state.current = id;
  timerReset();
  state.noted = new Set();
  track("paper_opened", id, { queue_left: queueCount() });
  trackPresence();          // tell everyone else I'm now on this paper
  renderList();
  renderDetail();
}

function refreshConflictBanner() {
  const node = document.getElementById("conflict-banner");
  if (!node) return;
  const id = state.current;
  const live = state.presence[id] || [];
  const o = state.others[id] || { done: [], progress: [] };
  let html = "";
  if (live.length) html += `<div class="cbanner live">🔴 <b>${esc(live.join(", "))}</b> ${live.length > 1 ? "are" : "is"} reviewing this paper right now — consider picking another.</div>`;
  if (o.done.length) html += `<div class="cbanner done">✓ Already completed by <b>${esc(o.done.join(", "))}</b>. You can skip it (or double-check).</div>`;
  else if (o.progress.length) html += `<div class="cbanner prog">⋯ In progress by <b>${esc(o.progress.join(", "))}</b>.</div>`;
  node.innerHTML = html;
}

function signalBadge(val) {
  if (val === true) return `<span class="badge yes">model: YES</span>`;
  if (val === false) return `<span class="badge no">model: NO</span>`;
  return `<span class="badge unk">model: —</span>`;
}

function renderDetail() {
  const p = state.byId[state.current];
  const root = $("#detail");
  if (!p) { root.innerHTML = `<div class="empty">Select a paper.</div>`; return; }
  const links = p.verified_links || {};

  root.innerHTML = "";
  root.appendChild(el(`<div id="conflict-banner"></div>`));
  // header
  root.appendChild(el(`
    <div class="dhead">
      <div class="dhead-top">
        <span class="pid big">${esc(p.custom_id)}</span>
        <span class="badge tier ${tierClass(p.tier)}">${esc(p.tier ?? "no tier")}</span>
        <span class="badge score">model score: ${esc(p.score ?? "—")}</span>
        <span class="badge web">run: ${esc(p.verification_status ?? p.web_verification ?? "—")}</span>
        <span class="counter">${queueCount()} left in queue</span>
      </div>
      <h2>${esc(p.title || "")}</h2>
      ${authorsLine(p) ? `<div class="authors">${esc(authorsLine(p))}</div>` : ""}
      <div class="quicklinks">
        <a href="${arxivAbs(p)}" target="_blank" rel="noopener">arXiv abs ↗</a>
        <a href="https://arxiv.org/pdf/${esc(p.custom_id)}" target="_blank" rel="noopener">PDF ↗</a>
        <a href="${gSearch(shortTitle(p))}" target="_blank" rel="noopener">Google ↗</a>
        <a href="https://scholar.google.com/scholar?q=${enc(shortTitle(p))}" target="_blank" rel="noopener">Scholar ↗</a>
        <a href="${ghSearch(p)}" target="_blank" rel="noopener">GitHub ↗</a>
        <a href="https://paperswithcode.com/search?q=${enc(shortTitle(p))}" target="_blank" rel="noopener">PwC ↗</a>
      </div>
    </div>`));
  $$(".quicklinks a", root).forEach((a) => a.addEventListener("click", () =>
    track("link_click", p.custom_id, { label: a.textContent.replace(" ↗", "") })));

  // abstract straight from arXiv — tells you what to search for
  if (p.abstract) {
    root.appendChild(collapsible("Abstract", `<div class="ctx"><p>${esc(p.abstract)}</p></div>`, true));
  }

  // context (collapsed so reviewers form their own view first)
  const ctxBox = collapsible("Paper context (claim / MRE) — open if you need it", `
    <div class="ctx"><b>Central claim</b><p>${esc(p.central_claim)}</p></div>
    <div class="ctx"><b>Claim evidence</b><p>${esc(p.claim_evidence)}</p></div>
    <div class="ctx"><b>MRE config</b><p>${esc(p.mre_config)}</p></div>`, false);
  ctxBox.querySelector("details").addEventListener("toggle", function () {
    if (this.open) trackOnce("context_opened", p.custom_id, null);
  });
  root.appendChild(ctxBox);

  // upstream extraction failed for a couple of papers — warn instead of
  // showing meaningless "model: —" badges silently
  if (!Object.keys(p.signals || {}).length) {
    root.appendChild(el(`<div class="cbanner prog">⚠ The model produced <b>no extraction</b> for this paper.
      Answer from your own search and explain in the notes — agree/disagree has no model value to compare against.</div>`));
  }
  if (p.verification_status === "incomplete" || p.verification_status === "degraded") {
    root.appendChild(el(`<div class="cbanner prog">⚠ Run health: <b>${esc(p.verification_status)}</b>
      (${esc(p.exit_reason || "unknown exit")}) — some signals may be guesses rather than tool-verified.
      Lean on your own search.</div>`));
  }

  // artifact steps (unlocked one at a time — see refreshStepLocks)
  stepCards = {};
  STEPS.forEach((step, i) => root.appendChild(renderStep(p, step, i + 1, links)));
  // score step
  root.appendChild(renderScoreStep(p, STEPS.length + 1));

  // what other reviewers labelled (collapsed so you form your own view first)
  root.appendChild(el(`<div id="others-panel"></div>`));

  // trace (on demand)
  if (p.has_trace && CFG.TRACE_BASE_URL) {
    const box = collapsible("🔍 Show model reasoning trace (loads on demand — may bias you)", `<div class="trace-body">Loading…</div>`, false);
    box.querySelector("details").addEventListener("toggle", function () {
      if (this.open && !this._loaded) {
        this._loaded = true;
        track("trace_opened", p.custom_id, null);
        loadTrace(p.custom_id, box.querySelector(".trace-body"));
      }
    });
    root.appendChild(box);
  }

  // footer: ONE primary action — you finish the four steps, then Save & next
  const footer = el(`
    <div class="dfooter">
      <span id="step-progress"></span>
      <span class="kbd-hint muted" title="Shortcuts work when you're not typing in a field">⌨ <b>a</b>gree · <b>d</b>isagree · <b>u</b>nsure → current step · <b>n</b> save+next</span>
      <span class="grow"></span>
      <span id="save-state" class="muted"></span>
      <button id="prev-btn" class="linkish">← previous</button>
      <button id="skip-btn" class="linkish">skip for now →</button>
      <button id="save-next-btn" class="cta">Save &amp; next paper →</button>
    </div>`);
  root.appendChild(footer);
  $("#prev-btn").addEventListener("click", () => navRelative(-1));
  $("#skip-btn").addEventListener("click", skipPaper);
  $("#save-next-btn").addEventListener("click", () => saveCurrent(true));
  refreshStepLocks();
  updateStepProgress();
  refreshScorePanel();
  refreshConflictBanner();
  refreshOthersPanel();
}

// ---- other reviewers' labels (compare panel) ------------------------------
// effective answer for an arbitrary reviewer row (no "Your answer" prefix)
function effectiveAnswer(step, p, row) {
  const v = row[`${step.key}_verdict`];
  if (!v) return "";
  if (v === "unsure") return "unsure";
  const mv = ((p.signals || {})[step.signal] || {}).value;
  if (typeof mv !== "boolean") return "answered (model gave no value)";
  const eff = v === "agree" ? mv : !mv;
  return `${step.noun} — ${eff ? "YES" : "NO"}`;
}

// What everyone else recorded for the current paper: per-signal verdicts,
// effective YES/NO, notes, found links, and their computed score/tier.
function otherReviewerCard(p, row) {
  const sc = reviewerScore(p, row);
  const rows = STEPS.map((step) => {
    const eff = effectiveAnswer(step, p, row);
    const note = row[`${step.key}_note`];
    const found = step.foundKey ? row[step.foundKey] : null;
    if (!eff && !note && !found) return "";
    return `<div class="orow">
      <div class="ostep">${esc(step.q)}</div>
      <div class="oeff">${eff ? esc(eff) : "<span class=\"muted\">—</span>"}</div>
      ${note ? `<div class="onote">“${esc(note)}”</div>` : ""}
      ${found ? `<div class="ofound"><a href="${esc(found)}" target="_blank" rel="noopener">${esc(found)}</a></div>` : ""}
    </div>`;
  }).join("");
  const scoreNote = row.score_note ? `<div class="onote">“${esc(row.score_note)}”</div>` : "";
  const scoreSugg = (row.score_verdict === "disagree" && row.score_suggested != null)
    ? ` · suggested ${esc(row.score_suggested)}` : "";
  return `<div class="ocard">
    <div class="ohead">
      <b>${esc(row.reviewer)}</b>
      <span class="badge ${row.status === "completed" ? "yes" : "unk"}">${esc(row.status === "completed" ? "completed" : "in progress")}</span>
      ${sc ? `<span class="badge tier ${tierClass(sc.tier)}">${esc(sc.tier)} · score ${sc.score}</span>` : ""}
      ${row.score_verdict ? `<span class="muted">score: ${esc(row.score_verdict)}${scoreSugg}</span>` : ""}
    </div>
    ${rows || `<div class="muted small">No per-signal verdicts recorded.</div>`}
    ${scoreNote}
  </div>`;
}

function refreshOthersPanel() {
  const node = document.getElementById("others-panel");
  if (!node) return;
  const p = state.byId[state.current];
  const rows = (state.othersFull[state.current] || []).slice()
    .sort((a, b) => (a.reviewer || "").localeCompare(b.reviewer || ""));
  if (!p || !rows.length) { node.innerHTML = ""; return; }
  const wasOpen = !!node.querySelector("details[open]");
  const body = `<div class="others-body">${rows.map((r) => otherReviewerCard(p, r)).join("")}</div>`;
  node.innerHTML = "";
  node.appendChild(collapsible(
    `👥 What other reviewers labelled (${rows.length}) — open to compare (may bias you)`,
    body, wasOpen));
  if (!wasOpen) {
    node.querySelector("details").addEventListener("toggle", function () {
      if (this.open) trackOnce("others_opened", state.current, { reviewers: rows.length });
    }, { once: true });
  }
}

let stepCards = {};   // step.key -> card element for the currently open paper

// what the reviewer's verdict actually means, e.g. "Your answer: NO — code is available: no"
function effectiveText(step, p, d) {
  const v = d[`${step.key}_verdict`];
  if (!v) return "";
  if (v === "unsure") return "Your answer: unsure";
  const mv = ((p.signals || {})[step.signal] || {}).value;
  if (typeof mv !== "boolean") return "Your answer recorded (model gave no value)";
  const eff = v === "agree" ? mv : !mv;
  return `Your answer: ${step.noun} — ${eff ? "YES" : "NO"}`;
}

function renderStep(p, step, n, links) {
  const d = draft(p.custom_id);
  const sig = (p.signals || {})[step.signal] || {};
  const modelLinks = step.linkKey ? (links[step.linkKey] || []) : [];
  const verdictField = `${step.key}_verdict`;
  const noteField = `${step.key}_note`;

  const card = el(`
    <div class="step ${d[verdictField] ? "answered" : ""}">
      <div class="step-h"><span class="stepn">${n}</span><h3>${esc(step.q)}</h3>${signalBadge(sig.value)}</div>
      <p class="guide">${esc(step.guide)}</p>
      <details class="ev"><summary>Model's evidence</summary><p>${esc(sig.evidence || "(none)")}</p></details>
      ${modelLinks.length ? `<div class="mlinks"><b>Model links:</b> ${modelLinks.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a>`).join(" ")}</div>` : ""}
      <div class="searchrow">${step.searches(p).map(([lab, url]) => `<a class="searchbtn" data-lab="${esc(lab)}" href="${esc(url)}" target="_blank" rel="noopener">Search: ${esc(lab)} ↗</a>`).join("")}</div>
      <div class="verdicts">${VERDICTS.map((v) => `<button class="vbtn ${d[verdictField] === v ? "sel " + v : ""}" data-v="${v}">${v === "agree" ? "✓ Agree" : v === "disagree" ? "✗ Disagree" : "? Unsure"}</button>`).join("")}<span class="effective">${esc(effectiveText(step, p, d))}</span></div>
      ${step.foundKey ? `<input class="found" type="url" placeholder="Link you found (optional)" value="${esc(d[step.foundKey] || "")}" />` : ""}
      <textarea class="note" placeholder="Note (what you found / why you disagree)">${esc(d[noteField] || "")}</textarea>
    </div>`);

  $$(".vbtn", card).forEach((b) => b.addEventListener("click", () => {
    const prev = d[verdictField] || null;
    d[verdictField] = b.dataset.v;
    markDirty();
    track("verdict_set", state.current, { step: step.key, verdict: b.dataset.v, prev, via: "click", seconds_in: timerSeconds() });
    renderStep_refresh(card, step, d);
    scrollToNextOpenStep();
  }));
  $$(".searchbtn", card).forEach((a) => a.addEventListener("click", () =>
    track("search_click", state.current, { step: step.key, label: a.dataset.lab })));
  $(".ev", card).addEventListener("toggle", function () {
    if (this.open) trackOnce("evidence_opened", step.key, { step: step.key });
  });
  $(".note", card).addEventListener("input", (e) => {
    d[noteField] = e.target.value; markDirty();
    trackOnce("note_edited", step.key, { step: step.key });
  });
  if (step.foundKey) $(".found", card).addEventListener("input", (e) => {
    d[step.foundKey] = e.target.value; markDirty();
    trackOnce("found_url", step.key, { step: step.key });
  });
  stepCards[step.key] = card;
  return card;
}

function renderStep_refresh(card, step, d) {
  const f = `${step.key}_verdict`;
  card.classList.toggle("answered", !!d[f]);
  $$(".vbtn", card).forEach((b) => {
    const on = d[f] === b.dataset.v;
    b.className = "vbtn" + (on ? " sel " + b.dataset.v : "");
  });
  const eff = $(".effective", card);
  if (eff) eff.textContent = effectiveText(step, state.byId[state.current], d);
  refreshStepLocks();
  updateStepProgress();
  refreshScorePanel();
  renderList();
}

// guided flow: only the current step is open; later steps stay locked until
// the one before them is answered. Answered steps stay editable.
function refreshStepLocks() {
  const d = draft(state.current);
  const firstOpen = STEPS.findIndex((s) => !d[`${s.key}_verdict`]);
  STEPS.forEach((s, i) => {
    const card = stepCards[s.key];
    if (!card) return;
    card.classList.toggle("locked", firstOpen !== -1 && i > firstOpen);
    card.classList.toggle("current", i === firstOpen);
  });
}

function scrollToNextOpenStep() {
  const d = draft(state.current);
  const next = STEPS.find((s) => !d[`${s.key}_verdict`]);
  const target = next ? stepCards[next.key] : document.getElementById("score-result");
  if (target) target.scrollIntoView({ block: "center", behavior: "smooth" });
}

// shake + highlight the step that still needs an answer
function nudgeFirstOpenStep() {
  const d = draft(state.current);
  const step = STEPS.find((s) => !d[`${s.key}_verdict`]);
  if (!step) return;
  const card = stepCards[step.key];
  if (card) {
    card.scrollIntoView({ block: "center", behavior: "smooth" });
    card.classList.remove("nudge"); void card.offsetWidth;
    card.classList.add("nudge");
    card.addEventListener("animationend", () => card.classList.remove("nudge"), { once: true });
  }
  const s = $("#save-state");
  if (s) s.textContent = `answer all ${VERDICT_FIELDS.length} steps before moving on (or skip)`;
  track("blocked_next", state.current, { steps_answered: answeredCount(state.current) });
}

// --- keyboard shortcuts: a/d/u verdict on first open step, n/p navigation ---
const KEY_VERDICT = { a: "agree", d: "disagree", u: "unsure" };
document.addEventListener("keydown", (e) => {
  if (!state.reviewer) return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
  if ($("#view-verify").classList.contains("hidden") || !state.current) return;
  const k = e.key.toLowerCase();
  if (k === "n") { e.preventDefault(); saveCurrent(true); return; }
  if (k === "p") { e.preventDefault(); navRelative(-1); return; }
  const verdict = KEY_VERDICT[k];
  if (!verdict) return;
  const d = draft(state.current);
  const step = STEPS.find((s) => !d[`${s.key}_verdict`]);
  if (!step) return;
  e.preventDefault();
  d[`${step.key}_verdict`] = verdict;
  markDirty();
  track("verdict_set", state.current, { step: step.key, verdict, prev: null, via: "keyboard", seconds_in: timerSeconds() });
  renderStep_refresh(stepCards[step.key], step, d);
  scrollToNextOpenStep();
});

// don't let a tab close eat unsaved verdicts
window.addEventListener("beforeunload", (e) => {
  if (state.dirty) { e.preventDefault(); e.returnValue = ""; }
});

function renderScoreStep(p, n) {
  const d = draft(p.custom_id);
  const card = el(`
    <div class="step score-step">
      <div class="step-h"><span class="stepn">${n}</span><h3>Score &amp; difficulty tier (computed from your verdicts)</h3></div>
      <p class="guide">You don't score this directly — it's derived from the four artifact steps with the project's formula
        <code>(no code +2) + (no dataset &amp; non-standard +3) + (no weights +1)</code>. Answer those steps and it fills in.</p>
      <div id="score-result"></div>
      <textarea class="note" placeholder="Optional note on the score / difficulty">${esc(d.score_note || "")}</textarea>
    </div>`);
  $(".note", card).addEventListener("input", (e) => {
    d.score_note = e.target.value; markDirty();
    trackOnce("note_edited", "score", { step: "score" });
  });
  return card;
}

function refreshScorePanel() {
  const node = document.getElementById("score-result");
  if (!node) return;
  const p = state.byId[state.current];
  const rs = reviewerScore(p);
  if (!rs) {
    node.innerHTML = `<div class="score-row pending">Answer the four artifact steps (agree/disagree — not unsure) to compute your score.</div>`;
    return;
  }
  const match = rs.score === p.score;
  node.innerHTML = `
    <div class="score-row ${match ? "match" : "mismatch"}">
      <div class="score-box"><span class="l">Your computed</span><span class="v">${rs.score} · ${esc(rs.tier)}</span></div>
      <div class="score-box muted-box"><span class="l">Model</span><span class="v">${esc(p.score ?? "—")} · ${esc(p.tier ?? "—")}</span></div>
      <div class="score-verdict">${match ? "✓ matches the model" : "✗ differs from the model"}</div>
    </div>`;
}

function updateStepProgress() {
  const done = answeredCount(state.current);
  const total = VERDICT_FIELDS.length;
  const node = $("#step-progress");
  if (node) node.innerHTML =
    `<span class="bar"><span class="bar-fill" style="width:${total ? Math.round(100 * done / total) : 0}%"></span></span>` +
    `<b>${done}/${total}</b> steps answered ${done === total ? '<span class="ok">— ready ✓</span>' : ""}`;
  // the single primary action only arms once every step is answered
  const cta = $("#save-next-btn");
  if (cta) {
    const ready = done === total;
    cta.disabled = !ready;
    cta.classList.toggle("ready", ready);
    cta.innerHTML = ready ? "✓ Save &amp; next paper →" : `Answer all ${total} steps to continue (${done}/${total})`;
  }
}

function markDirty() {
  state.dirty = true;
  const s = $("#save-state"); if (s) s.textContent = "unsaved changes";
}

function collapsible(summary, innerHTML, open) {
  return el(`<div class="collapse"><details ${open ? "open" : ""}><summary>${esc(summary)}</summary>${innerHTML}</details></div>`);
}

async function loadTrace(id, target) {
  try {
    const res = await fetch(`${CFG.TRACE_BASE_URL}/${id}.json`);
    if (!res.ok) throw new Error(res.status);
    const doc = await res.json();
    target.innerHTML = doc.messages.map((m) => `
      <div class="tmsg ${esc(m.role)}">
        <div class="trole">${esc(m.role)}${m.name ? " · " + esc(m.name) : ""}</div>
        ${m.content ? `<pre>${esc(m.content)}</pre>` : ""}
        ${(m.tool_calls || []).map((c) => `<div class="tcall"><b>→ ${esc(c.name)}</b><pre>${esc(c.arguments)}</pre></div>`).join("")}
      </div>`).join("");
  } catch (e) {
    target.innerHTML = `<div class="empty small">Trace unavailable (${esc(e.message)}). Has it been uploaded to Storage?</div>`;
  }
}

// ===========================================================================
// save / navigate
// ===========================================================================
function navRelative(delta) {
  const items = visiblePapers();
  const i = items.findIndex((x) => x.custom_id === state.current);
  const next = items[i + delta];
  if (delta < 0) track("nav_prev", state.current, null);
  if (next) openPaper(next.custom_id);
  else if (delta > 0 && state.filter === "queue") {
    const s = $("#save-state");
    if (s) s.textContent = "🎉 queue complete — nothing left to label";
  }
}

// explicit escape hatch: keeps the draft, logs the skip, moves on
async function skipPaper() {
  track("skipped", state.current, { active_seconds: timerSeconds(), steps_answered: answeredCount(state.current) });
  if (state.dirty) await saveCurrent(false);
  navRelative(1);
}

async function saveCurrent(advance) {
  if (!state.current) return;
  const p = state.byId[state.current];
  const d = draft(state.current);
  const completed = VERDICT_FIELDS.every((f) => d[f]);
  if (advance && !completed) {
    // guided flow: can't move on until all four steps are answered (skip to bail)
    if (state.dirty) await saveCurrent(false);
    nudgeFirstOpenStep();
    return;
  }
  const wasCompleted = state.saved[state.current]?.status === "completed";
  const rs = reviewerScore(p);   // computed from the four verdicts
  const payload = {
    paper_id: state.current,
    reviewer: state.reviewer,
    code_verdict: d.code_verdict || null, code_note: d.code_note || null, found_code_url: d.found_code_url || null,
    dataset_verdict: d.dataset_verdict || null, dataset_note: d.dataset_note || null, found_dataset_url: d.found_dataset_url || null,
    weights_verdict: d.weights_verdict || null, weights_note: d.weights_note || null, found_weights_url: d.found_weights_url || null,
    dataset_standard_verdict: d.dataset_standard_verdict || null, dataset_standard_note: d.dataset_standard_note || null,
    score_verdict: rs ? (rs.score === p.score ? "agree" : "disagree") : null,
    score_suggested: rs ? rs.score : null,
    score_note: d.score_note || null,
    status: completed ? "completed" : "in_progress",
  };
  const s = $("#save-state");
  if (!sb) { if (s) s.textContent = "⚠ Supabase not configured — not saved"; return; }
  if (s) s.textContent = "saving…";
  const { data, error } = await sb.from("verifications")
    .upsert(payload, { onConflict: "paper_id,reviewer" }).select().single();
  if (error) { if (s) s.textContent = "⚠ save failed: " + error.message; console.error(error); return; }
  state.saved[state.current] = data;
  state.drafts[state.current] = { ...data };
  state.dirty = false;
  if (s) s.textContent = "saved ✓";
  track(completed && !wasCompleted ? "completed" : "saved", state.current, {
    active_seconds: timerSeconds(),
    steps_answered: answeredCount(state.current),
    disagreed_on: VERDICT_FIELDS.filter((f) => d[f] === "disagree").map((f) => f.replace("_verdict", "")),
    score_match: rs ? rs.score === p.score : null,
  });
  renderList();
  if (advance) navRelative(1);
}

// ===========================================================================
// views
// ===========================================================================
function setView(view) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  $("#view-verify").classList.toggle("hidden", view !== "verify");
  $("#view-dashboard").classList.toggle("hidden", view !== "dashboard");
  if (view === "dashboard") renderDashboard();
}

// ===========================================================================
// dashboard (admin)
// ===========================================================================
let dashSub = null;
async function renderDashboard() {
  const root = $("#dashboard");
  root.innerHTML = `<div class="empty">Loading dashboard…</div>`;
  if (!sb) { root.innerHTML = `<div class="empty">Supabase not configured.</div>`; return; }

  const [{ data: vrows }, { data: arows }, { data: trows }] = await Promise.all([
    sb.from("verifications").select("*"),
    sb.from("activity").select("*").order("created_at", { ascending: false }).limit(60),
    sb.from("activity").select("reviewer,action,detail")
      .in("action", ["completed", "search_click", "skipped", "blocked_next", "trace_opened"])
      .order("created_at", { ascending: false }).limit(8000),
  ]);
  const verifs = vrows || [];
  const total = state.papers.length;

  // behaviour stats from telemetry (time per paper, search usage, skips…)
  const beh = {};
  for (const t of trows || []) {
    const b = beh[t.reviewer] || (beh[t.reviewer] = { times: [], searches: 0, skips: 0, blocked: 0, traces: 0 });
    let det = {};
    try { det = t.detail ? JSON.parse(t.detail) : {}; } catch (e) { /* old plain-text rows */ }
    if (t.action === "completed" && det.active_seconds != null) b.times.push(det.active_seconds);
    if (t.action === "search_click") b.searches++;
    if (t.action === "skipped") b.skips++;
    if (t.action === "blocked_next") b.blocked++;
    if (t.action === "trace_opened") b.traces++;
  }
  const median = (xs) => {
    if (!xs.length) return null;
    const s = [...xs].sort((a, b) => a - b);
    return s[Math.floor(s.length / 2)];
  };
  const fmtDur = (sec) => sec == null ? "—" : sec < 90 ? `${sec}s` : `${Math.round(sec / 60)}m`;

  // per reviewer
  const reviewers = {};
  for (const r of verifs) {
    const x = reviewers[r.reviewer] || (reviewers[r.reviewer] = { name: r.reviewer, done: 0, prog: 0, dis: 0, last: r.updated_at });
    if (r.status === "completed") x.done++; else x.prog++;
    if (VERDICT_FIELDS.some((f) => r[f] === "disagree")) x.dis++;
    if (r.updated_at > x.last) x.last = r.updated_at;
  }
  const covered = new Set(verifs.map((r) => r.paper_id));
  const completedPapers = new Set(verifs.filter((r) => r.status === "completed").map((r) => r.paper_id));
  const disagreements = verifs.filter((r) => VERDICT_FIELDS.some((f) => r[f] === "disagree"));

  root.innerHTML = `
    <div class="cards">
      <div class="kpi"><div class="n">${total}</div><div class="l">papers</div></div>
      <div class="kpi"><div class="n">${covered.size}</div><div class="l">reviewed ≥1×</div></div>
      <div class="kpi"><div class="n">${completedPapers.size}</div><div class="l">fully completed</div></div>
      <div class="kpi"><div class="n">${Object.keys(reviewers).length}</div><div class="l">reviewers</div></div>
      <div class="kpi warn"><div class="n">${disagreements.length}</div><div class="l">disagreements</div></div>
    </div>

    <div class="dash-grid">
      <section class="panel">
        <div class="panel-h"><h3>Reviewers</h3><button id="export-csv" class="secondary">Export CSV</button></div>
        <table class="tbl">
          <thead><tr><th>Reviewer</th><th>Completed</th><th>In progress</th><th>Disagreements</th>
            <th title="Median active time per completed paper">Time/paper</th>
            <th title="Search-shortcut clicks">Searches</th><th>Skips</th>
            <th title="Tried Save & next before answering all 4 steps">Blocked</th><th>Last active</th></tr></thead>
          <tbody>${Object.values(reviewers).sort((a, b) => b.done - a.done).map((x) => {
            const b = beh[x.name] || { times: [], searches: 0, skips: 0, blocked: 0 };
            return `<tr><td>${esc(x.name)}</td><td>${x.done}</td><td>${x.prog}</td><td>${x.dis}</td>
              <td>${fmtDur(median(b.times))}</td><td>${b.searches}</td><td>${b.skips}</td><td>${b.blocked}</td>
              <td>${fmtTime(x.last)}</td></tr>`;
          }).join("")
            || `<tr><td colspan="9" class="muted">No reviews yet.</td></tr>`}</tbody>
        </table>
      </section>

      <section class="panel">
        <div class="panel-h"><h3>Live activity</h3></div>
        <div id="feed" class="feed">${(arows || []).map(feedRow).join("") || `<div class="muted">No activity yet.</div>`}</div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-h"><h3>Disagreements with the model</h3></div>
      <table class="tbl">
        <thead><tr><th>Paper</th><th>Reviewer</th><th>Signals flagged</th><th>Their score</th><th>Notes</th></tr></thead>
        <tbody>${disagreements.map((r) => `
          <tr>
            <td><a href="${arxivAbs({ custom_id: r.paper_id })}" target="_blank" rel="noopener">${esc(r.paper_id)}</a></td>
            <td>${esc(r.reviewer)}</td>
            <td>${VERDICT_FIELDS.filter((f) => r[f] === "disagree").map((f) => f.replace("_verdict", "")).join(", ")}</td>
            <td>${r.score_suggested ?? "—"}</td>
            <td class="notes">${esc([r.code_note, r.dataset_note, r.weights_note, r.dataset_standard_note, r.score_note].filter(Boolean).join(" · "))}</td>
          </tr>`).join("") || `<tr><td colspan="5" class="muted">No disagreements logged.</td></tr>`}</tbody>
      </table>
    </section>`;

  $("#export-csv").addEventListener("click", () => exportCsv(verifs));

  // live feed
  if (dashSub) { sb.removeChannel(dashSub); dashSub = null; }
  dashSub = sb.channel("activity-feed")
    .on("postgres_changes", { event: "INSERT", schema: "public", table: "activity" }, (payload) => {
      const feed = $("#feed");
      if (feed) feed.insertAdjacentHTML("afterbegin", feedRow(payload.new));
    }).subscribe();
}

function feedRow(a) {
  let extra = "";
  if (a.detail) {
    try {
      const d = JSON.parse(a.detail);
      extra = Object.entries(d)
        .filter(([, v]) => v != null && String(v).length)
        .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("/") : v}`).join(" · ");
    } catch (e) { extra = a.detail; }
  }
  return `<div class="frow"><span class="ftime">${fmtTime(a.created_at)}</span> <b>${esc(a.reviewer)}</b> ${esc(a.action)} ${a.paper_id ? `<span class="fid">${esc(a.paper_id)}</span>` : ""}${extra ? ` <span class="fdetail">${esc(extra)}</span>` : ""}</div>`;
}
function fmtTime(t) {
  if (!t) return "—";
  const d = new Date(t);
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function exportCsv(rows) {
  const cols = ["paper_id", "reviewer", "status", "code_verdict", "dataset_verdict", "weights_verdict",
    "dataset_standard_verdict", "score_verdict", "score_suggested",
    "found_code_url", "found_dataset_url", "found_weights_url",
    "code_note", "dataset_note", "weights_note", "dataset_standard_note", "score_note", "updated_at"];
  const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(",")].concat(rows.map((r) => cols.map((c) => q(r[c])).join(","))).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `verifications_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}
