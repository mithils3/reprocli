import { createReadStream } from "node:fs";
import { appendFile, mkdir } from "node:fs/promises";
import { createInterface } from "node:readline";
import { resolve, join } from "node:path";
import { tmpdir } from "node:os";
import { type BenchmarkEntry } from "./prompt.js";
import { runReproSession } from "./session.js";
import { type ReproResult } from "./output.js";

async function main(): Promise<void> {
  const args = parseArgs();
  await mkdir(resolve(args.outputPath, ".."), { recursive: true });

  const entries = await loadEntries(args.benchmarkPath, args.paperId);
  if (entries.length === 0) {
    throw new Error(
      args.paperId
        ? `No entry found for --paper-id=${args.paperId}`
        : "Benchmark file is empty",
    );
  }
  console.error(`Running reproduction agent on ${entries.length} entry(ies)`);

  for (const entry of entries) {
    const safeId = entry.custom_id.replace(/\//g, "_");
    const workdir = join(args.workdirBase, safeId);
    await mkdir(workdir, { recursive: true });
    console.error(`[${entry.custom_id}] workdir=${workdir}`);

    let result: ReproResult;
    try {
      result = await runReproSession(entry, {
        workdir,
        modelProvider: args.modelProvider,
        modelId: args.modelId,
      });
    } catch (err) {
      result = {
        custom_id: entry.custom_id,
        reproduction_status: "failed",
        metric_results: [],
        claim_supported: null,
        claim_assessment: "",
        failure_reason: String(err),
      };
    }

    await appendFile(args.outputPath, JSON.stringify(result) + "\n", "utf-8");
    console.error(`[${entry.custom_id}] status=${result.reproduction_status}`);
  }
}

async function loadEntries(path: string, paperId?: string): Promise<BenchmarkEntry[]> {
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  const entries: BenchmarkEntry[] = [];
  for await (const line of rl) {
    if (line.trim()) entries.push(JSON.parse(line) as BenchmarkEntry);
  }
  return paperId ? entries.filter((e) => e.custom_id === paperId) : entries;
}

function parseArgs() {
  const argv = process.argv.slice(2);
  const get = (flag: string, fallback?: string): string | undefined => {
    const i = argv.indexOf(flag);
    return i !== -1 ? argv[i + 1] : fallback;
  };
  const benchmarkPath = get("--benchmark");
  if (!benchmarkPath) throw new Error("--benchmark <path> is required");
  const outputPath = get("--output", "outputs/reproduction_results.jsonl")!;
  return {
    benchmarkPath,
    outputPath,
    paperId: get("--paper-id"),
    workdirBase: get("--workdir", join(tmpdir(), "repro-agent"))!,
    modelProvider: get("--model-provider"),
    modelId: get("--model-id"),
  };
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
