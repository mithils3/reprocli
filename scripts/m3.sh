#!/bin/bash
# Serve MiniMaxAI/MiniMax-M3 (MXFP8) on 2x DeltaAI ghx4 nodes (4x GH200 each) and
# publish a routable endpoint other Delta nodes can attach to by URL.
#
# MiniMax-M3 is a 428B-param MoE (~22B active) with MiniMax Sparse Attention (MSA),
# a long (up to 1M-token) context, and a native vision encoder. The MXFP8 weights
# (~428 GB) do not fit in one ghx4 node's 4x96 GB HBM, so this runs TP=4 within
# each node and PP=2 across the two nodes (8 GH200 total) -- the same topology as
# the Kimi-K2.6 multi-node serve.
#
# The M3-specific vLLM flags come from the serving profile
# (src/reprocli_serve/profiles.py -> minimax_m3_profile), which mirrors the
# official recipe at https://recipes.vllm.ai/MiniMaxAI/MiniMax-M3:
#   --block-size 128            MSA sparse/index cache; the default 16 misaligns it
#   --tool-call-parser minimax_m3
#   --reasoning-parser minimax_m3
#   --mm-encoder-tp-mode data   replicate the vision encoder across TP ranks
# reprocli_serve also adds --enable-auto-tool-choice and --trust-remote-code, wires
# the multi-node rendezvous, waits for /health, and writes $ENDPOINT_FILE.
#
# Usage:
#   bash scripts/m3.sh                         # submit the 2-node serve job
#   tail -f slurm-serve-mn-<jobid>.out         # watch for "vLLM server READY"
#   bash scripts/m3_sample_prompts.sh          # then fire sample prompts at it
#
# Override any of these from the environment before running.
set -euo pipefail

export MODEL="${MODEL:-MiniMaxAI/MiniMax-M3-MXFP8}"
export SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M3}"
export ENDPOINT_FILE="${ENDPOINT_FILE:-/projects/bgnp/msalunkhe/endpoints/minimax_m3.json}"
export TP="${TP:-4}"            # tensor parallel within each 4-GPU node
NODES="${NODES:-2}"            # pipeline parallel = number of nodes

# A 428 GB checkpoint streams faster (and works offline) from a local dir. To
# pre-download once, then point MODEL at it:
#   hf download MiniMaxAI/MiniMax-M3-MXFP8 \
#     --local-dir /work/hdd/bfvr/msalunkhe/models/MiniMax-M3-MXFP8
#   export MODEL=/work/hdd/bfvr/msalunkhe/models/MiniMax-M3-MXFP8

echo "Submitting ${NODES}-node MiniMax-M3 serve: model=${MODEL} served=${SERVED_NAME} TP=${TP} PP=${NODES}"
sbatch --nodes="${NODES}" scripts/serve_multinode.sbatch

cat <<EOF

Submitted. Next:
  squeue --me                                  # wait for the job to start
  tail -f slurm-serve-mn-<jobid>.out           # watch for "vLLM server READY"
  cat ${ENDPOINT_FILE}                         # the published base_url
  ENDPOINT_FILE=${ENDPOINT_FILE} bash scripts/m3_sample_prompts.sh

Attach the paper classifier to the running server (model-agnostic, by URL):
  ENDPOINT_FILE=${ENDPOINT_FILE} bash scripts/serve_attach_runner.sh --num-prompts 2
EOF

# --- Reference only: the upstream vLLM "recipe" docker form -------------------
# DeltaAI/NCSA runs native vLLM (not docker); kept here for provenance. On an
# 8-GPU host the recipe is single-node TP=8; the 2-node form below assumes 8 GPUs
# per node. See https://recipes.vllm.ai/MiniMaxAI/MiniMax-M3.
#
#   docker run --gpus all --privileged --ipc=host -p 8000:8000 \
#     -v ~/.cache/huggingface:/root/.cache/huggingface \
#     -e GLOO_SOCKET_IFNAME=$IFACE_NAME -e NCCL_SOCKET_IFNAME=$IFACE_NAME \
#     vllm/vllm-openai:minimax-m3 MiniMaxAI/MiniMax-M3-MXFP8 \
#     --block-size 128 --tensor-parallel-size 8 \
#     --tool-call-parser minimax_m3 --enable-auto-tool-choice \
#     --reasoning-parser minimax_m3
