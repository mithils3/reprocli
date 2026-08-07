#!/bin/bash
# Repair sweep for slurm-2883229 (repro_easy_dsv4, DeepSeek-V4-Flash-0731).
#
#   scripts/reproduce/dsv4_flash/repair_2883229.sh          # submit
#   DRY_RUN=1 scripts/reproduce/dsv4_flash/repair_2883229.sh # print the sbatch line only
#
# WHAT IT RE-RUNS (23 of that sweep's 34 papers):
#   * 16 that exited context_budget. Their transcripts hit the old flat 128K input
#     ceiling, not a capability limit -- V4's encoder replays prior-turn reasoning
#     whenever tools are in the request, and under Think Max that replay measured
#     49-72% of the ceiling (median 61%). Qwen3.6 lost 1 of 34 and MiniMax-M2.7 3 of
#     34 on the same papers, so this was a harness interaction, not a model result.
#   * 7 that were still `running` with no terminal event, wedged on an unreturned
#     run_gpu acquire in the ghx4 queue (6 of them idle 6.7-12.1h at 2026-08-06T16:23Z).
#
# The 11 papers that exited `natural` are NOT re-run: nothing about them was broken.
# Re-running them would burn ~11 papers of ghx4 queue to reproduce results we already
# have, and would make the sweep's own before/after comparison meaningless.
#
# WHAT CHANGED UNDER IT since 2883229 (all three land in this run):
#   a4f1153  input ceiling comes from the served window (376832 here), not a flat 128000
#   399c3fc  Think Max retained; the window it set (1048576) killed the engine in
#            job 2889476 and is now 409600 -- see the deepseek_v4 profile
#   0cb89aa  elide-compact drops prior-turn reasoning, and the guards finally count it
#
# So this is NOT a like-for-like retry -- it is the same papers under a fixed harness.
# Compare it against 2883229 to size the harness's share of those 16 deaths; do NOT
# pool the two into one mean.
#
# SAFETY: SWEEP_DIR defaults to easy_sweeps/<this job id>, so this run gets a clean
# directory and cannot touch 2883229's bundles, verdicts or logs. ONLY_IDS also scopes
# IDS_FILE, STATUS_FILE and the per-paper logs to the job id, which is what makes it
# safe to point SWEEP_DIR at 2883229's directory if you ever want them side by side.
# This does NOT cancel 2883229 -- scancel the wedged runs yourself to free the queue.
#
# RESUME=0 is load-bearing. All 16 context_budget papers were audited and carry a
# verdict on disk, and RESUME=1 skips any paper that already has one -- so the default
# would silently no-op the exact papers this sweep exists to re-run.
set -euo pipefail

# DeltaAI charge account, confirmed 2026-08-06 against `accounts` and a successful
# submit (job 2889476). NOTE the two names: the PROJECT is bfvr, the SLURM ACCOUNT
# string is bfvr-dtai-gh -- the same -dtai-gh suffix the other sweeps carry on
# betw-dtai-gh. Passing the bare project code is rejected with "Invalid account or
# account/partition combination specified". Override with ACCOUNT=... if that
# changes; a wrong -A fails at submit rather than burning queue.
ACCOUNT="${ACCOUNT:-bfvr-dtai-gh}"

# 16 context_budget deaths + 7 queue-wedged runs, from the 2026-08-06T16:23Z snapshot.
ONLY_IDS="${ONLY_IDS:-\
2410.18164 2502.06684 2503.18430 2503.23035 2504.12397 2504.20571 2505.10475 \
2505.10978 2505.14827 2505.19154 2505.19713 2505.23305 2505.23747 2505.24864 \
2505.24873 2506.01511 2506.18890 2506.18896 2506.20671 2506.20990 2506.21724 \
2510.21311 2510.23574}"

# 8, not the sweep default 10: 23 papers over a 48h wall is not the binding
# constraint -- ghx4 queue pressure from concurrent JIT allocations is, and that is
# what wedged the 7 runs this sweep exists to rescue. Fewer in flight, fewer acquires
# competing. Raise it if the queue is quiet.
MAX_PARALLEL="${MAX_PARALLEL:-8}"

# Fresh batch id: this must land as its own sweep in the viewer, not merge into
# 2883229, or the comparison this run exists to make disappears into one mean.
JOB_NAME="${JOB_NAME:-repro_easy_dsv4_repair}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SBATCH_FILE="${HERE}/easy_dsv4_flash.sbatch"
[[ -f "${SBATCH_FILE}" ]] || { echo "missing ${SBATCH_FILE}" >&2; exit 1; }

n_ids="$(wc -w <<<"${ONLY_IDS}")"
echo "repair sweep: ${n_ids} paper(s), account=${ACCOUNT}, MAX_PARALLEL=${MAX_PARALLEL}"

# --export carries the knobs the sbatch reads; -A overrides its in-file directive.
set -- sbatch \
  -A "${ACCOUNT}" \
  -J "${JOB_NAME}" \
  --export="ALL,ONLY_IDS=${ONLY_IDS},MAX_PARALLEL=${MAX_PARALLEL},RESUME=0" \
  "${SBATCH_FILE}"

if [[ -n "${DRY_RUN:-}" ]]; then
  printf 'DRY_RUN, not submitting:\n'
  printf '%q ' "$@"; printf '\n'
  exit 0
fi
exec "$@"
