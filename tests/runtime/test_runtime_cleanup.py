from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from reprocli_vllm.config.config import DEFAULT_MODEL, KIMI_K2_6_MODEL, MINIMAX_M2_MODEL
from reprocli_vllm.vllm.server import VllmServer
from run_arxiv_prompt_vllm import parse_args


class RuntimeCleanupTests(unittest.TestCase):
    def test_minimax_defaults_are_active(self) -> None:
        with patch.object(sys, "argv", ["run_arxiv_prompt_vllm.py"]):
            args = parse_args()

        self.assertEqual(DEFAULT_MODEL, MINIMAX_M2_MODEL)
        self.assertEqual(args.model, MINIMAX_M2_MODEL)
        self.assertEqual(args.tool_call_parser, "minimax_m2")
        self.assertEqual(args.reasoning_parser, "minimax_m2")
        self.assertEqual(args.tensor_parallel_size, 4)
        self.assertEqual(args.max_model_len, 196608)
        self.assertEqual(args.temperature, 1.0)
        self.assertEqual(args.top_p, 0.95)
        self.assertEqual(args.top_k, 40)
        self.assertEqual(json.loads(args.compilation_config), {"cudagraph_mode": "PIECEWISE"})

    def test_kimi_k2_6_defaults_are_available(self) -> None:
        with patch.object(
            sys,
            "argv",
            ["run_arxiv_prompt_vllm.py", "--model", KIMI_K2_6_MODEL],
        ):
            args = parse_args()

        self.assertEqual(args.model, KIMI_K2_6_MODEL)
        self.assertEqual(args.tool_call_parser, "kimi_k2")
        self.assertEqual(args.reasoning_parser, "kimi_k2")
        self.assertEqual(args.mm_encoder_tp_mode, "data")
        self.assertEqual(args.tensor_parallel_size, 8)
        self.assertTrue(args.trust_remote_code)

    def test_kimi_server_command_uses_vllm_parser_flags(self) -> None:
        with patch.object(
            sys,
            "argv",
            ["run_arxiv_prompt_vllm.py", "--model", KIMI_K2_6_MODEL],
        ):
            args = parse_args()

        process = MagicMock()
        process.poll.return_value = None
        with (
            patch("reprocli_vllm.vllm.server.local_open_port", return_value=12345),
            patch.object(VllmServer, "wait_until_ready"),
            patch("reprocli_vllm.vllm.server.subprocess.Popen", return_value=process) as popen,
        ):
            server = VllmServer(args)
            server.__enter__()
            server.__exit__(None, None, None)

        command = popen.call_args.args[0]
        self.assertEqual(command[command.index("--tool-call-parser") + 1], "kimi_k2")
        self.assertEqual(command[command.index("--reasoning-parser") + 1], "kimi_k2")
        self.assertEqual(command[command.index("--mm-encoder-tp-mode") + 1], "data")
        self.assertIn("--enable-auto-tool-choice", command)
        self.assertIn("--trust-remote-code", command)

    def test_removed_cli_flags_are_absent_from_active_docs(self) -> None:
        texts = "\n".join(
            read_text(path)
            for path in (
                "src/run_arxiv_prompt_vllm.py",
                "README.md",
                "scripts/paper_classification.sbatch",
            )
        )
        removed = [
            "--model-profile",
            "--reasoning-effort",
            "--pwc-artifacts",
            "--requests-output",
            "--guided-decoding-backend",
            "--disable-structured-final-output",
        ]
        for flag in removed:
            with self.subTest(flag=flag):
                self.assertNotIn(flag, texts)

    def test_deleted_runtime_surfaces_are_absent(self) -> None:
        removed_paths = [
            "src/run_arxiv_prompt_openai.py",
            "src/reprocli_vllm/openai_arxiv.py",
            "src/reprocli_vllm/openai_batch.py",
            "src/reprocli_vllm/openai_progress.py",
            "src/reprocli_vllm/openai_client.py",
            "src/reprocli_vllm/openai_server.py",
            "src/reprocli_vllm/model_profiles.py",
            "src/reprocli_vllm/tools/github_search.py",
            "src/reprocli_data/scrape_paperswithcode_arxiv.py",
            "src/reprocli_data/upload_paperswithcode_dataset.py",
            "src/view_jsonl_conversations.py",
            "tools/jsonl_conversation_viewer.html",
            "notes/neurips_2025_deepseek_v4_flash_analysis.md",
        ]
        for relative in removed_paths:
            with self.subTest(path=relative):
                self.assertFalse((ROOT / relative).exists())

    def test_source_keeps_only_vllm_serving_api_openai_literal(self) -> None:
        hits = []
        for path in (ROOT / "src").rglob("*.py"):
            # reprocli_openai is the dedicated OpenAI re-check package; its
            # openai usage is intentional and outside the vLLM runtime surface.
            if "reprocli_openai" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            stripped = text.replace("vllm.entrypoints.openai.api_server", "")
            if "openai" in stripped.lower():
                hits.append(str(path.relative_to(ROOT)))

        self.assertEqual(hits, [])


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
