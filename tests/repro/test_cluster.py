from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cluster import (
    DEFAULT_APPTAINER_SIF,
    DEFAULT_CLUSTER,
    cluster_defaults,
    cluster_names,
    from_args,
    resolve_cluster,
)


class ResolveClusterTests(unittest.TestCase):
    def test_deltaai_is_the_only_profile(self):
        c = resolve_cluster(DEFAULT_CLUSTER)
        self.assertEqual(c.name, "deltaai")
        self.assertEqual(c.account, "betw-dtai-gh")
        self.assertEqual(c.partition, "ghx4")
        self.assertEqual(c.hw, "gh200")
        self.assertEqual(c.gpus_per_node, 4)
        # The mandatory Apptainer sandbox is backed by the pinned CUDA .sif by default.
        self.assertEqual(c.apptainer_image, DEFAULT_APPTAINER_SIF)
        # Each agent's CPU shell steps are capped so six can share the brain node.
        self.assertEqual(c.sandbox_cpus, 12)
        self.assertEqual(c.sandbox_mem_gb, 16)
        # deltaai is the sole known name.
        self.assertEqual(cluster_names(), ("deltaai",))

    def test_partition_and_image_overrides_win(self):
        c = resolve_cluster("deltaai", partition="ghx4-interactive", apptainer_image="/my/image.sif")
        self.assertEqual(c.partition, "ghx4-interactive")
        self.assertEqual(c.apptainer_image, "/my/image.sif")
        # Everything else stays pinned to the profile, including the CPU cap.
        self.assertEqual(c.account, "betw-dtai-gh")
        self.assertEqual(c.gpus_per_node, 4)
        self.assertEqual(c.hw, "gh200")
        self.assertEqual(c.sandbox_cpus, 12)
        self.assertEqual(c.sandbox_mem_gb, 16)

    def test_unknown_cluster_rejected(self):
        with self.assertRaises(SystemExit):
            resolve_cluster("nope")

    def test_default_is_a_known_name(self):
        self.assertIn(DEFAULT_CLUSTER, cluster_names())


class ClusterDefaultsTests(unittest.TestCase):
    def test_exposes_default_partition_per_known_cluster(self):
        defaults = cluster_defaults()
        self.assertEqual(defaults["deltaai"]["default_partition"], "ghx4")
        self.assertEqual(defaults["deltaai"]["account"], "betw-dtai-gh")
        # Every known cluster is represented, with the fields list_partitions surfaces.
        self.assertEqual(set(defaults), set(cluster_names()))
        for entry in defaults.values():
            self.assertEqual(
                set(entry), {"account", "default_partition", "gpus_per_node", "hw"}
            )


class FromArgsTests(unittest.TestCase):
    def _args(self, **kw):
        base = dict(partition=None, apptainer_image=None)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_from_args_uses_profile_when_unset(self):
        c = from_args(self._args())
        self.assertEqual(c.account, "betw-dtai-gh")
        self.assertEqual(c.partition, "ghx4")

    def test_from_args_applies_partition_and_image(self):
        c = from_args(self._args(partition="ghx4-interactive", apptainer_image="/x.sif"))
        self.assertEqual(c.partition, "ghx4-interactive")
        self.assertEqual(c.apptainer_image, "/x.sif")


if __name__ == "__main__":
    unittest.main()
