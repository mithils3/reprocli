"""The ``run_gpu`` tool schema, split out of ``run_gpu.py`` to keep each file focused.

The handler logic lives in ``run_gpu.py``; this module only builds the JSON schema the
model sees (the per-cluster GPU cap is baked into the descriptions). Kept separate so
``run_gpu.py`` stays under the project's file-size limit.
"""

from __future__ import annotations

from reprocli_vllm.config.config import function_tool

from reprocli_repro.tools.run_gpu import DEFAULT_GPUS, DEFAULT_MINUTES, MAX_MINUTES

__all__ = ["run_gpu_tool"]


def run_gpu_tool(gpus_per_node: int) -> dict:
    """Build the ``run_gpu`` schema, advertising this cluster's per-node GPU cap."""
    return function_tool(
        "run_gpu",
        "Run ONE command on a real GPU (training, evaluation, scoring, verifying the "
        "container's torch.cuda, nvidia-smi). The GPU allocation is HELD across calls: the "
        "first run_gpu acquires it (you may wait in the queue once) and every later "
        "run_gpu runs on the SAME node with NO new queue wait, so install → verify → "
        "run as successive calls. You are billed WALL-CLOCK for the whole time the "
        "allocation is held — gpus x held-time x hw, including while you reason or "
        "install between commands — so set release=true the moment you are done with "
        "the GPU to stop the meter (re-acquire later if you need it again). The command "
        "runs with the workspace as its cwd; cost and remaining budget are returned and "
        "recorded to evidence/. Each result also reports session_remaining_seconds — the "
        "wall left before this allocation hits its `minutes` (--time) cap and SLURM reclaims "
        "the node (losing any unsaved state); when it runs low a session_expiry_warning tells "
        "you to checkpoint to disk and, if you need more time, release and re-acquire.",
        {
            "command": {
                "type": "string",
                "description": "The GPU command to run (e.g. `python train.py ...`). Omit only with release=true to just free the session.",
            },
            "gpus": {
                "type": "integer",
                "default": DEFAULT_GPUS,
                "minimum": 1,
                "maximum": gpus_per_node,
                "description": (
                    f"GPUs to hold (1-{gpus_per_node}, one node); set only on the call that STARTS "
                    "the session. Default to 1 — many real runs are correctly single-GPU and a 1-GPU "
                    "FULL run is a real run, not a smoke test. Take more ONLY when the model/batch "
                    "won't fit in one GPU's memory or a parallelizable run won't finish in your "
                    "wall-clock; throughput then scales with gpus (wall budget ~same)."
                ),
            },
            "minutes": {
                "type": "integer",
                "default": DEFAULT_MINUTES,
                "minimum": 1,
                "maximum": MAX_MINUTES,
                "description": "Max lifetime of the held allocation (SLURM --time) and the budget "
                "pre-authorization; set on the call that starts the session. Pick ~ how long you will hold it.",
            },
            "release": {
                "type": "boolean",
                "default": False,
                "description": "Set true when you are done with the GPU: frees the allocation after "
                "this command (or immediately if no command) so wall-clock billing stops.",
            },
            "partition": {
                "type": "string",
                "description": "SLURM partition (node pool) to allocate on. Omit to use this "
                "cluster's default; call list_partitions to see the alternatives (e.g. a "
                "faster-queueing interactive pool). Takes effect only on the call that STARTS "
                "the session; fixed until you release it.",
            },
        },
        [],  # command is enforced by the handler (it is optional only with release=true)
    )
