function renderConversation(record) {
  const wrapper = document.createElement("div");
  wrapper.className = "thread";
  const events = record?.events || [];
  if (!events.length) return emptyNode("No conversation, output, or trace events found for this record.");
  wrapper.replaceChildren(...events.map(renderEvent));
  return wrapper;
}

function renderEvent(event) {
  const article = document.createElement("article");
  article.className = `bubble ${roleClass(event.role)}`;
  article.innerHTML = `<div class="bubbleRole">${esc(labelForRole(event))}</div>`;
  if (event.reasoning) article.appendChild(reasoningBlock(event.reasoning));
  if (event.content) article.appendChild(markdownBlock(event.content));
  if (event.tools?.length) article.appendChild(toolCallsBlock(event.tools));
  if (event.role === "tool_call") article.appendChild(singleToolBlock(event));
  if (event.role === "tool_result") article.appendChild(toolResultBlock(event));
  if (!event.content && !event.reasoning && !event.tools?.length && event.role !== "tool_result") {
    article.appendChild(emptyNode("Empty message."));
  }
  return article;
}

function renderInspector(record) {
  const div = document.createElement("div");
  if (!record) return emptyNode("No record selected.");
  div.className = "inspectorStack";
  div.appendChild(metricsPanel(record));
  if (record.extracted) div.appendChild(extractedPanel(record.extracted));
  div.appendChild(activityPanel(record));
  div.appendChild(rawPanel(record));
  return div;
}

function metricsPanel(record) {
  const usage = record.usage || {};
  const outputDetails = usage.output_tokens_details || usage.completion_tokens_details || {};
  const inputDetails = usage.input_tokens_details || usage.prompt_tokens_details || {};
  const values = [
    ["Tier", record.tier || "-"],
    ["Score", record.score || "-"],
    ["Tools", record.toolCount],
    ["Reasoning", record.reasoningCount],
    ["Input", usage.input_tokens ?? usage.prompt_tokens ?? "-"],
    ["Cached", inputDetails.cached_tokens ?? "-"],
    ["Output", usage.output_tokens ?? usage.completion_tokens ?? "-"],
    ["Reasoning Tok", outputDetails.reasoning_tokens ?? "-"],
    ["Total", usage.total_tokens ?? "-"],
    ["Rounds", record.toolLoop?.tool_rounds_used ?? "-"],
    ["Limit Hit", record.toolLoop?.hit_tool_round_limit ?? "-"],
    ["HTTP", record.statusCode || "-"]
  ];
  return panel("Run", `<div class="metricGrid">${values.map(([k, v]) => metric(k, v)).join("")}</div>`);
}

function extractedPanel(data) {
  const signals = data.signals || {};
  const rows = [
    textSection("Central Claim", data.central_claim || data.claim),
    textSection("MRE", data.mre_config),
    signalRows(signals),
    linksRows(data.verified_links || {}),
    textSection("Agent Task", data.agent_task),
    textSection("H100 Basis", data.h100_estimate_basis)
  ].filter(Boolean).join("");
  return panel("Extracted JSON", rows || `<pre>${esc(JSON.stringify(data, null, 2))}</pre>`);
}

function activityPanel(record) {
  const parts = record.rawParts.map((part) => `${part.kind}: ${part.source}:${part.line}`);
  const body = parts.length ? parts.map((part) => `<li>${esc(part)}</li>`).join("") : "<li>No source parts.</li>";
  return panel("Sources", `<ul class="sourceList">${body}</ul>`);
}

function rawPanel(record) {
  const raw = { request: record.requestRaw, response: record.responseRaw, extracted: record.extracted, parts: record.rawParts };
  return panel("Raw Payload", `<details><summary>Show JSON</summary><pre>${esc(JSON.stringify(raw, null, 2))}</pre></details>`);
}

function toolCallsBlock(tools) {
  const div = document.createElement("div");
  div.className = "toolStack";
  div.innerHTML = tools.map((tool) => toolCallHtml(tool)).join("");
  return div;
}

function singleToolBlock(event) {
  const name = event.name || "tool_call";
  const body = event.content ? `<pre>${esc(formatMaybeJson(event.content))}</pre>` : "";
  return htmlNode("div", "toolStack", toolCardHtml(name, "call", body));
}

function toolResultBlock(event) {
  const parsed = parseMaybeJson(event.content);
  const ok = parsed && typeof parsed === "object" ? parsed.ok : "";
  const label = ok === false ? "error" : "result";
  return htmlNode("div", "toolStack", toolCardHtml(event.name || "tool", label, `<pre>${esc(formatMaybeJson(parsed))}</pre>`));
}

function reasoningBlock(text) {
  return htmlNode("details", "reasoningBlock", `<summary>Reasoning</summary>${markdown(text)}`);
}

function markdownBlock(text) {
  return htmlNode("div", "markdown", markdown(text));
}

function toolCallHtml(tool) {
  return toolCardHtml(tool.name, "call", `<pre>${esc(JSON.stringify(tool.arguments, null, 2))}</pre>`);
}

function toolCardHtml(name, label, body) {
  return `<details class="toolCard" open><summary><span>${esc(name)}</span><em>${esc(label)}</em></summary>${body}</details>`;
}

function panel(title, body) {
  return htmlNode("section", "panel", `<h3>${esc(title)}</h3><div class="panelBody">${body}</div>`);
}

function metric(label, value) {
  return `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}

function textSection(title, value) {
  if (value === undefined || value === null || value === "") return "";
  return `<section class="textGroup"><h4>${esc(title)}</h4><p>${esc(value)}</p></section>`;
}

function signalRows(signals) {
  const rows = Object.entries(signals).filter(([, value]) => value && typeof value === "object");
  if (!rows.length) return "";
  return `<section class="textGroup"><h4>Signals</h4>${rows.map(([name, signal]) => (
    `<div class="signal ${signal.value ? "yes" : "no"}"><strong>${esc(labelize(name))}</strong><span>${signal.value ? "yes" : "no"}</span><p>${esc(signal.evidence || "")}</p></div>`
  )).join("")}</section>`;
}

function linksRows(groups) {
  const rows = Object.entries(groups).filter(([, links]) => Array.isArray(links) && links.length);
  if (!rows.length) return "";
  return `<section class="textGroup"><h4>Links</h4>${rows.map(([name, links]) => (
    `<div class="linkGroup"><strong>${esc(labelize(name))}</strong>${links.map(linkHtml).join("")}</div>`
  )).join("")}</section>`;
}

function linkHtml(link) {
  const text = String(link || "");
  return /^https?:\/\//i.test(text)
    ? `<a href="${esc(text)}" target="_blank" rel="noreferrer">${esc(text)}</a>`
    : `<span>${esc(text)}</span>`;
}

function markdown(text) {
  return esc(text).split(/\n{2,}/).map((block) => {
    if (block.startsWith("```")) return `<pre>${block.replace(/^```[^\n]*\n?|\n?```$/g, "")}</pre>`;
    if (/^#{1,3} /.test(block)) return block.replace(/^(#{1,3}) (.*)$/m, (_, h, b) => `<h${h.length}>${b}</h${h.length}>`);
    if (/^[-*] /m.test(block)) return `<ul>${block.split("\n").map((line) => `<li>${line.replace(/^[-*] /, "")}</li>`).join("")}</ul>`;
    return `<p>${block.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

function transcriptText(record) {
  return (record?.events || []).map((event) => {
    const tools = (event.tools || []).map((tool) => `[tool ${tool.name}] ${JSON.stringify(tool.arguments)}`).join("\n");
    return [`${labelForRole(event)}:`, event.reasoning && `[reasoning]\n${event.reasoning}`, event.content, tools].filter(Boolean).join("\n");
  }).join("\n\n");
}

function labelForRole(event) {
  if (event.role === "tool_result") return `Tool result: ${event.name || "tool"}`;
  if (event.role === "tool_call") return `Tool call: ${event.name || "tool"}`;
  return labelize(event.role || "message");
}

function roleClass(role) {
  return String(role || "message").replace(/[^a-z0-9_-]/gi, "_").toLowerCase();
}

function labelize(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMaybeJson(value) {
  if (typeof value === "string") {
    try { return JSON.stringify(JSON.parse(value), null, 2); } catch { return value; }
  }
  return JSON.stringify(value, null, 2);
}

function htmlNode(tag, className, html) {
  const node = document.createElement(tag);
  node.className = className;
  node.innerHTML = html;
  return node;
}

function emptyNode(text) {
  const node = document.createElement("div");
  node.className = "empty";
  node.textContent = text;
  return node;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}
