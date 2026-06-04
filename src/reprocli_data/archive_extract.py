from __future__ import annotations

import io
import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from .arxiv_source_download import write_single_source_file


def unpack_archive(data: bytes, output_dir: Path) -> int:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return extract_zip_members(archive, output_dir)
    except zipfile.BadZipFile:
        pass
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            return extract_tar_members(archive, output_dir)
    except tarfile.TarError:
        return write_single_source_file(data, output_dir, "supplementary_material.bin")


def extract_zip_members(archive: zipfile.ZipFile, output_dir: Path) -> int:
    files_written = 0
    for info in archive.infolist():
        target = safe_archive_target(output_dir, info.filename)
        if target is None or info.is_dir():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as handle:
            shutil.copyfileobj(source, handle)
        files_written += 1
    return files_written


def extract_tar_members(archive: tarfile.TarFile, output_dir: Path) -> int:
    files_written = 0
    for member in archive.getmembers():
        target = safe_archive_target(output_dir, member.name)
        if target is None:
            continue
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            source = archive.extractfile(member)
            if source is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            files_written += 1
    return files_written


def safe_archive_target(output_dir: Path, member_name: str) -> Path | None:
    pure_path = PurePosixPath(member_name.replace("\\", "/"))
    if pure_path.is_absolute() or ".." in pure_path.parts:
        return None
    parts = [part for part in pure_path.parts if part not in {"", "."}]
    return output_dir.joinpath(*parts) if parts else None
