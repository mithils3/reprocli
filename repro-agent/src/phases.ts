export type Phase = "browse" | "setup" | "run" | "done";

export interface PhaseTracker {
  current: Phase;
  bashCommands: string[];
  browseCount: number;
}

export function makePhaseTracker(): PhaseTracker {
  return { current: "browse", bashCommands: [], browseCount: 0 };
}

const SETUP_PATTERNS = /git\s+clone|pip\s+install|conda\s+install|npm\s+install|apt|wget|curl.*-[oO]/;
const RUN_PATTERNS = /python\s|pytest\s|bash\s|sh\s|\.\/|train|eval|inference/;

export function recordToolCall(
  tracker: PhaseTracker,
  toolName: string,
  params: Record<string, unknown>,
): string | null {
  if (toolName === "bash") {
    const cmd = String(params["command"] ?? "");
    tracker.bashCommands.push(cmd);

    if (tracker.current === "browse" && SETUP_PATTERNS.test(cmd)) {
      tracker.current = "setup";
    } else if (tracker.current === "setup" && RUN_PATTERNS.test(cmd)) {
      tracker.current = "run";
    } else if (tracker.current === "run") {
      tracker.current = "done";
      return (
        "The experiment command has run. Now emit the final JSON result. " +
        "Extract metric values from the command output above. " +
        "Your entire response must be a single JSON object — no prose."
      );
    }
  }

  if (["fetch_url", "github_browse", "hf_browse"].includes(toolName)) {
    tracker.browseCount++;
    if (tracker.current === "browse" && tracker.browseCount >= 3) {
      return (
        "You have browsed enough. Proceed to Step 2: " +
        "call bash to clone the repository and install dependencies."
      );
    }
  }

  return null;
}

export function hasBashBeenRun(tracker: PhaseTracker): boolean {
  return tracker.bashCommands.length > 0;
}
