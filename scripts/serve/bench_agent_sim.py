#!/usr/bin/env python3
"""Simulate a multi-agent sweep against an OpenAI-compatible endpoint.

bench_serve.py measures one cold/warm probe pair and a fixed-shape table; this
drives N concurrent agents through T turns each, generating the same traffic
shape as a real repro sweep:

  - one system prompt shared by every agent (cross-agent prefix hits)
  - per turn, the model's actual output is appended to the transcript, then a
    synthetic tool result; transcripts are append-only, so every turn after
    the first should hit the prefix cache
  - the overall cached share should land near the 80-95% seen in real runs;
    much lower means prefix caching is off or being evicted under load

Stdlib only, reuses bench_serve.py helpers (run from this directory or via
`python scripts/serve/bench_agent_sim.py`, which puts it on sys.path).

  python scripts/serve/bench_agent_sim.py \\
      --model deepseek-ai/DeepSeek-V4-Flash --agents 8 --turns 10

Uses vLLM's ignore_eos so every turn emits exactly --max-output tokens;
llama.cpp's OpenAI endpoint ignores that flag, so there turns can end early
at EOS and per-turn output sizes will vary.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import threading
import time

from bench_serve import Config, Result, _filler, calibrate, count_tokens, stream_text, wait_for_server


def build_system_prompt(cfg: Config, target: int) -> str:
    """A shared system prompt of ~`target` tokens, calibrated via /tokenize."""
    rng = random.Random(0)

    def build(words: int) -> list[dict]:
        return [
            {
                "role": "system",
                "content": f"You reproduce ML papers. Harness rules:\n{_filler(rng, words)}",
            }
        ]

    messages = calibrate(cfg, target, build, min_words=64, tol_floor=128, tol_frac=0.05)
    return messages[0]["content"]


def run_agent(
    cfg: Config,
    agent: int,
    args: argparse.Namespace,
    system_prompt: str,
    records: list[tuple[int, int, Result]],
    lock: threading.Lock,
) -> None:
    rng = random.Random(1000 + agent)
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Task {agent}: reproduce paper {agent} in ./work. "
            f"Repo notes:\n{_filler(rng, 300)}\nReport the anchor metric.",
        },
    ]
    for turn in range(args.turns):
        result, text = stream_text(cfg, messages, args.max_output)
        with lock:
            records.append((agent, turn, result))
        if result.error:
            print(f"agent {agent} turn {turn + 1} failed: {result.error}", file=sys.stderr)
            return
        tool_words = max(50, int(rng.gauss(args.tool_tokens, args.tool_tokens / 2) * 0.75))
        messages.append({"role": "assistant", "content": text or "(empty)"})
        messages.append(
            {"role": "user", "content": f"Tool output (exit 0):\n{_filler(rng, tool_words)}\nContinue."}
        )


def report(records: list[tuple[int, int, Result]], wall: float, turns: int) -> None:
    ok = [(a, t, r) for a, t, r in records if not r.error]
    if not ok:
        sys.exit("all turns failed")

    print("\nturn   ttft mean/p95 (s)   decode t/s   prompt tok   cached")
    for turn in range(turns):
        rs = [r for _, t, r in ok if t == turn]
        if not rs:
            continue
        ttfts = sorted(r.ttft for r in rs)
        p95 = ttfts[min(len(ttfts) - 1, int(len(ttfts) * 0.95))]
        cached_pct = 100 * sum(r.cached_tokens for r in rs) / max(1, sum(r.prompt_tokens for r in rs))
        # Median, and only over requests that recorded a first token. Under
        # concurrency a request that waits behind others has its queue time
        # charged to ttft, which leaves a short decode window and a per-request
        # rate several times the true one; one of those distorts a mean of 8
        # badly (turn 5 of the 2026-07-29 GLM-5.2 run read 199.9 t/s against ~44
        # either side). The aggregate at the bottom is the number to quote.
        timed = [r for r in rs if r.timed]
        decode = f"{statistics.median(r.decode_tps for r in timed):8.1f}" if timed else "      --"
        print(
            f"{turn + 1:4d}   {statistics.mean(ttfts):7.2f} / {p95:5.2f}     "
            f"{decode}   "
            f"{statistics.mean(r.prompt_tokens for r in rs):10.0f}   {cached_pct:5.1f}%"
        )

    prompt = sum(r.prompt_tokens for _, _, r in ok)
    cached = sum(r.cached_tokens for _, _, r in ok)
    out = sum(r.completion_tokens for _, _, r in ok)
    errors = len(records) - len(ok)
    print(f"\n{len(ok)} turns in {wall / 60:.1f}m  ({len(ok) / (wall / 60):.1f} turns/min)"
          + (f", {errors} FAILED" if errors else ""))
    print(f"prompt tokens {prompt:,}  cached {cached:,}  ({100 * cached / max(1, prompt):.1f}% cache share; real sweeps run 80-95%)")
    print(f"output tokens {out:,}  aggregate output {out / wall:.1f} t/s")
    if cached == 0:
        print("\nWARNING: nothing was ever cached. Prefix caching is off, or the")
        print("         server evicts every transcript between turns.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-V4-Flash", help="the --served-model-name")
    ap.add_argument("--agents", type=int, default=8, help="concurrent agents")
    ap.add_argument("--turns", type=int, default=10, help="turns per agent")
    ap.add_argument("--system-tokens", type=int, default=3000, help="shared system prompt size")
    ap.add_argument("--tool-tokens", type=int, default=1500, help="mean synthetic tool-result size")
    ap.add_argument("--max-output", type=int, default=768, help="output tokens per turn")
    ap.add_argument("--stagger", type=float, default=2.0, help="seconds between agent starts")
    ap.add_argument("--wait-timeout", type=float, default=0.0, help="seconds to wait for /health (0 = forever)")
    args = ap.parse_args()

    cfg = Config(base_url=args.base_url.rstrip("/"), model=args.model)
    wait_for_server(cfg, args.wait_timeout)
    system_prompt = build_system_prompt(cfg, args.system_tokens)
    n = count_tokens(cfg, [{"role": "system", "content": system_prompt}])
    print(f"system prompt: {n} tokens, shared by {args.agents} agents x {args.turns} turns, "
          f"~{args.tool_tokens} tok tool results, {args.max_output} tok out/turn")

    records: list[tuple[int, int, Result]] = []
    lock = threading.Lock()
    threads = []
    start = time.perf_counter()
    for i in range(args.agents):
        t = threading.Thread(target=run_agent, args=(cfg, i, args, system_prompt, records, lock))
        threads.append(t)
        t.start()
        time.sleep(args.stagger)
    for t in threads:
        t.join()
    report(records, time.perf_counter() - start, args.turns)


if __name__ == "__main__":
    main()
