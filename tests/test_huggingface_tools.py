from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.tools import huggingface_mcp as hf_mcp
from reprocli_vllm.tools.huggingface_tree import (
    format_tree_entry,
    huggingface_repository_tree_tool,
    repository_tree_payload,
)


DETAILS_TOOL = {
    "name": "hub_repo_details",
    "inputSchema": {
        "properties": {
            "repo_ids": {},
            "repo_type": {},
            "include_readme": {},
        }
    },
}

SEARCH_TOOL = {
    "name": "hf_hub_query",
    "inputSchema": {
        "properties": {
            "message": {},
            "results_limit": {},
        }
    },
}


class FakeHFClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def list_tools(self) -> list[dict]:
        return [SEARCH_TOOL, DETAILS_TOOL]

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        return {"content": [{"type": "text", "text": "ok"}]}


class RepoFile:
    def __init__(self, path: str, size: int | None = None, lfs: dict | None = None) -> None:
        self.path = path
        self.size = size
        self.lfs = lfs


class RepoFolder:
    def __init__(self, path: str) -> None:
        self.path = path


class HuggingFaceMCPTests(unittest.TestCase):
    def test_hf_url_parsing(self) -> None:
        self.assertEqual(
            hf_mcp.parse_hf_repo("https://huggingface.co/user/model", "model"),
            ("user/model", "model"),
        )
        self.assertEqual(
            hf_mcp.parse_hf_repo("https://huggingface.co/datasets/user/data/tree/main", "auto"),
            ("user/data", "dataset"),
        )
        self.assertEqual(
            hf_mcp.parse_hf_repo("https://huggingface.co/spaces/user/demo/blob/main/app.py", "auto"),
            ("user/demo", "space"),
        )

    def test_repo_ids_from_list_scalar_and_json_string(self) -> None:
        self.assertEqual(hf_mcp.repo_ids_from_value(["a/b", "c/d"]), ["a/b", "c/d"])
        self.assertEqual(hf_mcp.repo_ids_from_value("a/b"), ["a/b"])
        self.assertEqual(hf_mcp.repo_ids_from_value('["a/b", "c/d"]'), ["a/b", "c/d"])

    def test_repo_params_map_to_repo_ids_and_include_readme(self) -> None:
        params = hf_mcp.params_for_schema(
            DETAILS_TOOL,
            {"repo": "a/b", "repo_type": "auto"},
            repo_ids=["a/b"],
            repo_id="a/b",
            include_readme=True,
        )
        self.assertEqual(params, {"repo_ids": ["a/b"], "include_readme": True})

    def test_search_params_map_to_message_and_results_limit(self) -> None:
        params = hf_mcp.params_for_schema(
            SEARCH_TOOL,
            {"max_results": 7},
            query="graph diffusion checkpoint",
        )
        self.assertEqual(params, {"message": "graph diffusion checkpoint", "results_limit": 7})

    def test_repo_calls_reach_mcp_with_repo_ids(self) -> None:
        client = FakeHFClient()
        calls = [
            {"repo": "narunraman/steer_me"},
            {"repo": "https://huggingface.co/narunraman/steer_me"},
            {"repo": "https://huggingface.co/datasets/narunraman/steer_me"},
            {"repo": "https://huggingface.co/spaces/narunraman/steer_me"},
            {"repo_ids": ["narunraman/steer_me"]},
            {"repo_ids": '["narunraman/steer_me"]'},
        ]
        with (
            patch.object(hf_mcp, "hf_mcp_client", return_value=client),
            patch.object(hf_mcp, "safe_repository_tree_summary", return_value={"ok": True}),
        ):
            for arguments in calls:
                result = hf_mcp.huggingface_repo_tool(arguments)
                self.assertTrue(result["ok"])

        self.assertEqual(len(client.calls), len(calls))
        for name, arguments in client.calls:
            self.assertEqual(name, "hub_repo_details")
            self.assertEqual(arguments["repo_ids"], ["narunraman/steer_me"])
            self.assertTrue(arguments["include_readme"])


class HuggingFaceTreeTests(unittest.TestCase):
    def test_tree_tool_accepts_hf_dataset_url(self) -> None:
        with patch("reprocli_vllm.tools.huggingface_tree.list_repo_tree", return_value=[]):
            payload = huggingface_repository_tree_tool(
                {"repo": "https://huggingface.co/datasets/user/repo/tree/main/data"}
            )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["repo"], "user/repo")
        self.assertEqual(payload["repo_type"], "dataset")

    def test_tree_formatting_and_truncation(self) -> None:
        entries = [
            RepoFolder("data"),
            RepoFile("README.md", size=120),
            RepoFile("model.safetensors", size=12, lfs={"size": 999}),
        ]
        with patch("reprocli_vllm.tools.huggingface_tree.list_repo_tree", return_value=entries):
            payload = repository_tree_payload(
                repo_id="user/repo",
                repo_type="dataset",
                path=None,
                revision=None,
                recursive=False,
                max_entries=2,
            )
        self.assertTrue(payload["truncated"])
        self.assertEqual(payload["entry_count"], 3)
        self.assertEqual(payload["entries"], [
            {"path": "data", "type": "directory"},
            {"path": "README.md", "type": "file", "size": 120},
        ])
        self.assertEqual(
            format_tree_entry(entries[2]),
            {"path": "model.safetensors", "type": "file", "size": 12, "lfs": True, "lfs_size": 999},
        )


if __name__ == "__main__":
    unittest.main()
