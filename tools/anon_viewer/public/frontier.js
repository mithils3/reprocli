/* frontier.js: the Frontier view. One summary row per frontier agent (runs,
   reproduced count, mean audit score), then every
   frontier run in the runs table's row style. Reads only Data.frontierModels
   and Data.frontierRuns, so nothing here reaches the four existing views. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict;
  const TIER_CLS = { run: "tier-run", retrain: "tier-retrain", reimplement: "tier-reimplement" };
  const LEAD = "Runs of gpt-6.1-sol, gpt-6-astra and Muse Wonder in our loop and in two production harnesses, graded by the same auditor.";
  const num = (x) => (x == null || isNaN(x) ? null : Number(x));

  const Frontier = {
    root() { return document.querySelector("#frontier-root"); },

    summaryRow(m, runs) {
      const mine = runs.filter((r) => r.model === m.key);
      const scored = mine.filter((r) => num(r.audit_score) != null);
      const reproduced = mine.filter((r) => r.audit_reproduced === true).length;
      const mean = scored.length
        ? (scored.reduce((s, r) => s + Number(r.audit_score), 0) / scored.length).toFixed(1) : "·";
      return `<tr><td class="s-model">${esc(m.name)}</td>` +
        `<td class="num tnum">${mine.length}</td>` +
        `<td class="num tnum">${reproduced} of ${mine.length}</td>` +
        `<td class="num tnum">${mean}</td></tr>`;
    },

    runRow(r) {
      const fam = V().ofRun(r);
      const s = num(r.audit_score);
      const band = s == null ? "" : s >= 8 ? "yes" : s >= 6 ? "over" : s <= 0 ? "no" : "slate";
      const score = s == null ? "·" : `<span class="an-score ${band}">${esc(r.audit_score)}<span>/10</span></span>`;
      const mode = window.Modes.name(r.mode);
      return `<tr data-run="${esc(r.id)}" tabindex="0">
        <td class="s-model c-agent">${esc(r.model_name || r.model)}</td>
        <td class="c-tier"><span class="badge ${TIER_CLS[r.tier] || "slate"}">${esc(window.Data.tierName(r.tier))}</span></td>
        <td class="s-rid c-paper">${esc(r.arxiv_id)}</td>
        <td class="c-verdict"><span class="vg vd ${fam}">${V().meta(fam).glyph}</span>${V().inline(fam, V().word(r))}</td>
        <td class="num c-score">${score}</td>
        <td class="mode-cell c-mode" title="${esc(mode)}">${window.Modes.chip(r.mode)}</td>
      </tr>`;
    },

    render() {
      const host = this.root();
      if (!host) return;
      const D = window.Data, runs = D.frontierRuns;
      host.innerHTML = `
        <div class="ov-head">
          <div><h1>Frontier models</h1><div class="ov-sub">${esc(LEAD)}</div></div>
        </div>
        <div class="tscroll" style="min-height:0;max-height:none;margin-bottom:18px"><table class="stats-table">
          <thead><tr><th>Agent</th><th class="num">Papers</th><th class="num">Reproduced</th><th class="num">Mean score</th></tr></thead>
          <tbody>${D.frontierModels.map((m) => this.summaryRow(m, runs)).join("")}</tbody></table></div>
        <div class="tscroll"><table class="stats-table runs-table">
          <thead><tr><th>agent</th><th>tier</th><th>paper</th><th>verdict</th><th class="num">score</th><th>failure mode</th></tr></thead>
          <tbody id="fr-body">${runs.map((r) => this.runRow(r)).join("")}</tbody></table></div>`;
      host.querySelectorAll("#fr-body tr[data-run]").forEach((tr) => {
        const open = () => window.go("#/run/" + encodeURIComponent(tr.dataset.run));
        tr.onclick = open;
        tr.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); open(); } };
      });
    },
  };

  window.Frontier = Frontier;
})();
