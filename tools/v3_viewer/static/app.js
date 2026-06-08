let state = { records: [], summary: null, selected: null, filter: "all", query: "" };

const $ = (id) => document.getElementById(id);

async function loadSummary() {
  const res = await fetch("/api/summary");
  const data = await res.json();
  state.records = data.records;
  state.summary = data.summary;
  $("basePath").textContent = data.base_path;
  renderStats(data.summary);
  renderList();
  if (!state.selected && state.records.length) selectRecord(state.records[0].custom_id);
}

function renderStats(summary) {
  const cleanPct = pct(summary.clean_final_json, summary.record_count);
  const issueTotal = Object.values(summary.issue_counts || {}).reduce((a, b) => a + b, 0);
  const stats = [
    ["Records", summary.record_count, "Loaded papers"],
    ["Clean JSON", `${summary.clean_final_json}/${summary.record_count}`, `${cleanPct}% valid`],
    ["Round Limit", summary.round_limit, "Stopped by cap"],
    ["Score Drift", summary.score_drift, "Stored vs computed"],
    ["Trace Errors", summary.trace_errors, "Parse failures"],
    ["Trace Rows", `${summary.trace_rows}/${summary.record_count}`, "Conversation logs"],
  ];
  $("stats").innerHTML = `
    <div class="health-card">
      <span class="eyebrow">Run health</span>
      <strong>${cleanPct}%</strong>
      <div class="meter"><i style="width:${cleanPct}%"></i></div>
      <small>${issueTotal} total quality flags across ${summary.record_count} records</small>
    </div>
    ${stats.map(metricCard).join("")}
    ${distCard("Tier Distribution", summary.tiers, tierClass)}
    ${distCard("Score Distribution", summary.scores, () => "neutral")}
    ${distCard("Issue Distribution", summary.issue_counts, issueClass)}
  `;
}

function metricCard([label, value, note]) {
  return `<div class="stat"><span>${label}</span><strong>${escapeHtml(value)}</strong><small>${note}</small></div>`;
}

function distCard(title, data, classFor) {
  const rows = Object.entries(data || {}).sort(([a], [b]) => String(a).localeCompare(String(b)));
  const max = Math.max(1, ...rows.map(([, value]) => value));
  return `<article class="viz-card">
    <h2>${escapeHtml(title)}</h2>
    <div class="bars">${rows.map(([label, value]) => bar(label, value, max, classFor(label))).join("") || empty("No data")}</div>
  </article>`;
}

function bar(label, value, max, cls) {
  return `<div class="bar-row ${cls}">
    <span>${escapeHtml(label)}</span>
    <div class="bar"><i style="width:${Math.round((value / max) * 100)}%"></i></div>
    <b>${escapeHtml(value)}</b>
  </div>`;
}

function renderList() {
  const rows = filteredRecords();
  $("recordList").innerHTML = rows.map(recordCard).join("") || empty("No matching records");
  document.querySelectorAll(".record").forEach((node) => {
    node.addEventListener("click", () => selectRecord(node.dataset.id));
  });
}

function filteredRecords() {
  const query = state.query.toLowerCase();
  return state.records.filter((record) => {
    const haystack = `${record.custom_id} ${record.title} ${record.tier}`.toLowerCase();
    if (query && !haystack.includes(query)) return false;
    if (state.filter === "issues") return record.quality.issues.length > 0;
    if (state.filter === "round") return record.quality.hit_tool_round_limit;
    if (state.filter === "drift") return record.quality.score_drift;
    if (state.filter === "trace") return record.quality.issues.some((x) => x.includes("trace"));
    return true;
  });
}

function recordCard(record) {
  const active = state.selected === record.custom_id ? " active" : "";
  const issue = record.quality.issues.length ? "warn" : "good";
  const rounds = record.quality.tool_rounds_used ?? 0;
  const maxRounds = record.quality.max_tool_rounds ?? 1;
  return `
    <button class="record ${issue}${active}" data-id="${escapeAttr(record.custom_id)}">
      <span class="record-head"><b>${escapeHtml(record.custom_id)}</b><i>${escapeHtml(record.tier || "missing")}</i></span>
      <span class="record-title">${escapeHtml(record.title || "No extracted claim")}</span>
      <span class="record-meta">
        <span>score ${escapeHtml(record.score ?? "n/a")}</span>
        <span>${escapeHtml(rounds)}/${escapeHtml(maxRounds)} rounds</span>
        <span>${escapeHtml(record.trace_stats.messages || 0)} msgs</span>
      </span>
      ${miniMeter(rounds, maxRounds)}
    </button>`;
}

async function selectRecord(customId) {
  state.selected = customId;
  renderList();
  $("detail").className = "detail";
  $("detail").textContent = "Loading...";
  const res = await fetch(`/api/records/${encodeURIComponent(customId)}`);
  renderDetail(await res.json());
}

function renderDetail(record) {
  const extracted = record.extracted || {};
  const quality = record.quality || {};
  const trace = record.trace_stats || {};
  $("detail").innerHTML = `
    <section class="hero-panel ${quality.issues.length ? "warn-bg" : "good-bg"}">
      <div><span class="eyebrow">Selected paper</span><h2>${escapeHtml(record.custom_id)}</h2></div>
      <div class="badges">${badges(record)}</div>
    </section>
    <section class="viz-row">
      ${scoreAudit(extracted, quality)}
      ${traceFlow(record.trace, trace)}
    </section>
    <section class="panel">
      <h2>Classification</h2>
      ${field("Central claim", extracted.central_claim)}
      ${field("MRE config", extracted.mre_config)}
      ${field("Agent task", extracted.agent_task)}
    </section>
    <section class="signal-grid">${signalCards(extracted.signals || {})}</section>
    <section class="panel">${sectionTitle("Quality Checks")}${qualityList(record)}</section>
    <section class="panel">${sectionTitle("Verified Links")}${linkGroups(extracted.verified_links || {})}</section>
    <section class="panel">${sectionTitle("Final Answer")}${renderSmartText(finalContent(record.final))}</section>
    <section class="panel">${sectionTitle("Assistant Reasoning")}${renderSmartText(finalReasoning(record.final) || "No reasoning block saved.")}</section>
    <section class="panel">${sectionTitle("Transcript")}${transcript(record.trace)}</section>
    <section class="panel">${sectionTitle("Raw Payloads")}${rawBlock("Extracted JSON", extracted)}${rawBlock("Final row", record.final)}${rawBlock("Trace row", record.trace)}${rawBlock("Trace parse error", record.trace_error)}</section>
  `;
}

function scoreAudit(extracted, quality) {
  const rows = [
    ["Stored", `${extracted.score ?? "n/a"} / ${extracted.tier ?? "missing"}`],
    ["Computed", `${quality.computed_score ?? "n/a"} / ${quality.computed_tier ?? "missing"}`],
    ["Finish", quality.finish_reason || "missing"],
    ["Tokens", `${quality.prompt_tokens ?? "?"} + ${quality.completion_tokens ?? "?"}`],
  ];
  return `<article class="viz-card"><h2>Score Audit</h2>${rows.map(([k, v]) => `<div class="kv"><span>${k}</span><b>${escapeHtml(v)}</b></div>`).join("")}${miniMeter(quality.tool_rounds_used || 0, quality.max_tool_rounds || 1)}</article>`;
}

function traceFlow(trace, stats) {
  const roles = (stats.roles || {});
  const total = Math.max(1, Object.values(roles).reduce((a, b) => a + b, 0));
  const segments = Object.entries(roles).map(([role, count]) =>
    `<i class="${escapeAttr(role)}" title="${escapeAttr(role)}: ${count}" style="width:${Math.max(6, (count / total) * 100)}%"></i>`
  ).join("");
  const tools = Object.entries(stats.tool_counts || {}).slice(0, 4)
    .map(([name, count]) => `<span>${escapeHtml(name)} x${escapeHtml(count)}</span>`).join("");
  return `<article class="viz-card"><h2>Trace Flow</h2><div class="flow">${segments || "<i></i>"}</div><div class="trace-numbers"><b>${stats.messages || 0}</b><span>messages</span><b>${stats.tool_call_count || 0}</b><span>calls</span></div><div class="tool-chips">${tools || "<span>no tools</span>"}</div></article>`;
}

function badges(record) {
  const q = record.quality || {};
  const extracted = record.extracted || {};
  const items = [
    `stored ${extracted.score ?? "n/a"} / ${extracted.tier ?? "missing"}`,
    `computed ${q.computed_score ?? "n/a"} / ${q.computed_tier ?? "missing"}`,
    `${q.tool_rounds_used ?? 0}/${q.max_tool_rounds ?? 0} rounds`,
    `finish ${q.finish_reason || "missing"}`,
    `${q.prompt_tokens ?? "?"} prompt tok`,
    `${q.completion_tokens ?? "?"} completion tok`,
  ];
  return items.map((x) => `<span class="badge">${escapeHtml(x)}</span>`).join("");
}

function qualityList(record) {
  const rows = (record.quality || {}).issues || [];
  return `<ul class="check-list">${(rows.length ? rows : ["no detected issues"]).map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>`;
}

function signalCards(signals) {
  return ["code_available", "dataset_available", "weights_available", "dataset_is_standard"].map((name) => {
    const signal = signals[name] || {};
    const cls = signal.value ? "good" : "bad";
    return `<article class="panel signal ${cls}"><h2>${escapeHtml(labelize(name))}</h2><strong>${escapeHtml(String(signal.value))}</strong><div class="markdown">${renderMarkdown(signal.evidence || "")}</div></article>`;
  }).join("");
}

function transcript(trace) {
  const messages = (trace || {}).messages || [];
  return `<div class="transcript">${messages.map(renderMessage).join("") || empty("No parsed trace row")}</div>`;
}

function renderMessage(message, index) {
  const role = message.role || "unknown";
  const label = message.name ? `${role}: ${message.name}` : role;
  const content = typeof message.content === "string" ? message.content : "";
  const calls = (message.tool_calls || []).map((call) => {
    const fn = (call.function || {}).name || "unknown";
    const args = (call.function || {}).arguments || "";
    return `<pre>${escapeHtml(fn)}(${escapeHtml(args)})</pre>`;
  }).join("");
  return `<article class="message ${escapeAttr(role)}"><h3>#${index + 1} ${escapeHtml(label)}</h3>${content ? messageContent(role, content) : ""}${calls}</article>`;
}

function field(label, value) {
  return `<h3>${label}</h3><div class="markdown">${renderMarkdown(value || "missing")}</div>`;
}

function messageContent(role, content) {
  return role === "assistant" ? renderSmartText(content) : `<pre>${escapeHtml(content)}</pre>`;
}

function linkGroups(groups) {
  return Object.entries(groups).map(([name, urls]) => {
    const links = (urls || []).map((url) => `<li><a href="${escapeAttr(url)}">${escapeHtml(url)}</a></li>`).join("");
    return `<h3>${escapeHtml(labelize(name))}</h3><ul>${links || "<li>None</li>"}</ul>`;
  }).join("");
}

function rawBlock(label, payload) {
  if (!payload) return "";
  return `<details><summary>${label}</summary><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre></details>`;
}

function finalContent(final) {
  return (((final || {}).response || {}).body || {}).choices?.[0]?.message?.content || "";
}

function finalReasoning(final) {
  return (((final || {}).response || {}).body || {}).choices?.[0]?.message?.reasoning || "";
}

function miniMeter(value, max) {
  return `<span class="mini-meter"><i style="width:${Math.min(100, pct(value, max))}%"></i></span>`;
}

function sectionTitle(text) {
  return `<h2>${escapeHtml(text)}</h2>`;
}

function empty(text) {
  return `<p class="empty-note">${escapeHtml(text)}</p>`;
}

function pct(value, max) {
  return max ? Math.round((Number(value || 0) / Number(max)) * 100) : 0;
}

function labelize(value) {
  return String(value).replaceAll("_", " ");
}

function tierClass(label) {
  return String(label).toLowerCase().replace(/[^a-z]+/g, "-");
}

function issueClass(label) {
  return String(label).includes("drift") || String(label).includes("limit") ? "warn" : "bad";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

document.addEventListener("click", (event) => {
  const button = event.target.closest(".filters button");
  if (!button) return;
  state.filter = button.dataset.filter;
  document.querySelectorAll(".filters button").forEach((node) => node.classList.toggle("active", node === button));
  renderList();
});

$("search").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderList();
});
$("refresh").addEventListener("click", loadSummary);
loadSummary();
