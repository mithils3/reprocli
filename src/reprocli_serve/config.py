"""Serving defaults shared across the launcher modules.

These are the defaults the standalone, network-routable ``vllm serve`` uses for
each model; there is no in-process server left to mirror.
"""

from __future__ import annotations

# Network defaults. Bind to all interfaces so other nodes can reach the server;
# the *advertised* address is resolved separately (see network.py) from the
# high-speed fabric interface so the published URL is the one peers should dial.
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
# DeltaAI compute nodes have 4x 200GbE HPE Slingshot 11 NICs: hsn0..hsn3. Any one
# of them gives a routable IP for the API; for NCCL data, the cluster guidance is
# the prefix NCCL_SOCKET_IFNAME=hsn (uses all four). We publish the first hsn that
# has an address, preferring hsn0.
DEFAULT_FABRIC_IFACE = "hsn0"
FABRIC_IFACES = ["hsn0", "hsn1", "hsn2", "hsn3"]

# How long to wait for /health after launch before giving up.
SERVER_STARTUP_TIMEOUT = 1800.0
HEALTH_POLL_INTERVAL = 5.0

# Matches reprocli_vllm.config.config.MAX_MODEL_LEN.
MAX_MODEL_LEN = 196608
DEFAULT_GPU_MEMORY_UTILIZATION = 0.95

# The published endpoint contract. The reprocli runner reads ``base_url`` from
# this file when $REPROCLI_ENDPOINT_FILE points at it.
DEFAULT_ENDPOINT_FILENAME = "vllm_endpoint.json"

# Environment-variable names that form the cross-repo seam.
ENV_ENDPOINT_FILE = "REPROCLI_ENDPOINT_FILE"
