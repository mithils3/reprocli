#!/bin/bash
# E10 environment check. Run dsv4-retrain-2503.09657 (2503.09657, DeepSeek-V4-Flash, tier retrain).
# SRC_LOG=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2503.09657/8h/2896059-2503.09657-fb7896/evidence/commands.log
# Original: default seed 0. Wall 7.40 h. Measured 23.36 (I4 final, Wikitext2 ppl, seq 4096); target 16.17.
# Usage: SEED=1 bash rerun.sh   (new seeds 1 and 2). Lines marked PATCH are not in the transcript.
set -euo pipefail
: "${SEED:?set SEED}"; export SEED
SRC=/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/2503.09657/8h/2896059-2503.09657-fb7896/workspace
RUN=/work/nvme/bfvr/msalunkhe/rebuttal/e10/2503.09657/seed$SEED
R=$RUN/repro
if [ ! -d "$R/workspace" ]; then
  mkdir -p "$R/workspace" "$R/evidence"
  (cd "$SRC" && tar -cf - --exclude=./Cached-Supernets --exclude=./.venv .) | (cd "$R/workspace" && tar -xf -)
  ln -s "$SRC/.venv" "$R/workspace/.venv"
fi
# PATCH (not in transcript): helpers never pass --seed; search and prune scripts default to seed 0
for f in run_prune_iter1.sh run_prune_iter.sh; do rg -q -- '--seed' "$R/workspace/$f" || sed -i 's/--num_sparsity_levels 9$/--num_sparsity_levels 9 --seed ${SEED}/' "$R/workspace/$f"; done; rg -q -- '--seed' "$R/workspace/run_search_iter.sh" || sed -i 's/--configuration_name/--seed ${SEED} --configuration_name/' "$R/workspace/run_search_iter.sh"
# L38 ts 03:15:03 dur 61s gpus 1
cd $R/workspace && export HF_HOME=/tmp/hfhome HF_DATASETS_CACHE=/tmp/hfdata && mkdir -p /tmp/hfhome /tmp/hfdata && time .venv/bin/hf download meta-llama/Llama-2-7b-hf --local-dir /tmp/llama2-7b 2>&1 | tail -3 && echo "MODEL DONE" && ls /tmp/llama2-7b/*.safetensors | head && du -sh /tmp/llama2-7b
# L78 ts 03:55:30 dur 2042s gpus 1
cd $R/workspace && chmod +x run_prune_iter1.sh && bash run_prune_iter1.sh > $R/evidence/prune_iter1.log 2>&1; echo "PRUNE EXIT: $?"; tail -25 $R/evidence/prune_iter1.log
# L115 ts 05:21:52 dur 4088s gpus 1
cd $R/workspace && bash run_search_iter.sh 1 50 2048 > $R/evidence/search_iter1.log 2>&1; echo "SEARCH EXIT: $?" >> $R/evidence/search_iter1.log; echo "=== DONE ==="; tr '\r' '\n' < $R/evidence/search_iter1.log | tail -40
# L121 ts 05:58:21 dur 2036s gpus 1
cd $R/workspace && chmod +x run_prune_iter.sh && bash run_prune_iter.sh 2 > $R/evidence/prune_iter2.log 2>&1; echo "PRUNE2 EXIT: $?" >> $R/evidence/prune_iter2.log; tr '\r' '\n' < $R/evidence/prune_iter2.log | grep -E "Processing model.layers|Pruning to supernet|PRUNE2 EXIT|Traceback|Error" | tail -15
# L122 ts 07:06:29 dur 4073s gpus 1
cd $R/workspace && bash run_search_iter.sh 2 50 2048 > $R/evidence/search_iter2.log 2>&1; echo "SEARCH2 EXIT: $?" >> $R/evidence/search_iter2.log; tr '\r' '\n' < $R/evidence/search_iter2.log | grep -E "Generation 1/|Generation 6/|Generation 11/|Generation 16/|Generation 21/|Generation 26/|Generation 31/|Generation 36/|Generation 41/|Generation 46/|Generation 50/|wikitext2:|best wikitext2|ppl_train|Final configuration|SEARCH2 EXIT" | tail -30
# L127 ts 07:43:12 dur 2109s gpus 1
cd $R/workspace && bash run_prune_iter.sh 3 > $R/evidence/prune_iter3.log 2>&1; echo "PRUNE3 EXIT: $?" >> $R/evidence/prune_iter3.log; tr '\r' '\n' < $R/evidence/prune_iter3.log | grep -E "Pruning to supernet|PRUNE3 EXIT|Traceback|Error" | tail -5
# L128 ts 08:53:36 dur 4222s gpus 1
cd $R/workspace && bash run_search_iter.sh 3 50 2048 > $R/evidence/search_iter3.log 2>&1; echo "SEARCH3 EXIT: $?" >> $R/evidence/search_iter3.log; tr '\r' '\n' < $R/evidence/search_iter3.log | grep -E "Generation 1/|Generation 11/|Generation 21/|Generation 31/|Generation 41/|Generation 50/|wikitext2:|best wikitext2|ppl_train|SEARCH3 EXIT" | tail -25
# L129 ts 09:28:04 dur 2050s gpus 1
cd $R/workspace && bash run_prune_iter.sh 4 > $R/evidence/prune_iter4.log 2>&1; echo "PRUNE4 EXIT: $?" >> $R/evidence/prune_iter4.log; tr '\r' '\n' < $R/evidence/prune_iter4.log | grep -E "Pruning to supernet|PRUNE4 EXIT|Traceback|Error" | tail -5
# L130 ts 10:37:05 dur 4130s gpus 1
cd $R/workspace && bash run_search_iter.sh 4 50 2048 > $R/evidence/search_iter4.log 2>&1; echo "SEARCH4 EXIT: $?" >> $R/evidence/search_iter4.log; tr '\r' '\n' < $R/evidence/search_iter4.log | grep -E "Generation 1/|Generation 11/|Generation 21/|Generation 31/|Generation 41/|Generation 50/|wikitext2:|best wikitext2|ppl_train|SEARCH4 EXIT" | tail -25
# L131 ts 10:38:11 dur 38s gpus 1
cd $R/workspace && export HF_HOME=/tmp/hfhome HF_DATASETS_CACHE=/tmp/hfdata PYTHONUNBUFFERED=1 PYTHONPATH=$R/workspace/repo TRITON_CACHE_DIR=/tmp/triton_cache XDG_CACHE_HOME=/tmp/xdgcache && .venv/bin/python eval_pruned.py --model /tmp/llama2-7b --supernet_dir $R/workspace/Cached-Supernets/Llama-2-7b-hf-0.5-iteration4 --config $R/workspace/Cached-Supernets/Llama-2-7b-hf-0.5-iteration4/Llama-2-7b-hf-0.5.txt --seq_len 4096 2>&1 | grep -E "eval_pruned|Traceback" | tail -5 && echo "=== SPARSITY CHECK ===" && .venv/bin/python -c "
import torch, os
cfg='$R/workspace/Cached-Supernets/Llama-2-7b-hf-0.5-iteration4/Llama-2-7b-hf-0.5.txt'
sdir='$R/workspace/Cached-Supernets/Llama-2-7b-hf-0.5-iteration4'
tot=0; kept=0; nz=0; nz_tot=0
with open(cfg) as f:
    for line in f:
        line=line.strip()
        if not line: continue
        name, level = line.split(':'); level=int(level.strip())
        w = torch.load(os.path.join(sdir, name, f'{level}.pth'), map_location='cpu', weights_only=False)
        w0 = torch.load(os.path.join(sdir, name, '0.pth'), map_location='cpu', weights_only=False)
        tot += w0.numel()
        kept += (w.abs()>0).sum().item()
        nz += (w!=0).sum().item()
        nz_tot += w.numel()
print(f'params total(dense level0): {tot}, pruned-config nonzero: {nz}, kept fraction (nonzero/total): {nz/tot:.4f}')
print(f'pruned param count (nonzero): {nz/1e9:.2f}B of {tot/1e9:.2f}B -> sparsity {1-nz/tot:.3f}')
"
