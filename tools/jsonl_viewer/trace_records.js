function normalizeTraceRecord(raw, source, line) {
  const final = raw.final_response || {};
  const body = final?.response?.body || {};
  const choice = (body?.choices || [])[0] || {};
  const message = choice.message || {};
  const content = message.content || body?.output_text || "";
  const extracted = raw?.signals || raw?.central_claim ? raw : extractJson(content);
  const id = String(raw.custom_id || body.id || `${source}:${line}`);
  return baseRecord({
    raw, source, line, id, customId: String(raw.custom_id || ""), status: "success",
    statusCode: final?.response?.status_code || "", model: body.model || "",
    finish: choice.finish_reason || "", content, extracted,
    reasoning: message.reasoning || choice.reasoning || "",
    inputMessages: normalizeMessages(raw.messages || []),
    outputMessages: normalizeMessages(message.role || message.content ? [message] : []),
    requestRaw: raw, responseRaw: final, rawParts: [{ raw }],
    totalTokens: Number(body?.usage?.total_tokens || 0),
    tier: String(extracted?.tier || ""), score: String(extracted?.score ?? ""),
    claim: String(extracted?.central_claim || extracted?.claim || "")
  });
}

function messageContent(msg) {
  const content = flatten(msg?.content ?? msg?.text ?? "");
  const parts = [];
  if (content) parts.push(content);
  if (msg?.tool_calls) parts.push(`tool_calls:\n${JSON.stringify(msg.tool_calls, null, 2)}`);
  if (msg?.reasoning) parts.push(`reasoning:\n${flatten(msg.reasoning)}`);
  return parts.join("\n\n");
}
