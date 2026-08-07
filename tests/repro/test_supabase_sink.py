"""Batch grouping: SinkConfig.from_env reads REPRO_BATCH_ID / SLURM_JOB_ID and
upsert_run carries batch_id / batch_label onto the run row.

One sbatch sweep launches many ``python -m reprocli_repro`` processes; they share
REPRO_BATCH_ID so the run viewer can show the whole launch as a single group.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.supabase_sink import SinkConfig, SupabaseSink

_MIN_ENV = {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "k"}


def _cfg_with(env: dict[str, str]) -> SinkConfig:
    with mock.patch.dict("os.environ", {**_MIN_ENV, **env}, clear=True):
        cfg = SinkConfig.from_env()
    assert cfg is not None
    return cfg


class FromEnvBatchTests(unittest.TestCase):

    def test_explicit_batch_id_wins_over_slurm(self) -> None:
        cfg = _cfg_with({"REPRO_BATCH_ID": "sweep-42", "SLURM_JOB_ID": "999"})
        self.assertEqual(cfg.batch_id, "sweep-42")

    def test_slurm_job_id_fallback_is_prefixed(self) -> None:
        cfg = _cfg_with({"SLURM_JOB_ID": "999"})
        self.assertEqual(cfg.batch_id, "slurm-999")

    def test_empty_strings_count_as_unset(self) -> None:
        cfg = _cfg_with({"REPRO_BATCH_ID": "", "SLURM_JOB_ID": ""})
        self.assertIsNone(cfg.batch_id)

    def test_both_unset_is_none(self) -> None:
        cfg = _cfg_with({})
        self.assertIsNone(cfg.batch_id)
        self.assertIsNone(cfg.batch_label)

    def test_batch_label_read_from_env(self) -> None:
        cfg = _cfg_with({"REPRO_BATCH_LABEL": "dev15 #42"})
        self.assertEqual(cfg.batch_label, "dev15 #42")


class UpsertPayloadTests(unittest.TestCase):

    def test_upsert_run_carries_batch_fields(self) -> None:
        cfg = SinkConfig(
            url="https://x.supabase.co", service_key="k", host="h",
            upload_full_log=False, upload_stats=False,
            batch_id="slurm-999", batch_label="dev15 #999",
        )
        sink = SupabaseSink(cfg)
        captured: list = []
        try:
            sink._put = lambda kind, payload: captured.append((kind, payload))  # type: ignore[method-assign]
            ctx = SimpleNamespace(evidence="/runs/run123/evidence", arxiv_id="2506.09045", budget=None)
            sink.upsert_run(ctx, model="minimax-m2")
        finally:
            sink.close(timeout=2.0)
        kinds = [k for k, _ in captured]
        self.assertIn("run_upsert", kinds)
        payload = next(p for k, p in captured if k == "run_upsert")
        self.assertEqual(payload["batch_id"], "slurm-999")
        self.assertEqual(payload["batch_label"], "dev15 #999")


def _finalize_sink(upload_stats: bool = True) -> tuple[SupabaseSink, list]:
    """A sink whose HTTP POSTs are captured (no network) instead of sent."""
    cfg = SinkConfig(
        url="https://x.supabase.co", service_key="k", host="h",
        upload_full_log=False, upload_stats=upload_stats,
        batch_id=None, batch_label=None,
    )
    sink = SupabaseSink(cfg)
    posts: list = []
    sink._post = lambda *a, **k: posts.append((a, k))  # type: ignore[method-assign]
    return sink, posts


class FinalizeWorkerTests(unittest.TestCase):
    """_finalize runs on the worker: GPU rollup -> patch run row -> upload stats."""

    def test_gpu_fields_merged_into_run_patch_and_stats_section_written(self) -> None:
        run_fields = {"gpu_util_avg_pct": 43.0, "gpu_active_pct": 61.0, "gpu_samples": 5}
        gpu_stats = {**run_fields, "active_util_threshold_pct": 10, "timeline": [[0, 43.0, 38.2]]}
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = str(Path(tmp) / "stats.json")
            sink, posts = _finalize_sink()
            try:
                with mock.patch("reprocli_repro.gpu_usage.rollup", return_value=(run_fields, gpu_stats)):
                    sink._finalize("run1", {"status": "finished"}, {"run_id": "run1"}, stats_path, None)
            finally:
                sink.close(timeout=2.0)
            # first PATCH carries the finished fields merged with the GPU rollup
            patches = [a[2] for (a, _k) in posts if a[0] == "PATCH"]
            self.assertTrue(patches)
            self.assertEqual(patches[0]["gpu_util_avg_pct"], 43.0)
            self.assertEqual(patches[0]["status"], "finished")
            # stats.json got the "gpu" section (plus write_doc's tokens/rounds)
            doc = json.loads(Path(stats_path).read_text(encoding="utf-8"))
            self.assertEqual(doc["gpu"], gpu_stats)
            self.assertIn("tokens", doc)
            # a storage POST uploaded the stats artifact
            self.assertTrue(any(a[0] == "POST" and "storage" in a[1] for (a, _k) in posts))

    def test_rollup_failure_still_patches_and_uploads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = str(Path(tmp) / "stats.json")
            sink, posts = _finalize_sink()
            try:
                with mock.patch("reprocli_repro.gpu_usage.rollup", return_value=(None, None)):
                    sink._finalize("run1", {"status": "finished"}, {"run_id": "run1"}, stats_path, None)
            finally:
                sink.close(timeout=2.0)
            patches = [a[2] for (a, _k) in posts if a[0] == "PATCH"]
            self.assertTrue(patches)
            self.assertEqual(patches[0]["status"], "finished")
            self.assertNotIn("gpu_util_avg_pct", patches[0])
            doc = json.loads(Path(stats_path).read_text(encoding="utf-8"))
            self.assertNotIn("gpu", doc)
            self.assertTrue(any(a[0] == "POST" and "storage" in a[1] for (a, _k) in posts))


class FinishEnqueueTests(unittest.TestCase):
    """_finish enqueues exactly one finalize item (not the old three)."""

    def test_finish_enqueues_single_finalize_item(self) -> None:
        cfg = SinkConfig(
            url="https://x.supabase.co", service_key="k", host="h",
            upload_full_log=True, upload_stats=True, batch_id=None, batch_label=None,
        )
        sink = SupabaseSink(cfg)
        captured: list = []
        try:
            sink._put = lambda kind, payload: captured.append((kind, payload))  # type: ignore[method-assign]
            ctx = SimpleNamespace(evidence="/runs/run123/evidence", arxiv_id="2506.09045", budget=None)
            sink._finish(ctx, "run123", "natural")
        finally:
            sink.close(timeout=2.0)
        kinds = [k for k, _ in captured]
        self.assertEqual(kinds, ["finalize"])
        _, payload = captured[0]
        run_id, fields, meta, stats_path, log_path = payload
        self.assertEqual(run_id, "run123")
        self.assertEqual(fields["status"], "finished")
        self.assertEqual(meta["exit_reason"], "natural")
        self.assertTrue(stats_path.endswith("stats.json"))
        self.assertTrue(log_path.endswith("agent.full.log"))


if __name__ == "__main__":
    unittest.main()
