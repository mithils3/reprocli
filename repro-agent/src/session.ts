import {
  createAgentSession,
  DefaultResourceLoader,
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
  maxRetries?: number;
  timeoutMs?: number;
}

const log = (id: string, msg: string) =>
  console.error(`[${id}] ${new Date().toISOString()} ${msg}`);

export async function runReproSession(
  entry: BenchmarkEntry,
  options: ReproSessionOptions,
): Promise<ReproResult> {
  const provider = options.modelProvider ?? process.env["REPRO_MODEL_PROVIDER"] ?? "openai";
  const modelId = options.modelId ?? process.env["REPRO_MODEL_ID"] ?? "gpt-4o";
  const maxRetries = options.maxRetries ?? 3;
  const timeoutMs = options.timeoutMs ?? 10 * 60 * 1000; // 10 min
  const id = entry.custom_id;

  log(id, `starting session  provider=${provider}  model=${modelId}`);
  const model = getModel(provider as Parameters<typeof getModel>[0], modelId as never);

  const authStorage = AuthStorage.create();
  const modelRegistry = ModelRegistry.create(authStorage);
  const resourceLoader = new DefaultResourceLoader({
    cwd: options.workdir,
    agentDir: options.workdir,
    noExtensions: true,
    noSkills: true,
    noContextFiles: true,
    systemPrompt: SYSTEM_PROMPT,
  });
  const tracker = makePhaseTracker();
  let toolRoundsUsed = 0;
  let bashNudgesSent = 0;
  const pendingArgs = new Map<string, Record<string, unknown>>();

  log(id, "creating agent session...");
  const { session } = await createAgentSession({
    sessionManager: SessionManager.inMemory(),
    authStorage,
    modelRegistry,
    model,
    resourceLoader,
    noTools: "builtin",
    customTools: [...makeSandboxTools(options.workdir), ...webTools],
  });
  log(id, "session created, sending prompt...");

  return new Promise<ReproResult>((resolve, reject) => {
    const timer = setTimeout(() => {
      log(id, "TIMEOUT — no agent_end received within limit");
      resolve({
        custom_id: id,
        reproduction_status: "failed",
        metric_results: [],
        claim_supported: null,
        claim_assessment: "",
        failure_reason: `Timed out after ${timeoutMs / 1000}s`,
        tool_rounds_used: toolRoundsUsed,
      });
    }, timeoutMs);

    session.subscribe((event) => {
      log(id, `event: ${event.type}`);

      if (event.type === "tool_execution_start") {
        log(id, `  → tool_call: ${event.toolName}`);
        pendingArgs.set(event.toolCallId, event.args as Record<string, unknown>);
      }

      if (event.type === "tool_execution_end") {
        toolRoundsUsed++;
        const args = pendingArgs.get(event.toolCallId) ?? {};
        pendingArgs.delete(event.toolCallId);
        log(id, `  ← tool_end: ${event.toolName}  isError=${event.isError}`);
        const steer = recordToolCall(tracker, event.toolName, args);
        if (steer) {
          log(id, `  ↑ steering: ${steer.slice(0, 80)}`);
          void session.followUp(steer);
        }
      }

      if (event.type === "agent_end") {
        if (!hasBashBeenRun(tracker) && bashNudgesSent < maxRetries) {
          bashNudgesSent++;
          const nudge =
            "You have not called bash yet. Proceed to Step 2: " +
            "call bash to clone the repository and install dependencies.";
          log(id, `  bash not run — nudge #${bashNudgesSent}/${maxRetries}`);
          // Re-prompt (not followUp) so the agent actually runs again
          session.prompt(nudge).catch(reject);
          return;
        }

        clearTimeout(timer);
        if (!hasBashBeenRun(tracker)) {
          log(id, "max bash nudges reached — resolving as failed");
          resolve({
            custom_id: id,
            reproduction_status: "failed",
            metric_results: [],
            claim_supported: null,
            claim_assessment: "",
            failure_reason: "Agent never called bash after maximum nudges",
            tool_rounds_used: toolRoundsUsed,
          });
          return;
        }
        log(id, "agent_end — parsing output");
        const result = parseOutput(id, event.messages);
        result.tool_rounds_used = toolRoundsUsed;
        log(id, `  status=${result.reproduction_status}`);
        resolve(result);
      }
    });

    session.prompt(buildPrompt(entry)).catch((err: unknown) => {
      clearTimeout(timer);
      log(id, `prompt() threw: ${String(err)}`);
      resolve({
        custom_id: id,
        reproduction_status: "failed",
        metric_results: [],
        claim_supported: null,
        claim_assessment: "",
        failure_reason: String(err),
        tool_rounds_used: toolRoundsUsed,
      });
    });
  });
}
