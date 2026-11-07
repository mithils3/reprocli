# E8 x86 replay of the aarch64 build failures

Of the 16 build failures labelled aarch64-caused, 12 have a real aarch64 failure and an install command in the transcript. Replayed on Delta x86 (A40, Python 3.12, fresh venv, account bfvr-delta-gpu, jobs 23644935, 23644964, 23645028, 23645135), 9 of 12 build and import (Wilson 95% 0.47 to 0.91). 2 fail on x86 for the same version reason (pytorch3d has no cp312 wheel; jax/optax pins conflict) and 1 fails earlier on x86 for a Python-version reason (pillow 9.2.0) before the aarch64 blocker is reached.
The other 4 rows are excluded: 2 were not chip failures (MiniMax's vLLM install returned 0 on aarch64; Qwen's spconv failed on the cp312 ABI tag), and 2 have no install command in the transcript.
By model, the 9 that build on x86: MiniMax 4, Qwen 3, Muse Spark 2, DeepSeek 0. Removing all aarch64 runs leaves the best-agent rates unchanged (E8 README line 9).
Rows: results.csv. Commands: replay_cmds.tsv. Script: scripts/rebuttal/x86_replay.sh.
