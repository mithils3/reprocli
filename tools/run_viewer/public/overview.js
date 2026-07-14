/* overview.js — THE WORKSHEET (default landing). States the benchmark thesis up
   top — average-audit-score gauge + a dual-track took-vs-predicted compute ledger
   with the IN-THE-BLACK/RED balance — then a model×tier matrix, the secondary
   scatter, and a grid of paper small-multiples shown BY THEIR CLAIM. Click a paper
   to open its specimen page. Pure presentation over Report.papers() aggregation. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict, C = () => window.Charts, Tr = () => window.Trace;
  const fmtH = (n) => n == null ? "—" : (Math.round(n * 1000) / 1000).toLocaleString();
  const TIERS = ["Easy", "Medium", "Hard"];
  const TIER_CLS = { Easy: "yes", Medium: "over", Hard: "no" };

  const Overview = {
    rows: null, busy: false, msg: "", search: "", tier: "all", verdict: "all", sort: "tier", set: "all", model: "all",

    root() { return document.querySelector("#overview-root"); },

    async open() {
      if (!this.root()) return;
      if (!window.RemoteSource || !window.RemoteSource.client) {
        this.root().innerHTML = `<div class="empty">Supabase isn't reachable — open the <b>Local</b> tab to read a saved transcript.</div>`; return;
      }
      if (this.rows) { this.render(); this.load(true); } else this.load(false);
    },
    async load(force) {
      if (this.busy) return;
      if (this.rows && !force) { this.render(); return; }
      this.busy = true; this.msg = "loading runs…"; if (this.rows) this.render();
      try { this.rows = await window.RemoteSource.listRuns(); this.msg = ""; }
      catch (e) { this.msg = "error: " + (e.message || e); }
      finally { this.busy = false; this.render(); }
    },
    onTags() { if (this.root() && this.rows) this.render(); },
    onFreeze() { if (this.root() && this.rows) this.render(); },

    overviewRuns() {
      const rs = this.rows || [];
      return window.Freeze ? window.Freeze.filter(rs) : rs;
    },
    // the model dropdown scopes the WHOLE worksheet: runs are filtered by model
    // BEFORE per-paper aggregation, so gauge/ledger/matrix/cards all reflect it
    modelRuns() { const rs = this.overviewRuns(); return this.model === "all" ? rs : rs.filter((r) => r.model === this.model); },
    models() {
      const E = window.Estimates;
      return [...new Set(this.overviewRuns().filter((r) => r.model && (!E || E.row(r.arxiv_id))).map((r) => r.model))].sort();
    },
    // only papers present in reprobench-splits (have a lockfile row); then by set
    allPapers() { return window.Report.papers(this.modelRuns()).filter((p) => p.inDataset); },
    papers() { const ps = this.allPapers(); return this.set === "all" ? ps : ps.filter((p) => p.set === this.set); },
    setRuns() { const ok = new Set(this.papers().map((p) => p.arxiv_id)); return this.modelRuns().filter((r) => ok.has(r.arxiv_id)); },

    visible(papers) {
      const q = this.search.trim().toLowerCase();
      return papers.filter((p) =>
        (this.tier === "all" || (p.tier || "untiered") === this.tier) &&
        (this.verdict === "all" || p.verdict === this.verdict) &&
        (!q || (`${p.claim || ""} ${p.arxiv_id} ${p.model}`).toLowerCase().includes(q)));
    },
    sortPapers(papers) {
      const rank = { Easy: 1, Medium: 2, Hard: 3, untiered: 9 };
      const arr = [...papers];
      if (this.sort === "tier") arr.sort((a, b) => (rank[a.tier || "untiered"] - rank[b.tier || "untiered"]) || (b.reproduced - a.reproduced));
      else if (this.sort === "delta") arr.sort((a, b) => (a.delta ?? Infinity) - (b.delta ?? Infinity));
      else if (this.sort === "claim") arr.sort((a, b) => String(a.claim || a.arxiv_id).localeCompare(String(b.claim || b.arxiv_id)));
      else arr.sort((a, b) => (b.reproduced - a.reproduced) || (a.delta ?? 0) - (b.delta ?? 0));
      return arr;
    },

    thesisHtml(papers, sm) {
      const stampFam = sm.took == null ? "idle" : (sm.took <= (sm.predicted ?? Infinity) ? "reproduced" : "miss");
      const stampLbl = sm.took == null ? "NO DATA" : (sm.took <= (sm.predicted ?? Infinity) ? "UNDER BUDGET" : "OVER BUDGET");
      return `<section class="thesis">
        <div class="thesis-card gauge-card">
          ${C().arcGauge(sm.avgScore ?? 0, 10, { num: sm.avgScore == null ? "—" : `${sm.avgScore}/10`, pct: sm.scorePct == null ? "no grades yet" : `${sm.scorePct}%`, label: `average audit score ${sm.avgScore ?? "—"} of 10` })}
          <div class="gauge-cap"><b>avg audit score</b><span>${sm.gradedRuns} graded runs · ${sm.reproduced}/${sm.total} papers reproduced</span></div>
        </div>
        <div class="thesis-card ledger-card">
          <div class="lc-head"><span class="plate">compute ledger</span><span class="lc-sub">reproduced papers</span>${V().stamp(stampFam, stampLbl)}</div>
          <div class="lc-row"><span class="lc-l">took</span>${Tr().ledger(sm.took, sm.predicted, { size: "lg", pct: true })}<span class="lc-v tnum" title="${sm.took} H100·h">${R.fmtHM(sm.took)}</span></div>
          <div class="lc-row"><span class="lc-l">predicted</span><span class="lc-predbar"></span><span class="lc-v tnum" title="${sm.predicted} H100·h">${R.fmtHM(sm.predicted)}</span></div>
          <div class="lc-balance">${V().balance(sm.took, sm.predicted, { lead: true })}<span class="lc-eff">efficiency <b class="tnum">${sm.efficiency == null ? "—" : sm.efficiency + "%"}</b></span></div>
        </div>
      </section>`;
    },

    matrixHtml(papers) {
      const mt = window.Report.modelTier(this.setRuns());
      const head = `<tr><th></th>${mt.tiers.map((t) => `<th class="mt-tier"><span class="badge ${TIER_CLS[t] || "slate"}">${esc(t)}</span></th>`).join("")}</tr>`;
      const body = mt.models.map((m) => {
        const sc = mt.score(m);
        const chip = sc ? `<span class="mt-score tnum" title="avg audit score ${sc.avg}/10 over ${sc.graded} graded run${sc.graded === 1 ? "" : "s"}">${sc.pct}%</span>` : "";
        return `<tr><td class="mt-model">${esc(m)}${chip}</td>${mt.tiers.map((t) => {
          const c = mt.get(m, t);
          if (!c) return `<td class="mt-cell empty">·</td>`;
          const pc = c.total ? (c.repro / c.total) * 100 : 0;
          return `<td class="mt-cell"><span class="mt-frac tnum">${c.repro}/${c.total}</span><span class="mt-bar"><i style="width:${pc.toFixed(0)}%"></i></span></td>`;
        }).join("")}</tr>`;
      }).join("");
      const ts = window.Report.tierStats(papers);
      const tierChips = ts.keys.map((k) => `<span class="tier-stat"><span class="badge ${TIER_CLS[k] || "slate"}">${esc(k)}</span><b class="tnum">${ts.stats[k].repro}</b><span class="s-sub">/${ts.stats[k].total}</span></span>`).join("");
      return `<section class="grid2">
        <div class="panel-card">
          <div class="pc-head"><span class="plate">reproduced by model × tier</span><span class="lc-sub">% = avg audit score of graded runs</span></div>
          <table class="matrix">${head}${body}</table>
          <div class="tier-breakdown">${tierChips}</div>
        </div>
        <div class="panel-card">
          <div class="pc-head"><span class="plate">took vs predicted</span><span class="lc-sub">log–log · dot = paper · ┄ on-budget</span></div>
          ${C().scatter(papers.filter((p) => p.reproduced))}
        </div>
      </section>`;
    },

    paperCardHtml(p) {
      const m = V().meta(p.verdict);
      const links = p.links || {};
      const lk = (links.code || links.paper) ? `<span class="pc-links">${links.paper ? `<a href="${esc(links.paper)}" target="_blank" rel="noopener" title="paper">paper↗</a>` : ""}${links.code ? `<a href="${esc(links.code)}" target="_blank" rel="noopener" title="code">code↗</a>` : ""}</span>` : "";
      return `<button class="paper-card" data-arx="${esc(p.arxiv_id)}">
        <div class="pcd-top"><span class="vg vd ${p.verdict}" title="${esc(m.word)}">${m.glyph}</span>
          ${p.tier ? `<span class="badge ${TIER_CLS[p.tier] || "slate"}">${esc(p.tier)}</span>` : ""}
          ${p.set ? `<span class="set-badge ${p.set}">${esc(p.set)}</span>` : ""}
          ${p.auditScore != null ? `<span class="badge ${p.verdict === "reproduced" ? "yes" : p.verdict === "miss" ? "over" : "no"}" title="Stage-7 auditor${p.auditReportedScore != null ? ` — capped from ${p.auditReportedScore}/10` : ""}${p.auditVerdict ? ` · ${esc(p.auditVerdict)}` : ""}">${p.auditScore}/10${p.auditFlag ? " ⚑" : ""}</span>` : ""}
          <span class="pcd-runs">${p.successCount}/${p.totalRuns}</span></div>
        <div class="pcd-claim">${esc(p.claim || "(" + p.arxiv_id + ")")}</div>
        <div class="pcd-foot">${Tr().ledger(p.took, p.predicted, { pct: p.reproduced })}
          <span class="pcd-arx">${esc(p.arxiv_id)}</span>${lk}</div>
      </button>`;
    },

    legendHtml() {
      const g = (f, t) => { const m = V().meta(f); return `<span class="lg-item ${f}"><span class="vg">${m.glyph}</span>${t}</span>`; };
      return `<div class="vd-legend">${g("reproduced", "reproduced")}${g("miss", "miss / over-budget")}${g("fault", "fault")}${g("idle", "never ran")}<span class="lg-item"><i class="lg-pred-swatch"></i>predicted ceiling</span></div>`;
    },

    render() {
      const el = this.root(); if (!el) return;
      const brand = document.querySelector("#brand-count");
      const allP = this.allPapers();
      const papers = this.papers(), sm = window.Report.summary(papers);
      // brand badge stays global — it names the site, not the current filter
      const brandP = window.Report.papers(this.overviewRuns()).filter((p) => p.inDataset);
      if (brand) brand.textContent = `${brandP.length} papers · ${brandP.reduce((a, p) => a + p.totalRuns, 0)} runs`;
      const opts = (arr, cur) => arr.map(([v, l]) => `<option value="${v}" ${v === cur ? "selected" : ""}>${esc(l)}</option>`).join("");
      const cnt = (s) => allP.filter((p) => p.set === s).length;
      const seg = [["all", "all", allP.length], ["test", "test", cnt("test")], ["dev", "dev", cnt("dev")]]
        .map(([v, l, c]) => `<button class="seg-btn ${this.set === v ? "active" : ""}" data-set="${v}">${l}<span class="seg-c">${c}</span></button>`).join("");
      const vis = this.sortPapers(this.visible(papers));
      el.innerHTML = `
        <div class="ov-head">
          <div><h1>Reproduction worksheet</h1>
            <div class="ov-sub">Agents reproducing ML papers from <b>reprobench-splits</b> under a fixed H100·h budget — each curve is a run burning compute toward the paper's claim. ${esc(this.busy ? this.msg : "")}</div></div>
          <div class="ov-actions"><div class="set-seg" title="filter by dataset split">${seg}</div><select id="ov-model" title="scope the whole worksheet to one agent model">${opts([["all", "all models"], ...this.models().map((m) => [m, m])], this.model)}</select><button id="ov-csv" class="filt">⬇ CSV</button><button id="ov-refresh" class="filt" ${this.busy ? "disabled" : ""}>↻</button></div>
        </div>
        ${this.thesisHtml(papers, sm)}
        ${this.matrixHtml(papers)}
        <section class="papers-section">
          <div class="ps-head"><span class="plate">papers</span><span class="ps-count">${vis.length} of ${papers.length}</span>
            <div class="ps-filters">
              <select id="ov-tier">${opts([["all", "all tiers"], ["Easy", "Easy"], ["Medium", "Medium"], ["Hard", "Hard"]], this.tier)}</select>
              <select id="ov-verdict">${opts([["all", "all verdicts"], ["reproduced", "reproduced"], ["miss", "miss"], ["fault", "fault"], ["idle", "never ran"]], this.verdict)}</select>
              <select id="ov-sort">${opts([["tier", "sort: tier"], ["repro", "sort: reproduced"], ["delta", "sort: Δ budget"], ["claim", "sort: claim"]], this.sort)}</select>
              <input id="ov-search" class="s-search" type="search" placeholder="search claim / arxiv / model…" value="${esc(this.search)}" />
            </div>
          </div>
          ${this.legendHtml()}
          <div class="paper-grid">${vis.map((p) => this.paperCardHtml(p)).join("") || `<div class="empty small">No papers match.</div>`}</div>
        </section>`;
      this.wire(papers);
    },

    wire(papers) {
      const el = this.root();
      const cv = el.querySelector("#ov-csv"); if (cv) cv.onclick = () => window.Report.download(this.papers());
      const rf = el.querySelector("#ov-refresh"); if (rf) rf.onclick = () => this.load(true);
      const bind = (id, key, rerender) => { const e = el.querySelector(id); if (e) e.oninput = e.onchange = () => { this[key] = e.value; rerender ? this.render() : this.renderGrid(); }; };
      bind("#ov-tier", "tier"); bind("#ov-verdict", "verdict"); bind("#ov-sort", "sort"); bind("#ov-search", "search");
      bind("#ov-model", "model", true);
      el.querySelectorAll(".seg-btn").forEach((b) => b.onclick = () => { this.set = b.dataset.set; this.render(); });
      el.querySelectorAll(".paper-card").forEach((b) => b.onclick = () => window.openPaper && window.openPaper(b.dataset.arx));
    },
    renderGrid() {
      const host = this.root() && this.root().querySelector(".paper-grid");
      if (!host) return this.render();
      const vis = this.sortPapers(this.visible(this.papers()));
      const cnt = this.root().querySelector(".ps-count"); if (cnt) cnt.textContent = `${vis.length} of ${this.papers().length}`;
      host.innerHTML = vis.map((p) => this.paperCardHtml(p)).join("") || `<div class="empty small">No papers match.</div>`;
      host.querySelectorAll(".paper-card").forEach((b) => b.onclick = () => window.openPaper && window.openPaper(b.dataset.arx));
    },
  };

  window.Overview = Overview;
})();
