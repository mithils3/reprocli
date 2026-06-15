import {
  createAgentSession,
  SessionManager,
  AuthStorage,
  ModelRegistry,
} from "@earendil-works/pi-coding-agent";
import { getModel } from "@earendil-works/pi-ai";
import { SYSTEM_PROMPT, buildPrompt, type BenchmarkEntry } from "./prompt.js";
import { makeSandboxTools } from "./tools/sandbox.js";
import { webTools } from "./tools/web.js";
import { makePhaseTracker, recordToolCall, hasBashBeenRun } from "./phases.js";
import { parseOutput, type ReproResult } from "./output.js";

export interface ReproSessionOptions {
  workdir: string;
  modelProvider?: string;
  modelId?: string;
}

export async function runReproSession(
  entry: BenchmarkEntry,
  options: ReproSessionOptions,
): Promise<ReproResult> {
  const provider = options.modelProvider ?? process.env["REPRO_MODEL_PROVIDER"] ?? "openai";
  const modelId = options.modelId ?? process.env["REPRO_MODEL_ID"] ?? "gpt-4o";
  const model = getModel(provider as Parameters<typeof getModel>[0], modelId as never);

  const authStorage = AuthStorage.create();
  const modelRegistry = ModelRegistry.create(authStorage);
  const tracker = makePhaseTracker();
  let toolRoundsUsed = 0;

  const { session } = await createAgentSession({
    sessionManager: SessionManager.inMemory(),
    authStorage,
    modelRegistry,
    model,
    systemPrompt: SYSTEM_PROMPT,
    tools: [],
    customTools: [...makeSandboxTools(options.workdir), ...webTools],
    afterToolCall: async (ctx) => {
      toolRoundsUsed++;
      const toolName = (ctx as unknown as { toolName: string }).toolName ?? "";
      const params = (ctx as unknown as { params: Record<string, unknown> }).params ?? {};
      const steer = recordToolCall(tracker, toolName, params);
      if (steer) {
        session.followUp(steer);
      }
      return undefined;
    },
  });

  return new Promise<ReproResult>((resolve) => {
    session.subscribe((event) => {
      if (event.type === "agent_end") {
        if (!hasBashBeenRun(tracker)) {
          session.followUp(
            "You have not called bash yet. Proceed to Step 2: clone the repository and install dependencies.",
          );
          return;
        }
        const result = parseOutput(entry.custom_id, session.messages as unknown[]);
        result.tool_rounds_used = toolRoundsUsed;
        resolve(result);
      }
    });

    session.prompt(buildPrompt(entry)).catch((err: unknown) => {
      resolve({
        custom_id: entry.custom_id,
        reproduction_status: "failed",
        metric_results: [],
        claim_supported: null,
        claim_assessment: "",
        failure_reason: String(err),
      });
    });
  });
}
