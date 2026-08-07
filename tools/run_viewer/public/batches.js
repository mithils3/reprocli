/* batches.js — group Live-sidebar runs by sbatch launch. Rows carry an optional
   batch_id (stable group key, e.g. "slurm-3141592") + batch_label (human name).
   All runs from one sbatch sweep share a batch_id; old/ungrouped runs have it
   null and render exactly as before. This module only shapes the run list into
   collapsible groups; the item DOM is still RENDER.renderRunListItem. Exported on
   window.Batches, loaded after render.js (needs window.RENDER). */
"use strict";
(function () {
  const R = () => window.RENDER;
  // module-local collapse state: survives re-renders within the session (default expanded)
  const collapsed = new Set();

  // rows arrive sorted updated_at desc. Emit an ordered list interleaving
  // {kind:"batch", id, label, runs:[…]} (positioned at its most-recent run) and
  // {kind:"run", run} for batch_id-null rows, all in overall updated_at-desc order.
  // Grouping is keyed by window.Merge.batchKey, so a retry sbatch lands in its
  // parent's group; a group that ends up spanning several sbatch jobs also carries
  // the run_ids the retry superseded (see supersede note in merge.js).
  function group(rows) {
    const out = [], byId = new Map();
    for (const run of rows || []) {
      const bid = window.Merge ? window.Merge.batchKey(run) : run.batch_id;
      if (bid == null || bid === "") { out.push({ kind: "run", run }); continue; }
      let entry = byId.get(bid);
      if (!entry) {
        const label = window.Merge ? window.Merge.groupLabel(bid, run) : (run.batch_label || bid);
        entry = { kind: "batch", id: bid, label, runs: [], sources: new Set() };
        byId.set(bid, entry);
        out.push(entry);
      }
      entry.runs.push(run);
      entry.sources.add(run.batch_id);
    }
    for (const entry of byId.values()) {
      // Only a merged group can hold two attempts at one paper; leave single-job
      // sweeps counted exactly as before.
      entry.superseded = (entry.sources.size > 1 && window.Merge)
        ? window.Merge.supersededIds(entry.runs) : new Set();
    }
    return out;
  }

  // effectiveStatus buckets for a group of runs; a superseded attempt is not a
  // member of the roster any more, so it is left out of the tally.
  function counts(runs, superseded) {
    const RE = R(), c = { running: 0, done: 0, dead: 0, error: 0 };
    for (const run of runs) {
      if (superseded && superseded.has(run.run_id)) continue;
      const s = RE.effectiveStatus(run);
      if (s === "finished") c.done++;
      else if (s === "dead") c.dead++;
      else if (s === "error") c.error++;
      else c.running++;
    }
    return c;
  }
  // full-width proportional status segment bar (6px)
  function segBar(c) {
    const total = c.running + c.done + c.dead + c.error;
    if (!total) return "";
    const seg = (n, cls) => n ? `<i class="seg ${cls}" style="width:${(n / total * 100).toFixed(2)}%"></i>` : "";
    return `<span class="bseg">${seg(c.running, "running")}${seg(c.done, "done")}${seg(c.dead, "dead")}${seg(c.error, "error")}</span>`;
  }
  // colored count words, zero buckets omitted
  function countWords(c) {
    return [["running", "running"], ["done", "done"], ["dead", "dead"], ["error", "error"]]
      .filter(([k]) => c[k]).map(([k, w]) => `<span class="cw ${k}">${c[k]} ${w}</span>`).join(" · ");
  }

  // group header row: title line · status segment bar · count words + burn + recency
  function headerEl(entry, opts) {
    const RE = R(), isCol = collapsed.has(entry.id);
    const spent = entry.runs.reduce((a, r) => a + (Number(r.spent_h100) || 0), 0);
    const models = new Set(entry.runs.map((r) => r.model).filter(Boolean));
    const modelChip = models.size === 1 ? `<span class="schip">${RE.esc(RE.shortModel([...models][0]))}</span>` : "";
    const nonFrozenChip = window.Freeze && window.Freeze.isNonFrozenRecord(entry.runs[0])
      ? `<span class="schip non-frozen" title="Slurm job predates the frozen benchmark cutoff">non-frozen</span>` : "";
    const sup = entry.superseded || new Set();
    const c = counts(entry.runs, sup), latest = entry.runs[0].updated_at;
    const roster = entry.runs.length - sup.size;
    const mergedChip = entry.sources && entry.sources.size > 1
      ? `<span class="schip merged" title="${RE.esc([...entry.sources].join(" + "))}">merged ${entry.sources.size} jobs</span>` : "";
    const supChip = sup.size
      ? `<span class="schip superseded" title="re-run by a later attempt in this sweep">+${sup.size} superseded</span>` : "";
    const btn = RE.el(`<button class="batch-head ${isCol ? "collapsed" : ""}" title="batch ${RE.esc(entry.id)}" aria-expanded="${!isCol}">
      <span class="bh-title"><span class="bh-chev">${isCol ? "▸" : "▾"}</span><span class="bh-glyph">⛁</span><span class="bh-label">${RE.esc(entry.label || entry.id)}</span>${nonFrozenChip}${mergedChip}<span class="schip tnum">${roster} runs</span>${supChip}${modelChip}</span>
      ${segBar(c)}
      <span class="bh-sub"><span class="bh-counts">${countWords(c)}</span><span class="schip tnum" title="total compute spent">${RE.esc(RE.fmtHM(spent))}</span><span class="bh-time tnum" title="${RE.esc(RE.fmtTime(latest))}">${RE.esc(RE.fmtAgo(latest))}</span></span>
      </button>`);
    btn.addEventListener("click", () => {
      if (collapsed.has(entry.id)) collapsed.delete(entry.id); else collapsed.add(entry.id);
      if (opts && opts.rerender) opts.rerender();
    });
    return btn;
  }

  function runItem(run, opts, superseded) {
    const item = R().renderRunListItem(run);
    if (run.run_id === opts.currentRunId) item.classList.add("active");
    // A superseded attempt stays in the list (its transcript is still the record of
    // what went wrong) but reads as replaced and sits out of the group's counts.
    if (superseded && superseded.has(run.run_id)) {
      item.classList.add("superseded");
      const l1 = item.querySelector(".pl-l1");
      if (l1) l1.insertAdjacentHTML("beforeend", `<span class="schip superseded">superseded</span>`);
    }
    item.addEventListener("click", () => opts.onOpen(run.run_id));
    return item;
  }

  // clear listEl and append the grouped list; grouped runs sit in an indented wrapper
  function render(listEl, rows, opts) {
    listEl.innerHTML = "";
    for (const entry of group(rows)) {
      if (entry.kind === "run") { listEl.appendChild(runItem(entry.run, opts)); continue; }
      listEl.appendChild(headerEl(entry, opts));
      if (collapsed.has(entry.id)) continue;
      const wrap = document.createElement("div");
      wrap.className = "batch-runs";
      for (const run of entry.runs) wrap.appendChild(runItem(run, opts, entry.superseded));
      listEl.appendChild(wrap);
    }
  }

  window.Batches = { group, headerEl, render };
})();
