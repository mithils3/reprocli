from __future__ import annotations

import argparse
from typing import Any

from .batch_io import parse_json_content
from .openai_batch import RESPONSES_ENDPOINT, batch_response_body, responses_output_text
from .output_schema import FINAL_RESPONSE_FORMAT
from .papers import Paper

DEFAULT_MODEL = "gpt-5.5"
OPENAI_SYSTEM_MESSAGE = (
    "You have access to OpenAI hosted web_search. Use it when it helps verify "
    "artifact links relevant to the MRE, and rely on the paper text when search "
    "is unnecessary. Do not claim that code, data, weights, GitHub repositories, "
    "Hugging Face repositories, or project pages are verified unless web "
    "evidence supports that claim. If you cannot verify a likely artifact, mark "
    "it unavailable or unverified as instructed by the user prompt. Return only "
    "the requested JSON object."
)


def batch_request(args: argparse.Namespace, paper: Paper, prompt_template: str) -> dict[str, Any]:
    prompt = prompt_template.replace("{{PAPER_TEXT}}", paper_text(paper, args.max_paper_chars))
    body: dict[str, Any] = {
        "model": args.model,
        "input": [
            {"role": "system", "content": OPENAI_SYSTEM_MESSAGE},
            {"role": "user", "content": openai_prompt(prompt)},
        ],
        "tools": openai_tools(include_web_search=not args.disable_openai_web_search),
        "tool_choice": "auto",
        "text": response_text_format(),
        "max_output_tokens": args.max_output_tokens,
        "reasoning": {"effort": args.reasoning_effort},
        "store": args.store,
    }
    return {
        "custom_id": paper.arxiv_id,
        "method": "POST",
        "url": RESPONSES_ENDPOINT,
        "body": body,
    }


def final_rows(papers: list[Paper], batch_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    papers_by_id = {paper.arxiv_id: paper for paper in papers}
    rows = []
    for batch_row in batch_rows:
        custom_id = batch_row.get("custom_id") or ""
        paper = papers_by_id.get(custom_id, Paper(arxiv_id=custom_id))
        body = batch_response_body(batch_row)
        rows.append(
            {
                "custom_id": custom_id,
                "title": paper.title,
                "output_text": responses_output_text(body),
                "response": body,
                "batch_response": batch_row.get("response"),
                "batch_error": batch_row.get("error"),
            }
        )
    return sort_rows_by_papers(rows, papers)


def extracted_row(row: dict[str, Any]) -> dict[str, Any]:
    result = {"custom_id": row["custom_id"], "title": row.get("title", "")}
    parsed = parse_json_content(row.get("output_text") or "")
    if isinstance(parsed, dict):
        result.update(parsed)
    else:
        result["extracted_json"] = parsed
        result["raw_content"] = row.get("output_text") or ""
    return result


def sort_rows_by_papers(rows: list[dict[str, Any]], papers: list[Paper]) -> list[dict[str, Any]]:
    order = {paper.arxiv_id: index for index, paper in enumerate(papers)}
    return sorted(rows, key=lambda row: order.get(row.get("custom_id"), len(order)))


def openai_tools(*, include_web_search: bool) -> list[dict[str, Any]]:
    return [{"type": "web_search"}] if include_web_search else []


def response_text_format() -> dict[str, Any]:
    json_schema = FINAL_RESPONSE_FORMAT["json_schema"]
    return {
        "format": {
            "type": "json_schema",
            "name": json_schema["name"],
            "schema": json_schema["schema"],
            "strict": True,
        }
    }


def paper_text(paper: Paper, max_chars: int) -> str:
    text = paper.text()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED FOR OPENAI API BASELINE]\n"


def openai_prompt(prompt: str) -> str:
    replacements = {
        "You must use GitHub, Hugging Face, URL fetch, or available retrieval tools to verify artifact availability.": (
            "Use OpenAI hosted web_search when external evidence is needed to verify artifact availability."
        ),
        "Your first tool call must be GitHub search for likely code repositories. Use whatever query seems most useful from the paper title, acronym, project name, authors, arXiv ID, and artifact terms.": (
            "When searching is useful, look for likely paper/project pages, code repositories, datasets, checkpoints, weights, and Hugging Face pages using queries informed by the paper title, acronym, project name, authors, arXiv ID, and artifact terms."
        ),
        "   The GitHub repository tool includes root README text when available; use it as direct evidence about install, training, evaluation, checkpoint, and release status.\n": "",
        "If the first repository you inspect is missing MRE-relevant code, is only a benchmark/evaluation helper, is a stub, or says code will be released later, search for another official code source before marking code unavailable.\n\n": (
            "If a repository or project page you find is missing MRE-relevant code, is only a benchmark/evaluation helper, is a stub, or says code will be released later, look for another official code source before marking code unavailable when another source is plausible.\n\n"
        ),
        "If the GitHub API cannot parse, fetch, or verify a candidate repository, use GitHub search again with a better query before marking code unavailable.\n\n": "",
        "Always verify promising GitHub search results with the GitHub repository tool before counting code as available.\n\n": (
            "Count repository, dataset, checkpoint, and project-page results as available only when the paper text or web evidence supports that conclusion.\n\n"
        ),
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)
    return prompt
