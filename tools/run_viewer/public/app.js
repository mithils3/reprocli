/* app.js — boot + wiring. New IA: OVERVIEW (default worksheet) → PAPERS (by claim)
   → a paper → LIVE transcript (strip chart). Three sources, one renderer:
   Local = drop a transcript → parseTranscript → renderRun; Live = list runs from
   Supabase, open one, stream rounds via Realtime; Overview/Papers = aggregate the
   run rows + lockfile estimates. The data layer (supabase-data/tags/estimates) is
   unchanged — this is presentation + navigation. */
"use strict";

const R = window.RENDER;
const state = {
  view: "overview", runs: [], byId: {}, filter: "all", excludeDead: false, excludeRoundLimit: false,
  search: "", tagFilter: window.TagFilter.create(),
  currentRunId: null, liveRun: null, liveEvents: [], seenSeq: new Set(), runChannel: null, remote: false,
};
const $ = (s) => document.querySelector(s);
const liveDetail = () => $("#live-detail");

// ---- view switching --------------------------------------------------------
function setView(v) {
  state.view = v;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === v));
  document.querySelectorAll(".view").forEach((m) => m.classList.add("hidden"));
  const el = $("#view-" + v);
  if (el) el.classList.remove("hidden");
  const tog = $("#sidebar-toggle"); if (tog) tog.style.display = v === "live" ? "" : "none";
  if (v === "overview" && window.Overview) window.Overview.open();
  if (v === "papers" && window.Papers) window.Papers.open();
  if (v === "stats" && window.Stats) window.Stats.open();
}
window.setView = setView;
window.openPaper = (arxiv) => { setView("papers"); if (window.Papers) window.Papers.openPaper(arxiv); };

// ---- run list (Live) -------------------------------------------------------
const FILTERS = [["all", "All"], ["running", "Running"], ["dead", "Dead"], ["finished", "Finished"], ["error", "Error"]];
function renderFilters() {
  const chips = FILTERS.map(([k, l]) => `<button class="filt ${state.filter === k ? "active" : ""}" data-f="${k}">${l}</button>`).join("");
  const toggle = `<button class="filt excl-toggle ${state.excludeDead ? "active" : ""}" id="excl-dead-filt" title="hide runs with no update in ${R.DEAD_AFTER_HOURS}h">${state.excludeDead ? "Dead hidden" : "Exclude dead"}</button>`;
  const rlToggle = `<button class="filt excl-toggle ${state.excludeRoundLimit ? "active" : ""}" id="excl-rl-filt" title="hide runs that hit the tool-round limit">${state.excludeRoundLimit ? "Round-limit hidden" : "Exclude round-limit"}</button>`;
  $("#filters").innerHTML = chips + toggle + rlToggle;
  document.querySelectorAll("#filters .filt[data-f]").forEach((b) => b.addEventListener("click", () => { state.filter = b.dataset.f; renderFilters(); renderList(); }));
  $("#excl-dead-filt").addEventListener("click", () => { state.excludeDead = !state.excludeDead; renderFilters(); renderList(); });
  $("#excl-rl-filt").addEventListener("click", () => { state.excludeRoundLimit = !state.excludeRoundLimit; renderFilters(); renderList(); });
}
function visibleRuns() {
  const q = state.search.toLowerCase();
  return state.runs.filter((r) =>
    (state.filter === "all" || R.effectiveStatus(r) === state.filter) &&
    (!state.excludeDead || R.effectiveStatus(r) !== "dead") &&
    (!state.excludeRoundLimit || !R.isRoundLimit(r)) &&
    state.tagFilter.pass(r.run_id, window.Tags) &&
    (!q || (`${r.arxiv_id} ${r.model || ""} ${r.run_id} ${R.claimOf(r) || ""}`).toLowerCase().includes(q)));
}
function renderTagFilters() {
  const host = $("#tag-filters"); if (!host) return;
  state.tagFilter.render(host, window.Tags ? window.Tags.all() : [], () => { renderTagFilters(); renderList(); });
}
function renderList() {
  const list = $("#run-list"), rows = visibleRuns();
  list.innerHTML = "";
  if (!rows.length) { list.innerHTML = `<div class="empty small">${state.remote ? "No runs match." : "Supabase not reachable — use the Local tab."}</div>`; return; }
  for (const run of rows) {
    const item = R.renderRunListItem(run);
    if (run.run_id === state.currentRunId) item.classList.add("active");
    item.addEventListener("click", () => openRun(run.run_id));
    list.appendChild(item);
  }
}
function upsertRun(run) {
  if (!run || !run.run_id) return;
  state.byId[run.run_id] = Object.assign(state.byId[run.run_id] || {}, run);
  state.runs = Object.values(state.byId).sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
}
async function loadRunList() {
  if (!state.remote) { renderList(); return; }
  try { const runs = await window.RemoteSource.listRuns(); state.byId = {}; runs.forEach(upsertRun); renderList(); }
  catch (e) { state.remote = false; setConn(); renderList(); }
}

function onTagsChange() {
  renderTagFilters(); renderList();
  if (state.currentRunId) {
    const top = liveDetail().querySelector(".run-top");
    if (top) { const refocus = document.activeElement && document.activeElement.classList.contains("tag-input"); Tags.mount(top); if (refocus) { const i = top.querySelector(".tag-input"); if (i) i.focus(); } }
  }
  if (window.Overview && window.Overview.onTags) window.Overview.onTags();
  if (window.Papers && window.Papers.onTags) window.Papers.onTags();
  if (state.view === "stats" && window.Stats && window.Stats.onTags) window.Stats.onTags();
}

// ---- open + stream one run -------------------------------------------------
async function openRun(runId) {
  if (state.view !== "live") setView("live");
  state.currentRunId = runId; renderList();
  liveDetail().innerHTML = `<div class="empty">Loading ${R.esc(runId)}…</div>`;
  if (state.runChannel) { window.RemoteSource.unsubscribe(state.runChannel); state.runChannel = null; }
  let data;
  try { data = await window.RemoteSource.loadRun(runId); }
  catch (e) { liveDetail().innerHTML = `<div class="empty">Could not load run: ${R.esc(e.message || e)}</div>`; return; }
  state.liveRun = data.run; state.liveEvents = data.events;
  state.seenSeq = new Set(data.events.map((e) => e.seq));
  R.renderRun(liveDetail(), data.run, data.rounds);
  if (window.Tags) Tags.mount(liveDetail());
  state.runChannel = window.RemoteSource.subscribeRun(runId, onLiveEvent, onRunPatch);
  if (window.scheduleJumpUpdate) window.scheduleJumpUpdate();
}
window.openRun = openRun;

function onLiveEvent(e) {
  if (e.run_id !== state.currentRunId || state.seenSeq.has(e.seq)) return;
  state.seenSeq.add(e.seq); state.liveEvents.push(e);
  const rounds = window.RemoteSource.rowsToRounds(state.liveEvents);
  const key = window.RemoteSource.roundKey(e);
  const round = rounds.find((r) => `${r.kind}:${r.round_index}` === key);
  if (!round || !liveDetail().querySelector(".rounds")) return;
  const box = liveDetail(), near = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
  R.appendRound(liveDetail(), round, state.liveRun, rounds);
  if (near) box.scrollTop = box.scrollHeight;
}
function onRunPatch(patch) {
  if (!patch || patch.run_id !== state.currentRunId) return;
  Object.assign(state.liveRun, patch);
  const top = liveDetail().querySelector(".run-top");
  if (top) { top.innerHTML = R.topHtml(state.liveRun); if (window.Tags) Tags.mount(top); }
  upsertRun(state.liveRun); renderList();
}

// ---- local file source -----------------------------------------------------
function buildLocalRun(meta, rounds, name) {
  return { run_id: name, arxiv_id: meta.arxiv_id, model: null,
    status: rounds.some((r) => r.kind === "final") ? "finished" : "partial",
    exit_reason: meta.final_exit_reason, budget: meta.total_h100,
    total_h100: meta.total_h100, remaining_h100: meta.last_remaining_h100, spent_h100: meta.total_h100 != null && meta.last_remaining_h100 != null ? meta.total_h100 - meta.last_remaining_h100 : null };
}
let fileInput;
async function handleFile(file) {
  if (!file) return;
  const { rounds, meta } = window.parseTranscript(await file.text());
  const run = buildLocalRun(meta, rounds, file.name);
  const root = $("#local-detail");
  R.renderRun(root, run, rounds);
  const reset = R.el(`<button class="crumb" id="local-reset">‹ choose another file</button>`);
  reset.addEventListener("click", () => fileInput.click());
  root.querySelector(".run-detail").prepend(reset);
}
function wireLocal() {
  fileInput = document.createElement("input");
  fileInput.type = "file"; fileInput.accept = ".log,.txt"; fileInput.className = "hidden";
  document.body.appendChild(fileInput);
  fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));
  const drop = $("#drop"); if (drop) drop.addEventListener("click", () => fileInput.click());
  const view = $("#view-local");
  view.addEventListener("dragover", (e) => { e.preventDefault(); const d = $("#drop"); if (d) d.classList.add("over"); });
  view.addEventListener("dragleave", () => { const d = $("#drop"); if (d) d.classList.remove("over"); });
  view.addEventListener("drop", (e) => { e.preventDefault(); const d = $("#drop"); if (d) d.classList.remove("over"); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
}

// ---- boot ------------------------------------------------------------------
function setConn() {
  const pill = $("#conn");
  pill.innerHTML = state.remote ? `<span class="dot running"></span>live` : "offline";
  pill.style.color = state.remote ? "var(--yes-deep)" : "var(--muted)";
}
function boot() {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  $("#sidebar-toggle").addEventListener("click", () => { $("#view-live").classList.toggle("nolist"); $("#sidebar-toggle").classList.toggle("on"); });
  $("#search").addEventListener("input", (e) => { state.search = e.target.value; renderList(); });
  wireLocal(); renderFilters();
  state.remote = window.RemoteSource.init(); setConn(); loadRunList();
  if (state.remote) {
    window.RemoteSource.subscribeRunList((run) => { upsertRun(run); if (state.view === "live") renderList(); });
    if (window.Tags) { Tags.onChange(onTagsChange); Tags.load().catch(() => {}); window.RemoteSource.subscribeTags((row, evt) => Tags.applyRow(row, evt)); }
  } else {
    liveDetail().innerHTML = `<div class="empty">Supabase isn't reachable. Open <b>Local</b> to read a saved transcript, or set the keys in <code>config.js</code>.</div>`;
  }
  if (window.Estimates) {
    window.Estimates.onChange(() => {
      if (state.view === "live") renderList();
      if (window.Overview && window.Overview.onTags) window.Overview.onTags();
      if (window.Papers && window.Papers.onTags) window.Papers.onTags();
    });
    window.Estimates.load();
  }
  setView("overview");
}
document.addEventListener("DOMContentLoaded", boot);
