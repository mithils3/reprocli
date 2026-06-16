"""Tests for the audit run-directory tools: list/read/bash/python + path safety."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reprocli_vllm.papers import Paper  # noqa: E402
from reprocli_vllm.tools.run_dir_tools import (  # noqa: E402
    list_run_files,
    read_run_file,
    run_bash,
    run_dir_manifest,
    run_python,
)
from reprocli_vllm.tools.web_tools import execute_tool_call  # noqa: E402


def _run_dir(tmp_path: Path) -> Path:
    run = tmp_path / "2505.11483"
    run.mkdir()
    (run / "optimizer.log").write_text("peak_mem_usage: 64210\nconverged\n", encoding="utf-8")
    (run / "opt_result.json").write_text('{"peak_mem_usage": 64210}', encoding="utf-8")
    return run


def test_list_run_files(tmp_path):
    run = _run_dir(tmp_path)
    result = list_run_files({}, run)
    assert result["ok"]
    names = {entry["path"] for entry in result["entries"]}
    assert {"optimizer.log", "opt_result.json"} <= names


def test_read_run_file(tmp_path):
    run = _run_dir(tmp_path)
    result = read_run_file({"path": "optimizer.log"}, run)
    assert result["ok"]
    assert "peak_mem_usage: 64210" in result["text"]


def test_read_run_file_blocks_traversal(tmp_path):
    run = _run_dir(tmp_path)
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    result = read_run_file({"path": "../secret.txt"}, run)
    assert result["ok"] is False
    assert "Unsafe path" in result["error"] or "escapes" in result["error"]


def test_bash_runs_in_run_dir(tmp_path):
    run = _run_dir(tmp_path)
    result = run_bash({"command": "grep -c peak_mem_usage optimizer.log"}, run)
    assert result["ok"]
    assert result["stdout"].strip() == "1"


def test_python_is_stubbed(tmp_path):
    run = _run_dir(tmp_path)
    result = run_python({"code": "print(1)"}, run)
    assert result["ok"] is False
    assert "not implemented" in result["error"].lower()


def test_manifest_lists_files(tmp_path):
    run = _run_dir(tmp_path)
    manifest = run_dir_manifest(run)
    assert "optimizer.log" in manifest
    assert "opt_result.json" in manifest


def test_manifest_missing_dir_is_unverifiable(tmp_path):
    manifest = run_dir_manifest(tmp_path / "does_not_exist")
    assert "unverifiable" in manifest


def test_dispatch_routes_audit_tool_with_paper_run_dir(tmp_path):
    run = _run_dir(tmp_path)
    paper = Paper(arxiv_id="2505.11483", run_dir=str(run))
    call = {"function": {"name": "read_run_file", "arguments": {"path": "opt_result.json"}}}
    result = execute_tool_call(call, paper=paper)
    assert result["ok"]
    assert "64210" in result["text"]


def test_dispatch_audit_tool_without_run_dir_errors():
    paper = Paper(arxiv_id="2505.11483")  # no run_dir bound
    call = {"function": {"name": "list_run_files", "arguments": {}}}
    result = execute_tool_call(call, paper=paper)
    assert result["ok"] is False
    assert "run directory" in result["error"]
