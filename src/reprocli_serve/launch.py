"""Build and start the ``vllm serve`` subprocess.

The command mirrors what the reprocli runner's embedded server passed, so the
served model behaves the same; the difference is purely topological — this binds
a routable host/port and (for multi-node) wires the rendezvous flags.
"""

from __future__ import annotations

import argparse
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
        command.extend(["--compilation-config", compilation])
    if args.distributed_executor_backend:
        command.extend(["--distributed-executor-backend", args.distributed_executor_backend])
    kv_cache_dtype = args.kv_cache_dtype or profile.kv_cache_dtype
    if kv_cache_dtype:
        command.extend(["--kv-cache-dtype", kv_cache_dtype])
    block_size = args.block_size or profile.block_size
    if block_size:
        command.extend(["--block-size", str(block_size)])
    if args.enable_expert_parallel or profile.enable_expert_parallel:
        command.append("--enable-expert-parallel")
    if args.tokenizer_mode:
        command.extend(["--tokenizer-mode", args.tokenizer_mode])
    if args.structured_outputs_backend:
        command.extend(["--structured-outputs-config.backend", args.structured_outputs_backend])
    command.extend(_dataparallel_flags(args))
    command.extend(_multinode_flags(args))
    command.extend(args.extra_vllm_args)
    return command


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
