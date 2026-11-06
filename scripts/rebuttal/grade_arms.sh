#!/bin/bash
# Driver for grade_arms.py on DeltaAI: loads the key by pointer, then passes arguments through.
set -u
source <(rg '^export ANTHROPIC_API_KEY=' ~/.bashrc)
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd ~/reprocli && exec ~/reprocli/.venv/bin/python scripts/rebuttal/grade_arms.py "$@"
