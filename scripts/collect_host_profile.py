#!/usr/bin/env python3
"""Collect host machine + SIF container facts into host_profile.json.

Run this once on the login/compute node before starting the reproduction
agent. Write the output into the SAME folder as the benchmark JSONL (e.g.
outputs/host_profile.json, next to outputs/<benchmark>.jsonl) — that's where
run_reproduction_agent.py looks for it and copies it into each paper's
sandbox, so the agent reads it directly in the inspect_host phase instead of
running uname/nvidia-smi/apptainer exec itself.

RUN IN THE COMPUTR NODE, NOT THE LOGIN NODE! 

Usage:
    python scripts/collect_host_profile.py \\
        --sif /sw/user/NGC_containers/pytorch_25.08-py3.sif \\
        --output outputs/host_profile.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{' '.join(cmd)}: timed out after {timeout}s"


def get_arch() -> str:
    _, out, _ = run(["uname", "-m"])
    return out or "unknown"


def get_gpu_info() -> dict:
    info = {
        "has_gpu": False,
        "gpu_name": None,
        "gpu_count": 0,
        "driver_version": None,
        "cuda_driver_version": None,
    }
    if not shutil.which("nvidia-smi"):
        return info
    rc, out, _ = run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version",
            "--format=csv,noheader",
        ]
    )
    if rc == 0 and out:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        info["has_gpu"] = True
        info["gpu_count"] = len(lines)
        if lines:
            name, driver = (lines[0].split(",") + [None, None])[:2]
            info["gpu_name"] = name.strip() if name else None
            info["driver_version"] = driver.strip() if driver else None
    rc, out, _ = run(
        ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"]
    )
    if rc != 0 or not out:
        # cuda_version isn't a real nvidia-smi query field on older drivers; fall back
        rc, out, _ = run(["nvidia-smi"])
        if rc == 0 and "CUDA Version" in out:
            for line in out.splitlines():
                if "CUDA Version" in line:
                    info["cuda_driver_version"] = (
                        line.split("CUDA Version:")[-1].strip().split()[0]
                    )
                    break
    else:
        info["cuda_driver_version"] = out.splitlines()[0].strip()
    return info


def get_slurm_info() -> dict:
    info = {"slurm_available": False, "partitions": None}
    if not shutil.which("sinfo"):
        return info
    rc, out, _ = run(["sinfo", "-h", "-o", "%P"])
    if rc == 0:
        info["slurm_available"] = True
        info["partitions"] = sorted(
            {p.strip().rstrip("*") for p in out.splitlines() if p.strip()}
        )
    return info


def get_disk_info() -> dict:
    paths = [
        "/home",
        "/tmp",
        f"/work/nvme/{os.environ.get('USER', '')}",
        f"/work/hdd/{os.environ.get('USER', '')}",
    ]
    info = {}
    for p in paths:
        if not os.path.exists(p):
            info[p] = "does not exist"
            continue
        rc, out, _ = run(["df", "-h", p])
        if rc == 0 and out:
            info[p] = out.splitlines()[-1]
        else:
            info[p] = "unavailable"
    return info


def get_conda_info() -> dict:
    conda_path = shutil.which("conda")
    info = {"has_conda": bool(conda_path), "conda_path": conda_path}
    if conda_path:
        _, out, _ = run([conda_path, "--version"])
        info["conda_version"] = out or None
    return info


def get_apptainer_info() -> dict:
    apptainer_path = shutil.which("apptainer") or shutil.which("singularity")
    info = {"has_apptainer": bool(apptainer_path), "apptainer_path": apptainer_path}
    if apptainer_path:
        _, out, _ = run([apptainer_path, "version"])
        info["apptainer_version"] = out or None
    return info


def get_uv_info() -> dict:
    uv_path = shutil.which("uv") or os.path.expanduser("~/.local/bin/uv")
    has_uv = shutil.which("uv") is not None or os.path.exists(uv_path)
    info = {"has_uv": has_uv, "uv_path": uv_path if has_uv else None}
    if has_uv:
        _, out, _ = run([uv_path, "--version"])
        info["uv_version"] = out or None
    return info


def get_container_info(sif_path: str) -> dict:
    info: dict = {"path": sif_path, "exists": os.path.exists(sif_path)}
    if not info["exists"]:
        return info
    info["size_bytes"] = os.path.getsize(sif_path)

    apptainer = shutil.which("apptainer") or shutil.which("singularity")
    if not apptainer:
        info["error"] = (
            "apptainer/singularity not on PATH; cannot inspect container contents"
        )
        return info

    # One container launch with --nv (matches the standard GPU-check pattern:
    # apptainer exec --nv "$CONTAINER" python3 - <<'PY' ... PY) instead of many
    # separate apptainer exec calls — cheaper and reports torch/cuda together.
    probe_script = r"""
import json, sys
result = {"python_version": sys.version.split()[0], "python_path": sys.executable}
try:
    import torch
    result["torch_version"] = torch.__version__
    result["torch_file"] = torch.__file__
    result["torch_cuda_version"] = torch.version.cuda
    result["cuda_available"] = torch.cuda.is_available()
    result["cuda_device_count"] = torch.cuda.device_count()
    if result["cuda_available"] and result["cuda_device_count"] > 0:
        result["cuda_device_name"] = torch.cuda.get_device_name(0)
    import os
    result["site_packages_dir"] = os.path.dirname(os.path.dirname(torch.__file__))
except Exception as e:
    result["torch_error"] = str(e)
try:
    import torchvision
    result["torchvision_version"] = torchvision.__version__
    result["torchvision_file"] = torchvision.__file__
except Exception as e:
    result["torchvision_error"] = str(e)
try:
    import numpy
    result["numpy_version"] = numpy.__version__
except Exception as e:
    result["numpy_error"] = str(e)
try:
    import PIL
    result["pillow_version"] = PIL.__version__
except Exception as e:
    result["pillow_error"] = str(e)
print(json.dumps(result))
"""
    try:
        proc = subprocess.run(
            [apptainer, "exec", "--nv", sif_path, "python3", "-"],
            input=probe_script,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            info.update(json.loads(proc.stdout.strip().splitlines()[-1]))
        else:
            info["probe_error"] = proc.stderr.strip() or f"exit code {proc.returncode}"
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        info["probe_error"] = str(e)

    rc, out, _ = run(
        [
            apptainer,
            "exec",
            sif_path,
            "bash",
            "-lc",
            "command -v uv && uv --version || echo NO_UV",
        ],
        timeout=60,
    )
    info["uv_in_container"] = out if rc == 0 and "NO_UV" not in out else None

    return info


def main() -> None:
    p = argparse.ArgumentParser(
        description="Collect host + SIF container facts into host_profile.json"
    )
    p.add_argument(
        "--sif",
        default="/sw/user/NGC_containers/pytorch_25.08-py3.sif",
        help="Path to the NGC Apptainer/Singularity image",
    )
    p.add_argument(
        "--output",
        default="outputs/host_profile.json",
        help="Output JSON path — put it next to the benchmark JSONL (e.g. outputs/host_profile.json)",
    )
    args = p.parse_args()

    profile = {
        "arch": get_arch(),
        "disk_info": get_disk_info(),
    }
    profile.update(get_gpu_info())
    profile["cuda_visible"] = profile["has_gpu"]
    profile.update(get_slurm_info())
    profile.update(get_conda_info())
    profile.update(get_apptainer_info())
    profile.update(get_uv_info())
    profile["container"] = get_container_info(args.sif)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"Wrote {args.output}", file=sys.stderr)
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
