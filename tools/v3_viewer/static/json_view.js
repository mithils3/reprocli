function renderExtractedJson(payload) {
  if (!payload || typeof payload !== "object") return jsonEmpty("No extracted JSON payload.");
  const keys = Object.keys(payload);
  return `
    <div class="json-toolbar">
      <span>${jsonEscape(keys.length)} top-level fields</span>
      <span>${jsonEscape(JSON.stringify(payload).length)} chars</span>
    </div>
    <div class="json-tree">${renderJsonObject(payload, "root", true)}</div>
    <details class="json-raw"><summary>Raw extracted JSON</summary><pre>${jsonEscape(JSON.stringify(payload, null, 2))}</pre></details>
  `;
}

function renderJsonValue(value, key, root) {
  if (Array.isArray(value)) return renderJsonArray(value, key);
  if (value && typeof value === "object") return renderJsonObject(value, key, root);
  return renderJsonScalar(value, key);
}

function renderJsonObject(value, key, root) {
  const entries = Object.entries(value);
  const body = entries.map(([childKey, childValue]) => renderJsonValue(childValue, childKey, false)).join("");
  if (root) return `<div class="json-object root">${body || jsonEmpty("Empty object")}</div>`;
  return `
    <details class="json-node object" open>
      <summary>${jsonKey(key)}<span class="json-type">object · ${entries.length}</span></summary>
      <div class="json-children">${body || jsonEmpty("Empty object")}</div>
    </details>
  `;
}

function renderJsonArray(value, key) {
  const body = value.map((item, index) => renderJsonValue(item, String(index), false)).join("");
  return `
    <details class="json-node array" open>
      <summary>${jsonKey(key)}<span class="json-type">array · ${value.length}</span></summary>
      <div class="json-children">${body || jsonEmpty("Empty array")}</div>
    </details>
  `;
}

function renderJsonScalar(value, key) {
  const type = value === null ? "null" : typeof value;
  const rendered = type === "string" ? renderJsonString(value) : `<code>${jsonEscape(String(value))}</code>`;
  return `
    <div class="json-row ${jsonClass(type)}">
      ${jsonKey(key)}
      <div class="json-value">
        <span class="json-type">${jsonEscape(type)}</span>
        ${rendered}
      </div>
    </div>
  `;
}

function renderJsonString(value) {
  const text = String(value);
  if (!text) return `<span class="json-empty-string">empty string</span>`;
  return `<div class="json-string">${jsonEscape(text)}</div>`;
}

function jsonKey(key) {
  return `<span class="json-key">${jsonEscape(key)}</span>`;
}

function jsonClass(type) {
  return String(type).replace(/[^a-z0-9]+/gi, "-").toLowerCase();
}

function jsonEmpty(text) {
  return `<p class="empty-note">${jsonEscape(text)}</p>`;
}

function jsonEscape(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}
