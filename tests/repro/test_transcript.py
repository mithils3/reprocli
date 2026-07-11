from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.transcript import (
    WALL_DEADLINE_ENV,
    round_status_message,
    sweep_wall_note,
)


def test_round_status_message_without_wall_env(monkeypatch):
    monkeypatch.delenv(WALL_DEADLINE_ENV, raising=False)
    msg = round_status_message(0, 300)
    assert msg == {"role": "user", "content": "Tool round 1/300 · 299 left"}


def test_sweep_wall_note_hours_and_minutes_left(monkeypatch):
    now = 1_000_000.0
    monkeypatch.setenv(WALL_DEADLINE_ENV, str(now + 47 * 3600 + 59 * 60 + 30))
    assert sweep_wall_note(now=now) == "sweep wall ~47h59m left"


def test_sweep_wall_note_small_remainder(monkeypatch):
    now = 1_000_000.0
    monkeypatch.setenv(WALL_DEADLINE_ENV, str(now + 90))
    assert sweep_wall_note(now=now) == "sweep wall ~0h01m left"


def test_sweep_wall_note_expired(monkeypatch):
    now = 1_000_000.0
    monkeypatch.setenv(WALL_DEADLINE_ENV, str(now - 1))
    note = sweep_wall_note(now=now)
    assert note == "sweep wall EXPIRED — the job hosting this run is being killed; finalize immediately"


def test_sweep_wall_note_garbage_value_returns_none(monkeypatch):
    monkeypatch.setenv(WALL_DEADLINE_ENV, "abc")
    assert sweep_wall_note() is None


def test_sweep_wall_note_empty_value_returns_none(monkeypatch):
    monkeypatch.setenv(WALL_DEADLINE_ENV, "")
    assert sweep_wall_note() is None


def test_sweep_wall_note_unset_returns_none(monkeypatch):
    monkeypatch.delenv(WALL_DEADLINE_ENV, raising=False)
    assert sweep_wall_note() is None


def test_round_status_message_with_wall_env(monkeypatch):
    monkeypatch.setenv(WALL_DEADLINE_ENV, str(time.time() + 3600))
    msg = round_status_message(0, 300)
    assert "sweep wall ~" in msg["content"]
    assert msg["content"].startswith("Tool round 1/300 · 299 left · ")
