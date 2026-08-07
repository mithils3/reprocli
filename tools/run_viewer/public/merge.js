/* merge.js — sweep-merge policy: the sbatch jobs that are really one sweep.

   A retry sbatch launched with ONLY_IDS re-runs the papers its parent sweep left
   unfinished. Slurm hands that retry a fresh job id, so the harness stamps a new
   batch_id and the Live sidebar shows two cards for what is one sweep of one
   roster. This module folds a retry into its parent and marks the attempts the
   retry superseded, so a merged group counts each paper once.

   Presentation only: rows keep their own batch_id in Supabase, and every other
   consumer (Analysis sweeps, batch_runs.py, the audit joins) still sees the two
   jobs separately — which is what those want, since a bundle belongs to the job
   that wrote it. Exported on window.Merge; must load before batches.js. */
"use strict";

(function () {
  // retry batch_id -> parent batch_id it belongs to.
  const PARENT = {
    // ONLY_IDS retry of the six papers 2698678 left stuck mid-run when the harness
    // fault killed their drivers (commit 1a66837). Same roster, same brain.
    "slurm-2759663": "slurm-2698678",
    // Repair of the 23 papers 2883229 did not fairly measure — 16 killed by the
    // old flat 128K input ceiling (exit context_budget) and 7 wedged on an
    // unreturned run_gpu acquire (repair_2883229.sh). Folding it in supersedes
    // those attempts, so the merged roster is 2883229's 11 natural exits plus the
    // repair's re-runs.
    "slurm-2889575": "slurm-2883229",
  };
  // canonical batch_id -> label for the merged group (the parent's own label names
  // only one of the jobs, so a merged group states both).
  const LABEL = {
    "slurm-2698678": "repro_medium_qwen3 #2698678 +2759663",
    "slurm-2883229": "repro_easy_dsv4 #2883229 +2889575",
  };

  const startedMs = (run) => {
    const t = Date.parse((run && (run.started_at || run.updated_at)) || "");
    return Number.isFinite(t) ? t : 0;
  };

  // Canonical group key for a run: its parent's batch_id when it is a retry.
  function batchKey(run) {
    const bid = run && run.batch_id;
    return PARENT[String(bid || "")] || bid;
  }

  // Header label for a group, given its canonical key and any run in it.
  function groupLabel(key, run) {
    return LABEL[String(key || "")] || (run && run.batch_label) || key;
  }

  // Every batch_id that belongs to the group `key` names: `key` itself plus the
  // retries folded into it. A published Analysis sweep stores one batch_id, so
  // fetching its runs has to expand back to the whole group or the retry's papers
  // arrive without meters.
  function batchIds(key) {
    const k = String(key || "");
    if (!k) return [];
    return [k, ...Object.keys(PARENT).filter((retry) => PARENT[retry] === k)];
  }

  // run_ids in `runs` that a later attempt at the same paper replaced. Only the
  // newest attempt per arxiv_id survives; ties (no usable timestamp) keep the
  // first, which arrives newest-first from the sidebar query.
  function supersededIds(runs) {
    const newest = new Map();
    for (const run of runs || []) {
      const id = run && run.arxiv_id;
      if (!id) continue;
      const prev = newest.get(id);
      if (!prev || startedMs(run) > startedMs(prev)) newest.set(id, run);
    }
    const out = new Set();
    for (const run of runs || []) {
      const id = run && run.arxiv_id;
      if (!id) continue;
      const win = newest.get(id);
      if (win && win.run_id !== run.run_id) out.add(run.run_id);
    }
    return out;
  }

  window.Merge = { batchKey, groupLabel, batchIds, supersededIds };
})();
