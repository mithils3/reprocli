from __future__ import annotations

from pathlib import Path

SUPPLEMENT_EXCERPT_CHARS = 12_000
SUPPLEMENT_EXCERPT_FILES = 12
CODE_EVIDENCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cu",
    ".h",
    ".hpp",
    ".ipynb",
    ".jl",
    ".js",
    ".json",
    ".m",
    ".md",
    ".py",
    ".r",
    ".rs",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
CODE_EVIDENCE_FILENAMES = {
    "dockerfile",
    "environment.yml",
    "makefile",
    "pyproject.toml",
    "readme",
    "readme.md",
    "requirements.txt",
    "setup.py",
}


def supplement_text(status: str, source_url: str, files: list[dict]) -> str:
    if not status and not source_url and not files:
        return ""
    lines = [
        "OPENREVIEW_SUPPLEMENT:",
        f"status: {status or 'unknown'}",
        "code_evidence: MRE-relevant supplement code/configs/scripts/notebooks are first-party evidence.",
    ]
    if source_url:
        lines.append(f"source_url: {source_url}")
    if files:
        lines.extend(["files:", *supplement_manifest_lines(files)])
    excerpts = supplement_excerpt_sections(files)
    if excerpts:
        lines.extend(["", "OPENREVIEW_SUPPLEMENT_EXCERPTS:", *excerpts])
    return "\n".join(lines)


def supplement_manifest_lines(files: list[dict]) -> list[str]:
    lines = []
    for item in sorted(files, key=file_path):
        lines.append(f"- {file_path(item)}")
    return lines


def supplement_excerpt_sections(files: list[dict]) -> list[str]:
    sections = []
    for item in sorted(text_files(files), key=excerpt_sort_key)[:SUPPLEMENT_EXCERPT_FILES]:
        path = file_path(item)
        text = str(item.get("text") or "").strip()
        if len(text) > SUPPLEMENT_EXCERPT_CHARS:
            text = text[:SUPPLEMENT_EXCERPT_CHARS] + "\n...[truncated]"
        sections.append(f"### supplement/{path}\n{text}")
    return sections


def text_files(files: list[dict]) -> list[dict]:
    return [item for item in files if item.get("is_text") and item.get("text")]


def excerpt_sort_key(item: dict) -> tuple[bool, str]:
    return (not is_code_evidence_file(item), file_path(item))


def is_code_evidence_file(item: dict) -> bool:
    path = file_path(item).casefold()
    filename = str(item.get("filename") or path.rsplit("/", 1)[-1]).casefold()
    extension = str(item.get("extension") or Path(path).suffix).casefold()
    return (
        extension in CODE_EVIDENCE_EXTENSIONS
        or filename in CODE_EVIDENCE_FILENAMES
        or filename.startswith("readme")
    )


def file_path(item: dict) -> str:
    return str(item.get("relative_path") or item.get("filename") or "unknown")
