const state = { records: [], filtered: [], selected: -1, tab: "answer", files: [] };
const $ = (id) => document.getElementById(id);
const els = {
  source: $("sourceLabel"), select: $("serverFileSelect"), open: $("openServerFile"),
  input: $("fileInput"), drop: $("dropzone"), search: $("searchInput"),
  status: $("statusFilter"), tier: $("tierFilter"), list: $("recordList"),
  title: $("detailTitle"), meta: $("detailMeta"), content: $("content"),
  prev: $("prevRecord"), next: $("nextRecord"), copyInput: $("copyInput"),
  copyAnswer: $("copyAnswer"), copyJson: $("copyJson"), download: $("downloadFiltered"),
  clear: $("clearRecords"), toast: $("toast")
};

document.querySelectorAll(".tabs button").forEach((button) => {
  button.onclick = () => {
    state.tab = button.dataset.tab;
    document.querySelectorAll(".tabs button").forEach((tab) => tab.classList.toggle("active", tab === button));
    renderDetail();
  };
});
els.open.onclick = openServerFile;
els.input.onchange = (event) => loadFiles([...event.target.files]);
els.search.oninput = applyFilters;
els.status.onchange = applyFilters;
els.tier.onchange = applyFilters;
els.prev.onclick = () => move(-1);
els.next.onclick = () => move(1);
els.copyInput.onclick = () => copy(textOf(selected()?.inputMessages));
els.copyAnswer.onclick = () => copy(selected()?.content || "");
els.copyJson.onclick = () => copy(JSON.stringify(selected()?.extracted || selected()?.raw || {}, null, 2));
els.download.onclick = downloadFiltered;
els.clear.onclick = () => loadRecords([], []);
["dragenter", "dragover"].forEach((name) => els.drop.addEventListener(name, drag));
["dragleave", "drop"].forEach((name) => els.drop.addEventListener(name, (event) => {
  event.preventDefault(); els.drop.classList.remove("active");
}));
els.drop.ondrop = (event) => loadFiles([...event.dataTransfer.files]);

init();

async function init() {
  render();
  try {
    const payload = await (await fetch("/api/files")).json();
    state.files = payload.files || [];
  } catch {
    state.files = [];
  }
  els.select.replaceChildren(...(state.files.length ? state.files.map(fileOption) : [opt("", "No server files found")]));
  els.open.disabled = !state.files.length;
  if (state.files.length === 1) openServerFile();
}

function fileOption(file) {
  return opt(file.path, `${file.path} (${formatBytes(file.size)})`);
}

function opt(value, label) {
  const option = document.createElement("option");
  option.value = value; option.textContent = label;
  return option;
}

async function openServerFile() {
  const path = els.select.value;
  if (!path) return;
  const paths = [...new Set([path, pairedPath(path)].filter(Boolean))];
  const texts = await Promise.all(paths.map(async (filePath) => ({
    name: filePath,
    text: await (await fetch(`/api/file?path=${encodeURIComponent(filePath)}`)).text()
  })));
  loadTexts(texts);
}

function pairedPath(path) {
  const known = new Set(state.files.map((file) => file.path));
  const candidates = path.endsWith("_requests.jsonl")
    ? [path.replace(/_requests\.jsonl$/, ".jsonl"), path.replace(/_requests\.jsonl$/, "_responses.jsonl")]
    : [path.replace(/\.jsonl$/, "_requests.jsonl"), path.replace(/_responses\.jsonl$/, "_requests.jsonl")];
  return candidates.find((candidate) => candidate !== path && known.has(candidate));
}

async function loadFiles(files) {
  const jsonl = files.filter((file) => file.name.endsWith(".jsonl") || file.type.includes("json"));
  if (!jsonl.length) return toast("No JSONL files selected.");
  loadTexts(await Promise.all(jsonl.map(async (file) => ({ name: file.name, text: await file.text() }))));
}

function loadTexts(texts) {
  const entries = texts.flatMap(({ name, text }) => parseJsonl(text, name));
  loadRecords(merge(entries), texts.map((item) => item.name));
  toast(`Loaded ${entries.length} line(s) from ${texts.length} file(s).`);
}

function loadRecords(records, sources) {
  state.records = records; state.selected = records.length ? 0 : -1;
  els.source.textContent = sources.length ? sources.join(", ") : "No file loaded";
  applyFilters();
}

function parseJsonl(text, source) {
  return text.split(/\r?\n/).flatMap((line, index) => {
    if (!line.trim()) return [];
    try { return [normalize(JSON.parse(line), source, index + 1)]; }
    catch (error) { return [parseError(line, source, index + 1, error)]; }
  });
}

function parseError(rawLine, source, lineNumber, error) {
  const raw = { parse_error: error.message, raw_line: rawLine };
  return baseRecord({ raw, source, line: lineNumber, id: `${source}:${lineNumber}`, status: "parse_error", rawParts: [{ raw }] });
}

function normalize(raw, source, line) {
  const body = raw?.response?.body || raw?.body || raw;
  const choice = (body?.choices || raw?.choices || [])[0] || {};
  const message = choice.message || {};
  const requestMessages = raw?.body && !raw?.response ? normalizeMessages(raw.body.messages || raw.body.input || []) : [];
  const responseMessages = responsesMessages(body);
  const outputMessages = responseMessages.length ? responseMessages : normalizeMessages(message.role || message.content ? [message] : []);
  const content = message.content || body?.output_text || raw?.output_text || textOf(responseMessages);
  const extracted = raw?.signals || raw?.central_claim ? raw : extractJson(content);
  const id = String(raw.custom_id || raw.id || body.id || `${source}:${line}`);
  const status = raw.error || raw?.response?.error ? "error" : requestMessages.length && !content ? "request" : "success";
  return baseRecord({
    raw, source, line, id, customId: String(raw.custom_id || ""), status,
    statusCode: raw?.response?.status_code || "", model: body.model || "",
    finish: choice.finish_reason || "", content, extracted,
    reasoning: reasoningText(body) || message.reasoning || choice.reasoning || raw.reasoning || "",
    inputMessages: requestMessages, outputMessages, requestRaw: requestMessages.length ? raw : null,
    responseRaw: requestMessages.length ? null : raw, rawParts: [{ raw }],
    totalTokens: Number(body?.usage?.total_tokens || 0),
    tier: String(extracted?.tier || ""), score: String(extracted?.score ?? ""),
    claim: String(extracted?.central_claim || extracted?.claim || "")
  });
}

function responsesMessages(body) {
  return (body?.output || []).filter((item) => item.type === "message").flatMap((item) => {
    const content = flattenResponsesContent(item.content);
    return content ? [{ role: item.role || "assistant", content }] : [];
  });
}

function flattenResponsesContent(content) {
  return Array.isArray(content) ? content.map((item) => item?.text || item?.content || "").filter(Boolean).join("\n") : "";
}

function reasoningText(body) {
  return (body?.output || []).filter((item) => item.type === "reasoning").flatMap((item) => {
    const summary = Array.isArray(item.summary) ? item.summary.map((part) => part.text || "").filter(Boolean) : [];
    const content = Array.isArray(item.content) ? item.content.map((part) => part.text || "").filter(Boolean) : [];
    return [...summary, ...content];
  }).join("\n\n");
}

function baseRecord(record) {
  return { inputMessages: [], outputMessages: [], content: "", reasoning: "", extracted: null, tier: "", score: "", claim: "", totalTokens: 0, ...record };
}

function normalizeMessages(messages) {
  return Array.isArray(messages) ? messages.map((msg, index) => ({
    role: String(msg?.role || `message_${index + 1}`),
    content: flatten(msg?.content ?? msg?.text ?? "")
  })).filter((msg) => msg.content || msg.role) : [];
}

function flatten(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(flatten).join("\n");
  if (value && typeof value === "object") return value.text || value.content || JSON.stringify(value, null, 2);
  return "";
}

function merge(entries) {
  const rows = [], byId = new Map();
  for (const entry of entries) {
    if (!entry.customId) { rows.push(finalize(entry)); continue; }
    const existing = byId.get(entry.customId);
    if (!existing) { byId.set(entry.customId, entry); rows.push(entry); continue; }
    existing.inputMessages = entry.inputMessages.length ? entry.inputMessages : existing.inputMessages;
    existing.outputMessages = entry.outputMessages.length ? entry.outputMessages : existing.outputMessages;
    Object.assign(existing, entry.content ? entry : {});
    existing.requestRaw = entry.requestRaw || existing.requestRaw;
    existing.responseRaw = entry.responseRaw || existing.responseRaw;
    existing.rawParts.push(...entry.rawParts);
  }
  return rows.map(finalize);
}

function finalize(record) {
  record.search = [record.id, record.model, record.tier, record.claim, record.content, record.reasoning, textOf(record.inputMessages), JSON.stringify(record.extracted || {})].join(" ").toLowerCase();
  return record;
}

function applyFilters() {
  const query = els.search.value.trim().toLowerCase();
  const status = els.status.value, tier = els.tier.value;
  state.filtered = state.records.filter((record) => (!query || record.search.includes(query)) && (status === "all" || record.status === status) && (tier === "all" || record.tier === tier));
  updateTierOptions();
  if (!state.filtered[state.selected]) state.selected = state.filtered.length ? 0 : -1;
  render();
}

function updateTierOptions() {
  const current = els.tier.value;
  const tiers = [...new Set(state.records.map((record) => record.tier).filter(Boolean))].sort();
  els.tier.replaceChildren(opt("all", "All tiers"), ...tiers.map((tier) => opt(tier, tier)));
  els.tier.value = tiers.includes(current) ? current : "all";
}

function render() {
  const success = state.records.filter((record) => record.status === "success").length;
  $("statRecords").textContent = fmt(state.records.length);
  $("statTokens").textContent = fmt(state.records.reduce((sum, record) => sum + record.totalTokens, 0));
  $("statSuccess").textContent = fmt(success);
  $("statErrors").textContent = fmt(state.records.length - success);
  renderList(); renderDetail();
  els.prev.disabled = state.selected <= 0; els.next.disabled = state.selected >= state.filtered.length - 1;
}

function renderList() {
  els.list.replaceChildren(...(state.filtered.length ? state.filtered.map(recordButton) : [empty("No records loaded.")]));
}

function recordButton(record, index) {
  const button = document.createElement("button");
  button.className = `record${index === state.selected ? " selected" : ""}`;
  button.onclick = () => { state.selected = index; render(); };
  button.innerHTML = `<div class="top"><span class="id">${esc(record.id)}</span>${badge(record.status)}${record.tier ? badge(record.tier, "warn") : ""}</div><div class="sub">${esc(record.source || "")} | line ${record.line || ""} | ${fmt(record.totalTokens)} tokens | ${esc(record.finish || "")}</div><div class="excerpt">${esc(record.claim || record.content || textOf(record.inputMessages) || record.reasoning || "Empty record")}</div>`;
  return button;
}

function renderDetail() {
  const record = selected();
  if (!record) { els.title.textContent = "Load a JSONL file"; els.meta.replaceChildren(); els.content.replaceChildren(empty("Open or upload JSONL.")); return; }
  els.title.textContent = record.id;
  els.meta.innerHTML = [record.source, `line ${record.line}`, record.status, record.statusCode && `HTTP ${record.statusCode}`, record.model, record.inputMessages.length ? "input loaded" : "output only", record.tier && `tier ${record.tier}`, record.score && `score ${record.score}`].filter(Boolean).map((item) => `<span class="badge">${esc(item)}</span>`).join("");
  const renderers = { input: renderInput, answer: renderAnswer, reasoning: renderReasoning, json: renderJson, raw: renderRaw };
  els.content.replaceChildren(renderers[state.tab](record));
}

function renderInput(record) {
  return record.inputMessages.length ? messages(record.inputMessages) : empty("No request/input messages loaded for this id.");
}
function renderAnswer(record) { return record.outputMessages.length ? messages(record.outputMessages) : messages([{ role: "assistant", content: record.content }]); }
function renderReasoning(record) { return record.reasoning ? messages([{ role: "reasoning", content: record.reasoning }]) : empty("No reasoning field."); }
function renderJson(record) { return renderExtractedJson(record); }
function renderRaw(record) { return code(JSON.stringify({ request: record.requestRaw, response: record.responseRaw || record.raw, parts: record.rawParts }, null, 2)); }

function messages(items) {
  const div = document.createElement("div");
  div.innerHTML = items.map((msg) => `<article class="message"><div class="role">${esc(msg.role)}</div><div class="markdown">${markdown(msg.content || "")}</div></article>`).join("");
  return div;
}

function markdown(text) {
  const escaped = esc(text);
  return escaped.split(/\n{2,}/).map((block) => {
    if (block.startsWith("```")) return `<pre>${block.replace(/^```[^\n]*\n?|\n?```$/g, "")}</pre>`;
    if (/^#{1,3} /.test(block)) return block.replace(/^(#{1,3}) (.*)$/m, (_, hashes, body) => `<h${hashes.length}>${body}</h${hashes.length}>`);
    if (/^[-*] /m.test(block)) return `<ul>${block.split("\n").map((line) => `<li>${line.replace(/^[-*] /, "")}</li>`).join("")}</ul>`;
    return `<p>${block.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

function extractJson(text) {
  const match = text.match(/```json\s*([\s\S]*?)```/i);
  const candidate = match ? match[1] : text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1);
  try { return candidate ? JSON.parse(candidate) : null; } catch { return null; }
}

function selected() { return state.filtered[state.selected] || null; }
function move(delta) { state.selected = Math.max(0, Math.min(state.filtered.length - 1, state.selected + delta)); render(); }
function textOf(messages) { return (messages || []).map((msg) => msg.content).join("\n\n"); }
function code(text) { const pre = document.createElement("pre"); pre.className = "code"; pre.textContent = text; return pre; }
function empty(text) { const div = document.createElement("div"); div.className = "empty"; div.textContent = text; return div; }
function badge(text, kind = text === "success" ? "good" : text === "error" ? "bad" : "warn") { return `<span class="badge ${kind}">${esc(text)}</span>`; }
function fmt(value) { return new Intl.NumberFormat().format(Number(value || 0)); }
function formatBytes(value) { return value < 1024 ? `${value} B` : value < 1048576 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1048576).toFixed(1)} MB`; }
function esc(value) { return String(value || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])); }
function drag(event) { event.preventDefault(); els.drop.classList.add("active"); }
function copy(text) { navigator.clipboard?.writeText(text || "").then(() => toast("Copied.")); }
function toast(text) { els.toast.textContent = text; els.toast.classList.add("show"); setTimeout(() => els.toast.classList.remove("show"), 1800); }
function downloadFiltered() {
  const lines = state.filtered.flatMap((record) => record.rawParts.map((part) => JSON.stringify(part.raw)));
  const url = URL.createObjectURL(new Blob([lines.join("\n") + "\n"], { type: "application/jsonl" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: "filtered_conversations.jsonl" });
  link.click(); URL.revokeObjectURL(url);
}
