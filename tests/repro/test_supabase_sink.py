"""Batch grouping: SinkConfig.from_env reads REPRO_BATCH_ID / SLURM_JOB_ID and
upsert_run carries batch_id / batch_label onto the run row.

One sbatch sweep launches many ``python -m reprocli_repro`` processes; they share
REPRO_BATCH_ID so the run viewer can show the whole launch as a single group.
"""

from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
