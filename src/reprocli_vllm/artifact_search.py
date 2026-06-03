from __future__ import annotations

import re
import urllib.parse
from typing import Any

ARXIV_ID_RE = re.compile(r"\b\d{4}\.\d{4,5}(?:v\d+)?\b")
URL_RE = re.compile(r"https?://[^\s)'\"<>]+")


def search_artifacts(query: str, max_results: int) -> dict[str, Any]:
    direct_results = direct_url_results(query)
    results = [
        *direct_results,
        *arxiv_id_results(query),
        *github_candidate_results(query, direct_results),
    ]
    results = dedupe_results(results)[:max_results]
    return {
        "ok": bool(results),
        "provider": "direct_artifact_search",
        "query": query,
        "results": results,
        "hint": "Verify candidate URLs with github_repo, huggingface_repo, or fetch_url.",
    }


def direct_url_results(query: str) -> list[dict[str, Any]]:
    results = []
    for url in URL_RE.findall(query):
        parsed = urllib.parse.urlparse(url)
        result_type = "url"
        if parsed.netloc.endswith("github.com"):
            result_type = "github"
        elif parsed.netloc.endswith("huggingface.co"):
            result_type = "huggingface"
        elif parsed.netloc.endswith("arxiv.org"):
            result_type = "paper"
        results.append(
            {
                "source": "direct_url",
                "type": result_type,
                "title": parsed.netloc + parsed.path,
                "url": url,
            }
        )
    return results


def arxiv_id_results(query: str) -> list[dict[str, Any]]:
    return [
        {
            "source": "arxiv_id",
            "type": "paper",
            "title": f"arXiv {paper_id}",
            "url": f"https://arxiv.org/abs/{paper_id}",
        }
        for paper_id in sorted(set(ARXIV_ID_RE.findall(query)))
    ]


def github_candidate_results(query: str, direct_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(result.get("type") == "github" for result in direct_results):
        return []
    if not any(word in query.lower() for word in ("github", "repo", "repository", "code")):
        return []
    tokens = query_tokens(query)
    if len(tokens) < 2:
        return []
    owner, repo = tokens[0], tokens[1]
    return [
        {
            "source": "github_candidate",
            "type": "github",
            "title": f"{owner}/{repo}",
            "url": f"https://github.com/{owner}/{repo}",
            "warning": "Heuristic candidate; verify with github_repo.",
        }
    ]


def query_tokens(query: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9_.-]+", query)
        if token.lower() not in SEARCH_STOP_WORDS
        and not token.startswith("http")
        and "." not in token
    ]


SEARCH_STOP_WORDS = {
    "github",
    "gitlab",
    "repository",
    "repo",
    "code",
    "official",
    "paper",
    "model",
    "weights",
    "checkpoint",
    "checkpoints",
    "dataset",
    "benchmark",
    "download",
    "arxiv",
}


def dedupe_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for result in results:
        url = result.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(result)
    return deduped
