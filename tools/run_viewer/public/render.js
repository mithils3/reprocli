/* render.js — turn the normalized Run/Round/Call shape into DOM, reusing the
   verify_app design system. Shared by the Local (parsed) and Live (Supabase)
   sources. Pure helpers (esc/el/json-tree) are lifted from verify_app. */
"use strict";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}
const fmtTime = (t) => t ? new Date(t).toLocaleString([],
  { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
const num = (v) => (v == null ? null : (Math.round(v * 10000) / 10000));
const collapsibleHtml = (summary, inner, open) =>
  `<div class="collapse"><details ${open ? "open" : ""}><summary>${esc(summary)}</summary>${inner}</details></div>`;

// ---- json tree (tool-call args) — pure helpers from verify_app json_view.js ----
const isUrl = (s) => typeof s === "string" && /^https?:\/\/\S+$/.test(s);
const keyHtml = (k) => k === null ? "" : `<span class="jkey">"${esc(k)}"</span><span class="jpunc">: </span>`;
const TOG = `<span class="jtoggle"></span>`;
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
    return `<div class="jnode"><div class="jline">${TOG}${keyHtml(key)}${valHtml(value)}${comma}</div></div>`;
  const arr = Array.isArray(value);
  const open = arr ? "[" : "{", close = arr ? "]" : "}";
  const keys = arr ? value.map((_, i) => i) : Object.keys(value);
  if (!keys.length)
    return `<div class="jnode"><div class="jline">${TOG}${keyHtml(key)}<span class="jbrace">${open}${close}</span>${comma}</div></div>`;
  const n = keys.length, count = arr ? `${n} item${n > 1 ? "s" : ""}` : `${n} key${n > 1 ? "s" : ""}`;
  const children = keys.map((k, i) => nodeHtml(value[k], arr ? null : k, i === n - 1)).join("");
  return `<div class="jnode branch"><div class="jline jhead">${TOG}${keyHtml(key)}<span class="jbrace">${open}</span><span class="jpreview"> … <span class="jbrace">${close}</span>${comma} <span class="jcount">${count}</span></span></div>` +
    `<div class="jchildren">${children}</div><div class="jline jclose">${TOG}<span class="jbrace">${close}</span>${comma}</div></div>`;
}

// ---- status / meters -------------------------------------------------------
const GOOD_EXIT = (e) => e === "natural" || e === "completed";
function statusInfo(run) {
  const s = run.status || "running";
  if (s === "finished") return { cls: "finished", label: "done" };
  if (s === "error") return { cls: "error", label: "error" };
  if (s === "partial") return { cls: "running", label: "partial" };
  return { cls: "running", label: "running" };
}
function costMeterHtml(run) {
  const total = num(run.total_h100 ?? run.budget);
  let spent = num(run.spent_h100);
  if (spent == null && total != null && run.remaining_h100 != null) spent = num(total - run.remaining_h100);
  if (total == null && spent == null) return "";
  const pct = total ? Math.max(0, Math.min(100, (spent / total) * 100)) : 0;
  const done = run.status === "finished" || run.status === "error";
  const rem = run.remaining_h100 != null ? num(run.remaining_h100) : (total != null && spent != null ? num(total - spent) : null);
  return `<div class="meter"><div class="meter-row">
    <span>compute</span>
    <span class="bar"><span class="bar-fill ${done ? "done" : ""}" style="width:${pct.toFixed(1)}%"></span></span>
    <span><b>${spent ?? "?"}</b> / ${total ?? "?"} H100-h spent${rem != null ? ` · <b>${rem}</b> left` : ""}</span>
  </div></div>`;
}

// ---- run header ------------------------------------------------------------
function runHeaderHtml(run) {
  const si = statusInfo(run);
  const exit = run.exit_reason ? `<span class="badge ${GOOD_EXIT(run.exit_reason) ? "yes" : "unk"}">exit: ${esc(run.exit_reason)}</span>` : "";
  const dl = run.full_log_url ? `<a class="link" href="${esc(run.full_log_url)}" target="_blank" rel="noopener">⬇ full log</a>` : "";
  const times = (run.started_at || run.updated_at)
    ? `<div class="muted" style="font-size:12px;margin-top:6px">started ${fmtTime(run.started_at)} · updated ${fmtTime(run.updated_at)}${run.host ? " · " + esc(run.host) : ""}</div>` : "";
  return `<div class="dhead"><div class="dhead-top">
    <span class="pid big">${esc(run.arxiv_id || "?")}</span>
    <span class="badge ${si.cls === "finished" ? "yes" : si.cls === "error" ? "no" : "accent"}">${si.label}</span>
    ${run.model ? `<span class="badge">${esc(run.model)}</span>` : ""}
    ${run.budget != null ? `<span class="schip">${esc(run.budget)}h budget</span>` : ""}
    ${exit}${dl}
  </div><h2>${esc(run.run_id || run.arxiv_id || "transcript")}</h2>${times}</div>`;
}

// ---- calls / rounds --------------------------------------------------------
function streamHtml(label, text, cls) {
  if (!text) return "";
  const n = text.split("\n").length;
  return collapsibleHtml(`${label} · ${n} line${n !== 1 ? "s" : ""}`, `<pre class="stream ${cls}">${esc(text)}</pre>`, false);
}
function resultHtml(c) {
  if (c.ok === undefined) return "";
  const chip = (v) => `<span class="schip">${esc(v)}</span>`;
  let s = `<div class="result"><span class="badge ${c.ok ? "yes" : "no"}">${c.ok ? "ok" : "failed"}</span>`;
  if (c.rc != null) s += chip("rc " + c.rc);
  if (c.duration_s != null) s += chip(c.duration_s + "s");
  if (c.cost_h100 != null) s += chip("+" + c.cost_h100 + " h100h");
  if (c.remaining_h100 != null) s += chip(c.remaining_h100 + " left");
  if (c.bytes_written != null) s += chip(c.bytes_written + " B");
  if (c.path && c.detail_kind !== "path") s += chip(c.path);
  return s + "</div>";
}
function callHtml(c) {
  let body = "";
  if (c.detail_kind === "json" && c.args) body += `<div class="jraw">${nodeHtml(c.args, null, true)}</div>`;
  else if (c.command) body += `<pre class="cmd ${c.detail_kind || ""}">${esc(c.command)}</pre>`;
  body += resultHtml(c);
  if (c.error) body += `<div class="err">${esc(c.error)}</div>`;
  body += streamHtml("stdout", c.stdout, "out");
  body += streamHtml("stderr", c.stderr, "errt");
  if (c.truncated) body += `<div class="trunc">… output truncated (head only) — see agent.full.log for the rest</div>`;
  return `<div class="call"><div class="call-h"><span class="tool">${esc(c.tool_name)}</span></div><div class="call-body">${body}</div></div>`;
}
function block(label, text) {
  return text ? `<div class="block"><div class="block-l">${label}</div><p class="rprose">${esc(text)}</p></div>` : "";
}
function roundCardHtml(round, arxiv) {
  const isFinal = round.kind === "final";
  const bad = isFinal && round.exit_reason && !GOOD_EXIT(round.exit_reason);
  const key = `${round.kind}:${round.round_index}`;
  const tag = isFinal ? "✅ FINAL" : `round ${round.round_index ?? "?"}`;
  const exit = isFinal && round.exit_reason ? `<span class="badge ${bad ? "no" : "yes"}">exit: ${esc(round.exit_reason)}</span>` : "";
  return `<div class="rcard ${isFinal ? "final" : ""} ${bad ? "bad" : ""}" data-key="${esc(key)}">
    <div class="rcard-h"><span class="schip">${tag}</span>${exit}
      <span class="pid">${esc(round.arxiv_id || arxiv || "")}</span>
      ${round.ts ? `<span class="ftime">${esc(round.ts)}</span>` : ""}</div>
    ${block("💭 reasoning", round.reasoning)}${block("🗒 assistant", round.content)}
    ${round.calls.map(callHtml).join("")}</div>`;
}

const topHtml = (run) => runHeaderHtml(run) + costMeterHtml(run);
function renderRun(rootEl, run, rounds) {
  rootEl.innerHTML = `<div class="run-detail"><div class="run-top">${topHtml(run)}</div><div class="rounds"></div></div>`;
  rootEl.querySelector(".rounds").innerHTML = (rounds || []).map((r) => roundCardHtml(r, run.arxiv_id)).join("");
}
function appendRound(roundsEl, round, arxiv) {
  const key = `${round.kind}:${round.round_index}`;
  const html = roundCardHtml(round, arxiv);
  const ex = roundsEl.querySelector(`[data-key="${CSS.escape(key)}"]`);
  if (ex) ex.outerHTML = html; else roundsEl.insertAdjacentHTML("beforeend", html);
}

window.RENDER = { esc, el, fmtTime, statusInfo, renderRun, renderRunListItem, appendRound, topHtml };
function renderRunListItem(run) {
  const si = statusInfo(run);
  return el(`<button class="plitem" data-run="${esc(run.run_id)}">
    <span class="dot ${si.cls}"></span>
    <span class="pmeta"><span class="pid">${esc(run.arxiv_id)}</span>
      <span class="ptitle">${esc(run.model || "—")}</span>
      <span class="prow2"><span class="schip">${esc(run.budget ?? "?")}h</span>
        ${run.status === "running" ? '<span class="live-tag">● live</span>' : `<span class="schip">${si.label}</span>`}
        <span class="schip">${fmtTime(run.updated_at)}</span></span></span></button>`);
}
