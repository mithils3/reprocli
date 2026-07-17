"""Command-line arguments for ``python -m reprocli_serve``."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from reprocli_serve.config import (
    DEFAULT_ENDPOINT_FILENAME,
    DEFAULT_FABRIC_IFACE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENV_ENDPOINT_FILE,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reprocli_serve",
        description="Stand up a vLLM chat-completions server other nodes can reach.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="HF id or local path, e.g. /work/nvme/bfvr/msalunkhe/MiniMax-M2.7.",
    )
    parser.add_argument(
        "--served-model-name",
        help="Name clients pass as 'model' (default: the --model value).",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address (default: 0.0.0.0).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port (default: 8000).")

    # Address discovery for the *published* URL.
    parser.add_argument(
        "--advertise-ip",
        help="Force the host in the published URL (default: discover from --iface).",
    )
    parser.add_argument(
        "--iface",
        default=DEFAULT_FABRIC_IFACE,
        help=f"Fabric interface to read the routable IP from (default: {DEFAULT_FABRIC_IFACE}).",
    )
    parser.add_argument(
        "--endpoint-file",
        type=Path,
        default=Path(os.environ.get(ENV_ENDPOINT_FILE, DEFAULT_ENDPOINT_FILENAME)),
        help=(
            "Where to publish the endpoint JSON so consumers can find the URL "
            f"(default: ${ENV_ENDPOINT_FILE} or ./{DEFAULT_ENDPOINT_FILENAME})."
        ),
    )

    # Profile overrides (None => use the model's profile default).
    parser.add_argument("--tensor-parallel-size", type=int)
    parser.add_argument("--pipeline-parallel-size", type=int)
    parser.add_argument(
        "--enable-expert-parallel",
        action="store_true",
        help="Shard MoE experts across the parallel group (instead of replicating "
        "them per TP rank). An alternative to pipeline parallelism for MoE models.",
    )
    parser.add_argument("--max-model-len", type=int)
    parser.add_argument("--gpu-memory-utilization", type=float)
    parser.add_argument("--tool-call-parser")
    parser.add_argument("--reasoning-parser")
    parser.add_argument("--mm-encoder-tp-mode")
    parser.add_argument("--compilation-config")
    parser.add_argument("--distributed-executor-backend", choices=("mp", "ray"))
    parser.add_argument("--kv-cache-dtype")
    parser.add_argument("--block-size", type=int)
    parser.add_argument(
        "--swap-space",
        type=float,
        help="GiB of pinned host RAM for preempted-KV offload (0 disables; "
        "unset falls back to the profile, then vLLM's default).",
    )
    parser.add_argument("--tokenizer-mode")
    parser.add_argument("--structured-outputs-backend")
    parser.add_argument("--trust-remote-code", action="store_true")

    # Multi-node rendezvous (one process per node; only rank 0 serves the API).
    parser.add_argument("--nnodes", type=int)
    parser.add_argument("--node-rank", type=int)
    parser.add_argument("--master-addr")

    # Data-parallel rendezvous (wide-EP: TP stays intra-node, DP spans nodes, and
    # --enable-expert-parallel shards the MoE across all DP*TP ranks). An
    # alternative to pipeline parallel for spanning nodes without inter-node TP.
    parser.add_argument("--data-parallel-size", type=int)
    parser.add_argument("--data-parallel-size-local", type=int)
    parser.add_argument("--data-parallel-start-rank", type=int)
    parser.add_argument("--data-parallel-address")
    parser.add_argument("--data-parallel-rpc-port", type=int)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run a non-head rank: no API, no health wait, no endpoint publish.",
    )

    parser.add_argument("--vllm-bin", default="vllm", help="vLLM CLI binary (default: vllm).")
    parser.add_argument(
        "extra_vllm_args",
        nargs="*",
        help="Extra args forwarded verbatim to 'vllm serve' (after a '--').",
    )

    args = parser.parse_args(argv)
    if not args.served_model_name:
        args.served_model_name = args.model
    if args.port < 1 or args.port > 65535:
        parser.error("--port must be in 1..65535")
    return args
