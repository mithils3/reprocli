# Paths and pins for the mini-SWE-agent arm on DeltaAI. Source it before miniswe_run.py.
export ARM_W=/work/nvme/bfvr/msalunkhe/rebuttal/miniswe
export ARM_VENV=$ARM_W/venv
export MSWEA_GLOBAL_CONFIG_DIR=$ARM_W/config       # keeps mini away from ~/.config/mini-swe-agent
export MSWEA_SILENT_STARTUP=1
export MSWEA_COST_TRACKING=ignore_errors           # litellm has no price for muse-wonder; usage.json prices each call
export LITELLM_LOCAL_MODEL_COST_MAP=True
export REPROCLI_SLURM_ACCOUNT=betw-dtai-gh         # run_gpu charges this account
export PYTHONPYCACHEPREFIX=${TMPDIR:-/tmp}/miniswe-arm-pycache-${USER:-user}
# Run as: source env.sh; source <(rg '^export META_MODEL_KEY=' ~/.bashrc); PYTHONPATH=$HOME/reprocli/src $ARM_VENV/bin/python miniswe_run.py ...
