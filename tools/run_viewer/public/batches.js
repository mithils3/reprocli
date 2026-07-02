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
  function group(rows) {
    const out = [], byId = new Map();
    for (const run of rows || []) {
      const bid = run.batch_id;
      if (bid == null || bid === "") { out.push({ kind: "run", run }); continue; }
      let entry = byId.get(bid);
      if (!entry) {
        entry = { kind: "batch", id: bid, label: run.batch_label || bid, runs: [] };
        byId.set(bid, entry);
        out.push(entry);
      }
      entry.runs.push(run);
    }
    return out;
  }

  // compact status summary using RENDER.effectiveStatus buckets, zero buckets omitted
  function statusSummary(runs) {
    const RE = R(), c = { running: 0, done: 0, dead: 0, error: 0 };
    for (const run of runs) {
      const s = RE.effectiveStatus(run);
      if (s === "finished") c.done++;
      else if (s === "dead") c.dead++;
      else if (s === "error") c.error++;
      else c.running++;
    }
    return [["running", "running"], ["done", "done"], ["dead", "dead"], ["error", "error"]]
      .filter(([k]) => c[k]).map(([k, w]) => `${c[k]} ${w}`).join(" · ");
  }

  // group header row: chevron + label + count + status summary + total spent + latest update
  function headerEl(entry, opts) {
    const RE = R(), isCol = collapsed.has(entry.id);
    const spent = entry.runs.reduce((a, r) => a + (Number(r.spent_h100) || 0), 0);
    const models = new Set(entry.runs.map((r) => r.model).filter(Boolean));
    const modelChip = models.size === 1 ? `<span class="schip">${RE.esc([...models][0])}</span>` : "";
    const summary = statusSummary(entry.runs);
    const btn = RE.el(`<button class="batch-head ${isCol ? "collapsed" : ""}" title="batch ${RE.esc(entry.id)}" aria-expanded="${!isCol}">
      <span class="bh-chev">${isCol ? "▸" : "▾"}</span>
      <span class="bh-body">
        <span class="bh-title"><span class="bh-glyph">⛁</span><span class="bh-label">${RE.esc(entry.label || entry.id)}</span><span class="schip tnum">${entry.runs.length} runs</span>${modelChip}</span>
        <span class="bh-sub">${summary ? `<span class="bh-status">${RE.esc(summary)}</span>` : ""}<span class="schip tnum" title="total compute spent">${RE.esc(RE.fmtHM(spent))}</span><span class="bh-time tnum">${RE.esc(RE.fmtTime(entry.runs[0].updated_at))}</span></span>
      </span></button>`);
    btn.addEventListener("click", () => {
      if (collapsed.has(entry.id)) collapsed.delete(entry.id); else collapsed.add(entry.id);
      if (opts && opts.rerender) opts.rerender();
    });
    return btn;
  }

  function runItem(run, opts) {
    const item = R().renderRunListItem(run);
    if (run.run_id === opts.currentRunId) item.classList.add("active");
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
      for (const run of entry.runs) wrap.appendChild(runItem(run, opts));
      listEl.appendChild(wrap);
    }
  }

  window.Batches = { group, headerEl, render };
})();
