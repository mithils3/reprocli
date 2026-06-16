/* JSON viewer tab — renders the model's extracted JSON for one paper in the
   app's own card/field language (like the Review tab), with a collapsed raw
   JSON tree as a fallback. Reuses globals from app.js (state, esc, el,
   collapsible, signalBadge, tierClass, authorsLine, STEPS, track, $$).
   Loaded after app.js. */
"use strict";

const jv = { id: null, wired: false };

// ---- small formatters ------------------------------------------------------
const isUrl = (s) => typeof s === "string" && /^https?:\/\/\S+$/.test(s);
const prettyUrl = (u) => u.replace(/^https?:\/\//, "");
const labelize = (k) => k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const LABELS = {
  paper_or_project: "Paper / project", code: "Code", dataset: "Dataset", weights: "Weights",
  h100_band: "H100 band", h100_hours_estimate: "H100 hours (est.)",
  h100_recomputed_hours: "Recomputed hours", audited_h100_hours: "Audited hours",
  selection_band: "Selection band", h100_arithmetic_mismatch: "Arithmetic mismatch",
  h100_needs_human_review: "Needs human review", verification_status: "Run status",
  exit_reason: "Exit reason", source_url: "Source", paper_kind: "Paper kind", has_trace: "Has trace",
};
const lab = (k) => LABELS[k] || labelize(k);
const link = (u) => `<a class="qlink" href="${esc(u)}" target="_blank" rel="noopener">${esc(prettyUrl(u))}</a>`;

// one scalar value -> styled html
function fmtVal(v) {
  if (v === null || v === undefined || v === "") return `<span class="muted">—</span>`;
  if (typeof v === "boolean") return `<span class="badge ${v ? "yes" : "no"}">${v ? "yes" : "no"}</span>`;
  if (isUrl(v)) return link(v);
  return esc(String(v));
}

// ---- raw json tree (collapsed fallback) ------------------------------------
const keyHtml = (k) => k === null ? "" : `<span class="jkey">"${esc(k)}"</span><span class="jpunc">: </span>`;
const tog = `<span class="jtoggle"></span>`;
function valHtml(v) {
  if (v === null) return `<span class="jval jnull">null</span>`;
  const t = typeof v;
  if (t === "boolean") return `<span class="jval jbool">${v}</span>`;
  if (t === "number") return `<span class="jval jnum">${esc(String(v))}</span>`;
  if (isUrl(v)) return `<a class="jval jstr jlink" href="${esc(v)}" target="_blank" rel="noopener">"${esc(v)}"</a>`;
  return `<span class="jval jstr">"${esc(String(v))}"</span>`;
}
function nodeHtml(value, key, isLast) {
  const comma = isLast ? "" : `<span class="jpunc">,</span>`;
  if (value === null || typeof value !== "object")
    return `<div class="jnode"><div class="jline">${tog}${keyHtml(key)}${valHtml(value)}${comma}</div></div>`;
  const arr = Array.isArray(value);
  const open = arr ? "[" : "{", close = arr ? "]" : "}";
  const keys = arr ? value.map((_, i) => i) : Object.keys(value);
  if (!keys.length)
    return `<div class="jnode"><div class="jline">${tog}${keyHtml(key)}<span class="jbrace">${open}${close}</span>${comma}</div></div>`;
  const n = keys.length, count = arr ? `${n} item${n > 1 ? "s" : ""}` : `${n} key${n > 1 ? "s" : ""}`;
  const children = keys.map((k, i) => nodeHtml(value[k], arr ? null : k, i === n - 1)).join("");
  return `<div class="jnode branch">
    <div class="jline jhead">${tog}${keyHtml(key)}<span class="jbrace">${open}</span><span class="jpreview"> … <span class="jbrace">${close}</span>${comma} <span class="jcount">${count}</span></span></div>
    <div class="jchildren">${children}</div>
    <div class="jline jclose">${tog}<span class="jbrace">${close}</span>${comma}</div></div>`;
}

// ---- field (record) view ---------------------------------------------------
const card = (inner) => `<div class="rcard">${inner}</div>`;
const group = (label, body) => `<section class="rgroup"><div class="rgroup-h">${esc(label)}</div>${body}</section>`;
const kvGrid = (pairs) => `<div class="rgrid">${pairs.map(([l, v]) =>
  `<div class="rcell"><div class="rlabel">${esc(l)}</div><div class="rval">${v}</div></div>`).join("")}</div>`;

// header mirrors the Review tab's .dhead exactly
function headerHtml(p) {
  return `<div class="dhead">
    <div class="dhead-top">
      <span class="pid big">${esc(p.custom_id)}</span>
      <span class="badge tier ${tierClass(p.tier)}">${esc(p.tier ?? "no tier")}</span>
      <span class="badge score">model score: ${esc(p.score ?? "—")}</span>
      <span class="badge web">run: ${esc(p.verification_status ?? p.web_verification ?? "—")}</span>
      ${p.paper_kind ? `<span class="badge">${esc(p.paper_kind)}</span>` : ""}
    </div>
    <h2>${esc(p.title || "")}</h2>
    ${authorsLine(p) ? `<div class="authors">${esc(authorsLine(p))}</div>` : ""}
  </div>`;
}

// one card per artifact signal (label + model verdict badge + evidence)
function signalsBody(p) {
  const sigs = p.signals || {};
  return STEPS.map((s) => {
    const sig = sigs[s.signal] || {};
    return card(`<div class="rcard-h"><h4>${esc(s.q)}</h4>${signalBadge(sig.value)}` +
      `${sig.verification ? `<span class="badge">${esc(sig.verification)}</span>` : ""}</div>` +
      `<p class="rprose ${sig.evidence ? "" : "muted"}">${esc(sig.evidence || "No evidence recorded.")}</p>`);
  }).join("");
}

function linksBody(p) {
  const vl = p.verified_links || {};
  const rows = Object.keys(vl).map((k) => {
    const urls = (vl[k] || []).filter(Boolean);
    if (!urls.length) return "";
    return `<div class="rlinks-row"><span class="rlabel">${esc(lab(k))}</span>` +
      `<div class="quicklinks">${urls.map(link).join("")}</div></div>`;
  }).filter(Boolean).join("");
  return rows ? card(rows) : "";
}

function computeBody(p) {
  const keys = ["h100_band", "h100_hours_estimate", "h100_recomputed_hours", "audited_h100_hours",
    "selection_band", "h100_arithmetic_mismatch", "h100_needs_human_review"];
  const pairs = keys.filter((k) => p[k] !== undefined && p[k] !== null).map((k) => [lab(k), fmtVal(p[k])]);
  if (!pairs.length) return "";
  const basis = p.h100_estimate_basis ? `<p class="rprose muted">${esc(p.h100_estimate_basis)}</p>` : "";
  return card(kvGrid(pairs) + basis);
}

function proseBody(p, fields) {
  return fields.filter(([, v]) => v).map(([l, v]) =>
    `<div class="ctx"><b>${esc(l)}</b><p>${esc(v)}</p></div>`).join("")
    || `<div class="ctx"><p class="muted">No claim/reproduction text extracted.</p></div>`;
}

function metaBody(p) {
  const keys = ["year", "paper_kind", "score", "tier", "verification_status", "exit_reason", "has_trace", "source_url"];
  return card(kvGrid(keys.filter((k) => p[k] !== undefined).map((k) => [lab(k), fmtVal(p[k])])));
}

function renderRecord() {
  const head = document.getElementById("json-head");
  const root = document.getElementById("json-tree");
  const p = state.byId[jv.id];
  if (!p) { head.innerHTML = ""; root.innerHTML = `<div class="empty small">No paper selected.</div>`; return; }
  head.innerHTML = headerHtml(p);
  root.innerHTML = "";
  root.appendChild(el(group("Artifact signals", signalsBody(p))));
  const lb = linksBody(p);
  if (lb) root.appendChild(el(group("Artifact links", lb)));
  const cb = computeBody(p);
  if (cb) root.appendChild(el(group("Compute estimate", cb)));
  root.appendChild(collapsible("Claim & reproduction", proseBody(p, [
    ["Central claim", p.central_claim], ["Claim evidence", p.claim_evidence],
    ["MRE config", p.mre_config], ["Agent task", p.agent_task],
  ]), false));
  if (p.abstract) root.appendChild(collapsible("Abstract", `<div class="ctx"><p>${esc(p.abstract)}</p></div>`, false));
  root.appendChild(el(group("Metadata", metaBody(p))));
  root.appendChild(collapsible("⟨⟩ Raw extracted JSON", `<div class="jraw">${nodeHtml(p, null, true)}</div>`, false));
  track("json_opened", p.custom_id, null);
}

// ---- toolbar / picker ------------------------------------------------------
// search only narrows the dropdown; the displayed paper stays on jv.id until
// the reviewer explicitly picks a new option (the `change` handler re-renders).
function buildPicker() {
  const sel = document.getElementById("json-picker");
  const q = (document.getElementById("json-search").value || "").toLowerCase();
  const matches = state.papers.filter((p) =>
    !q || (p.custom_id + " " + (p.title || "")).toLowerCase().includes(q));
  sel.innerHTML = matches.length
    ? matches.map((p) =>
        `<option value="${esc(p.custom_id)}">${esc(p.custom_id)} — ${esc(shortTitle(p) || p.title || "")}</option>`).join("")
    : `<option value="">No papers match “${esc(q)}”</option>`;
  if (jv.id && matches.some((p) => p.custom_id === jv.id)) sel.value = jv.id;
}

// expand/collapse every <details> section, plus the raw-JSON tree branches
function setCollapsedAll(collapsed) {
  $$("#view-json details").forEach((d) => { d.open = !collapsed; });
  const rootNode = document.querySelector("#json-tree .jraw > .jnode");
  $$("#json-tree .jnode.branch").forEach((node) => {
    if (node === rootNode) { node.classList.remove("collapsed"); return; }  // keep raw root open
    node.classList.toggle("collapsed", collapsed);
  });
}

function wireOnce() {
  if (jv.wired) return;
  jv.wired = true;
  const sel = document.getElementById("json-picker");
  sel.addEventListener("change", () => { jv.id = sel.value; renderRecord(); });
  document.getElementById("json-search").addEventListener("input", buildPicker);
  document.getElementById("json-collapse").addEventListener("click", () => setCollapsedAll(true));
  document.getElementById("json-expand").addEventListener("click", () => setCollapsedAll(false));
  document.getElementById("json-copy").addEventListener("click", copyJson);
  document.getElementById("json-download").addEventListener("click", downloadJson);
  // fold a raw-tree branch by clicking its brace row (let links through)
  document.getElementById("json-tree").addEventListener("click", (e) => {
    if (e.target.closest("a")) return;
    const h = e.target.closest(".jhead");
    if (h && h.parentElement.classList.contains("branch")) h.parentElement.classList.toggle("collapsed");
  });
}

function flash(btn, text) {
  const old = btn.textContent;
  btn.textContent = text;
  setTimeout(() => { btn.textContent = old; }, 1200);
}
function copyJson() {
  const p = state.byId[jv.id];
  if (!p) return;
  navigator.clipboard.writeText(JSON.stringify(p, null, 2)).then(
    () => flash(document.getElementById("json-copy"), "Copied ✓"),
    () => flash(document.getElementById("json-copy"), "Copy failed"));
}
function downloadJson() {
  const p = state.byId[jv.id];
  if (!p) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(p, null, 2)], { type: "application/json" }));
  a.download = `${p.custom_id}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// entry point called by setView("json"): sync to whatever paper is open, render
window.renderJsonView = function renderJsonView() {
  if (!state.papers.length) return;
  if (state.current) jv.id = state.current;       // follow the paper you were reviewing
  if (!jv.id || !state.byId[jv.id]) jv.id = state.papers[0].custom_id;
  wireOnce();
  buildPicker();
  renderRecord();
};
