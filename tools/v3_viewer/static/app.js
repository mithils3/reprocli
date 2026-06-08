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
  const stats = [
    ["Records", summary.record_count],
    ["Clean JSON", `${summary.clean_final_json}/${summary.record_count}`],
    ["Round limit", summary.round_limit],
    ["Score drift", summary.score_drift],
    ["Trace errors", summary.trace_errors],
    ["Trace rows", `${summary.trace_rows}/${summary.record_count}`],
  ];
  $("stats").innerHTML = stats.map(([label, value]) => `
    <div class="stat"><strong>${escapeHtml(value)}</strong><span>${label}</span></div>
  `).join("");
}

function renderList() {
  const query = state.query.toLowerCase();
  const rows = state.records.filter((record) => {
    const haystack = `${record.custom_id} ${record.title} ${record.tier}`.toLowerCase();
    if (query && !haystack.includes(query)) return false;
    if (state.filter === "issues") return record.quality.issues.length > 0;
    if (state.filter === "round") return record.quality.hit_tool_round_limit;
    if (state.filter === "drift") return record.quality.score_drift;
    if (state.filter === "trace") return record.quality.issues.some((x) => x.includes("trace"));
    return true;
  });
  $("recordList").innerHTML = rows.map(recordCard).join("");
  document.querySelectorAll(".record").forEach((node) => {
    node.addEventListener("click", () => selectRecord(node.dataset.id));
  });
}

function recordCard(record) {
  const active = state.selected === record.custom_id ? " active" : "";
  const issueClass = record.quality.issues.length ? "warn" : "good";
  return `
    <div class="record${active}" data-id="${escapeAttr(record.custom_id)}">
      <div class="id">
        <span>${escapeHtml(record.custom_id)}</span>
        <span class="${issueClass}">${escapeHtml(record.tier || "missing")}</span>
      </div>
      <div class="badges">
        <span class="badge">score ${escapeHtml(record.score ?? "n/a")}</span>
        <span class="badge">${escapeHtml(record.quality.tool_rounds_used ?? 0)} rounds</span>
        <span class="badge">${escapeHtml(record.web_verification || "no web")}</span>
      </div>
      <p>${escapeHtml(record.title || "No extracted claim")}</p>
    </div>
  `;
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
  const trace = record.trace || {};
  const messages = trace.messages || [];
  $("detail").innerHTML = `
    <section class="panel ${quality.issues.length ? "warn-bg" : "good-bg"}">
      <h2>${escapeHtml(record.custom_id)}</h2>
      <div class="badges">${badges(record)}</div>
    </section>
    <section class="panel">
      <h2>Classification</h2>
      ${field("Central claim", extracted.central_claim)}
      ${field("MRE config", extracted.mre_config)}
      ${field("Agent task", extracted.agent_task)}
    </section>
    <section class="grid">${signalCards(extracted.signals || {})}</section>
    <section class="panel">
      <h2>Quality Checks</h2>
      ${qualityList(record)}
    </section>
    <section class="panel">
      <h2>Verified Links</h2>
      ${linkGroups(extracted.verified_links || {})}
    </section>
    <section class="panel">
      <h2>Final Answer</h2>
      <pre>${escapeHtml(finalContent(record.final))}</pre>
    </section>
    <section class="panel">
      <h2>Assistant Reasoning</h2>
      <pre>${escapeHtml(finalReasoning(record.final) || "No reasoning block saved.")}</pre>
    </section>
    <section class="panel">
      <h2>Transcript</h2>
      <div class="transcript">${messages.map(renderMessage).join("") || "No parsed trace row."}</div>
    </section>
    <section class="panel">
      <h2>Raw Payloads</h2>
      ${rawBlock("Extracted JSON", extracted)}
      ${rawBlock("Final row", record.final)}
      ${rawBlock("Trace row", record.trace)}
      ${rawBlock("Trace parse error", record.trace_error)}
    </section>
  `;
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
  const q = record.quality || {};
  const issues = q.issues || [];
  const rows = issues.length ? issues : ["no detected issues"];
  return `<ul>${rows.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>`;
}

function signalCards(signals) {
  return ["code_available", "dataset_available", "weights_available", "dataset_is_standard"]
    .map((name) => {
      const signal = signals[name] || {};
      const cls = signal.value ? "good" : "bad";
      return `<div class="panel signal">
        <h3>${escapeHtml(name)}</h3>
        <strong class="${cls}">${escapeHtml(String(signal.value))}</strong>
        <p>${escapeHtml(signal.evidence || "")}</p>
      </div>`;
    }).join("");
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
  return `<article class="message ${escapeAttr(role)}">
    <h3>#${index + 1} ${escapeHtml(label)}</h3>
    ${content ? `<pre>${escapeHtml(content)}</pre>` : ""}
    ${calls}
  </article>`;
}

function field(label, value) {
  return `<h3>${label}</h3><p>${escapeHtml(value || "missing")}</p>`;
}

function linkGroups(groups) {
  return Object.entries(groups).map(([name, urls]) => {
    const links = (urls || []).map((url) => `<li><a href="${escapeAttr(url)}">${escapeHtml(url)}</a></li>`).join("");
    return `<h3>${escapeHtml(name)}</h3><ul>${links || "<li>None</li>"}</ul>`;
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
