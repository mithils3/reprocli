"""Entry point: launch vLLM, wait for health, publish the URL, then block.

    python -m reprocli_serve --model /path/to/MiniMax-M2.7 --port 8000

On a head rank this prints the routable base URL and writes the endpoint file
once ``/health`` is green; it then waits on the server process and removes the
endpoint file on exit. Headless (non-head) ranks just exec vLLM and wait.
"""

from __future__ import annotations

import os
import signal
import sys
import types

from reprocli_serve import network
from reprocli_serve.args import parse_args
from reprocli_serve.endpoint import build_payload, remove_endpoint, write_endpoint
from reprocli_serve.launch import build_serve_command, start_process
from reprocli_serve.profiles import resolve_profile
from reprocli_serve.wait import wait_until_ready


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    profile = resolve_profile(args.model)
    command = build_serve_command(args, profile)
    process = start_process(command)

    def _forward(signum: int, _frame: types.FrameType | None) -> None:
        process.send_signal(signum)

    signal.signal(signal.SIGINT, _forward)
    signal.signal(signal.SIGTERM, _forward)

    if args.headless:
        # Non-head rank: no API to publish or probe; just shadow the process.
        return process.wait()

    published = False
    try:
        wait_until_ready(f"http://127.0.0.1:{args.port}/health", process)
        host = network.advertised_host(args.advertise_ip, args.iface)
        url = network.base_url(host, args.port)
        payload = build_payload(
            base_url=url,
            host=host,
            port=args.port,
            served_model_name=args.served_model_name,
            model_path=args.model,
            node=os.environ.get("SLURMD_NODENAME", ""),
            job_id=os.environ.get("SLURM_JOB_ID", ""),
        )
        write_endpoint(args.endpoint_file, payload)
        published = True
        _announce(url, args)
        return process.wait()
    finally:
        if published:
            remove_endpoint(args.endpoint_file)


def _announce(url: str, args) -> None:
    line = "=" * 72
    print(
        f"\n{line}\n"
        f"vLLM server READY\n"
        f"  base url        : {url}\n"
        f"  served model    : {args.served_model_name}\n"
        f"  endpoint file   : {args.endpoint_file}\n"
        f"  attach a runner : --vllm-server-url {url} --model {args.served_model_name}\n"
        f"  or export       : export REPROCLI_SERVER_URL={url}\n"
        f"{line}\n",
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
