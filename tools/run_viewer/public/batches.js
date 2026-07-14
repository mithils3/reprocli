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

  // effectiveStatus buckets for a group of runs
  function counts(runs) {
    const RE = R(), c = { running: 0, done: 0, dead: 0, error: 0 };
    for (const run of runs) {
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
    const c = counts(entry.runs), latest = entry.runs[0].updated_at;
    const btn = RE.el(`<button class="batch-head ${isCol ? "collapsed" : ""}" title="batch ${RE.esc(entry.id)}" aria-expanded="${!isCol}">
      <span class="bh-title"><span class="bh-chev">${isCol ? "▸" : "▾"}</span><span class="bh-glyph">⛁</span><span class="bh-label">${RE.esc(entry.label || entry.id)}</span>${nonFrozenChip}<span class="schip tnum">${entry.runs.length} runs</span>${modelChip}</span>
      ${segBar(c)}
      <span class="bh-sub"><span class="bh-counts">${countWords(c)}</span><span class="schip tnum" title="total compute spent">${RE.esc(RE.fmtHM(spent))}</span><span class="bh-time tnum" title="${RE.esc(RE.fmtTime(latest))}">${RE.esc(RE.fmtAgo(latest))}</span></span>
      </button>`);
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
