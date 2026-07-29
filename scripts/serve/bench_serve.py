#!/usr/bin/env python3
"""Benchmark a vLLM OpenAI endpoint on a realistic agentic profile.

Two scenarios:

  agentic  A ~85k-token transcript, measured three ways:
             cold prefill  nothing cached; what an agent pays on turn 1.
             warm prefill  same transcript + one appended turn; what every
                           later turn pays, since transcripts are append-only
                           and hit vLLM's prefix cache. This is the number
                           that actually sets sweep wall-clock.
             decode        sustained output token rate.

  table    npp 512 / ntg 128 at concurrency 1,2,4,8 -- the same shape as the
           llama-batched-bench table in tasks/serve-gguf-llamacpp-gh200.md
           section 8, so the vLLM and llama.cpp paths are comparable.

Stdlib only: this runs inside whatever venv is serving, with no extra installs.

  python scripts/serve/bench_serve.py --scenario agentic
  python scripts/serve/bench_serve.py --scenario table
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
WORDS = (
    "tensor buffer kernel stride offset gradient checkpoint scheduler epoch "
    "logits attention residual embedding projection quantize dequantize cache "
    "shard replica pipeline throughput latency allocator registry manifest"
).split()


@dataclass
class Result:
    """One completed streaming request."""

    ttft: float
    wall: float
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    error: str | None = None

    @property
    def timed(self) -> bool:
        """True when a first token was observed, so ttft splits prefill from decode.

        Without it neither rate is recoverable: prefill has no duration, and the
        decode window silently absorbs prefill plus queueing. Both rates return
        NaN in that case and the reporters drop them -- returning 0.0 here put a
        fabricated measurement into statistics.mean() and dragged the average
        toward zero, which is how a working server reported `PP t/s 0.0`.
        """
        return self.ttft > 0.0 and self.prompt_tokens > 0

    @property
    def prefill_tps(self) -> float:
        return self.prompt_tokens / self.ttft if self.timed else float("nan")

    @property
    def decode_tps(self) -> float:
        tail = self.wall - self.ttft
        n = self.completion_tokens - 1
        return n / tail if self.timed and tail > 0 and n > 0 else float("nan")


@dataclass
class Config:
    base_url: str
    model: str
    timeout: float = 3600.0


def _post(cfg: Config, path: str, payload: dict) -> urllib.request.addinfourl:
    req = urllib.request.Request(
        f"{cfg.base_url}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=cfg.timeout)


def wait_for_server(cfg: Config, timeout: float = 0.0) -> None:
    """Poll /health every 5s until it answers 200. Waits forever by default.

    vLLM only binds the API server once engine init finishes, so a refused
    connection means "still loading", not "broken". Startup for a 400 GiB
    checkpoint with CPU offload is ~35-45 min and varies with what is cached,
    so there is no useful deadline to pick -- just poll until it is up, or
    Ctrl-C. Pass a positive `timeout` to bound it.
    """
    base = cfg.base_url.rsplit("/v1", 1)[0]
    start = time.monotonic()
    last_note = 0.0
    while True:
        elapsed = time.monotonic() - start
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=10) as resp:
                if resp.status == 200:
                    print(f"server healthy after {elapsed / 60:.1f}m")
                    return
        except Exception:  # noqa: BLE001 - refused/timeout both mean "not yet"
            pass
        if timeout > 0 and elapsed >= timeout:
            sys.exit(f"server did not answer {base}/health within {timeout:.0f}s")
        if elapsed - last_note >= 60:
            print(f"waiting for {base}/health ... {elapsed / 60:.0f}m elapsed")
            last_note = elapsed
        time.sleep(5)


def count_tokens(cfg: Config, messages: list[dict]) -> int:
    """Exact prompt length via vLLM's /tokenize, so 85k means 85k."""
    base = cfg.base_url.rsplit("/v1", 1)[0]
    req = urllib.request.Request(
        f"{base}/tokenize",
        data=json.dumps({"model": cfg.model, "messages": messages}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["count"]


def stream_once(cfg: Config, messages: list[dict], max_tokens: int) -> Result:
    """Fire one streaming completion, timing first token and last."""
    payload = {
        "model": cfg.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 1.0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "ignore_eos": True,  # vLLM extension: force exactly max_tokens out
    }
    start = time.perf_counter()
    ttft = 0.0
    prompt_tokens = completion_tokens = cached = 0
    try:
        with _post(cfg, "/chat/completions", payload) as resp:
            for raw in resp:
                line = raw.decode().strip()
                if not line.startswith("data: "):
                    continue
                body = line[6:]
                if body == "[DONE]":
                    break
                chunk = json.loads(body)
                # The reasoning parser splits output across several delta fields;
                # a GLM-5.2 thinking trace arrives as reasoning_content and a
                # tool call as tool_calls, so counting only `content` would time
                # the wrong first token -- or, if the whole response is reasoning
                # or a tool call, never time one at all.
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    payload_fields = (
                        delta.get("content"),
                        delta.get("reasoning_content"),
                        delta.get("tool_calls"),
                    )
                    if any(payload_fields) and ttft == 0.0:
                        ttft = time.perf_counter() - start
                if usage := chunk.get("usage"):
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    details = usage.get("prompt_tokens_details") or {}
                    cached = details.get("cached_tokens") or 0
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return Result(0.0, 0.0, 0, 0, error=str(exc))
    return Result(ttft, time.perf_counter() - start, prompt_tokens, completion_tokens, cached)


def stream_many(cfg: Config, jobs: list[tuple[list[dict], int]]) -> tuple[list[Result], float]:
    """Run jobs concurrently; return results plus batch wall-clock."""
    out: list[Result | None] = [None] * len(jobs)

    def worker(i: int) -> None:
        out[i] = stream_once(cfg, jobs[i][0], jobs[i][1])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(jobs))]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return [r for r in out if r is not None], time.perf_counter() - start


def _filler(rng: random.Random, n_words: int) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(n_words))


def build_transcript(cfg: Config, target: int, nonce: str, seed: int = 0) -> list[dict]:
    """A synthetic agent transcript of ~`target` prompt tokens.

    `nonce` goes in the FIRST message. Prefix caching keys on the leading
    tokens, so a fresh nonce guarantees a genuine cold prefill; reusing one
    guarantees a hit.
    """
    rng = random.Random(seed)
    words = max(256, int(target * 0.75))  # ~1.3 tok/word for this vocabulary
    for _ in range(4):  # calibrate against the real tokenizer
        messages = [
            {"role": "system", "content": f"Session {nonce}. You reproduce ML papers."},
            {"role": "user", "content": "Reproduce the paper in ./work. Report the anchor metric."},
            {"role": "assistant", "content": f"Reading the repo.\n\n{_filler(rng, words // 2)}"},
            {"role": "user", "content": f"Tool output:\n{_filler(rng, words // 2)}"},
            {"role": "user", "content": "Continue. What is the next step?"},
        ]
        got = count_tokens(cfg, messages)
        if abs(got - target) <= max(512, target * 0.02):
            return messages
        words = max(256, int(words * target / max(got, 1)))
    return messages


def fmt(results: list[Result]) -> str:
    ok = [r for r in results if not r.error]
    if not ok:
        return "all requests failed"
    timed = [r for r in ok if r.timed]
    if not timed:
        return f"no first-token timing on {len(ok)} request(s) -- rates unavailable"
    note = f"   [{len(ok) - len(timed)}/{len(ok)} untimed, excluded]" if len(timed) < len(ok) else ""
    return (
        f"prefill {statistics.mean(r.prefill_tps for r in timed):7.1f} t/s   "
        f"decode {statistics.mean(r.decode_tps for r in timed):6.1f} t/s   "
        f"ttft {statistics.mean(r.ttft for r in timed):6.2f}s{note}"
    )


def scenario_agentic(cfg: Config, target: int, out_tokens: int) -> None:
    print(f"\n=== agentic: ~{target} token transcript, {out_tokens} tokens out ===\n")

    cold = build_transcript(cfg, target, nonce="cold-run-1")
    n = count_tokens(cfg, cold)
    print(f"transcript is {n} prompt tokens (measured via /tokenize)\n")

    r1 = stream_once(cfg, cold, out_tokens)
    if r1.error:
        sys.exit(f"cold request failed: {r1.error}")
    print(f"cold prefill   {fmt([r1])}")
    print(f"               {r1.cached_tokens} of {r1.prompt_tokens} prompt tokens were cached")

    # Turn 2: identical prefix, one appended turn. This is the real agent path.
    warm = cold + [
        {"role": "assistant", "content": "Next I will run the training script."},
        {"role": "user", "content": "Tool output: exit 0. Continue."},
    ]
    r2 = stream_once(cfg, warm, out_tokens)
    if r2.error:
        sys.exit(f"warm request failed: {r2.error}")
    print(f"warm prefill   {fmt([r2])}")
    print(f"               {r2.cached_tokens} of {r2.prompt_tokens} prompt tokens were cached")

    if r2.ttft > 0:
        print(f"\nttft {r1.ttft:.2f}s -> {r2.ttft:.2f}s  ({r1.ttft / r2.ttft:.1f}x faster on turn 2)")
    if r2.cached_tokens == 0:
        print("\nWARNING: nothing cached on turn 2. Prefix caching is off, or the")
        print("         prompt diverged. Every agent turn is paying a cold prefill.")


def scenario_table(cfg: Config, npp: int, ntg: int, levels: list[int]) -> None:
    print(f"\n=== table: npp {npp} / ntg {ntg} -- comparable to runbook section 8 ===\n")
    print("  B   PP t/s    TG t/s   total t/s")
    for b in levels:
        jobs = [
            (build_transcript(cfg, npp, nonce=f"tbl-{b}-{i}", seed=i), ntg) for i in range(b)
        ]
        results, wall = stream_many(cfg, jobs)
        ok = [r for r in results if not r.error]
        if not ok:
            print(f"{b:3d}   FAILED: {results[0].error if results else 'no results'}")
            continue
        # total is the honest aggregate: it needs only completion counts and the
        # batch wall-clock, so it survives even when no request got a ttft.
        total = sum(r.completion_tokens for r in ok) / wall if wall > 0 else 0.0
        timed = [r for r in ok if r.timed]
        if not timed:
            print(f"{b:3d}        --       --   {total:7.1f}   ({len(ok)} untimed)")
            continue
        note = f"   ({len(ok) - len(timed)}/{len(ok)} untimed)" if len(timed) < len(ok) else ""
        print(
            f"{b:3d}  {statistics.mean(r.prefill_tps for r in timed):7.1f}  "
            f"{statistics.mean(r.decode_tps for r in timed):7.1f}   {total:7.1f}{note}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--model", default="zai-org/GLM-5.2", help="the --served-model-name")
    ap.add_argument("--scenario", choices=["agentic", "table", "both"], default="both")
    ap.add_argument("--input-tokens", type=int, default=85000, help="agentic transcript size")
    ap.add_argument("--output-tokens", type=int, default=256)
    ap.add_argument("--npp", type=int, default=512, help="table: prompt tokens")
    ap.add_argument("--ntg", type=int, default=128, help="table: generated tokens")
    ap.add_argument("--npl", default="1,2,4,8", help="table: concurrency levels")
    ap.add_argument("--wait-timeout", type=float, default=0.0, help="seconds to wait for /health (0 = forever)")
    ap.add_argument("--no-wait", action="store_true", help="fail immediately if the server is down")
    args = ap.parse_args()

    cfg = Config(base_url=args.base_url.rstrip("/"), model=args.model)
    if not args.no_wait:
        wait_for_server(cfg, args.wait_timeout)
    try:
        count_tokens(cfg, [{"role": "user", "content": "ping"}])
    except Exception as exc:  # noqa: BLE001 - bad URL, bad model name, or (with --no-wait) no server
        sys.exit(f"probe failed at {cfg.base_url} for model {cfg.model!r}: {exc}")

    if args.scenario in ("agentic", "both"):
        scenario_agentic(cfg, args.input_tokens, args.output_tokens)
    if args.scenario in ("table", "both"):
        scenario_table(cfg, args.npp, args.ntg, [int(x) for x in args.npl.split(",")])


if __name__ == "__main__":
    main()
