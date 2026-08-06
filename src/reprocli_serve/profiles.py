"""Per-model serving flags — the single source of truth for how a model is served.

A profile is the set of ``vllm serve`` flags a model needs to expose tool calling
and reasoning correctly. The auditor runner never holds these: it is a URL-only
client of an already-served brain and carries only request-time sampling defaults
(``reprocli_vllm/config/cli_args.py``). Sampling params
(temperature/top_p/top_k) are NOT here either: those are request-time fields the
client sends, not server launch flags.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from reprocli_serve.config import DEFAULT_GPU_MEMORY_UTILIZATION, MAX_MODEL_LEN

KIMI_K2_6_MODEL = "moonshotai/Kimi-K2.6"
MINIMAX_COMPILATION_CONFIG = {"cudagraph_mode": "PIECEWISE"}
# vLLM enables the norm_quant / act_quant custom fusions by default for this model
# ("Enabled custom fusions: norm_quant, act_quant, allreduce_rms" at startup). They
# are reported to garble token output for DeepSeek-V4-Flash-0731 on aarch64, at
# temperature 0, with prompt encoding and sampling ruled out (vllm#50773). Turning
# them off is the one serve-side change that addresses the degenerate decoding seen
# in sweep 2818716 (5 of 16 runs collapsed into token repetition; 0 of 64 across the
# qwen3 / minimax / glm52 sweeps on the same node). launch.py drops either key if the
# installed vLLM's PassConfig does not carry it, so an older or newer build still starts.
DEEPSEEK_V4_COMPILATION_CONFIG = {
    "pass_config": {"fuse_norm_quant": False, "fuse_act_quant": False},
}
# Laguna dies at the profiling run without this, behind a misleading async
# CUBLAS_STATUS_EXECUTION_FAILED. The real crash is vLLM fusing RMSNorm into the
# all-reduce and letting FlashInfer pick the mnnvl symmetric-memory backend, which
# the 2xGH200 topology cannot do (illegal memory access in the CUDASymmetricMemory
# dtor). Turning the fusion off is one of the three legs; the other two are
# --disable-custom-all-reduce and VLLM_ALLREDUCE_USE_SYMM_MEM=0, both launch-side.
# See tasks/serve-laguna-s21-vllm-gh200.md (verified 2026-07-21).
LAGUNA_COMPILATION_CONFIG = {"pass_config": {"fuse_allreduce_rms": False}}


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
    default_chat_template_kwargs: str | None = None
    block_size: int | None = None
    kv_cache_dtype: str | None = None
    max_num_seqs: int | None = None
    swap_space_gb: float | None = None
    extra: dict = field(default_factory=dict)


def minimax_profile() -> Profile:
    return Profile(
        name="minimax_m2",
        tensor_parallel_size=4,
        tool_call_parser="minimax_m2",
        reasoning_parser="minimax_m2",
        compilation_config=json.dumps(
            MINIMAX_COMPILATION_CONFIG, separators=(",", ":")
        ),
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
        # a single GH200 (job 2634994). The Medium sweep runs parallel=10 + one
        # audit stream, so 32 is ample headroom while collapsing the mamba-state
        # and capture footprint ~16x.
        max_num_seqs=32,
    )


def deepseek_v4_profile() -> Profile:
    # DeepSeek-V4-Flash: a 158B MoE (~13B active) with the Lightning Indexer
    # (sparse attention) served natively INT8/FP8. On DeltaAI it runs TP=2 on ONE
    # ghx4 node's two-GPU share with thin GPU KV: ~149 GiB of weights (~74 GiB/GPU)
    # for the preview checkpoint, ~155 GiB (~78 GiB/GPU) for the -0731 release,
    # which carries a DSpark speculative-decoding module. Both share this profile
    # (is_deepseek_v4 matches either), verified 2026-07-16 on the preview
    # (tasks/serve-dsv4flash-vllm-gh200.md). Two flags are
    # REQUIRED, not tunable:
    #   - kv_cache_dtype fp8: V4's fp8_ds_mla KV layout asserts on anything else.
    #   - the CPU KV-offload tier and the DeepGEMM LD_LIBRARY_PATH +
    #     VLLM_USE_FLASHINFER_SAMPLER=0 exports live in the sbatch, not here
    #     (they are launch-env, not serve flags).
    # max_model_len 409600 = 400*1024, a whole number of 256-token blocks, just over
    # the 393216 Think Max floor (AA index 40 = Max Effort, the rung that separates
    # V4-Flash from Qwen3.6-27B's 37). The floor is not the target: the repro harness
    # takes its input ceiling from whatever this serves, so serving 393216 exactly
    # left the agent nothing above the floor.
    # NOT the checkpoint's full 1M: at TP=2 the weights take 74 of 95 GiB and GPU KV
    # gets ~10.9, while V4's sparse-MLA workspace scales with max_model_len. 1048576
    # killed the engine mid-prefill in job 2889476 -- an aten::new_empty inside
    # fused_deepseek_v4_qnorm_rope_kv_rope_quant_insert, surfaced through the torch
    # stable-ABI dispatcher as an opaque call failure. Same vLLM 0.26.0 served 393216
    # fine for 27 runs in 2883229, so the window is the variable, not the engine.
    # For an honest 1M, go TP=4 on the full node: ~39 GiB of weights per GPU leaves
    # ~45 GiB for KV instead of 10.9. The Think Max kwargs themselves
    # ride REPROCLI_CHAT_TEMPLATE_KWARGS (client apply_chat_template_kwargs), not a
    # serve flag. The parsers follow notes/References/Model Selection Notes.md
    # ("parser deepseek_v4"). No --tokenizer-mode: vLLM 0.25.1 already logs
    # "Defaulting to tokenizer_mode='deepseek_v4' for DeepseekV4ForCausalLM" and
    # renders through renderers/deepseek_v4.py, which is what makes the Think Max
    # chat_template_kwargs bind (job 2818716 startup log). If a given vLLM build
    # names the tool parser differently (e.g. deepseek_v3), override with the
    # sbatch's TOOL_PARSER/REASONING_PARSER.
    # block_size 256 matches the vLLM recipe. It is what the model's own
    # DEEPSEEK_SPARSE_SWA backend already forces ("Setting kv cache block size to 256"),
    # so this pins the value rather than changing it, the way minimax_m3 pins 128.
    # compilation_config disables the two custom fusions that garble output on this
    # checkpoint (see DEEPSEEK_V4_COMPILATION_CONFIG). Passing any config also routes
    # through launch.py's GH200 guard, which additionally forces fuse_allreduce_rms
    # off (the FlashInfer mnnvl allreduce fusion IMAs here, job 2667723).
    return Profile(
        name="deepseek_v4",
        tensor_parallel_size=2,
        tool_call_parser="deepseek_v4",
        reasoning_parser="deepseek_v4",
        max_model_len=409600,
        kv_cache_dtype="fp8",
        block_size=256,
        compilation_config=json.dumps(
            DEEPSEEK_V4_COMPILATION_CONFIG, separators=(",", ":")
        ),
    )


def laguna_profile() -> Profile:
    # poolside/Laguna-S-2.1: a 117.6B MoE (~8.5B active) agentic-coding specialist,
    # arch LagunaForCausalLM, sliding-window attention with per-head gating in 36 of
    # 48 layers. vLLM 0.25.1 registers the arch and the poolside_v1 parsers natively.
    # This profile targets the INT4 (W4A16) checkpoint: ~72 GiB of weights, so TP=2
    # puts ~36 GiB on each 96 GB GH200 and leaves ~53 GiB/GPU for KV -- roomier than
    # the FP8 checkpoint's ~56.6 GiB/GPU, which is what the runbook verified.
    #
    # max_model_len 262144 is the ceiling, not a choice: only the BF16 repo goes to
    # 1M, and both quantized checkpoints cap at 256K.
    #
    # kv_cache_dtype fp8 is a capacity option, not a requirement (unlike V4's
    # fp8_ds_mla, which asserts): it halves per-token KV so several concurrent 256K
    # transcripts fit alongside the audit stream.
    #
    # default_chat_template_kwargs pins what the checkpoint already declares:
    # generation_config.json ships default_chat_template_kwargs {"enable_thinking": true}
    # and chat_template.jinja does `enable_thinking | default(true)`, so this is a no-op
    # against the shipped template. It is pinned anyway because the two published sources
    # disagree -- the vLLM recipe page states "reasoning is off by default in the chat
    # template" -- and the failure is silent and total: with thinking off the template
    # emits `</think>` instead of `<think>` at the generation-prompt tail and the model
    # answers without reasoning for a whole sweep before anyone notices.
    #
    # This does NOT fix the leak seen in sweep 2859889 (0 of 2136 rounds carried
    # reasoning_content, 2034 had a bare `</think>` in content). That is the opposite
    # problem: thinking is ON, so the template pre-fills `<think>` into the prompt, the
    # model emits only the closing tag, and poolside_v1 never enters the reasoning state.
    # Fixing that needs a parser that handles a pre-filled open tag, plus a harness-side
    # stop on replaying old reasoning -- see the note in reprocli_repro.
    #
    # Laguna has NO DSA indexer, so the deep_gemm / libnvrtc / CXXABI import warnings
    # that matter for V4-Flash are benign here -- vLLM falls back to the TRITON FP8
    # MoE backend and serves correctly. Do not chase them.
    return Profile(
        name="laguna_s21",
        tensor_parallel_size=2,
        tool_call_parser="poolside_v1",
        reasoning_parser="poolside_v1",
        max_model_len=262144,
        gpu_memory_utilization=0.93,
        kv_cache_dtype="fp8",
        compilation_config=json.dumps(
            LAGUNA_COMPILATION_CONFIG, separators=(",", ":")
        ),
        default_chat_template_kwargs=json.dumps(
            {"enable_thinking": True}, separators=(",", ":")
        ),
    )


@dataclass(frozen=True)
class _Family:
    """One rung of the ``resolve_profile`` ladder.

    A model is recognized either by its id/path (``name_matches``) or, for a local
    checkpoint whose directory name says nothing useful, by the ``architectures``
    its ``config.json`` declares (``arch_prefix``).
    """

    name_matches: Callable[[str], bool]
    arch_prefix: str
    profile: Callable[[], Profile]


def _named(marker: str) -> Callable[[str], bool]:
    """Match any model id/path containing ``marker``."""
    return lambda name: marker in name


def _is_kimi_name(name: str) -> bool:
    # Kimi matches the exact repo id / trailing path segment rather than a
    # substring, so a neighbouring checkpoint directory does not claim it.
    return name == KIMI_K2_6_MODEL or name.endswith("/Kimi-K2.6")


# ORDER IS LOAD-BEARING. The first family that matches wins, and MiniMax-M3 must be
# tested before the MiniMax fallback below: M3 takes the minimax_m3 parsers and the
# mandatory --block-size 128, not M2's parsers and cudagraph config.
_FAMILIES: tuple[_Family, ...] = (
    _Family(_is_kimi_name, "KimiK25", kimi_profile),
    _Family(_named("MiniMax-M3"), "MiniMaxM3", minimax_m3_profile),
    _Family(_named("DeepSeek-V4"), "DeepseekV4", deepseek_v4_profile),
    _Family(_named("Qwen3"), "Qwen3", qwen3_profile),
    _Family(_named("Laguna"), "Laguna", laguna_profile),
)


def _architectures(model: str) -> list[str]:
    """``architectures`` declared by a local checkpoint's config.json.

    Empty for a bare HF id, an absent file, or anything unreadable — the caller
    then falls through to the next family.
    """
    config_path = Path(model) / "config.json"
    if not config_path.exists():
        return []
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [str(name) for name in config.get("architectures") or []]


def resolve_profile(model: str) -> Profile:
    """Pick the serving profile for ``model`` (a HF id or a local path).

    config.json is read at most once, lazily: a model recognized by name never
    touches the disk at all.
    """
    name = model.rstrip("/")
    architectures: list[str] | None = None
    for family in _FAMILIES:
        if family.name_matches(name):
            return family.profile()
        if architectures is None:
            architectures = _architectures(model)
        if any(arch.startswith(family.arch_prefix) for arch in architectures):
            return family.profile()
    return minimax_profile()
