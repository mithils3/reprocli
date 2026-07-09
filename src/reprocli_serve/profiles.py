"""Per-model serving flags — the single source of truth for how a model is served.

A profile is the set of ``vllm serve`` flags a model needs to expose tool calling
and reasoning correctly. The auditor runner never holds these: it is a URL-only
client of an already-served brain and carries only request-time sampling defaults
(``reprocli_vllm/config/minimax_defaults.py``). Sampling params
(temperature/top_p/top_k) are NOT here either: those are request-time fields the
client sends, not server launch flags.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from reprocli_serve.config import DEFAULT_GPU_MEMORY_UTILIZATION, MAX_MODEL_LEN

KIMI_K2_6_MODEL = "moonshotai/Kimi-K2.6"
MINIMAX_M2_MODEL = "MiniMaxAI/MiniMax-M2.7"
MINIMAX_COMPILATION_CONFIG = {"cudagraph_mode": "PIECEWISE"}
QWEN3_MODEL = "Qwen/Qwen3.6-27B-FP8"


@dataclass
class Profile:
    """vLLM serve flags for one model family."""

    name: str
    tensor_parallel_size: int
    tool_call_parser: str
    reasoning_parser: str
    max_model_len: int = MAX_MODEL_LEN
    gpu_memory_utilization: float = DEFAULT_GPU_MEMORY_UTILIZATION
    trust_remote_code: bool = True
    enable_expert_parallel: bool = False
    mm_encoder_tp_mode: str | None = None
    compilation_config: str | None = None
    block_size: int | None = None
    kv_cache_dtype: str | None = None
    max_num_seqs: int | None = None
    extra: dict = field(default_factory=dict)


def minimax_profile() -> Profile:
    return Profile(
        name="minimax_m2",
        tensor_parallel_size=4,
        tool_call_parser="minimax_m2",
        reasoning_parser="minimax_m2",
        compilation_config=json.dumps(MINIMAX_COMPILATION_CONFIG, separators=(",", ":")),
    )


def kimi_profile() -> Profile:
    # 8 GPUs of tensor parallel; on 4-GPU/node DeltaAI this is TP=4 + PP=2 across
    # two nodes (see scripts/serve/serve_multinode.sbatch). The parser flags are the
    # invariant; tensor/pipeline parallel are set by the launcher for the layout.
    return Profile(
        name="kimi_k2",
        tensor_parallel_size=8,
        tool_call_parser="kimi_k2",
        reasoning_parser="kimi_k2",
        mm_encoder_tp_mode="data",
    )


def minimax_m3_profile() -> Profile:
    # MiniMax-M3: a 428B-param MoE (~22B active) with MiniMax Sparse Attention
    # (MSA) and a native vision encoder. --block-size 128 is MANDATORY: MSA's
    # sparse/index cache is sized to 128, and the vLLM default (16) misaligns the
    # sparse-attention indexing. The parsers are minimax_m3 (NOT minimax_m2), and
    # M3 does not take M2's compilation-config. On DeltaAI's 4-GPU ghx4 nodes the
    # layout is plain TP=8 spanning two nodes (inter-node TP over the Slingshot
    # fabric); the launcher wires the cross-node rendezvous (see
    # scripts/minimax_m3/paper_classification_minimax_m3.sbatch). Expert parallel
    # is left OFF: EP would shard whole experts across all 8 ranks, putting the
    # MoE all-to-all on the inter-node socket fabric on top of the TP all-reduce;
    # with EP off the experts are TP-sharded instead and the MoE rides the same
    # all-reduce as the rest of the model. Pass --enable-expert-parallel at the
    # CLI to opt back in. kv_cache_dtype fp8 buys a ~1.5x KV pool (a recipe
    # option) for more concurrent requests / longer context at the same HBM.
    return Profile(
        name="minimax_m3",
        tensor_parallel_size=8,
        tool_call_parser="minimax_m3",
        reasoning_parser="minimax_m3",
        mm_encoder_tp_mode="data",
        block_size=128,
        kv_cache_dtype="fp8",
    )


def qwen3_profile() -> Profile:
    # Qwen3.6-27B: the flagship *dense* (27B) Qwen3.6 model. It uses gated delta
    # networks (a Mamba-style hybrid attention) and a native vision encoder, and
    # serves 262K context. On DeltaAI's GH200 the FP8 checkpoint (~33 GB weights)
    # fits a SINGLE GPU, so this is a plain TP=1 serve (unlike the 4-8 GPU MoE
    # profiles above). The parsers are the Qwen3 family's: qwen3_coder for tool
    # calls, qwen3 for reasoning. --mm-encoder-tp-mode data keeps the vision
    # encoder replicated per rank (a no-op at TP=1, kept to match the vLLM recipe
    # so scaling to TP>1 stays correct). kv_cache_dtype fp8 buys a bigger KV pool
    # (more concurrent requests / longer context) at the same HBM. We leave
    # compilation_config unset: the minimax cudagraph tweak does not apply, and
    # forcing PIECEWISE cudagraph can trip Qwen3.6's Mamba-cache sizing.
    return Profile(
        name="qwen3",
        tensor_parallel_size=1,
        tool_call_parser="qwen3_coder",
        reasoning_parser="qwen3",
        max_model_len=262144,  # Qwen3.6-27B's native context; fp8 KV cache fits it on one GH200.
        mm_encoder_tp_mode="data",
        kv_cache_dtype="fp8",
        # Qwen3.6 is a gated-delta/Mamba hybrid: a per-sequence recurrent state
        # cache is allocated for every concurrent seq. At 512 that state (plus the
        # 1->512 cudagraph capture range) OOM-kills the engine during profiling on
        # a single GH200 (job 2634994). The sweep runs parallel=6 + one audit
        # stream, so 32 is ample headroom while collapsing the mamba-state and
        # capture footprint ~16x.
        max_num_seqs=32,
    )


def is_qwen3(model: str) -> bool:
    if "Qwen3" in model.rstrip("/"):
        return True
    config_path = Path(model) / "config.json"
    if not config_path.exists():
        return False
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    architectures = config.get("architectures") or []
    return any(str(name).startswith("Qwen3") for name in architectures)


def is_kimi_k2_6(model: str) -> bool:
    if model == KIMI_K2_6_MODEL or model.rstrip("/").endswith("/Kimi-K2.6"):
        return True
    config_path = Path(model) / "config.json"
    if not config_path.exists():
        return False
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    architectures = config.get("architectures") or []
    return any(str(name).startswith("KimiK25") for name in architectures)


def is_minimax_m3(model: str) -> bool:
    if "MiniMax-M3" in model.rstrip("/"):
        return True
    config_path = Path(model) / "config.json"
    if not config_path.exists():
        return False
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    architectures = config.get("architectures") or []
    return any(str(name).startswith("MiniMaxM3") for name in architectures)


def resolve_profile(model: str) -> Profile:
    """Pick the serving profile for ``model`` (a HF id or a local path)."""
    if is_kimi_k2_6(model):
        return kimi_profile()
    if is_minimax_m3(model):
        return minimax_m3_profile()
    if is_qwen3(model):
        return qwen3_profile()
    return minimax_profile()
