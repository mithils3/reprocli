from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.config import BUNDLE_FILE_MAX_CHARS
from reprocli_vllm.papers import Paper
from reprocli_vllm.tools.paper_bundle import paper_bundle_file_contents_tool
from reprocli_vllm.tools.web_tools import execute_tool_call


def sample_paper() -> Paper:
    return Paper(
        arxiv_id="2501.00001",
        supplement_files=[
            {
                "relative_path": "README.md",
                "filename": "README.md",
                "extension": ".md",
                "file_size": 24,
                "sha256": "readme-sha",
                "is_text": True,
                "text": "bundle readme text",
            },
            {
                "relative_path": "configs/train.yaml",
                "filename": "train.yaml",
                "extension": ".yaml",
                "file_size": 80,
                "sha256": "config-sha",
                "is_text": True,
                "text": "learning_rate: 0.001\nbatch_size: 8\n",
            },
            {
                "relative_path": "data/blob.bin",
                "filename": "blob.bin",
                "extension": ".bin",
                "file_size": 3,
                "sha256": "bin-sha",
                "is_text": False,
                "text": "",
                "content": b"\x00\x01\x02",
            },
        ],
    )


def tool_call(name: str, arguments: dict) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


class PaperBundleFileContentsTests(unittest.TestCase):
    def test_reads_text_file_by_manifest_path(self) -> None:
        result = paper_bundle_file_contents_tool({"path": "README.md"}, sample_paper())

        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], "README.md")
        self.assertEqual(result["text"], "bundle readme text")
        self.assertFalse(result["truncated"])

    def test_reads_text_file_by_supplement_prefixed_path(self) -> None:
        result = paper_bundle_file_contents_tool(
            {"path": "supplement/configs/train.yaml"},
            sample_paper(),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], "configs/train.yaml")
        self.assertIn("learning_rate", result["text"])

    def test_truncates_text_and_reports_truncated(self) -> None:
        result = paper_bundle_file_contents_tool(
            {"path": "configs/train.yaml", "max_chars": 8},
            sample_paper(),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "learning")
        self.assertTrue(result["truncated"])
        self.assertEqual(result["max_chars"], 8)

    def test_bounds_requested_max_chars(self) -> None:
        paper = sample_paper()
        paper.supplement_files[0]["text"] = "x" * (BUNDLE_FILE_MAX_CHARS + 1)
        result = paper_bundle_file_contents_tool(
            {"path": "README.md", "max_chars": BUNDLE_FILE_MAX_CHARS + 100},
            paper,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["text"]), BUNDLE_FILE_MAX_CHARS)
        self.assertTrue(result["truncated"])

    def test_rejects_unsafe_or_unknown_paths(self) -> None:
        paper = sample_paper()
        bad_paths = [
            "",
            "/README.md",
            "../README.md",
            "configs/../README.md",
            "configs\\train.yaml",
            "missing.txt",
        ]

        for path in bad_paths:
            with self.subTest(path=path):
                result = paper_bundle_file_contents_tool({"path": path}, paper)
                self.assertFalse(result["ok"])

    def test_binary_file_returns_metadata_without_text(self) -> None:
        result = paper_bundle_file_contents_tool({"path": "data/blob.bin"}, sample_paper())

        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], "data/blob.bin")
        self.assertFalse(result["is_text"])
        self.assertNotIn("text", result)
        self.assertNotIn("truncated", result)


class PaperBundleDispatchTests(unittest.TestCase):
    def test_execute_tool_call_requires_current_paper_context(self) -> None:
        call = tool_call("paper_bundle_file_contents", {"path": "README.md"})

        missing = execute_tool_call(call)
        routed = execute_tool_call(call, paper=sample_paper())

        self.assertFalse(missing["ok"])
        self.assertIn("requires current Paper context", missing["error"])
        self.assertTrue(routed["ok"])
        self.assertEqual(routed["text"], "bundle readme text")


if __name__ == "__main__":
    unittest.main()
