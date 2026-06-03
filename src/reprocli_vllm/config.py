from __future__ import annotations

from pathlib import Path


DEFAULT_DATASET = "Mithilss/neurips-2025-arxiv-latex-sources"
DEFAULT_MODEL = "MiniMaxAI/MiniMax-M2.7"
DEFAULT_OUTPUT = Path("outputs/neurips_2025_minimax_m27.jsonl")
DEFAULT_REQUESTS_OUTPUT = Path("outputs/neurips_2025_minimax_m27_requests.jsonl")
PLACEHOLDER = "{PAPER_TEXT}"
TEX_EXTENSION = ".tex"
MINIMAX_PARSER = "minimax_m2"
COMPILATION_CONFIG = {
    "mode": 3,
    "pass_config": {"fuse_minimax_qk_norm": True},
}
NO_COMPILE_CONFIG = {"mode": 0}
WEB_SYSTEM_MESSAGE = (
    "You have web verification tools. Before producing the final JSON, use the "
    "tools to verify artifact links relevant to the MRE. Do not claim that code, "
    "data, weights, GitHub repositories, Hugging Face repositories, or project "
    "pages are verified unless a tool result supports that claim. If tools fail "
    "or cannot verify a link, mark the artifact unavailable or unverified as "
    "instructed by the user prompt. After using tools, return only the requested "
    "JSON object."
)
FINAL_NO_TOOLS_MESSAGE = (
    "Tool use is complete and no tools are available in this request. Use only "
    "the paper text and prior tool results already in the conversation. Return "
    "only the requested JSON object; do not write search plans, tool calls, or "
    "prose outside the JSON."
)
WEB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search DuckDuckGo HTML for public pages about a paper, repository, "
                "dataset, checkpoint, or project."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query with exact project/repo/dataset names.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum search results to return.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a public URL and return status, final URL, and text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP or HTTPS URL."},
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters of page text to return.",
                        "default": 6000,
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_repo",
            "description": "Inspect a GitHub repo for metadata, root files, and releases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub URL or owner/repo.",
                    }
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "huggingface_repo",
            "description": "Inspect a Hugging Face model, dataset, or space.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "HF URL or repo id."},
                    "repo_type": {
                        "type": "string",
                        "enum": ["model", "dataset", "space", "auto"],
                        "default": "auto",
                    },
                },
                "required": ["repo"],
            },
        },
    },
]
