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
  presence: {},      // paper_id -> [names] viewing RIGHT NOW (everyone else)
  current: null,     // paper_id
  filter: "queue",
  search: "",
  dirty: false,
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
  $("#gate").classList.add("hidden");
  $("#app").classList.remove("hidden");

  await loadMyVerifications();
  await loadAllVerifications();
  startLiveSync();
  logActivity("login", null, null);
  buildFilters();
  renderList();
  setView("verify");
  const first = visiblePapers()[0];     // drop the reviewer straight into the next unprocessed paper
  if (first) openPaper(first.custom_id);
}

function signOut() {
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
  if (!sb) return;
  const { data, error } = await sb.from("verifications").select("paper_id,reviewer,status");
  if (error) { console.error(error); return; }
  for (const r of data || []) {
    if (r.reviewer === state.reviewer) continue;
    const m = state.others[r.paper_id] || (state.others[r.paper_id] = { done: [], progress: [] });
    (r.status === "completed" ? m.done : m.progress).push(r.reviewer);
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
// completion = the four artifact signals (the score is computed from them)
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
function reviewerSignals(p) {
  const d = draft(p.custom_id);
  const sig = p.signals || {};
  const out = {};
  for (const step of STEPS) {
    const mv = (sig[step.signal] || {}).value;
    const v = d[`${step.key}_verdict`];
    out[step.key] = typeof mv === "boolean"
      ? (v === "agree" ? mv : v === "disagree" ? !mv : null)
      : null;
  }
  return out;
}

// reviewer's computed score/tier, or null if any signal is unsure/unanswered
function reviewerScore(p) {
  const e = reviewerSignals(p);
  if ([e.code, e.dataset, e.weights, e.dataset_standard].some((x) => x === null)) return null;
  const score = scoreFromSignals(e.code, e.dataset, e.weights, e.dataset_standard);
  return { score, tier: tierFromScore(score, e.dataset, e.dataset_standard) };
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
  $("#filters").innerHTML = "";
  for (const [key, label] of filters) {
    const b = el(`<button class="filt ${key === state.filter ? "active" : ""}" data-f="${key}">${label} <span class="fcount">${counts[key]}</span></button>`);
    b.addEventListener("click", () => { state.filter = key; renderList(); });
    $("#filters").appendChild(b);
  }
}

function visiblePapers() {
  return state.papers.filter((p) => {
    const id = p.custom_id;
    const st = paperStatus(id);
    // default queue: anything not yet completed by anyone (just keep labelling)
    if (state.filter === "queue" && completedByAnyone(id)) return false;
    if (state.filter === "mine" && st !== "progress") return false;
    if (state.filter === "done" && !completedByAnyone(id)) return false;
    if (state.filter === "disagree" && !hasDisagreement(id)) return false;
    // "all" applies no status filter
    if (state.search) {
      const hay = (id + " " + (p.title || "")).toLowerCase();
      if (!hay.includes(state.search)) return false;
    }
    return true;
  });
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
          <span class="pid">${esc(p.custom_id)} <span class="tchip ${tierClass(p.tier)}">${esc(p.tier ?? "?")}</span> ${dis ? '<span class="flag">⚠</span>' : ""}</span>
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
  state.current = id;
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
  const idx = state.papers.findIndex((x) => x.custom_id === p.custom_id);
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
        <span class="badge web">web: ${esc(p.web_verification ?? "—")}</span>
        ${p.h100_hours_estimate != null ? `<span class="badge web" title="${esc(p.h100_estimate_basis || "")}">~${esc(p.h100_hours_estimate)} H100·h</span>` : ""}
        <span class="counter">${idx + 1} / ${state.papers.length}</span>
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

  // abstract straight from arXiv — tells you what to search for
  if (p.abstract) {
    root.appendChild(collapsible("Abstract", `<div class="ctx"><p>${esc(p.abstract)}</p></div>`, true));
  }

  // context (collapsed so reviewers form their own view first)
  root.appendChild(collapsible("Paper context (claim / MRE) — open if you need it", `
    <div class="ctx"><b>Central claim</b><p>${esc(p.central_claim)}</p></div>
    <div class="ctx"><b>Claim evidence</b><p>${esc(p.claim_evidence)}</p></div>
    <div class="ctx"><b>MRE config</b><p>${esc(p.mre_config)}</p></div>`, false));

  // upstream extraction failed for a couple of papers — warn instead of
  // showing meaningless "model: —" badges silently
  if (!Object.keys(p.signals || {}).length) {
    root.appendChild(el(`<div class="cbanner prog">⚠ The model produced <b>no extraction</b> for this paper.
      Answer from your own search and explain in the notes — agree/disagree has no model value to compare against.</div>`));
  }

  // artifact steps
  stepCards = {};
  STEPS.forEach((step, i) => root.appendChild(renderStep(p, step, i + 1, links)));
  // score step
  root.appendChild(renderScoreStep(p, STEPS.length + 1));

  // trace (on demand)
  if (p.has_trace && CFG.TRACE_BASE_URL) {
    const box = collapsible("🔍 Show model reasoning trace (loads on demand — may bias you)", `<div class="trace-body">Loading…</div>`, false);
    box.querySelector("details").addEventListener("toggle", function () {
      if (this.open && !this._loaded) { this._loaded = true; loadTrace(p.custom_id, box.querySelector(".trace-body")); }
    });
    root.appendChild(box);
  }

  // footer
  const footer = el(`
    <div class="dfooter">
      <span id="step-progress"></span>
      <span class="kbd-hint muted" title="Shortcuts work when you're not typing in a field">⌨ <b>a</b>gree · <b>d</b>isagree · <b>u</b>nsure → first open step · <b>n</b> save+next · <b>p</b> prev</span>
      <span class="grow"></span>
      <span id="save-state" class="muted"></span>
      <button id="prev-btn" class="secondary">← Prev</button>
      <button id="save-btn">Save</button>
      <button id="save-next-btn">Save &amp; next →</button>
    </div>`);
  root.appendChild(footer);
  $("#prev-btn").addEventListener("click", () => navRelative(-1));
  $("#save-btn").addEventListener("click", () => saveCurrent(false));
  $("#save-next-btn").addEventListener("click", () => saveCurrent(true));
  updateStepProgress();
  refreshScorePanel();
  refreshConflictBanner();
  logActivity("opened", p.custom_id, null);
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
      <div class="searchrow">${step.searches(p).map(([lab, url]) => `<a class="searchbtn" href="${esc(url)}" target="_blank" rel="noopener">Search: ${esc(lab)} ↗</a>`).join("")}</div>
      <div class="verdicts">${VERDICTS.map((v) => `<button class="vbtn ${d[verdictField] === v ? "sel " + v : ""}" data-v="${v}">${v === "agree" ? "✓ Agree" : v === "disagree" ? "✗ Disagree" : "? Unsure"}</button>`).join("")}<span class="effective">${esc(effectiveText(step, p, d))}</span></div>
      ${step.foundKey ? `<input class="found" type="url" placeholder="Link you found (optional)" value="${esc(d[step.foundKey] || "")}" />` : ""}
      <textarea class="note" placeholder="Note (what you found / why you disagree)">${esc(d[noteField] || "")}</textarea>
    </div>`);

  $$(".vbtn", card).forEach((b) => b.addEventListener("click", () => {
    d[verdictField] = b.dataset.v;
    markDirty();
    renderStep_refresh(card, step, d);
  }));
  $(".note", card).addEventListener("input", (e) => { d[noteField] = e.target.value; markDirty(); });
  if (step.foundKey) $(".found", card).addEventListener("input", (e) => { d[step.foundKey] = e.target.value; markDirty(); });
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
  updateStepProgress();
  refreshScorePanel();
  renderList();
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
  renderStep_refresh(stepCards[step.key], step, d);
  const next = STEPS.find((s) => !d[`${s.key}_verdict`]);
  const target = stepCards[(next || step).key];
  if (target) target.scrollIntoView({ block: "center", behavior: "smooth" });
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
      <p class="guide">You don't score this directly — it's derived from steps 1–4 with the project's formula
        <code>(no code +2) + (no dataset &amp; non-standard +3) + (no weights +1)</code>. Answer the four steps above and it fills in.</p>
      <div id="score-result"></div>
      <textarea class="note" placeholder="Optional note on the score / difficulty">${esc(d.score_note || "")}</textarea>
    </div>`);
  $(".note", card).addEventListener("input", (e) => { d.score_note = e.target.value; markDirty(); });
  return card;
}

function refreshScorePanel() {
  const node = document.getElementById("score-result");
  if (!node) return;
  const p = state.byId[state.current];
  const rs = reviewerScore(p);
  if (!rs) {
    node.innerHTML = `<div class="score-row pending">Answer steps 1–4 (agree/disagree — not unsure) to compute your score.</div>`;
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
  const d = state.drafts[state.current] || {};
  const done = VERDICT_FIELDS.filter((f) => d[f]).length;
  const node = $("#step-progress");
  if (node) node.innerHTML = `<b>${done}/${VERDICT_FIELDS.length}</b> steps answered ${done === VERDICT_FIELDS.length ? '<span class="ok">— ready to complete ✓</span>' : ""}`;
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
  if (next) openPaper(next.custom_id);
}

async function saveCurrent(advance) {
  if (!state.current) return;
  const p = state.byId[state.current];
  const d = draft(state.current);
  const completed = VERDICT_FIELDS.every((f) => d[f]);
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
  logActivity(completed && !wasCompleted ? "completed" : "saved", state.current, null);
  renderList();
  if (advance) navRelative(1);
}

async function logActivity(action, paperId, detail) {
  if (!sb) return;
  try { await sb.from("activity").insert({ reviewer: state.reviewer, paper_id: paperId, action, detail }); }
  catch (e) { /* non-fatal */ }
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

  const [{ data: vrows }, { data: arows }] = await Promise.all([
    sb.from("verifications").select("*"),
    sb.from("activity").select("*").order("created_at", { ascending: false }).limit(60),
  ]);
  const verifs = vrows || [];
  const total = state.papers.length;

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
          <thead><tr><th>Reviewer</th><th>Completed</th><th>In progress</th><th>Disagreements</th><th>Last active</th></tr></thead>
          <tbody>${Object.values(reviewers).sort((a, b) => b.done - a.done).map((x) => `
            <tr><td>${esc(x.name)}</td><td>${x.done}</td><td>${x.prog}</td><td>${x.dis}</td><td>${fmtTime(x.last)}</td></tr>`).join("")
            || `<tr><td colspan="5" class="muted">No reviews yet.</td></tr>`}</tbody>
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
  return `<div class="frow"><span class="ftime">${fmtTime(a.created_at)}</span> <b>${esc(a.reviewer)}</b> ${esc(a.action)} ${a.paper_id ? `<span class="fid">${esc(a.paper_id)}</span>` : ""}</div>`;
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
