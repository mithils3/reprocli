from __future__ import annotations

import os
from pathlib import Path


def default_cache_dir(model: str) -> Path | None:
    model_path = Path(model)
    if model_path.is_absolute() or model_path.exists():
        return model_path / "vllm_cache"
    return None


def subprocess_env(cache_dir: Path | None) -> dict[str, str] | None:
    if cache_dir is None:
        return None
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["VLLM_CACHE_ROOT"] = str(cache_dir)
    return env
