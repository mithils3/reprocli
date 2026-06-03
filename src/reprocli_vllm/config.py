from __future__ import annotations

from pathlib import Path


DEFAULT_DATASET = "Mithilss/neurips-2025-arxiv-latex-sources"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
DEFAULT_OUTPUT = Path("outputs/neurips_2025_deepseek_v4_flash.jsonl")
DEFAULT_EXTRACTED_OUTPUT = Path("outputs/neurips_2025_deepseek_v4_flash_extracted.jsonl")
DEFAULT_REQUESTS_OUTPUT = Path("outputs/neurips_2025_deepseek_v4_flash_requests.jsonl")
PLACEHOLDER = "{PAPER_TEXT}"
TEX_EXTENSION = ".tex"
MAX_MODEL_LEN = 196608
TOOL_TIMEOUT = 20.0
TOOL_MAX_CHARS = 8000
REQUEST_TIMEOUT = 1800.0
SERVER_STARTUP_TIMEOUT = 1800.0
WEB_SYSTEM_MESSAGE = (
    "You have web verification tools. Before producing the final JSON, use the "
    "tools to verify artifact links relevant to the MRE. Do not claim that code, "
    "data, weights, GitHub repositories, Hugging Face repositories, or project "
    "pages are verified unless a tool result supports that claim. If tools fail "
    "or cannot verify a link, mark the artifact unavailable or unverified as "
    "instructed by the user prompt. Prefer direct github_repo, huggingface_repo, "
    "or fetch_url checks when the paper or prior results contain a candidate URL "
    "or repo id. Use web_search only when no direct candidate exists. Do not call "
    "the same tool with the same arguments twice. If a likely artifact cannot be "
    "verified after direct checks, stop searching and mark it unavailable or "
    "unverified. After using tools, return only the requested JSON object."
)
FINAL_NO_TOOLS_MESSAGE = (
    "Tool use is complete and no tools are available in this request. Use only "
    "the paper text and prior tool results already in the conversation. Think "
    "through the private consistency checklist before answering: clean URLs only "
    "in verified_links, web_verification is available/partial/unavailable, score "
    "matches the formula, tier matches score, and h100_hours_estimate matches its "
    "basis. Return only the requested JSON object. The first output character "
    "must be { and the last output character must be }. Do not write search "
    "plans, tool calls, markdown fences, or prose outside the JSON."
)
WEB_TOOLS = [
    {
        "type": "function",
            "function": {
            "name": "web_search",
            "description": (
                "Extract direct artifact URLs, arXiv IDs, and obvious GitHub owner/repo "
                "candidates from a query. This is a lightweight discovery helper; "
                "verify candidates with github_repo, huggingface_repo, or fetch_url."
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
