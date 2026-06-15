export interface VerificationTarget {
  metric: string;
  expected_value: number;
  source: string;
  conditions: string;
}

export interface SignalEntry {
  value: boolean;
  evidence: string;
}

export interface BenchmarkEntry {
  custom_id: string;
  central_claim: string;
  claim_evidence: string;
  mre_config: string;
  web_verification: string;
  verified_links: {
    paper_or_project?: string[];
    code?: string[];
    dataset?: string[];
    weights?: string[];
  };
  signals: {
    code_available: SignalEntry;
    dataset_available: SignalEntry;
    weights_available: SignalEntry;
    dataset_is_standard: SignalEntry;
  };
  verification_targets: VerificationTarget[];
  agent_task: string;
  h100_hours_estimate: number;
  h100_estimate_basis: string;
  score?: number;
  tier?: string;
}

export const SYSTEM_PROMPT = `You are a reproduction agent for an ML-paper benchmark.

You are given a benchmark entry with a Minimal Reproduction Example (MRE) to run.
Follow the agent_task steps in order:

  Step 1 — Browse: use github_browse, hf_browse, or fetch_url to read the repository
             README, key source files, and any setup instructions.
  Step 2 — Setup: use bash to clone the repo and install dependencies.
  Step 3 — Run: use bash to execute the experiment as specified in mre_config.
  Step 4 — Report: print a single JSON object (no prose) with these keys:
             reproduction_status: "success" | "partial" | "failed"
             metric_results: [{ metric: <name>, actual_value: <number|null> }]
             claim_supported: true | false | null
             claim_assessment: <one paragraph — assess the overall pattern of results
               against the central_claim, not each number in isolation>
             failure_reason: <if failed, why>

The metric names in metric_results must match verification_targets[].metric exactly.
Do not skip steps. Do not fabricate results — only report values you observed from
actual command output.`;

export function buildPrompt(entry: BenchmarkEntry): string {
  const availability = [
    `code_available: ${entry.signals.code_available.value} — ${entry.signals.code_available.evidence}`,
    `dataset_available: ${entry.signals.dataset_available.value} — ${entry.signals.dataset_available.evidence}`,
    `weights_available: ${entry.signals.weights_available.value} — ${entry.signals.weights_available.evidence}`,
    `dataset_is_standard: ${entry.signals.dataset_is_standard.value} — ${entry.signals.dataset_is_standard.evidence}`,
  ].join("\n");

  const parts: string[] = [
    `# Paper: ${entry.custom_id}`,
    `## Central Claim\n${entry.central_claim}`,
    `## Claim Evidence\n${entry.claim_evidence}`,
    `## Artifact Availability\n${availability}`,
    `## Web Verification Notes\n${entry.web_verification}`,
    `## Verified Links\n${JSON.stringify(entry.verified_links, null, 2)}`,
    `## MRE Configuration\n${entry.mre_config}`,
    `## Estimated Compute\n${entry.h100_hours_estimate} H100-hours — ${entry.h100_estimate_basis}`,
    `## Verification Targets\n${JSON.stringify(entry.verification_targets, null, 2)}`,
    `## Agent Task\n${entry.agent_task}`,
  ];

  if (entry.score !== undefined || entry.tier !== undefined) {
    parts.push(`## Difficulty\nscore: ${entry.score ?? "n/a"}, tier: ${entry.tier ?? "n/a"}`);
  }

  return parts.join("\n\n");
}
