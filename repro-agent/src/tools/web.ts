import type { AgentTool } from "@earendil-works/pi-agent-core";
import { Type } from "@earendil-works/pi-ai";

const MAX_CHARS = 50_000;

function text(t: string) {
  return [{ type: "text" as const, text: t }];
}

function githubHeaders(): Record<string, string> {
  const h: Record<string, string> = { Accept: "application/vnd.github+json" };
  const token = process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN;
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

function parseGitHubRepo(value: string): [string, string] | null {
  const url = value.match(/github\.com\/([^/]+)\/([^/\s]+)/);
  if (url) return [url[1], url[2].replace(/\.git$/, "")];
  const parts = value.trim().split("/").filter(Boolean);
  return parts.length >= 2 ? [parts[0], parts[1]] : null;
}

function parseHFRepo(value: string): string {
  const url = value.match(/huggingface\.co\/([^/\s]+\/[^/\s]+)/);
  return url ? url[1] : value.trim();
}

export const fetchUrlTool: AgentTool = {
  name: "fetch_url",
  label: "Fetch URL",
  description: "Fetch a public HTTP/HTTPS URL and return its text content.",
  parameters: Type.Object({
    url: Type.String({ description: "HTTP or HTTPS URL to fetch." }),
    max_chars: Type.Optional(Type.Integer({ default: MAX_CHARS })),
  }),
  execute: async (_id, params) => {
    const p = params as { url: string; max_chars?: number };
    try {
      const res = await fetch(p.url);
      const body = await res.text();
      const limit = p.max_chars ?? MAX_CHARS;
      return {
        content: text(`status: ${res.status}\n${body.slice(0, limit)}`),
        details: { url: p.url, status: res.status },
      };
    } catch (err: unknown) {
      return { content: text(`Error: ${(err as Error).message}`), details: {} };
    }
  },
};

export const githubBrowseTool: AgentTool = {
  name: "github_browse",
  label: "GitHub Browse",
  description:
    "Browse a GitHub repository. Returns the README by default, or a specific file if path is given.",
  parameters: Type.Object({
    repo: Type.String({ description: "GitHub repo as owner/repo or full URL." }),
    path: Type.Optional(Type.String({ description: "File path within the repo (omit for README)." })),
    ref: Type.Optional(Type.String({ description: "Branch, tag, or commit SHA." })),
  }),
  execute: async (_id, params) => {
    const p = params as { repo: string; path?: string; ref?: string };
    const repo = parseGitHubRepo(p.repo);
    if (!repo) return { content: text("Could not parse repo"), details: {} };
    const [owner, name] = repo;
    const headers = githubHeaders();
    const refQ = p.ref ? `?ref=${p.ref}` : "";
    const url = p.path
      ? `https://api.github.com/repos/${owner}/${name}/contents/${p.path}${refQ}`
      : `https://api.github.com/repos/${owner}/${name}/readme`;
    try {
      const res = await fetch(url, { headers });
      const json = (await res.json()) as Record<string, unknown>;
      const decoded =
        typeof json["content"] === "string"
          ? Buffer.from(json["content"] as string, "base64").toString("utf-8")
          : JSON.stringify(json, null, 2);
      return {
        content: text(decoded.slice(0, MAX_CHARS)),
        details: { repo: `${owner}/${name}`, path: p.path ?? "README" },
      };
    } catch (err: unknown) {
      return { content: text(`Error: ${(err as Error).message}`), details: {} };
    }
  },
};

export const hfBrowseTool: AgentTool = {
  name: "hf_browse",
  label: "HuggingFace Browse",
  description: "Browse a HuggingFace model or dataset: returns card metadata and file listing.",
  parameters: Type.Object({
    repo: Type.String({ description: "HF repo as namespace/name or full URL." }),
    repo_type: Type.Optional(
      Type.Union([Type.Literal("model"), Type.Literal("dataset")], { default: "model" })
    ),
  }),
  execute: async (_id, params) => {
    const p = params as { repo: string; repo_type?: string };
    const repoId = parseHFRepo(p.repo);
    const repoType = p.repo_type ?? "model";
    const prefix = repoType === "dataset" ? "datasets/" : "";
    try {
      const res = await fetch(`https://huggingface.co/api/${prefix}${repoId}`);
      const json = (await res.json()) as Record<string, unknown>;
      const files = ((json["siblings"] as Array<{ rfilename: string }>) ?? [])
        .slice(0, 40)
        .map((f) => f.rfilename)
        .join("\n");
      const card = json["cardData"] ? JSON.stringify(json["cardData"], null, 2) : "";
      return {
        content: text(`repo: ${repoId}\ntype: ${repoType}\n\nfiles:\n${files}\n\ncard:\n${card}`.slice(0, MAX_CHARS)),
        details: { repoId, repoType },
      };
    } catch (err: unknown) {
      return { content: text(`Error: ${(err as Error).message}`), details: {} };
    }
  },
};

export const webTools: AgentTool[] = [fetchUrlTool, githubBrowseTool, hfBrowseTool];
