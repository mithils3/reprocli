function parseJsonlText(text, source) {
  return text.split(/\r?\n/).flatMap((line, index) => {
    if (!line.trim()) return [];
    try { return [normalizeEntry(JSON.parse(line), source, index + 1)]; }
    catch (error) { return [parseErrorRecord(line, source, index + 1, error)]; }
  });
}

function parseErrorRecord(rawLine, source, line, error) {
  return baseRecord({
    id: `${source}:${line}`,
    source,
    line,
    status: "parse_error",
    errors: [error.message],
    rawParts: [{ kind: "parse_error", source, line, raw: { raw_line: rawLine, error: error.message } }]
  });
}

function normalizeEntry(raw, source, line) {
  if (Array.isArray(raw?.messages) && raw?.final_response) return traceRecord(raw, source, line);
  if (raw?.method && raw?.body) return requestRecord(raw, source, line);
  if (raw?.signals || raw?.central_claim) return extractedRecord(raw, source, line);
  return responseRecord(raw, source, line);
}

function traceRecord(raw, source, line) {
  const finalBody = raw.final_response?.response?.body || {};
  const extracted = extractJson(finalAssistantText(finalBody));
  return baseRecord({
    raw,
    source,
    line,
    id: idOf(raw, source, line),
    customId: String(raw.custom_id || ""),
    status: raw.final_response?.error ? "error" : "success",
    messages: normalizeMessages(raw.messages || []),
    responseRaw: raw.final_response,
    extracted,
    toolLoop: raw.tool_loop || raw.final_response?.tool_loop || {},
    model: finalBody.model || "",
    usage: finalBody.usage || {},
    rawParts: [{ kind: "trace", source, line, raw }]
  });
}

function requestRecord(raw, source, line) {
  return baseRecord({
    raw,
    source,
    line,
    id: idOf(raw, source, line),
    customId: String(raw.custom_id || ""),
    status: "request",
    requestMessages: normalizeMessages(raw.body.messages || raw.body.input || []),
    requestRaw: raw,
    model: raw.body.model || "",
    rawParts: [{ kind: "request", source, line, raw }]
  });
}

function extractedRecord(raw, source, line) {
  return baseRecord({
    raw,
    source,
    line,
    id: idOf(raw, source, line),
    customId: String(raw.custom_id || ""),
    status: "success",
    title: raw.title || "",
    extracted: raw,
    rawParts: [{ kind: "extracted", source, line, raw }]
  });
}

function responseRecord(raw, source, line) {
  const body = responseBody(raw);
  const extracted = raw.output_text ? extractJson(raw.output_text) : extractJson(finalAssistantText(body));
  const status = raw.error || raw.batch_error || raw.response?.error ? "error" : "success";
  return baseRecord({
    raw,
    source,
    line,
    id: idOf(raw, source, line, body),
    customId: String(raw.custom_id || ""),
    status,
    title: raw.title || "",
    responseRaw: raw,
    outputItems: normalizeOutputItems(body, raw.output_text),
    extracted,
    model: body.model || raw.response?.model || "",
    usage: body.usage || raw.usage || {},
    statusCode: raw.response?.status_code || raw.batch_response?.status_code || "",
    rawParts: [{ kind: "response", source, line, raw }]
  });
}

function baseRecord(record) {
  return {
    id: "",
    customId: "",
    title: "",
    source: "",
    line: "",
    status: "success",
    messages: [],
    requestMessages: [],
    outputItems: [],
    extracted: null,
    requestRaw: null,
    responseRaw: null,
    rawParts: [],
    errors: [],
    model: "",
    usage: {},
    toolLoop: {},
    statusCode: "",
    search: "",
    ...record
  };
}

function mergeRecords(entries) {
  const rows = [], byId = new Map();
  for (const entry of entries) {
    if (!entry.customId) { rows.push(finalizeRecord(entry)); continue; }
    const existing = byId.get(entry.customId);
    if (!existing) { byId.set(entry.customId, entry); rows.push(entry); continue; }
    mergeInto(existing, entry);
  }
  return rows.map(finalizeRecord);
}

function mergeInto(target, entry) {
  for (const key of ["title", "model", "statusCode"]) if (!target[key] && entry[key]) target[key] = entry[key];
  if (entry.status !== "request") target.status = entry.status;
  if (entry.messages.length) target.messages = entry.messages;
  if (entry.requestMessages.length) target.requestMessages = entry.requestMessages;
  if (entry.outputItems.length) target.outputItems = entry.outputItems;
  if (entry.extracted) target.extracted = entry.extracted;
  if (entry.requestRaw) target.requestRaw = entry.requestRaw;
  if (entry.responseRaw) target.responseRaw = entry.responseRaw;
  if (Object.keys(entry.usage || {}).length) target.usage = entry.usage;
  if (Object.keys(entry.toolLoop || {}).length) target.toolLoop = entry.toolLoop;
  target.errors.push(...entry.errors);
  target.rawParts.push(...entry.rawParts);
}

function finalizeRecord(record) {
  const events = conversationEvents(record);
  record.events = events;
  record.toolCount = events.reduce((sum, event) => sum + (event.tools?.length || (event.role === "tool_call" ? 1 : 0)), 0);
  record.reasoningCount = events.filter((event) => event.reasoning || event.role === "reasoning").length;
  record.totalTokens = Number(record.usage?.total_tokens || record.usage?.total || 0);
  record.tier = String(record.extracted?.tier || "");
  record.score = String(record.extracted?.score ?? "");
  record.claim = String(record.extracted?.central_claim || record.extracted?.claim || "");
  record.search = [record.id, record.title, record.model, record.tier, record.claim, eventText(events), JSON.stringify(record.extracted || {})].join(" ").toLowerCase();
  return record;
}

function conversationEvents(record) {
  if (record.messages.length) return eventsFromMessages(record.messages);
  return [...eventsFromMessages(record.requestMessages), ...record.outputItems];
}

function eventsFromMessages(messages) {
  return messages.flatMap((message, index) => {
    const role = String(message.role || `message_${index + 1}`);
    if (role === "tool") return [toolResultEvent(message)];
    return [{
      role,
      content: messageContent(message),
      reasoning: flattenText(message.reasoning),
      tools: (message.tool_calls || []).map(toolCallEvent)
    }];
  });
}

function normalizeOutputItems(body, fallbackText) {
  const output = Array.isArray(body?.output) ? body.output : [];
  if (output.length) return output.map(outputItemEvent).filter(Boolean);
  const choices = body?.choices || [];
  const message = choices[0]?.message;
  if (message) return eventsFromMessages([message]);
  const text = fallbackText || body?.output_text || "";
  return text ? [{ role: "assistant", content: text, tools: [] }] : [];
}

function outputItemEvent(item) {
  if (item.type === "reasoning") return { role: "reasoning", content: reasoningItemText(item), tools: [] };
  if (item.type === "web_search_call") return { role: "tool_call", content: webSearchText(item), name: "web_search", tools: [] };
  if (item.type === "function_call") return { role: "tool_call", name: item.name || "function_call", content: item.arguments || "", tools: [] };
  if (item.type === "function_call_output") return { role: "tool_result", name: item.call_id || "tool_result", content: item.output || "", tools: [] };
  if (item.type === "message") return { role: item.role || "assistant", content: flattenResponsesContent(item.content), tools: [] };
  return { role: item.type || "output", content: JSON.stringify(item, null, 2), tools: [] };
}

function normalizeMessages(messages) {
  return Array.isArray(messages) ? messages.map((message) => ({ ...message })) : [];
}

function toolCallEvent(call) {
  const fn = call.function || {};
  return { id: call.id || "", name: fn.name || call.name || "tool_call", arguments: parseMaybeJson(fn.arguments || call.arguments || "") };
}

function toolResultEvent(message) {
  return { role: "tool_result", name: message.name || message.tool_call_id || "tool", content: message.content || "", tools: [] };
}

function responseBody(raw) {
  if (raw?.response?.body) return raw.response.body;
  if (raw?.batch_response?.body) return raw.batch_response.body;
  if (raw?.response?.output || raw?.response?.choices) return raw.response;
  return raw?.body || raw || {};
}

function idOf(raw, source, line, body = {}) {
  return String(raw.custom_id || raw.id || body.id || `${source}:${line}`);
}

function messageContent(message) {
  return flattenText(message.content ?? message.text ?? "");
}

function flattenResponsesContent(content) {
  return Array.isArray(content) ? content.map((part) => part.text || part.content || "").filter(Boolean).join("\n") : "";
}

function reasoningItemText(item) {
  const summary = Array.isArray(item.summary) ? item.summary.map((part) => part.text || "").filter(Boolean) : [];
  const content = Array.isArray(item.content) ? item.content.map((part) => part.text || "").filter(Boolean) : [];
  return [...summary, ...content].join("\n\n") || item.status || "";
}

function webSearchText(item) {
  const action = item.action || {};
  return action.url || action.query || (action.queries || []).join(" | ") || item.status || "";
}

function finalAssistantText(body) {
  if (body?.output_text) return body.output_text;
  return normalizeOutputItems(body, "").filter((event) => event.role === "assistant").map((event) => event.content).join("\n\n");
}

function flattenText(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(flattenText).filter(Boolean).join("\n");
  if (value && typeof value === "object") return value.text || value.content || JSON.stringify(value, null, 2);
  return "";
}

function parseMaybeJson(value) {
  if (value && typeof value === "object") return value;
  try { return JSON.parse(value || "{}"); } catch { return value || ""; }
}

function extractJson(text) {
  const value = String(text || "");
  const fenced = value.match(/```json\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1] : value.slice(value.indexOf("{"), value.lastIndexOf("}") + 1);
  try { return candidate ? JSON.parse(candidate) : null; } catch { return null; }
}

function eventText(events) {
  return events.map((event) => [event.role, event.name, event.content, event.reasoning, JSON.stringify(event.tools || [])].join(" ")).join(" ");
}
