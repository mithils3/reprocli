from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cluster import resolve_cluster
from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools.partitions import list_partitions


def _ctx() -> ExecutionContext:
    return ExecutionContext(arxiv_id="x", cluster=resolve_cluster("deltaai"))


def _completed(stdout: str = "", *, rc: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr=stderr)


_SINFO = (
    "ghx4*|up|2-00:00:00|3/5/0/8|gpu:h200:4\n"
    "ghx4*|up|2-00:00:00|3/5/0/8|gpu:h200:4\n"   # duplicate state row -> collapses to one
    "ghx4-interactive|up|2:00:00|1/3/0/4|gpu:h200:4\n"
)


class ListPartitionsTests(unittest.TestCase):
    def test_parses_sinfo_and_dedupes_per_partition(self):
        with mock.patch(
            "reprocli_repro.tools.partitions.subprocess.run", return_value=_completed(_SINFO)
        ):
            res = list_partitions({}, _ctx())
        self.assertTrue(res["ok"])
        parts = {p["partition"]: p for p in res["partitions"]}
        self.assertEqual(set(parts), {"ghx4", "ghx4-interactive"})  # deduped
        self.assertTrue(parts["ghx4"]["is_slurm_default"])          # `*` marker stripped + flagged
        self.assertFalse(parts["ghx4-interactive"]["is_slurm_default"])
        self.assertEqual(parts["ghx4"]["nodes_allocated_idle_other_total"], "3/5/0/8")
        self.assertEqual(parts["ghx4-interactive"]["timelimit"], "2:00:00")

    def test_reports_known_defaults_and_active_cluster(self):
        with mock.patch(
            "reprocli_repro.tools.partitions.subprocess.run", return_value=_completed(_SINFO)
        ):
            res = list_partitions({}, _ctx())
        self.assertEqual(res["active_cluster"], "deltaai")
        self.assertEqual(res["active_default_partition"], "ghx4")
        self.assertEqual(res["known_cluster_defaults"]["deltaai"]["default_partition"], "ghx4")
        self.assertEqual(set(res["known_cluster_defaults"]), {"deltaai"})

    def test_sinfo_absent_degrades_to_defaults_with_a_note(self):
        with mock.patch(
            "reprocli_repro.tools.partitions.subprocess.run", side_effect=FileNotFoundError()
        ):
            res = list_partitions({}, _ctx())
        self.assertTrue(res["ok"])                 # still useful: defaults are returned
        self.assertEqual(res["partitions"], [])
        self.assertIn("sinfo", res["note"])
        self.assertEqual(res["known_cluster_defaults"]["deltaai"]["default_partition"], "ghx4")

    def test_sinfo_nonzero_exit_is_a_note_not_a_crash(self):
        with mock.patch(
            "reprocli_repro.tools.partitions.subprocess.run",
            return_value=_completed("", rc=1, stderr="slurm down"),
        ):
            res = list_partitions({}, _ctx())
        self.assertTrue(res["ok"])
        self.assertEqual(res["partitions"], [])
        self.assertIn("slurm down", res["note"])


if __name__ == "__main__":
    unittest.main()
