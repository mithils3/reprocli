from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.vllm.endpoint import (
    ENV_ENDPOINT_FILE,
    ENV_SERVER_URL,
    normalize_server_url,
    resolve_server_url,
)


class NormalizeTests(unittest.TestCase):
    def test_strips_trailing_slash(self) -> None:
        self.assertEqual(normalize_server_url("http://h:8000/"), "http://h:8000")

    def test_strips_trailing_v1(self) -> None:
        self.assertEqual(normalize_server_url("http://h:8000/v1"), "http://h:8000")

    def test_strips_v1_and_slash(self) -> None:
        self.assertEqual(normalize_server_url("http://h:8000/v1/"), "http://h:8000")


class ResolvePrecedenceTests(unittest.TestCase):
    def test_cli_flag_wins(self) -> None:
        with patch.dict("os.environ", {ENV_SERVER_URL: "http://env:8000"}, clear=False):
            self.assertEqual(resolve_server_url("http://cli:8000/v1"), "http://cli:8000")

    def test_env_url_when_no_flag(self) -> None:
        with patch.dict("os.environ", {ENV_SERVER_URL: "http://env:8000/"}, clear=False):
            self.assertEqual(resolve_server_url(None), "http://env:8000")

    def test_endpoint_file_when_no_flag_or_env(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "vllm_endpoint.json"
            path.write_text(json.dumps({"base_url": "http://file:8000"}), encoding="utf-8")
            env = {ENV_ENDPOINT_FILE: str(path)}
            with patch.dict("os.environ", env, clear=True):
                self.assertEqual(resolve_server_url(None), "http://file:8000")

    def test_none_when_nothing_set(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(resolve_server_url(None))

    def test_none_when_endpoint_file_missing(self) -> None:
        env = {ENV_ENDPOINT_FILE: "/no/such/endpoint.json"}
        with patch.dict("os.environ", env, clear=True):
            self.assertIsNone(resolve_server_url(None))


if __name__ == "__main__":
    unittest.main()
