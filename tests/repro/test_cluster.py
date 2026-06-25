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
    def test_deltaai_is_the_default_profile(self):
        c = resolve_cluster(DEFAULT_CLUSTER)
        self.assertEqual(c.name, "deltaai")
        self.assertEqual(c.account, "betw-dtai-gh")
        self.assertEqual(c.partition, "ghx4")
        self.assertEqual(c.hw, "gh200")
        self.assertEqual(c.gpus_per_node, 4)
        # Host modules are inert under the container sandbox (the image is the toolchain).
        self.assertEqual(c.modules, ())
        # The mandatory Apptainer sandbox is backed by the NGC PyTorch .sif by default.
        self.assertEqual(c.apptainer_image, DEFAULT_APPTAINER_SIF)

    def test_delta_h200_has_no_default_sandbox_image(self):
        # x86 H200 pins no image: --apptainer-image is required (require_apptainer fails
        # otherwise), so the sandbox is still mandatory, just not pre-pinned.
        c = resolve_cluster("delta-h200")
        self.assertEqual(c.account, "bfvr-delta-gpu")
        self.assertEqual(c.partition, "gpuH200x8-interactive")
        self.assertEqual(c.hw, "h200")
        self.assertEqual(c.gpus_per_node, 8)
        self.assertIsNone(c.apptainer_image)

    def test_per_field_overrides_win(self):
        c = resolve_cluster(
            "deltaai",
            account="my-acct",
            partition="my-part",
            gpus_per_node=2,
            hw="h200",
            modules=["python/3.12", "cuda"],
            scratch_root="/scratch",
        )
        self.assertEqual(c.account, "my-acct")
        self.assertEqual(c.partition, "my-part")
        self.assertEqual(c.gpus_per_node, 2)
        self.assertEqual(c.hw, "h200")
        self.assertEqual(c.modules, ("python/3.12", "cuda"))
        self.assertEqual(c.scratch_root, "/scratch")

    def test_unknown_cluster_rejected(self):
        with self.assertRaises(SystemExit):
            resolve_cluster("nope")

    def test_unknown_hw_override_rejected(self):
        with self.assertRaises(SystemExit):
            resolve_cluster("deltaai", hw="tpu")

    def test_default_is_a_known_name(self):
        self.assertIn(DEFAULT_CLUSTER, cluster_names())


class ClusterDefaultsTests(unittest.TestCase):
    def test_exposes_default_partition_per_known_cluster(self):
        defaults = cluster_defaults()
        self.assertEqual(defaults["deltaai"]["default_partition"], "ghx4")
        self.assertEqual(defaults["deltaai"]["account"], "betw-dtai-gh")
        self.assertEqual(defaults["delta-h200"]["default_partition"], "gpuH200x8-interactive")
        # Every known cluster is represented, with the fields list_partitions surfaces.
        self.assertEqual(set(defaults), set(cluster_names()))
        for entry in defaults.values():
            self.assertEqual(
                set(entry), {"account", "default_partition", "gpus_per_node", "hw"}
            )


class FromArgsTests(unittest.TestCase):
    def _args(self, **kw):
        base = dict(
            cluster="deltaai",
            account=None,
            partition=None,
            gpus_per_node=None,
            hw=None,
            modules="",
            apptainer_image=None,
            scratch_root=None,
        )
        base.update(kw)
        return argparse.Namespace(**base)

    def test_from_args_uses_profile_when_unset(self):
        c = from_args(self._args())
        self.assertEqual(c.account, "betw-dtai-gh")

    def test_from_args_overrides_and_splits_modules(self):
        c = from_args(self._args(cluster="deltaai", account="acct", modules="a b c"))
        self.assertEqual(c.account, "acct")
        self.assertEqual(c.modules, ("a", "b", "c"))


if __name__ == "__main__":
    unittest.main()
