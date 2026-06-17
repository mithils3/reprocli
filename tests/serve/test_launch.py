from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_serve.args import parse_args
from reprocli_serve.launch import build_serve_command
from reprocli_serve.profiles import resolve_profile


def command_for(argv: list[str]) -> list[str]:
    args = parse_args(argv)
    return build_serve_command(args, resolve_profile(args.model))


def value_after(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


class MinimaxServeCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cmd = command_for(["--model", "MiniMaxAI/MiniMax-M2.7"])

    def test_serves_the_model_on_all_interfaces(self) -> None:
        self.assertEqual(self.cmd[:3], ["vllm", "serve", "MiniMaxAI/MiniMax-M2.7"])
        self.assertEqual(value_after(self.cmd, "--host"), "0.0.0.0")
        self.assertEqual(value_after(self.cmd, "--port"), "8000")

    def test_uses_minimax_profile_flags(self) -> None:
        self.assertEqual(value_after(self.cmd, "--tensor-parallel-size"), "4")
        self.assertEqual(value_after(self.cmd, "--tool-call-parser"), "minimax_m2")
        self.assertEqual(value_after(self.cmd, "--reasoning-parser"), "minimax_m2")
        self.assertIn("--enable-auto-tool-choice", self.cmd)
        self.assertIn("--trust-remote-code", self.cmd)
        self.assertIn("cudagraph_mode", value_after(self.cmd, "--compilation-config"))

    def test_served_model_name_defaults_to_model(self) -> None:
        self.assertEqual(value_after(self.cmd, "--served-model-name"), "MiniMaxAI/MiniMax-M2.7")

    def test_served_model_name_override(self) -> None:
        cmd = command_for(["--model", "/local/path", "--served-model-name", "MiniMaxAI/MiniMax-M2.7"])
        self.assertEqual(value_after(cmd, "--served-model-name"), "MiniMaxAI/MiniMax-M2.7")


class KimiMultinodeServeCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cmd = command_for(
            [
                "--model",
                "moonshotai/Kimi-K2.6",
                "--tensor-parallel-size",
                "4",
                "--pipeline-parallel-size",
                "2",
                "--nnodes",
                "2",
                "--node-rank",
                "1",
                "--master-addr",
                "1.2.3.4",
                "--headless",
            ]
        )

    def test_uses_kimi_profile_flags(self) -> None:
        self.assertEqual(value_after(self.cmd, "--tool-call-parser"), "kimi_k2")
        self.assertEqual(value_after(self.cmd, "--reasoning-parser"), "kimi_k2")
        self.assertEqual(value_after(self.cmd, "--mm-encoder-tp-mode"), "data")

    def test_wires_multinode_rendezvous(self) -> None:
        self.assertEqual(value_after(self.cmd, "--tensor-parallel-size"), "4")
        self.assertEqual(value_after(self.cmd, "--pipeline-parallel-size"), "2")
        self.assertEqual(value_after(self.cmd, "--nnodes"), "2")
        self.assertEqual(value_after(self.cmd, "--node-rank"), "1")
        self.assertEqual(value_after(self.cmd, "--master-addr"), "1.2.3.4")
        self.assertIn("--headless", self.cmd)


class PassthroughTests(unittest.TestCase):
    def test_extra_args_are_appended_verbatim(self) -> None:
        cmd = command_for(["--model", "m", "--", "--swap-space", "16"])
        self.assertEqual(cmd[-2:], ["--swap-space", "16"])

    def test_single_node_omits_multinode_flags(self) -> None:
        cmd = command_for(["--model", "MiniMaxAI/MiniMax-M2.7"])
        for flag in ("--pipeline-parallel-size", "--nnodes", "--node-rank", "--headless"):
            self.assertNotIn(flag, cmd)


if __name__ == "__main__":
    unittest.main()
