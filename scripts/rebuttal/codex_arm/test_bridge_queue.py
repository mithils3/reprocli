"""Offline test of the run_gpu bridge: a queued acquire outlives the shim, and the next call reattaches.

    PYTHONPATH=src python scripts/rebuttal/codex_arm/test_bridge_queue.py
"""

import json
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_run as cr  # noqa: E402
from codex_events import Recorder  # noqa: E402

GRANT_AFTER = 3.0
acquisitions = []


def fake_execute(call, ctx):
    """Stands in for the harness handler: the first call waits for a grant, later calls reuse it."""
    args = json.loads(call["function"]["arguments"])
    if ctx.session is None:
        acquisitions.append(args["command"])
        time.sleep(GRANT_AFTER)  # queued in Slurm
        ctx.session = types.SimpleNamespace(started=time.monotonic(), jobid="fake")
    return {"ok": True, "tool": "run_gpu", "command": args["command"], "returncode": 0}


cr.execute_repro_tool_call = fake_execute
root = Path(tempfile.mkdtemp())
io = root / "codex_io"
io.mkdir()
ctx = types.SimpleNamespace(session=None)
rec = Recorder(root, root / "evidence", "gpt-6.1-terra", root / "workspace")
bridge = cr.Bridge(io, ctx, rec)
bridge.start()


def request(rid, command):
    req = bridge.req / f"{rid}.json"
    tmp = bridge.req / f"{rid}.tmp"
    tmp.write_text(json.dumps({"id": rid, "arguments": {"command": command}}))
    tmp.replace(req)


request("a", "step-a")  # the shim that makes this call is killed by Codex's command timeout
time.sleep(1.0)
request("b", "step-b")  # the agent's next run_gpu call, after a timeout
deadline = time.monotonic() + 15
while not (bridge.res / "b.json").exists() and time.monotonic() < deadline:
    time.sleep(0.2)
bridge.stop.set()

checks = {
    "one acquisition for two calls": len(acquisitions) == 1,
    "second call served after the grant": (bridge.res / "b.json").exists(),
    "queue wait recorded (about the grant time)": GRANT_AFTER - 0.5 <= bridge.queue_wait_s <= GRANT_AFTER + 2.0,
}
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"queue_wait_s={bridge.queue_wait_s:.2f} acquisitions={acquisitions}")
sys.exit(0 if all(checks.values()) else 1)
