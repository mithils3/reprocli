/* app.js — boot + wiring. Two sources, one renderer:
   Local  = drop/pick a transcript → parseTranscript → renderRun
   Live   = list runs from Supabase, open one, stream rounds via Realtime. */
"use strict";

const R = window.RENDER;
const state = {
  view: "live", runs: [], byId: {}, filter: "all", search: "",
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
  if (v === "stats" && window.Stats) window.Stats.open();
}

// ---- run list (Live) -------------------------------------------------------
const FILTERS = [["all", "All"], ["running", "Running"], ["dead", "Dead"], ["finished", "Finished"], ["error", "Error"]];
function renderFilters() {
  $("#filters").innerHTML = FILTERS.map(([k, l]) =>
    `<button class="filt ${state.filter === k ? "active" : ""}" data-f="${k}">${l}</button>`).join("");
  document.querySelectorAll("#filters .filt").forEach((b) =>
    b.addEventListener("click", () => { state.filter = b.dataset.f; renderFilters(); renderList(); }));
}
function visibleRuns() {
  const q = state.search.toLowerCase();
  return state.runs.filter((r) =>
    (state.filter === "all" || R.effectiveStatus(r) === state.filter) &&
    (!q || (`${r.arxiv_id} ${r.model || ""} ${r.run_id}`).toLowerCase().includes(q)));
}
function renderList() {
  const list = $("#run-list");
  const rows = visibleRuns();
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
  try {
    const runs = await window.RemoteSource.listRuns();
    state.byId = {}; runs.forEach(upsertRun); renderList();
  } catch (e) { state.remote = false; setConn(); renderList(); }
}

// ---- open + stream one run -------------------------------------------------
async function openRun(runId) {
  state.currentRunId = runId;
  renderList();
  liveDetail().innerHTML = `<div class="empty">Loading ${R.esc(runId)}…</div>`;
  if (state.runChannel) { window.RemoteSource.unsubscribe(state.runChannel); state.runChannel = null; }
  let data;
  try { data = await window.RemoteSource.loadRun(runId); }
  catch (e) { liveDetail().innerHTML = `<div class="empty">Could not load run: ${R.esc(e.message || e)}</div>`; return; }
  state.liveRun = data.run; state.liveEvents = data.events;
  state.seenSeq = new Set(data.events.map((e) => e.seq));
  R.renderRun(liveDetail(), data.run, data.rounds);
  state.runChannel = window.RemoteSource.subscribeRun(runId, onLiveEvent, onRunPatch);
}
function onLiveEvent(e) {
  if (e.run_id !== state.currentRunId || state.seenSeq.has(e.seq)) return;
  state.seenSeq.add(e.seq);
  state.liveEvents.push(e);
  const rounds = window.RemoteSource.rowsToRounds(state.liveEvents);
  const key = window.RemoteSource.roundKey(e);
  const round = rounds.find((r) => `${r.kind}:${r.round_index}` === key);
  const roundsEl = liveDetail().querySelector(".rounds");
  if (!round || !roundsEl) return;
  const box = liveDetail();
  const near = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
  R.appendRound(roundsEl, round, state.liveRun.arxiv_id);
  if (near) box.scrollTop = box.scrollHeight;
}
function onRunPatch(patch) {
  if (!patch || patch.run_id !== state.currentRunId) return;
  Object.assign(state.liveRun, patch);
  const top = liveDetail().querySelector(".run-top");
  if (top) top.innerHTML = R.topHtml(state.liveRun);
  upsertRun(state.liveRun); renderList();
}

// ---- local file source -----------------------------------------------------
function buildLocalRun(meta, rounds, name) {
  return {
    run_id: name, arxiv_id: meta.arxiv_id, model: null,
    status: rounds.some((r) => r.kind === "final") ? "finished" : "partial",
    exit_reason: meta.final_exit_reason, budget: meta.total_h100,
    total_h100: meta.total_h100, remaining_h100: meta.last_remaining_h100,
  };
}
async function handleFile(file) {
  if (!file) return;
  const text = await file.text();
  const { rounds, meta } = window.parseTranscript(text);
  const run = buildLocalRun(meta, rounds, file.name);
  const root = $("#local-detail");
  R.renderRun(root, run, rounds);
  const reset = R.el(`<button class="link" id="local-reset" style="margin-bottom:10px">← choose another file</button>`);
  reset.addEventListener("click", () => fileInput.click());
  root.querySelector(".run-detail").prepend(reset);
}

let fileInput;
function wireLocal() {
  fileInput = document.createElement("input");
  fileInput.type = "file"; fileInput.accept = ".log,.txt"; fileInput.className = "hidden";
  document.body.appendChild(fileInput);
  fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));
  const drop = $("#drop");
  if (drop) drop.addEventListener("click", () => fileInput.click());
  const view = $("#view-local");
  view.addEventListener("dragover", (e) => { e.preventDefault(); const d = $("#drop"); if (d) d.classList.add("over"); });
  view.addEventListener("dragleave", () => { const d = $("#drop"); if (d) d.classList.remove("over"); });
  view.addEventListener("drop", (e) => {
    e.preventDefault(); const d = $("#drop"); if (d) d.classList.remove("over");
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });
}

// ---- boot ------------------------------------------------------------------
function setConn() {
  const pill = $("#conn");
  pill.textContent = state.remote ? "● live" : "offline";
  pill.style.color = state.remote ? "var(--yes-deep)" : "var(--muted)";
}
function boot() {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  $("#sidebar-toggle").addEventListener("click", () => {
    $("#view-live").classList.toggle("nolist");
    $("#sidebar-toggle").classList.toggle("on");
  });
  $("#search").addEventListener("input", (e) => { state.search = e.target.value; renderList(); });
  wireLocal();
  renderFilters();
  state.remote = window.RemoteSource.init();
  setConn();
  loadRunList();
  if (state.remote) {
    window.RemoteSource.subscribeRunList((run) => { upsertRun(run); if (state.view === "live") renderList(); });
  } else {
    liveDetail().innerHTML = `<div class="empty">Supabase isn't configured/reachable. Switch to <b>Local file</b> to view a transcript, or set the keys in <code>config.js</code>.</div>`;
  }
  setView("live");
}
document.addEventListener("DOMContentLoaded", boot);
