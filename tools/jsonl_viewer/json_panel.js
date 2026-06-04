function renderExtractedJson(record) {
  const data = record.extracted;
  if (!data) return empty("No JSON object found in answer.");
  const div = document.createElement("div");
  div.className = "json-view";
  div.innerHTML = [
    summary(record, data),
    runSection(record),
    toolSection(record),
    textSection("Central Claim", data.central_claim || data.claim),
    textSection("Claim Evidence", data.claim_evidence),
    textSection("MRE Config", data.mre_config),
    signalSection(data.signals || {}),
    linksSection(data.verified_links || {}),
    textSection("Agent Task", data.agent_task),
    textSection("H100 Estimate Basis", data.h100_estimate_basis),
    rawSection(data)
  ].filter(Boolean).join("");
  return div;
}

function summary(record, data) {
  const usage = usageInfo(record);
  return `<section class="json-hero">
    ${metric("Tier", data.tier || "-")}
    ${metric("Score", data.score ?? "-")}
    ${metric("H100 Hours", data.h100_hours_estimate ?? "-")}
    ${metric("Tokens", usage.total ?? record.totalTokens ?? "-")}
  </section>`;
}

function metric(label, value) {
  return `<div><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}

function textSection(title, value) {
  if (value === undefined || value === null || value === "") return "";
  return `<section class="json-section"><h3>${esc(title)}</h3><p>${esc(value)}</p></section>`;
}

function runSection(record) {
  const body = responseBody(record);
  const usage = usageInfo(record);
  const calls = outputCounts(body);
  const duration = elapsed(body);
  const items = [
    ["Model", record.model || body?.model],
    ["Status", body?.status || record.status],
    ["Web", record.extracted?.web_verification],
    ["HTTP", record.statusCode],
    ["Finish", record.finish],
    ["Web calls", calls.web],
    ["Output items", calls.output],
    ["Duration", duration],
    ["Input", usage.input],
    ["Cached", usage.cached],
    ["Output", usage.output],
    ["Reasoning", usage.reasoning],
    ["Total", usage.total]
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!items.length) return "";
  return `<section class="json-section"><h3>Run Metadata</h3>
    <div class="run-grid">${items.map(([label, value]) => metric(label, fmtMaybe(value))).join("")}</div>
  </section>`;
}

function toolSection(record) {
  const calls = openAiToolCalls(responseBody(record)).slice(0, 14);
  if (!calls.length) return "";
  const total = openAiToolCalls(responseBody(record)).length;
  return `<section class="json-section"><h3>Verification Activity</h3><div class="tool-list">
    ${calls.map(toolCall).join("")}
    ${total > calls.length ? `<div class="tool-more">${fmt(total - calls.length)} more call(s)</div>` : ""}
  </div></section>`;
}

function toolCall(call) {
  const label = call.kind === "open_page" ? "Opened" : call.kind === "search" ? "Searched" : labelize(call.kind);
  return `<article class="tool-call"><strong>${label}</strong><span>${esc(call.text)}</span></article>`;
}

function signalSection(signals) {
  const rows = [
    ["Code", signals.code_available],
    ["Dataset", signals.dataset_available],
    ["Weights", signals.weights_available],
    ["Standard Dataset", signals.dataset_is_standard]
  ].filter(([, signal]) => signal);
  if (!rows.length) return "";
  return `<section class="json-section"><h3>Artifact Signals</h3><div class="signal-list">
    ${rows.map(([label, signal]) => signalRow(label, signal)).join("")}
  </div></section>`;
}

function signalRow(label, signal) {
  const good = Boolean(signal.value);
  return `<article class="signal ${good ? "yes" : "no"}">
    <div><strong>${esc(label)}</strong><span>${good ? "Available" : "Missing"}</span></div>
    <p>${esc(signal.evidence || "")}</p>
  </article>`;
}

function linksSection(groups) {
  const sections = Object.entries(groups).filter(([, links]) => Array.isArray(links) && links.length);
  if (!sections.length) return "";
  return `<section class="json-section"><h3>Verified Links</h3><div class="link-groups">
    ${sections.map(([name, links]) => linkGroup(name, links)).join("")}
  </div></section>`;
}

function linkGroup(name, links) {
  return `<div class="link-group"><h4>${labelize(name)}</h4>
    ${links.map((link) => linkItem(link)).join("")}
  </div>`;
}

function linkItem(value) {
  const text = String(value || "");
  const isUrl = /^https?:\/\//i.test(text);
  return isUrl ? `<a href="${esc(text)}" target="_blank" rel="noreferrer">${esc(text)}</a>` : `<span>${esc(text)}</span>`;
}

function rawSection(data) {
  return `<details class="json-raw"><summary>Raw JSON</summary>${code(JSON.stringify(data, null, 2)).outerHTML}</details>`;
}

function labelize(value) {
  return esc(String(value || "").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()));
}

function responseBody(record) {
  return record?.responseRaw?.response?.body || record?.raw?.response?.body || record?.responseRaw?.body || record?.raw?.body || {};
}

function usageInfo(record) {
  const usage = responseBody(record)?.usage || {};
  const inputDetails = usage.input_tokens_details || usage.prompt_tokens_details || {};
  const outputDetails = usage.output_tokens_details || usage.completion_tokens_details || {};
  return {
    input: usage.input_tokens ?? usage.prompt_tokens,
    cached: inputDetails.cached_tokens,
    output: usage.output_tokens ?? usage.completion_tokens,
    reasoning: outputDetails.reasoning_tokens,
    total: usage.total_tokens
  };
}

function outputCounts(body) {
  const output = Array.isArray(body?.output) ? body.output : [];
  return {
    output: output.length || "",
    web: output.filter((item) => item.type === "web_search_call").length || ""
  };
}

function openAiToolCalls(body) {
  const output = Array.isArray(body?.output) ? body.output : [];
  return output.filter((item) => item.type === "web_search_call").map((item) => {
    const action = item.action || {};
    return { kind: action.type || "web_search", text: action.url || action.query || (action.queries || []).join(" | ") || item.status || "" };
  }).filter((item) => item.text);
}

function elapsed(body) {
  const start = body?.created_at || body?.created;
  const end = body?.completed_at;
  return start && end ? `${fmtMaybe(end - start)}s` : "";
}

function fmtMaybe(value) {
  return typeof value === "number" ? fmt(value) : value;
}
