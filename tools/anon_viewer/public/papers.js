/* papers.js: the papers grid and one paper's page. The grid puts every target
   paper on a row and every agent in a column, so a row reads as how the field
   fared on that claim and a column reads as one agent across the whole set.
   A cell is the audit score, coloured by its verdict family, or blank where that
   agent has no run on that paper. Opening a row lists that paper's runs. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict;
  const TIER_CLS = { run: "yes", retrain: "over", reimplement: "no" };

  function cellHtml(run, dim) {
    if (!run) return `<td class="pm-cell empty">·</td>`;
    const fam = V().ofRun(run);
    const s = run.audit_score;
    return `<td class="pm-cell ${dim ? "dim" : ""}"><button class="pm-chip ${fam}" data-run="${esc(run.id)}"
      title="${esc(run.model_name)} · ${esc(V().word(run))} · ${esc(run.mode_name || "")}">${s == null ? "·" : esc(s)}</button></td>`;
  }

  const PapersView = {
    root() { return document.querySelector("#papers-root"); },

    papers() {
      const S = window.State;
      return window.Data.papers.filter((p) => S.tier === "all" || p.tier === S.tier);
    },

    renderList() {
      const host = this.root();
      if (!host) return;
      const S = window.State;
      const models = window.Data.models, papers = this.papers();
      const byKey = {};
      window.Data.runs.forEach((r) => { byKey[r.arxiv_id + "|" + r.model] = r; });
      const head = `<tr><th>claim</th><th>paper</th><th>tier</th><th class="num">predicted</th>` +
        models.map((m) => `<th class="pm-head ${S.model !== "all" && S.model !== m.key ? "dim" : ""}">${esc(m.name)}</th>`).join("") + `</tr>`;
      const body = papers.map((p) => {
        const runs = models.map((m) => byKey[p.arxiv_id + "|" + m.key] || null);
        const scored = runs.filter((r) => r && r.audit_score != null);
        const mean = scored.length ? scored.reduce((a, r) => a + r.audit_score, 0) / scored.length : null;
        return `<tr data-arx="${esc(p.arxiv_id)}" tabindex="0">
          <td class="pl-claim-cell"><span class="pcell-claim" title="${esc(p.claim || p.arxiv_id)}">${esc(p.claim || p.arxiv_id)}</span>
            ${p.gist ? `<span class="pcell-gist">${esc(p.gist)}</span>` : ""}
            ${mean == null ? "" : `<span class="s-sub tnum">mean ${mean.toFixed(2)}</span>`}</td>
          <td class="s-rid">${esc(p.arxiv_id)}</td>
          <td><span class="badge ${TIER_CLS[p.tier] || "slate"}">${esc(window.Data.tierName(p.tier))}</span></td>
          <td class="num tnum">${p.predicted_h100 ? R.fmtHM(p.predicted_h100) : "·"}</td>
          ${runs.map((r, i) => cellHtml(r, S.model !== "all" && S.model !== models[i].key)).join("")}</tr>`;
      }).join("");
      host.innerHTML = `
        <div class="ov-head"><div><h1>Papers</h1>
          <div class="ov-sub">Every target paper, shown by the claim the agent was asked to reproduce. One cell per agent, carrying the audit score of its run.</div></div></div>
        <div class="ps-head"><span class="plate">papers</span><span class="ps-count">${papers.length}</span>
          <span class="pm-legend">${["reproduced", "miss", "fault"].map((f) =>
            `<span class="lg-item ${f}"><span class="pm-chip ${f} sw-chip">·</span>${esc(V().meta(f).word)}</span>`).join("")}</span></div>
        <div class="tscroll"><table class="stats-table papers-table"><thead>${head}</thead>
          <tbody>${body || `<tr><td colspan="${4 + models.length}" class="empty small">No papers match.</td></tr>`}</tbody></table></div>`;
      host.querySelectorAll("tbody tr[data-arx]").forEach((tr) => {
        const open = () => window.go("#/paper/" + encodeURIComponent(tr.dataset.arx));
        tr.onclick = open;
        tr.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); open(); } };
      });
      host.querySelectorAll(".pm-chip[data-run]").forEach((b) => {
        b.onclick = (e) => { e.stopPropagation(); window.go("#/run/" + encodeURIComponent(b.dataset.run)); };
      });
    },

    renderPaper(arx) {
      const host = this.root();
      if (!host) return;
      const p = window.Data.byPaper[arx];
      if (!p) { host.innerHTML = `<div class="empty">That paper is not in this collection.</div>`; return; }
      const tier = window.Data.tier(p.tier);
      const runs = window.Data.runsForPaper(arx)
        .sort((a, b) => (b.audit_score == null ? -1 : b.audit_score) - (a.audit_score == null ? -1 : a.audit_score));
      const links = `${p.paper_url ? `<a href="${esc(p.paper_url)}" target="_blank" rel="noopener">paper↗</a>` : ""}${p.code_url ? `<a href="${esc(p.code_url)}" target="_blank" rel="noopener">code↗</a>` : ""}`;
      const rows = runs.map((r) => {
        const fam = V().ofRun(r);
        const score = r.audit_score == null ? "·"
          : `<span class="an-score ${r.audit_score >= 8 ? "yes" : r.audit_score >= 6 ? "over" : r.audit_score <= 0 ? "no" : "slate"}">${esc(r.audit_score)}<span>/10</span></span>`;
        return `<tr data-run="${esc(r.id)}" tabindex="0">
          <td class="s-model">${esc(r.model_name)}</td>
          <td>${V().inline(fam, V().word(r))}</td>
          <td class="num">${score}</td>
          <td class="mode-cell">${window.Modes.chip(r.mode)}</td>
          <td class="fuel-cell">${R.microFuelHtml(r)}</td>
          <td class="num tnum">${r.rounds == null ? "·" : esc(r.rounds)}</td></tr>`;
      }).join("");
      host.innerHTML = `<button class="crumb" id="pp-back">‹ all papers</button>
        <div class="spec-hero"><div class="spec-main">
          <div class="spec-tags">${p.tier ? `<span class="badge ${TIER_CLS[p.tier] || "slate"}">${esc(tier.name)}</span>` : ""}
            ${p.kind ? `<span class="schip">${esc(p.kind)}</span>` : ""}
            <a class="spec-arx" href="https://arxiv.org/abs/${esc(p.arxiv_id)}" target="_blank" rel="noopener">${esc(p.arxiv_id)} ↗</a>
            <span class="spec-links">${links}</span></div>
          <h1 class="spec-claim">${esc(p.claim || p.arxiv_id)}</h1>
          ${p.gist ? `<p class="an-d-gist">${esc(p.gist)}</p>` : ""}
          <div class="spec-band"><span class="plate">compute</span> predicted <b class="tnum">${p.predicted_h100 ? R.fmtHM(p.predicted_h100) : "not predicted"}</b>${p.band ? ` · band ${esc(p.band)}` : ""}</div>
          ${tier.what ? `<div class="spec-band"><span class="plate">tier</span> ${esc(tier.name)} · ${esc(tier.what)}</div>` : ""}
        </div></div>
        <div class="ps-head"><span class="plate">runs on this paper</span><span class="ps-count">${runs.length}</span></div>
        <div class="tscroll"><table class="stats-table runs-table"><thead><tr><th>agent</th><th>verdict</th><th class="num">score</th><th>failure mode</th><th>spent / budget</th><th class="num">rounds</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="6" class="empty small">No runs on this paper.</td></tr>`}</tbody></table></div>`;
      host.querySelector("#pp-back").onclick = () => window.go("#/papers");
      host.querySelectorAll("tbody tr[data-run]").forEach((tr) => {
        const open = () => window.go("#/run/" + encodeURIComponent(tr.dataset.run));
        tr.onclick = open;
        tr.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); open(); } };
      });
    },
  };

  window.PapersView = PapersView;
})();
