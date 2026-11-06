# Rebuttal status (orchestrator-maintained)

Started 2026-11-06 evening while Mithil is away for the weekend. Budget caps: OpenAI $700 of $750, Meta $480 of $500, GPU on betw-dtai-gh.

| Item | State | Where |
| :- | :- | :- |
| DeltaAI checkout `~/reprocli` (repro-next) | done | /u/msalunkhe/reprocli |
| Harness venv | building | ~/reprocli/.venv |
| Slurm account override (betw) | building | src/reprocli_repro/cluster.py |
| OpenAI flex + strict body shape | building | src/reprocli_vllm/vllm/client.py |
| Muse Wonder body-shape check | running | |
| Subset (24 papers, seed 22528) | building | rebuttal/subset.json |
| E5 log integrity | running | rebuttal/results/e5 |
| E6 tolerance | running | rebuttal/results/e6 |
| E7 target re-derivation | running | rebuttal/results/e7 |
| E8 bound and empty cells | running | rebuttal/results/e8 |
| E9 checkpoint scan | running | rebuttal/results/e9 |
| E10 pipeline extraction | running | rebuttal/results/e10 |
| Codex CLI arm | building | scripts/rebuttal/codex_arm |
| mini-SWE-agent arm | building | scripts/rebuttal/miniswe_arm |
| E1/E2/E3/E8-rerun sweeps | waiting on venv, subset, flex | |
| Grading (Sonnet-5) | waiting on runs | |
