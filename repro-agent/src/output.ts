export interface MetricResult {
  metric: string;
  actual_value: number | null;
}

export interface ReproResult {
  custom_id: string;
  reproduction_status: "success" | "partial" | "failed";
  metric_results: MetricResult[];
  claim_supported: boolean | null;
  claim_assessment: string;
  failure_reason?: string;
  tool_rounds_used?: number;
}

export function parseOutput(customId: string, messages: unknown[]): ReproResult {
  const base: ReproResult = {
    custom_id: customId,
    reproduction_status: "failed",
    metric_results: [],
    claim_supported: null,
    claim_assessment: "",
  };

  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i] as Record<string, unknown>;
    if (msg["role"] !== "assistant") continue;
    const text = extractText(msg);
    if (!text) continue;
    const parsed = tryParseJson(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return { ...base, ...(parsed as Partial<ReproResult>), custom_id: customId };
    }
  }
  return base;
}

function extractText(msg: Record<string, unknown>): string {
  const content = msg["content"];
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((b): b is { type: string; text: string } => typeof b === "object" && b !== null && "type" in b)
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("");
  }
  return "";
}

function tryParseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    // ignore
  }
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start !== -1 && end > start) {
    try {
      return JSON.parse(text.slice(start, end + 1));
    } catch {
      // ignore
    }
  }
  return null;
}
