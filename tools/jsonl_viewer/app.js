const state = { records: [], filtered: [], selected: -1, files: [] };
const $ = (id) => document.getElementById(id);
const els = {
  source: $("sourceLabel"),
  select: $("serverFileSelect"),
  open: $("openServerFile"),
  input: $("fileInput"),
  drop: $("dropzone"),
  search: $("searchInput"),
  status: $("statusFilter"),
  tier: $("tierFilter"),
  list: $("recordList"),
  title: $("detailTitle"),
  meta: $("detailMeta"),
  conversation: $("conversation"),
  inspector: $("inspector"),
  prev: $("prevRecord"),
  next: $("nextRecord"),
  copyTranscript: $("copyTranscript"),
  copyJson: $("copyJson"),
  download: $("downloadFiltered"),
  clear: $("clearRecords"),
  toast: $("toast")
};

init();

async function init() {
  bindEvents();
  render();
  await loadServerFileList();
}

function bindEvents() {
  els.open.onclick = openServerFile;
  els.input.onchange = (event) => loadFiles([...event.target.files]);
  els.search.oninput = applyFilters;
  els.status.onchange = applyFilters;
  els.tier.onchange = applyFilters;
  els.prev.onclick = () => moveSelection(-1);
  els.next.onclick = () => moveSelection(1);
  els.copyTranscript.onclick = () => copy(transcriptText(selected()));
  els.copyJson.onclick = () => copy(JSON.stringify(selected()?.extracted || selected()?.rawParts || {}, null, 2));
  els.download.onclick = downloadFiltered;
  els.clear.onclick = () => loadRecords([], []);
  ["dragenter", "dragover"].forEach((name) => els.drop.addEventListener(name, dragOver));
  ["dragleave", "drop"].forEach((name) => els.drop.addEventListener(name, dragEnd));
  els.drop.ondrop = (event) => loadFiles([...event.dataTransfer.files]);
}

async function loadServerFileList() {
  try {
    const payload = await (await fetch("/api/files")).json();
    state.files = payload.files || [];
  } catch {
    state.files = [];
  }
  els.select.replaceChildren(...(state.files.length ? state.files.map(fileOption) : [option("", "No server files found")]));
  els.open.disabled = !state.files.length;
}

function fileOption(file) {
  return option(file.path, `${file.path} (${formatBytes(file.size)})`);
}

function option(value, label) {
  const item = document.createElement("option");
  item.value = value;
  item.textContent = label;
  return item;
}

async function openServerFile() {
  const path = els.select.value;
  if (!path) return;
  const paths = relatedServerPaths(path);
  const texts = [];
  for (const filePath of paths) {
    const response = await fetch(`/api/file?path=${encodeURIComponent(filePath)}`);
    if (response.ok) texts.push({ name: filePath, text: await response.text() });
  }
  loadTexts(texts);
}

function relatedServerPaths(path) {
  const known = new Set(state.files.map((file) => file.path));
  const stem = path.replace(/(_trace|_extracted|_requests|_responses|_batch_input|_batch_results|_batch_errors)?\.jsonl$/, "");
  const candidates = [
    path,
    `${stem}.jsonl`,
    `${stem}_trace.jsonl`,
    `${stem}_extracted.jsonl`,
    `${stem}_requests.jsonl`,
    `${stem}_responses.jsonl`,
    `${stem}_batch_input.jsonl`,
    `${stem}_batch_results.jsonl`,
    `${stem}_batch_errors.jsonl`
  ];
  const exact = candidates.filter((candidate) => known.has(candidate));
  const prefixed = state.files
    .map((file) => file.path)
    .filter((candidate) => (
      candidate.startsWith(`${stem}_batch_results`) ||
      candidate.startsWith(`${stem}_batch_errors`)
    ) && candidate.endsWith(".jsonl"));
  return [...new Set([...exact, ...prefixed])];
}

async function loadFiles(files) {
  const jsonl = files.filter((file) => file.name.endsWith(".jsonl") || file.type.includes("json"));
  if (!jsonl.length) return toast("No JSONL files selected.");
  const texts = await Promise.all(jsonl.map(async (file) => ({ name: file.name, text: await file.text() })));
  loadTexts(texts);
}

function loadTexts(texts) {
  const entries = texts.flatMap(({ name, text }) => parseJsonlText(text, name));
  loadRecords(mergeRecords(entries), texts.map((item) => item.name));
  toast(`Loaded ${entries.length} JSONL row(s) from ${texts.length} file(s).`);
}

function loadRecords(records, sources) {
  state.records = records;
  state.selected = records.length ? 0 : -1;
  els.source.textContent = sources.length ? sources.join(", ") : "No file loaded";
  updateTierOptions();
  applyFilters();
}

function applyFilters() {
  const query = els.search.value.trim().toLowerCase();
  const status = els.status.value;
  const tier = els.tier.value;
  const currentId = selected()?.id;
  state.filtered = state.records.filter((record) => {
    const statusMatch = status === "all" || record.status === status;
    const tierMatch = tier === "all" || record.tier === tier;
    return statusMatch && tierMatch && (!query || record.search.includes(query));
  });
  const nextIndex = state.filtered.findIndex((record) => record.id === currentId);
  state.selected = nextIndex >= 0 ? nextIndex : (state.filtered.length ? 0 : -1);
  render();
}

function updateTierOptions() {
  const current = els.tier.value;
  const tiers = [...new Set(state.records.map((record) => record.tier).filter(Boolean))].sort();
  els.tier.replaceChildren(option("all", "All tiers"), ...tiers.map((tier) => option(tier, tier)));
  els.tier.value = tiers.includes(current) ? current : "all";
}

function render() {
  renderStats();
  renderList();
  renderDetail();
  els.prev.disabled = state.selected <= 0;
  els.next.disabled = state.selected >= state.filtered.length - 1;
}

function renderStats() {
  $("statRecords").textContent = formatNumber(state.records.length);
  $("statTools").textContent = formatNumber(state.records.reduce((sum, record) => sum + record.toolCount, 0));
  $("statReasoning").textContent = formatNumber(state.records.reduce((sum, record) => sum + record.reasoningCount, 0));
  $("statTokens").textContent = formatNumber(state.records.reduce((sum, record) => sum + record.totalTokens, 0));
}

function renderList() {
  els.list.replaceChildren(...(state.filtered.length ? state.filtered.map(recordButton) : [emptyListItem("No records loaded.")]));
}

function recordButton(record, index) {
  const button = document.createElement("button");
  button.className = `record${index === state.selected ? " selected" : ""}`;
  button.onclick = () => { state.selected = index; render(); };
  const title = record.title || record.claim || record.id;
  button.innerHTML = `
    <div class="recordTop"><span class="id">${esc(record.id)}</span>${badge(record.status)}${record.tier ? badge(record.tier, "tier") : ""}</div>
    <div class="recordTitle">${esc(title)}</div>
    <div class="recordMeta">${esc(record.model || "unknown model")} | ${formatNumber(record.toolCount)} tools | ${formatNumber(record.reasoningCount)} reasoning | ${formatNumber(record.totalTokens)} tokens</div>
  `;
  return button;
}

function renderDetail() {
  const record = selected();
  if (!record) {
    els.title.textContent = "Load a JSONL file";
    els.meta.replaceChildren();
    els.conversation.replaceChildren(emptyNode("Open or upload JSONL."));
    els.inspector.replaceChildren(emptyNode("No record selected."));
    return;
  }
  els.title.textContent = record.title || record.id;
  els.meta.innerHTML = [
    record.id,
    record.status,
    record.model,
    record.statusCode && `HTTP ${record.statusCode}`,
    record.tier && `tier ${record.tier}`,
    record.score && `score ${record.score}`,
    `${record.rawParts.length} source file(s)`
  ].filter(Boolean).map((item) => `<span class="badge">${esc(item)}</span>`).join("");
  els.conversation.replaceChildren(renderConversation(record));
  els.inspector.replaceChildren(renderInspector(record));
}

function selected() {
  return state.filtered[state.selected] || null;
}

function moveSelection(delta) {
  state.selected = Math.max(0, Math.min(state.filtered.length - 1, state.selected + delta));
  render();
}

function emptyListItem(text) {
  const item = document.createElement("div");
  item.className = "empty";
  item.textContent = text;
  return item;
}

function badge(text, kind = "") {
  return `<span class="badge ${kind || String(text).toLowerCase()}">${esc(text)}</span>`;
}

function dragOver(event) {
  event.preventDefault();
  els.drop.classList.add("active");
}

function dragEnd(event) {
  event.preventDefault();
  els.drop.classList.remove("active");
}

function copy(text) {
  navigator.clipboard?.writeText(text || "").then(() => toast("Copied."));
}

function toast(text) {
  els.toast.textContent = text;
  els.toast.classList.add("show");
  setTimeout(() => els.toast.classList.remove("show"), 1800);
}

function downloadFiltered() {
  const lines = state.filtered.flatMap((record) => record.rawParts.map((part) => JSON.stringify(part.raw)));
  const blob = new Blob([lines.join("\n") + (lines.length ? "\n" : "")], { type: "application/jsonl" });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: "filtered_reprocli_records.jsonl" });
  link.click();
  URL.revokeObjectURL(url);
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(Number(value || 0));
}

function formatBytes(value) {
  return value < 1024 ? `${value} B` : value < 1048576 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1048576).toFixed(1)} MB`;
}
