"""Build and start the ``vllm serve`` subprocess.

The command is assembled from the model's serve profile and binds a routable
host/port (and, for multi-node, wires the rendezvous flags).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys

from reprocli_serve.profiles import Profile


def build_serve_command(args: argparse.Namespace, profile: Profile) -> list[str]:
    tp = args.tensor_parallel_size or profile.tensor_parallel_size
    command = [
        args.vllm_bin,
        "serve",
        args.model,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--served-model-name",
        args.served_model_name,
        "--tensor-parallel-size",
        str(tp),
        "--max-model-len",
        str(args.max_model_len or profile.max_model_len),
        "--gpu-memory-utilization",
        str(args.gpu_memory_utilization or profile.gpu_memory_utilization),
        "--tool-call-parser",
        args.tool_call_parser or profile.tool_call_parser,
        "--reasoning-parser",
        args.reasoning_parser or profile.reasoning_parser,
        "--enable-auto-tool-choice",
        # Without this, vLLM omits usage.prompt_tokens_details entirely, so every
        # response reports cached_tokens=0 even when prefix caching is hitting. The
        # KV reuse happens regardless (enable_prefix_caching defaults to True); this
        # flag is purely what makes the cache-hit count observable downstream.
        "--enable-prompt-tokens-details",
    ]
    if args.trust_remote_code or profile.trust_remote_code:
        command.append("--trust-remote-code")
    mm_mode = args.mm_encoder_tp_mode or profile.mm_encoder_tp_mode
    if mm_mode:
        command.extend(["--mm-encoder-tp-mode", mm_mode])
    compilation = args.compilation_config or profile.compilation_config
    if compilation:
        command.extend(["--compilation-config", _supported_compilation_config(compilation)])
    # Server-side default for the chat template's render-time switches (thinking on/off,
    # effort ladders). Per-request REPROCLI_CHAT_TEMPLATE_KWARGS still wins where it is
    # set; this is the floor for the requests that omit them.
    template_kwargs = args.default_chat_template_kwargs or profile.default_chat_template_kwargs
    if template_kwargs:
        command.extend(["--default-chat-template-kwargs", template_kwargs])
    if args.distributed_executor_backend:
        command.extend(["--distributed-executor-backend", args.distributed_executor_backend])
    kv_cache_dtype = args.kv_cache_dtype or profile.kv_cache_dtype
    if kv_cache_dtype:
        command.extend(["--kv-cache-dtype", kv_cache_dtype])
    block_size = args.block_size or profile.block_size
    if block_size:
        command.extend(["--block-size", str(block_size)])
    swap_space = args.swap_space if args.swap_space is not None else profile.swap_space_gb
    if swap_space is not None:
        command.extend(["--swap-space", str(swap_space)])
    if profile.max_num_seqs:
        command.extend(["--max-num-seqs", str(profile.max_num_seqs)])
    if args.enable_expert_parallel or profile.enable_expert_parallel:
        command.append("--enable-expert-parallel")
    if args.tokenizer_mode:
        command.extend(["--tokenizer-mode", args.tokenizer_mode])
    if args.structured_outputs_backend:
        command.extend(["--structured-outputs-config.backend", args.structured_outputs_backend])
    command.extend(_dataparallel_flags(args))
    command.extend(_multinode_flags(args))
    command.extend(_supported_extra_args(args.extra_vllm_args))
    return command


def _supported_extra_args(extra: list[str]) -> list[str]:
    """Drop pass-through flags this GPU cannot run.

    One launch-time rewrite so far, the extra-args sibling of the ``pass_config``
    rewrites below:

    - ``--moe-backend deep_gemm_mega_moe`` is dropped below SM100. It is the
      vLLM recipe's Blackwell FP8 MoE kernel, and on a Hopper card vLLM raises
      ``NotImplementedError("DeepGEMM MegaMoE requires SM100 GPUs.")`` only
      AFTER loading all 48 checkpoint shards, so the serve dies ~3 minutes in
      and the allocation is spent (job 2858259 on 2xGH200). The Hopper port is
      an unmerged RFC (vllm#42284), blocked on an upstream DeepGEMM PR.
      Dropping the flag lands on vLLM's auto MoE-backend selection, which is
      what the official recipe does on Hopper and what every verified GH200
      serve of this model has run. Pass a non-mega backend explicitly to
      override; other ``--moe-backend`` values are left alone.
    """
    kept: list[str] = []
    index = 0
    while index < len(extra):
        token = extra[index]
        value = None
        width = 1
        if token == "--moe-backend" and index + 1 < len(extra):
            value = extra[index + 1]
            width = 2
        elif token.startswith("--moe-backend="):
            value = token.split("=", 1)[1]
        if value == "deep_gemm_mega_moe" and _below_sm100():
            print(
                "reprocli_serve: dropping --moe-backend deep_gemm_mega_moe "
                "(SM100-only; vLLM auto-selects the MoE backend on this GPU — "
                "pass a non-mega backend explicitly to override)",
                file=sys.stderr,
                flush=True,
            )
            index += width
            continue
        kept.append(token)
        index += 1
    return kept


def _below_sm100() -> bool:
    """True only when the GPU is determinably pre-Blackwell (compute major < 10).

    An undeterminable capability (no torch, no CUDA, a probe that raises) returns
    False: leave the operator's flag alone and let vLLM be the authority. torch is
    imported lazily so a command without a mega-MoE flag never pays for it.
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        return torch.cuda.get_device_capability(0)[0] < 10
    except Exception:
        return False


def _supported_compilation_config(compilation: str) -> str:
    """Normalize ``pass_config`` against the installed vLLM.

    Two launch-time rewrites, both keyed off the installed ``PassConfig`` so
    they track the venv instead of being edited into every sbatch script:

    - Unknown keys are dropped. vLLM deletes a pass flag once the fusion
      becomes automatic (e.g. the MiniMax QK-norm pass), and an unknown key
      makes ``vllm serve`` exit 2 on a pydantic validation error before ready.
      Older builds still need the explicit flag for throughput.
    - ``fuse_allreduce_rms`` defaults to OFF. vLLM 0.25 enables the FlashInfer
      allreduce+RMSNorm fusion by default for TP compiles, and the mnnvl
      backend it auto-selects on GH200 hits a CUDA illegal memory access in the
      profile run (job 2667723 died before ready on the 2-GPU ghx4 share). Set
      the key explicitly in the config to opt back in on a build that fixed it.
    """
    try:
        config = json.loads(compilation)
    except json.JSONDecodeError:
        return compilation
    if not isinstance(config, dict):
        return compilation
    known = _known_pass_config_fields()
    if known is None:
        return compilation
    raw_passes = config.get("pass_config")
    passes = dict(raw_passes) if isinstance(raw_passes, dict) else {}
    changed = False
    dropped = sorted(set(passes) - known)
    if dropped:
        passes = {key: value for key, value in passes.items() if key in known}
        changed = True
        print(
            "reprocli_serve: dropping pass_config keys this vLLM does not support: "
            + " ".join(dropped),
            file=sys.stderr,
            flush=True,
        )
    if "fuse_allreduce_rms" in known and "fuse_allreduce_rms" not in passes:
        passes["fuse_allreduce_rms"] = False
        changed = True
        print(
            "reprocli_serve: disabling fuse_allreduce_rms (FlashInfer mnnvl "
            "allreduce fusion IMAs on GH200; set it in --compilation-config to "
            "opt back in)",
            file=sys.stderr,
            flush=True,
        )
    if not changed:
        return compilation
    if passes:
        config["pass_config"] = passes
    else:
        config.pop("pass_config", None)
    return json.dumps(config, separators=(",", ":"))


def _known_pass_config_fields() -> set[str] | None:
    """Field names of the installed vLLM's PassConfig, or None if undeterminable."""
    try:
        from vllm.config import PassConfig
    except Exception:
        return None
    fields = getattr(PassConfig, "model_fields", None)
    if fields:
        return set(fields)
    try:
        return {field.name for field in dataclasses.fields(PassConfig)}
    except Exception:
        return None


def _dataparallel_flags(args: argparse.Namespace) -> list[str]:
    """Data-parallel rendezvous flags (wide-EP), set only for a multi-node DP serve."""
    flags: list[str] = []
    if not (args.data_parallel_size and args.data_parallel_size > 1):
        return flags
    flags.extend(["--data-parallel-size", str(args.data_parallel_size)])
    if args.data_parallel_size_local is not None:
        flags.extend(["--data-parallel-size-local", str(args.data_parallel_size_local)])
    if args.data_parallel_start_rank is not None:
        flags.extend(["--data-parallel-start-rank", str(args.data_parallel_start_rank)])
    if args.data_parallel_address:
        flags.extend(["--data-parallel-address", args.data_parallel_address])
    if args.data_parallel_rpc_port:
        flags.extend(["--data-parallel-rpc-port", str(args.data_parallel_rpc_port)])
    return flags


def _multinode_flags(args: argparse.Namespace) -> list[str]:
    """Pipeline-parallel rendezvous flags, set only for a multi-node serve."""
    flags: list[str] = []
    if args.pipeline_parallel_size and args.pipeline_parallel_size > 1:
        flags.extend(["--pipeline-parallel-size", str(args.pipeline_parallel_size)])
    if args.nnodes and args.nnodes > 1:
        flags.extend(["--nnodes", str(args.nnodes)])
    if args.node_rank is not None:
        flags.extend(["--node-rank", str(args.node_rank)])
    if args.master_addr:
        flags.extend(["--master-addr", args.master_addr])
    if args.headless:
        flags.append("--headless")
    return flags


def start_process(
    command: list[str], env: dict[str, str] | None = None
) -> subprocess.Popen:
    """Launch vLLM, inheriting stdout/stderr so logs land in the Slurm log.

    ``env`` of None inherits this process's environment unchanged; a dict
    replaces it wholesale (callers pass a copy of ``os.environ`` plus overrides).
    """
    print("Starting vLLM server: " + " ".join(command), file=sys.stderr, flush=True)
    return subprocess.Popen(command, env=env)
