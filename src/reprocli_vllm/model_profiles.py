from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import DEFAULT_MODEL, MAX_MODEL_LEN

DEEPSEEK_FLASH_MODEL = DEFAULT_MODEL


@dataclass(frozen=True)
class ModelProfile:
    name: str
    model: str
    tensor_parallel_size: int
    max_model_len: int
    gpu_memory_utilization: float
    tool_call_parser: str
    reasoning_parser: str
    tokenizer_mode: str | None = None
    compilation_config: dict[str, Any] | None = None
    trust_remote_code: bool = False
    kv_cache_dtype: str | None = None
    block_size: int | None = None
    enable_expert_parallel: bool = False
    disable_flashinfer_autotune: bool = False
    default_reasoning_effort: str = "none"
    temperature: float = 0.0
    top_p: float = 1.0


PROFILES = {
    "deepseek_v4_flash": ModelProfile(
        name="deepseek_v4_flash",
        model=DEEPSEEK_FLASH_MODEL,
        tensor_parallel_size=4,
        max_model_len=MAX_MODEL_LEN,
        gpu_memory_utilization=0.92,
        tool_call_parser="deepseek_v4",
        reasoning_parser="deepseek_v4",
        tokenizer_mode="deepseek_v4",
        trust_remote_code=True,
        kv_cache_dtype="fp8",
        block_size=256,
        disable_flashinfer_autotune=True,
        default_reasoning_effort="high",
        temperature=1.0,
        top_p=1.0,
    ),
}


def infer_profile_name(model: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "deepseek_v4_flash"
