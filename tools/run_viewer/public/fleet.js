/* fleet.js — the Live detail pane when no run is open: a live fleet dashboard
   built from the same filtered rows the sidebar shows. Header + count, a strip of
   family-coloured stat tiles (running/done/dead/error + total burn), then a grid
   of compact cards for the running runs (or the most-recent finished ones when
   nothing is live). Clicking a card opens the run. Dependency-light: reuses
   window.RENDER helpers + Verdict. app.js re-renders it from renderList(). */
"use strict";

(function () {
  const R = () => window.RENDER;

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
  const tile = (label, value, cls) => `<div class="ftile ${cls || ""}"><div class="ft-l">${label}</div><div class="ft-v tnum">${value}</div></div>`;

  function fcard(run) {
    const RE = R(), V = window.Verdict;
    const claim = RE.claimOf(run) || run.arxiv_id || run.run_id;
    const model = RE.shortModel(run.model);
    const live = RE.effectiveStatus(run) === "running";
    const ago = live ? `<span class="dot running"></span>${RE.fmtAgo(run.updated_at)}` : RE.fmtAgo(run.updated_at);
    const c = RE.el(`<button class="fcard" type="button" data-run="${RE.esc(run.run_id)}" title="${RE.esc(run.arxiv_id || "")}">
      <span class="fc-top">${V ? V.runInline(run) : ""}<span class="fc-ago ${live ? "live" : ""}">${ago}</span></span>
      <span class="fc-claim">${RE.esc(claim)}</span>
      ${model ? `<span class="fc-model tnum">${RE.esc(model)}</span>` : ""}
      <span class="fc-fuel">${RE.microFuelHtml(run)}</span></button>`);
    c.addEventListener("click", () => { if (window.openRun) window.openRun(run.run_id); });
    return c;
  }

  function render(rootEl, runs) {
    const RE = R();
    runs = runs || [];
    const c = counts(runs);
    const burn = runs.reduce((a, r) => a + (Number(r.spent_h100) || 0), 0);
    const running = runs.filter((r) => RE.effectiveStatus(r) === "running");
    let cards, gridTitle, note = "";
    if (running.length) { gridTitle = "Live now"; cards = running.slice(0, 12); if (running.length > 12) note = `+${running.length - 12} more`; }
    else { gridTitle = "Most recent"; const rest = runs; cards = rest.slice(0, 12); if (rest.length > 12) note = `+${rest.length - 12} more`; }
    rootEl.innerHTML = `<div class="fleet">
      <div class="fleet-head"><h2>Fleet</h2><span class="fleet-count">${runs.length} run${runs.length !== 1 ? "s" : ""} visible</span></div>
      <div class="ftiles">
        ${tile("RUNNING", c.running, "accent")}${tile("DONE", c.done, "yes")}${tile("DEAD", c.dead, "slate")}${tile("ERROR", c.error, "no")}${tile("TOTAL BURN", RE.fmtHM(burn), "")}
      </div>
      <div class="cluster-slot"></div>
      <div class="fleet-sub"><span class="fs-title">${gridTitle}</span>${note ? `<span class="fs-note">${note}</span>` : ""}</div>
      <div class="fgrid"></div></div>`;
    const grid = rootEl.querySelector(".fgrid");
    if (!cards.length) grid.innerHTML = `<div class="empty small">No runs to show yet.</div>`;
    else cards.forEach((r) => grid.appendChild(fcard(r)));
    if (window.Hosts) window.Hosts.mountCluster(rootEl.querySelector(".cluster-slot")); // Cluster telemetry (hosts.js)
  }

  window.Fleet = { render };
})();
