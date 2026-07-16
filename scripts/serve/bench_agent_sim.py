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
import json
import random
import statistics
import sys
import threading
import time
import urllib.error

from bench_serve import Config, Result, _filler, _post, count_tokens, wait_for_server


def stream_turn(cfg: Config, messages: list[dict], max_tokens: int) -> tuple[Result, str]:
    """Like bench_serve.stream_once, but also returns the generated text.

    The text is appended to the transcript so the next turn's prefix covers
    the tokens the server just generated (and already holds in cache), which
    is exactly what a real agent harness does.
    """
    payload = {
        "model": cfg.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 1.0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "ignore_eos": True,
    }
    start = time.perf_counter()
    ttft = 0.0
    prompt_tokens = completion_tokens = cached = 0
    content: list[str] = []
    reasoning: list[str] = []
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
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content") or delta.get("reasoning_content"):
                        if ttft == 0.0:
                            ttft = time.perf_counter() - start
                    if delta.get("content"):
                        content.append(delta["content"])
                    if delta.get("reasoning_content"):
                        reasoning.append(delta["reasoning_content"])
                if usage := chunk.get("usage"):
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    details = usage.get("prompt_tokens_details") or {}
                    cached = details.get("cached_tokens") or 0
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return Result(0.0, 0.0, 0, 0, error=str(exc)), ""
    result = Result(ttft, time.perf_counter() - start, prompt_tokens, completion_tokens, cached)
    # Reasoning-only turns still need SOMETHING appended, or the next prompt
    # would not cover the generated tokens and the cache comparison skews.
    return result, "".join(content) or "".join(reasoning)


def build_system_prompt(cfg: Config, target: int) -> str:
    """A shared system prompt of ~`target` tokens, calibrated via /tokenize."""
    rng = random.Random(0)
    words = max(64, int(target * 0.75))
    text = ""
    for _ in range(4):
        text = f"You reproduce ML papers. Harness rules:\n{_filler(rng, words)}"
        got = count_tokens(cfg, [{"role": "system", "content": text}])
        if abs(got - target) <= max(128, target * 0.05):
            break
        words = max(64, int(words * target / max(got, 1)))
    return text


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
        result, text = stream_turn(cfg, messages, args.max_output)
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

    print(f"\nturn   ttft mean/p95 (s)   decode t/s   prompt tok   cached")
    for turn in range(turns):
        rs = [r for _, t, r in ok if t == turn]
        if not rs:
            continue
        ttfts = sorted(r.ttft for r in rs)
        p95 = ttfts[min(len(ttfts) - 1, int(len(ttfts) * 0.95))]
        cached_pct = 100 * sum(r.cached_tokens for r in rs) / max(1, sum(r.prompt_tokens for r in rs))
        print(
            f"{turn + 1:4d}   {statistics.mean(ttfts):7.2f} / {p95:5.2f}     "
            f"{statistics.mean(r.decode_tps for r in rs):8.1f}   "
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
