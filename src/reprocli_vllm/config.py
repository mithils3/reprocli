from __future__ import annotations

from pathlib import Path


PAPER_BUNDLE_DATASET = "Mithilss/neurips-2025-paper-bundles"
PAPER_BUNDLE_DATASET_URL = "https://huggingface.co/datasets/Mithilss/neurips-2025-paper-bundles"
DEFAULT_VLLM_DATASET = PAPER_BUNDLE_DATASET
MINIMAX_M2_MODEL = "MiniMaxAI/MiniMax-M2.7"
KIMI_K2_6_MODEL = "moonshotai/Kimi-K2.6"
DEFAULT_MODEL = MINIMAX_M2_MODEL
DEFAULT_OUTPUT = Path("outputs/neurips_2025_minimax_m2_trial.jsonl")
DEFAULT_EXTRACTED_OUTPUT = Path("outputs/neurips_2025_minimax_m2_trial_extracted.jsonl")
PLACEHOLDER = "{PAPER_TEXT}"
MAX_MODEL_LEN = 196608
TOOL_TIMEOUT = 20.0
TOOL_MAX_CHARS = 24_000
TOOL_RESULT_MAX_CHARS = 40_000
BUNDLE_FILE_DEFAULT_CHARS = 60_000
BUNDLE_FILE_MAX_CHARS = 200_000
REQUEST_TIMEOUT = 1800.0
SERVER_STARTUP_TIMEOUT = 1800.0
WEB_SYSTEM_MESSAGE = (
    "You have GitHub MCP, Hugging Face MCP, direct URL fetch, and current-paper "
    "bundle file tools. Use "
    "them to verify MRE-relevant code, data, checkpoint, project-page, GitHub, "
    "and Hugging Face evidence before producing the final JSON. Tool choice is "
    "automatic: choose whichever available tool is most useful from the paper "
    "text and bundled OpenReview supplement evidence. "
    "Treat MRE-relevant code, configs, scripts, notebooks, and READMEs included in the bundled "
    "OpenReview supplement as first-party code evidence for the paper. Use paper_bundle_file_contents "
    "for bundled supplement README/config/script/notebook/dataset-manifest text when the manifest "
    "lists a relevant file. Do not invent local filesystem tools such as read, file_read, bash, or shell. "
    "Do not claim an external artifact is verified "
    "unless a tool result supports that claim. Treat GitHub search as a "
    "GitHub-scoped web search and Hugging Face search as an HF-scoped web "
    "search. GitHub code search supports quoted phrases and OR/NOT syntax, but "
    "keep combined code-search queries within GitHub's 256-character query "
    "limit; otherwise make separate calls. Hugging Face MCP search is semantic "
    "and natural-language oriented, so do not rely on OR as boolean syntax "
    "there; try separate alias queries when needed. If no direct GitHub repo is present, "
    "or a candidate repo is empty, "
    "irrelevant, private, or only promises a future release, search again with "
    "meaningfully different queries before marking code unavailable. Try full "
    "title, title without subtitle, acronym, acronym hyphen/no-hyphen variants, "
    "method name, benchmark name, arXiv ID, author/lab names, and terms such as "
    "code, github, official, dataset, model, checkpoint, weights, benchmark, or "
    "implementation. When a search tool supports rich syntax, combine useful "
    "alternatives in one query, for example an exact phrase plus acronym plus "
    "artifact terms; otherwise make separate calls. Prefer direct github_repo, "
    "github_file_contents, github_repository_tree, huggingface_repo, "
    "huggingface_repository_tree, or fetch_url checks when a candidate URL or "
    "repo id exists. Use huggingface_repo for HF details, README/card evidence, "
    "and a root tree; use huggingface_repository_tree for deeper HF file "
    "structure; use fetch_url for specific HF files once a path is known. For "
    "promising GitHub repos, read README files and key docs, configs, examples, "
    "or scripts with github_file_contents before counting code as available. Do not call the "
    "same tool with identical arguments twice. After reasonable variant "
    "searches and direct checks are exhausted, set the signal value to false "
    "with verification tool_searched_not_found; finding nothing after a real "
    "search is successful verification of absence, not a tool failure. Return "
    "only the requested JSON object."
)
FINAL_NO_TOOLS_MESSAGE = (
    "The tool phase is finished. Write the final JSON now from the paper text "
    "and the tool results above. Fill each signal's verification field with "
    "what actually happened during the tool phase; this message is not a tool "
    "failure. Checklist: clean URLs only in verified_links; search summaries go "
    "in evidence strings, not URL arrays; signals are scoped to the MRE; "
    "h100_estimate.hours matches its arithmetic fields; no score or tier. "
    "Return only the JSON object: the first output character must be { and the "
    "last must be }. No prose, no markdown fences, no tool calls."
)
CONTEXT_BUDGET_NOTE = (
    "The conversation hit its context budget, so the tool phase ended early. "
    "Mark any category you could not finish checking as tool_failed or "
    "paper_text_only instead of guessing. "
)

# --- Verification-target curation mode -------------------------------------
MRE_PLACEHOLDER = "{MRE_RECORD}"
VERIFICATION_PROMPT_FILE = Path("prompt_verification.txt")
VERIFICATION_DEFAULT_OUTPUT = Path("outputs/v5/audit_pool_verification_targets.jsonl")
VERIFICATION_DEFAULT_EXTRACTED = Path("outputs/v5/audit_pool_verification_targets_extracted.jsonl")
VERIFICATION_MRE_RECORDS_DEFAULT = Path("outputs/v5/audit_pool_extracted.jsonl")
VERIFICATION_SYSTEM_MESSAGE = (
    "You are a verification-target curator for an ML reproduction benchmark. "
    "You are given the MRE record the benchmark already chose for one paper: its "
    "central claim, the MRE experiment, the repo and links, the agent task, and "
    "the reported numbers. You have NO tools. From that record alone, produce ONE "
    "flat target.json that a deterministic grader can run with no further model "
    "judgment: it deletes stale_outputs, runs harness_cmd (and baseline_cmd) at "
    "the pinned repo, reads ONLY artifact_path, computes measured = metric_name "
    "over artifact_path[metric_field], and PASSes iff every target satisfies "
    "op(measured, value, tol). Take repo and commands from verified_links, "
    "mre_config, and agent_task; take reference numbers from claim_evidence and "
    "mre_config. If the exact output filename is unknown, force a dump with a "
    "--dump/--output flag in harness_cmd and name that file as artifact_path; "
    "leave commit empty for the curator to pin. Never grade prose or a printed "
    "scalar. If the claim is not deterministically gradeable, set "
    "exclusion_reason and leave the run fields empty. Return only the JSON object."
)
VERIFICATION_FINAL_NO_TOOLS_MESSAGE = (
    "Write the final target.json now from the MRE record above. Checklist: "
    "harness_cmd is the exact command we run and bakes in any injected input; "
    "artifact_path is a file the run creates (never agent stdout); stale_outputs "
    "lists shipped result/metric/pred files to delete first; metric_name + "
    "metric_field name a scoring function and the artifact field it reads; "
    "metric_spec says how measured is computed; each target has value (number, or "
    "null only for is_true), op, and tol; set answer_key only when ground truth "
    "is withheld; if not deterministically gradeable, set exclusion_reason and "
    "leave the run fields empty. Return only the JSON object: the first output "
    "character must be { and the last must be }. No prose, no markdown."
)


def function_tool(
    name: str,
    description: str,
    properties: dict,
    required: list[str],
) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def query_tool(name: str, description: str) -> dict:
    properties = {
        "query": {
            "type": "string",
            "description": (
                "GitHub search query. Use full titles, acronyms, arXiv IDs, "
                "method/benchmark names, and artifact terms; combine aliases "
                "with GitHub search syntax when useful. For code search, keep "
                "combined queries under 256 characters."
            ),
        },
        "max_results": {"type": "integer", "default": 5},
        "sort": {"type": "string", "description": "Optional GitHub sort field."},
        "order": {"type": "string", "enum": ["asc", "desc"]},
    }
    return function_tool(name, description, properties, ["query"])


WEB_TOOLS = [
    function_tool(
        "paper_bundle_file_contents",
        "Read a text file from the current paper's bundled OpenReview supplement by manifest path. Use only paths listed in OPENREVIEW_SUPPLEMENT files; pass either path/to/file or supplement/path/to/file.",
        {
            "path": {
                "type": "string",
                "description": "Supplement manifest path, for example README.md or supplement/code/train.py.",
            },
            "max_chars": {
                "type": "integer",
                "default": BUNDLE_FILE_DEFAULT_CHARS,
                "minimum": 1,
                "maximum": BUNDLE_FILE_MAX_CHARS,
            },
        },
        ["path"],
    ),
    query_tool(
        "github_search_repositories",
        "Search GitHub repositories through MCP like a GitHub-scoped web search.",
    ),
    query_tool(
        "github_search_code",
        "Search GitHub code through MCP. Supports GitHub code-search syntax such as quoted phrases, OR, NOT, and qualifiers; keep query under 256 characters.",
    ),
    function_tool(
        "github_repo",
        "Inspect a GitHub repo through MCP for root files, README candidates, latest release, and tree; read key files with github_file_contents before final verification.",
        {"repo": {"type": "string", "description": "GitHub URL or owner/repo."}},
        ["repo"],
    ),
    function_tool(
        "github_file_contents",
        "Read a GitHub file or directory through MCP. Use for README.md, docs, configs, examples, scripts, and training/eval files; long results are truncated, so request specific paths.",
        {
            "repo": {"type": "string", "description": "GitHub URL or owner/repo."},
            "path": {"type": "string", "description": "File or directory path."},
            "ref": {"type": "string", "description": "Optional branch, tag, or ref."},
        },
        ["repo", "path"],
    ),
    function_tool(
        "github_repository_tree",
        "Read a GitHub repository tree through MCP. Prefer path_filter over recursive listings; large trees are truncated.",
        {
            "repo": {"type": "string", "description": "GitHub URL or owner/repo."},
            "path_filter": {"type": "string", "description": "Optional path prefix."},
            "recursive": {"type": "boolean", "default": False},
        },
        ["repo"],
    ),
    function_tool(
        "huggingface_search",
        "Search Hugging Face MCP repositories, papers, Spaces, docs, or Hub query using semantic or natural-language aliases; use separate calls for OR-like variants.",
        {
            "query": {
                "type": "string",
                "description": (
                    "Hugging Face search query. Try title, acronym variants, "
                    "arXiv ID, method name, benchmark name, and artifact terms. "
                    "Do not assume boolean OR semantics."
                ),
            },
            "search_type": {
                "type": "string",
                "enum": ["repositories", "papers", "spaces", "docs", "hub"],
                "default": "repositories",
            },
            "max_results": {"type": "integer", "default": 5},
        },
        ["query"],
    ),
    function_tool(
        "huggingface_repo",
        "Get Hugging Face repository details, README/card evidence, and a compact root tree through MCP and Hub APIs.",
        {
            "repo": {"type": "string", "description": "HF URL or namespace/repo id."},
            "repo_type": {
                "type": "string",
                "enum": ["model", "dataset", "space", "auto"],
                "default": "auto",
            },
        },
        ["repo"],
    ),
    function_tool(
        "huggingface_repository_tree",
        "List Hugging Face repository files or folders through the Hub API. Use this for deeper HF file structure after huggingface_repo finds a candidate.",
        {
            "repo": {"type": "string", "description": "HF URL or namespace/repo id."},
            "repo_type": {
                "type": "string",
                "enum": ["model", "dataset", "space", "auto"],
                "default": "auto",
            },
            "path": {"type": "string", "description": "Optional path inside the repository."},
            "revision": {"type": "string", "description": "Optional branch, tag, or commit."},
            "recursive": {"type": "boolean", "default": False},
            "max_entries": {"type": "integer", "default": 80},
        },
        ["repo"],
    ),
    function_tool(
        "fetch_url",
        "Fetch a direct public URL and return status, final URL, and text.",
        {
            "url": {"type": "string", "description": "HTTP or HTTPS URL."},
            "max_chars": {"type": "integer", "default": TOOL_MAX_CHARS},
        },
        ["url"],
    ),
]
