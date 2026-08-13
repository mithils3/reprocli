#!/usr/bin/env bash
# Reproduce + audit every tier-Medium paper of the frozen eval-100 on Muse Spark 1.2
# Contributor (model id muse-spark-1.2-contributor) via the Meta Model API.
#
#   nohup scripts/reproduce/muse_spark/medium_muse_spark.sh > medium_muse.log 2>&1 &
#
# Needs $META_MODEL_KEY. Env overrides (SPLIT, MODEL, MAX_PARALLEL, ONLY_IDS,
# BUDGET_H100_HOURS, RESUME, ...) are documented in muse_spark_sweep.sh.
set -uo pipefail
TIER=Medium exec "$(dirname "${BASH_SOURCE[0]}")/muse_spark_sweep.sh" "$@"
