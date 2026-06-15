import { exec } from "node:child_process";
import { promisify } from "node:util";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import type { AgentTool } from "@earendil-works/pi-agent-core";
import { Type } from "@earendil-works/pi-ai";

const execAsync = promisify(exec);
const MAX_OUTPUT = 10_000;
const DEFAULT_TIMEOUT_S = 300;

function confined(workdir: string, p: string): string {
  const abs = resolve(workdir, p);
  if (!abs.startsWith(resolve(workdir) + "/") && abs !== resolve(workdir)) {
    throw new Error(`Path escapes workdir: ${p}`);
  }
  return abs;
}

function text(t: string) {
  return [{ type: "text" as const, text: t }];
}

export function makeSandboxTools(workdir: string): AgentTool[] {
  const bash: AgentTool = {
    name: "bash",
    label: "Bash",
    description:
      "Run a shell command in the sandbox working directory. " +
      "Use for git clone, pip install, and running training/eval scripts.",
    parameters: Type.Object({
      command: Type.String({ description: "Shell command to run." }),
      timeout: Type.Optional(
        Type.Integer({ description: "Timeout in seconds (default 300).", default: DEFAULT_TIMEOUT_S })
      ),
    }),
    executionMode: "sequential",
    execute: async (_id, params) => {
      const p = params as { command: string; timeout?: number };
      const timeoutMs = (p.timeout ?? DEFAULT_TIMEOUT_S) * 1000;
      try {
        const { stdout, stderr } = await execAsync(p.command, { cwd: workdir, timeout: timeoutMs });
        const out = (stdout + stderr).slice(0, MAX_OUTPUT);
        return { content: text(out || "(no output)"), details: { workdir } };
      } catch (err: unknown) {
        const e = err as { stdout?: string; stderr?: string; message?: string };
        const msg = ((e.stdout ?? "") + (e.stderr ?? "") + (e.message ?? "")).slice(0, MAX_OUTPUT);
        return { content: text(`Error:\n${msg}`), details: {} };
      }
    },
  };

  const read_file: AgentTool = {
    name: "read_file",
    label: "Read File",
    description: "Read a file from the sandbox working directory by relative path.",
    parameters: Type.Object({
      path: Type.String({ description: "Relative file path." }),
      max_chars: Type.Optional(Type.Integer({ default: MAX_OUTPUT })),
    }),
    execute: async (_id, params) => {
      const p = params as { path: string; max_chars?: number };
      try {
        const abs = confined(workdir, p.path);
        const content = await readFile(abs, "utf-8");
        return { content: text(content.slice(0, p.max_chars ?? MAX_OUTPUT)), details: {} };
      } catch (err: unknown) {
        return { content: text(`Error: ${(err as Error).message}`), details: {} };
      }
    },
  };

  const write_file: AgentTool = {
    name: "write_file",
    label: "Write File",
    description: "Write content to a file in the sandbox working directory.",
    parameters: Type.Object({
      path: Type.String({ description: "Relative file path." }),
      content: Type.String({ description: "Content to write." }),
    }),
    execute: async (_id, params) => {
      const p = params as { path: string; content: string };
      try {
        const abs = confined(workdir, p.path);
        await mkdir(resolve(abs, ".."), { recursive: true });
        await writeFile(abs, p.content, "utf-8");
        return {
          content: text(`Written ${p.content.length} chars to ${p.path}`),
          details: {},
        };
      } catch (err: unknown) {
        return { content: text(`Error: ${(err as Error).message}`), details: {} };
      }
    },
  };

  return [bash, read_file, write_file];
}
