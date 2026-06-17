from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_serve import network
from reprocli_serve.profiles import resolve_profile

SAMPLE_IP_OUTPUT = (
    "2: hsn0    inet 141.142.249.0/16 brd 141.142.255.255 scope global hsn0\\       valid_lft forever\n"
)
LOOPBACK_ONLY = "1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever\n"


class DiscoverIpv4Tests(unittest.TestCase):
    def test_parses_fabric_ip(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=SAMPLE_IP_OUTPUT)
        with patch("reprocli_serve.network.subprocess.run", return_value=completed):
            self.assertEqual(network.discover_ipv4("hsn0"), "141.142.249.0")

    def test_skips_loopback(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=LOOPBACK_ONLY)
        with patch("reprocli_serve.network.subprocess.run", return_value=completed):
            self.assertIsNone(network.discover_ipv4("lo"))


class AdvertisedHostTests(unittest.TestCase):
    def test_explicit_wins(self) -> None:
        self.assertEqual(network.advertised_host("9.9.9.9", "hsn0"), "9.9.9.9")

    def test_falls_back_to_iface(self) -> None:
        with patch("reprocli_serve.network.discover_ipv4", return_value="141.142.249.0"):
            self.assertEqual(network.advertised_host(None, "hsn0"), "141.142.249.0")

    def test_tries_rest_of_hsn_family_when_first_has_no_ip(self) -> None:
        # hsn0 has no address; hsn1 does. Must still publish a routable IP.
        def fake(iface: str):
            return "141.142.5.5" if iface == "hsn1" else None

        with patch("reprocli_serve.network.discover_ipv4", side_effect=fake):
            self.assertEqual(network.advertised_host(None, "hsn0"), "141.142.5.5")

    def test_never_publishes_loopback(self) -> None:
        with (
            patch("reprocli_serve.network.discover_ipv4", return_value=None),
            patch("reprocli_serve.network.hostname_ipv4", return_value=None),
            patch("reprocli_serve.network.socket.gethostname", return_value="gh049"),
        ):
            self.assertEqual(network.advertised_host(None, "hsn0"), "gh049")

    def test_base_url_format(self) -> None:
        self.assertEqual(network.base_url("1.2.3.4", 8000), "http://1.2.3.4:8000")


class ProfileTests(unittest.TestCase):
    def test_kimi_by_id(self) -> None:
        profile = resolve_profile("moonshotai/Kimi-K2.6")
        self.assertEqual(profile.tool_call_parser, "kimi_k2")
        self.assertEqual(profile.mm_encoder_tp_mode, "data")
        self.assertEqual(profile.tensor_parallel_size, 8)

    def test_kimi_by_local_path_suffix(self) -> None:
        self.assertEqual(resolve_profile("/work/models/Kimi-K2.6").reasoning_parser, "kimi_k2")

    def test_minimax_default(self) -> None:
        profile = resolve_profile("MiniMaxAI/MiniMax-M2.7")
        self.assertEqual(profile.tool_call_parser, "minimax_m2")
        self.assertEqual(profile.tensor_parallel_size, 4)
        self.assertIsNotNone(profile.compilation_config)


if __name__ == "__main__":
    unittest.main()
