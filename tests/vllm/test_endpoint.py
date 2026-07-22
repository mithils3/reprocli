from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_vllm.vllm.endpoint import (
    ENV_API_KEY,
    ENV_ENDPOINT_FILE,
    ENV_EXTRA_BODY,
    ENV_OPENROUTER_PROVIDER,
    ENV_SERVED_MODEL,
    ENV_SERVER_URL,
    auth_headers,
    body_overlay,
    merge_patch,
    normalize_server_url,
    openrouter_provider_routing,
    resolve_api_key,
    resolve_served_model,
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


class ResolveServedModelTests(unittest.TestCase):
    def _patch_models(self, ids: list[str]):
        return patch(
            "reprocli_vllm.vllm.endpoint.fetch_served_models",
            return_value=list(ids),
        )

    def test_picks_only_advertised_model(self) -> None:
        with patch.dict("os.environ", {}, clear=True), self._patch_models(["m/A"]):
            self.assertEqual(resolve_served_model("http://h:8000"), "m/A")

    def test_picks_first_when_several(self) -> None:
        with patch.dict("os.environ", {}, clear=True), self._patch_models(["m/A", "m/B"]):
            self.assertEqual(resolve_served_model("http://h:8000"), "m/A")

    def test_cli_override_wins_when_advertised(self) -> None:
        with patch.dict("os.environ", {}, clear=True), self._patch_models(["m/A", "m/B"]):
            self.assertEqual(resolve_served_model("http://h:8000", "m/B"), "m/B")

    def test_env_override_when_no_flag(self) -> None:
        env = {ENV_SERVED_MODEL: "m/B"}
        with patch.dict("os.environ", env, clear=True), self._patch_models(["m/A", "m/B"]):
            self.assertEqual(resolve_served_model("http://h:8000"), "m/B")

    def test_flag_beats_env(self) -> None:
        env = {ENV_SERVED_MODEL: "m/B"}
        with patch.dict("os.environ", env, clear=True), self._patch_models(["m/A", "m/B"]):
            self.assertEqual(resolve_served_model("http://h:8000", "m/A"), "m/A")

    def test_override_not_served_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True), self._patch_models(["m/A"]):
            with self.assertRaises(RuntimeError):
                resolve_served_model("http://h:8000", "m/typo")

    def test_no_models_advertised_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True), self._patch_models([]):
            with self.assertRaises(RuntimeError):
                resolve_served_model("http://h:8000")

    def _unlistable(self):
        return patch(
            "reprocli_vllm.vllm.endpoint.fetch_served_models",
            side_effect=RuntimeError("could not list models"),
        )

    def test_explicit_model_survives_unlistable_endpoint(self) -> None:
        # A hosted API may gate or omit /v1/models; an explicit name is enough.
        with patch.dict("os.environ", {}, clear=True), self._unlistable():
            self.assertEqual(
                resolve_served_model("https://api.anthropic.com", "claude-opus-4-8"),
                "claude-opus-4-8",
            )

    def test_unlistable_endpoint_still_raises_without_a_name(self) -> None:
        with patch.dict("os.environ", {}, clear=True), self._unlistable():
            with self.assertRaises(RuntimeError):
                resolve_served_model("https://api.anthropic.com")


class BodyOverlayTests(unittest.TestCase):
    def test_none_when_unset_or_blank(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(body_overlay())
        with patch.dict("os.environ", {ENV_EXTRA_BODY: "  "}, clear=True):
            self.assertIsNone(body_overlay())

    def test_parses_object(self) -> None:
        with patch.dict("os.environ", {ENV_EXTRA_BODY: '{"thinking": {"type": "adaptive"}}'}, clear=True):
            self.assertEqual(body_overlay(), {"thinking": {"type": "adaptive"}})

    def test_malformed_json_raises(self) -> None:
        with patch.dict("os.environ", {ENV_EXTRA_BODY: "{thinking"}, clear=True):
            with self.assertRaises(ValueError):
                body_overlay()

    def test_non_object_raises(self) -> None:
        with patch.dict("os.environ", {ENV_EXTRA_BODY: '["thinking"]'}, clear=True):
            with self.assertRaises(ValueError):
                body_overlay()


class MergePatchTests(unittest.TestCase):
    def test_sets_deletes_and_merges_nested(self) -> None:
        target = {"keep": 1, "drop": 2, "nested": {"a": 1, "b": 2}}
        merge_patch(target, {"add": 3, "drop": None, "nested": {"b": 9, "c": 3}})
        self.assertEqual(
            target, {"keep": 1, "add": 3, "nested": {"a": 1, "b": 9, "c": 3}}
        )

    def test_replaces_a_scalar_with_an_object(self) -> None:
        target = {"thinking": "off"}
        merge_patch(target, {"thinking": {"type": "adaptive"}})
        self.assertEqual(target["thinking"], {"type": "adaptive"})


class AuthHeaderTests(unittest.TestCase):
    def test_no_key_means_no_header(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(resolve_api_key())
            self.assertEqual(auth_headers(), {})

    def test_cli_value_wins(self) -> None:
        with patch.dict("os.environ", {ENV_API_KEY: "env"}, clear=True):
            self.assertEqual(auth_headers("sk-or-cli"), {"Authorization": "Bearer sk-or-cli"})

    def test_reprocli_env_key(self) -> None:
        with patch.dict("os.environ", {ENV_API_KEY: "sk-or-env"}, clear=True):
            self.assertEqual(auth_headers(), {"Authorization": "Bearer sk-or-env"})

    def test_openrouter_env_is_a_fallback(self) -> None:
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-2"}, clear=True):
            self.assertEqual(resolve_api_key(), "sk-or-2")

    def test_openai_key_is_never_used(self) -> None:
        # Guard against leaking an OpenAI key to a different provider's URL.
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-openai"}, clear=True):
            self.assertIsNone(resolve_api_key())
            self.assertEqual(auth_headers(), {})


class ProviderRoutingTests(unittest.TestCase):
    def test_none_when_unset(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(openrouter_provider_routing())

    def test_blank_is_treated_as_unset(self) -> None:
        with patch.dict("os.environ", {ENV_OPENROUTER_PROVIDER: "  ,  "}, clear=True):
            self.assertIsNone(openrouter_provider_routing())

    def test_single_provider_pins_with_no_fallback(self) -> None:
        with patch.dict("os.environ", {ENV_OPENROUTER_PROVIDER: "deepseek"}, clear=True):
            self.assertEqual(
                openrouter_provider_routing(),
                {"order": ["deepseek"], "allow_fallbacks": False},
            )

    def test_comma_list_keeps_order(self) -> None:
        with patch.dict(
            "os.environ", {ENV_OPENROUTER_PROVIDER: "deepseek, novita"}, clear=True
        ):
            self.assertEqual(
                openrouter_provider_routing(),
                {"order": ["deepseek", "novita"], "allow_fallbacks": False},
            )


if __name__ == "__main__":
    unittest.main()
