"""Bash environment for mini-SWE-agent 2.4.6 that runs each action in the thin harness's Apptainer sandbox.

Copied from the Distillation runner's mini_apptainer.py (read only) and changed to match reprocli's workspace_bash:
  - each action is one `apptainer exec` built by reprocli_repro.sandbox.Sandbox.wrap_argv, the argv workspace_bash
    runs: --cleanenv --no-home --pwd /repro/workspace, the same binds, the host's network (no --net flag);
  - no Apptainer instance and no SWE-bench history cleanup: the thin harness has neither;
  - while an action runs, service() is called about once a second, so a run_gpu request from the sandbox is served
    on the host (miniswe_run.Mailbox) while the action waits.
Kept from the copy: a timed-out action is killed with its whole process tree, output goes to a file and only the
two ends of a long output stay in memory (read_output), and a submission line ends the run (submits).
"""
import codecs
import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from minisweagent.exceptions import Submitted

from reprocli_repro.sandbox import Sandbox

SUBMIT = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
OUTPUT_KEEP = 32_768
MARK = "\n[miniswe kept the first and the last {keep} bytes of {size} bytes, {chars} characters]\n"
POLL_S = 1.0
RUN_GPU_CALL = re.compile(r"(^|[;&|(]\s*)run_gpu(\s|$)")


class CutOutput(str):
    """The two ends of an output too long to keep. len() gives the characters of the full output."""

    def __new__(cls, text, chars):
        self = super().__new__(cls, text)
        self.chars = chars
        return self

    def __len__(self):
        return self.chars

    def __getnewargs__(self):
        return str.__str__(self), self.chars


def submits(text, returncode):
    """True when mini takes this output as the submission. Same test as DockerEnvironment."""
    lines = text.lstrip().splitlines()
    return bool(lines) and lines[0].strip() == SUBMIT and returncode == 0


def read_output(out, returncode=0):
    """Text of the open file `out`, and its size and characters when it was cut (else {})."""
    size = os.fstat(out.fileno()).st_size
    out.seek(0)
    first = out.read(min(size, OUTPUT_KEEP))
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    head = decoder.decode(first)
    if size <= 2 * OUTPUT_KEEP or submits(head, returncode):
        return head + decoder.decode(out.read(size - len(first)), final=True), {}
    chars, left = len(head), size - len(first)
    while left > 0 and (piece := out.read(min(left, 1 << 20))):
        left -= len(piece)
        chars += len(decoder.decode(piece))
    chars += len(decoder.decode(b"", final=True))
    out.seek(size - OUTPUT_KEEP)
    tail = out.read(OUTPUT_KEEP).decode("utf-8", errors="replace")
    text = head + MARK.format(keep=OUTPUT_KEEP, size=size, chars=chars) + tail
    return CutOutput(text, chars), {"output_bytes": size, "output_chars": chars}


def _start_time(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return stat[stat.rindex(")") + 2:].split()[19]
    except (OSError, ValueError, IndexError):
        return None


def descendants(root):
    """(pid, start time) of every process under root, root included."""
    seen, stack = [], [root]
    while stack:
        pid = stack.pop()
        if any(p == pid for p, _ in seen):
            continue
        start = _start_time(pid)
        if start is None:
            continue
        seen.append((pid, start))
        for task in Path(f"/proc/{pid}/task").glob("*"):
            try:
                stack.extend(int(c) for c in (task / "children").read_text().split())
            except (OSError, ValueError):
                pass
    return seen


def kill_tree(proc):
    """SIGKILL proc, its process group and everything under it."""
    tree = descendants(proc.pid)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    for pid, start in tree:
        if _start_time(pid) == start:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    proc.wait()


class ApptainerExecEnvironment:
    """mini's Environment: execute() runs one bash action in the sandbox and returns mini's result dict."""

    def __init__(self, *, sandbox: Sandbox, cwd: str, timeout: int, path_inside: str,
                 on_result: Callable[[str, dict, float], None] | None = None,
                 service: Callable[[], None] | None = None, gpu_timeout: int = 3600):
        self.sandbox = sandbox
        self.cwd = cwd
        self.timeout = timeout
        self.gpu_timeout = gpu_timeout
        self.path_inside = path_inside
        self.on_result = on_result
        self.service = service
        self.n_actions = 0

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("TERM", None)
        env["APPTAINERENV_PATH"] = f"/repro/bin:{self.path_inside}"
        return env

    def _run(self, command: str, timeout: int) -> dict[str, Any]:
        argv = self.sandbox.wrap_argv(command)
        start = time.time()
        with tempfile.TemporaryFile() as out:
            try:
                proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                        env=self._env(), start_new_session=True)
                returncode, error = self._wait(proc, start + timeout, argv, timeout)
            except Exception as e:
                returncode, error = -1, e
            text, cut = read_output(out, returncode)
        result = {"output": text, "returncode": returncode, "exception_info": "",
                  "extra": {"exec_ms": round((time.time() - start) * 1000, 1), **cut}}
        if error is not None:
            result["exception_info"] = f"An error occurred while executing the command: {error}"
            result["extra"].update(exception_type=type(error).__name__, exception=str(error))
        return result

    def _wait(self, proc, deadline, argv, timeout):
        while True:
            if self.service is not None:
                self.service()
            try:
                return proc.wait(timeout=POLL_S), None
            except subprocess.TimeoutExpired:
                pass
            if time.time() >= deadline:
                kill_tree(proc)
                return -1, subprocess.TimeoutExpired(argv, timeout)

    def execute(self, action: dict, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        command = action.get("command", "")
        gpu = bool(RUN_GPU_CALL.search(command))
        limit = timeout or (self.gpu_timeout if gpu else self.timeout)
        self.n_actions += 1
        output = self._run(command, limit)
        if self.on_result is not None and not gpu:  # run_gpu writes its own commands.log line
            self.on_result(command, output, output["extra"]["exec_ms"] / 1000)
        self._check_finished(output)
        return output

    def _check_finished(self, output: dict):
        if submits(output.get("output", ""), output["returncode"]):
            submission = "".join(output["output"].lstrip().splitlines(keepends=True)[1:])
            raise Submitted({"role": "exit", "content": submission,
                             "extra": {"exit_status": "Submitted", "submission": submission}})

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return {"cwd": self.cwd, "timeout": self.timeout, **kwargs}

    def serialize(self) -> dict:
        return {"info": {"config": {"environment": {"cwd": self.cwd, "timeout": self.timeout,
                                                    "gpu_timeout": self.gpu_timeout,
                                                    "image": self.sandbox.image},
                                    "environment_type": f"{self.__class__.__module__}.{self.__class__.__name__}"},
                         "container": {"network": "host", "actions": self.n_actions}}}

    def cleanup(self):
        pass

