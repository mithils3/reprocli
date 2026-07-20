/* analysis.js — the Analysis tab. Three modes in one container, mirroring Papers:
   • list   — a card per uploaded sweep (repro_sweeps): tier · freeze · failure-mix
              strip · mean score. Click to open the report.
   • report — one sweep: header + freeze caveat + headline stat cards + per-band
              table + failure-mode bars + a grid of per-paper cards.
   • paper  — one paper's full dissection (delegated to AnalysisDetail).
   Data: RemoteSource.listSweeps / loadSweep (anon read). Detail helpers + the
   failure-mode/verdict/score vocabulary live in analysis_detail.js. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict, D = () => window.AnalysisDetail;
  const fmtHM = (n) => R.fmtHM(n);
  const TIER = { Easy: "yes", Medium: "over", Hard: "no" };

  const tierBadge = (t) => t ? `<span class="badge ${TIER[t] || "slate"}">${esc(t)}</span>` : "";
  const freezeChip = (f) => f ? `<span class="schip an-frozen">post-freeze</span>` : `<span class="schip non-frozen">pre-freeze</span>`;
  const panel = (title, body) => `<section class="panel-card"><div class="pc-head"><span class="plate">${esc(title)}</span></div>${body}</section>`;

  const Analysis = {
    sweeps: null, busy: false, view: "list", data: null, cur: null,

    root() { return document.querySelector("#analysis-root"); },
    open() {
      if (!this.root()) return;
      if (!window.RemoteSource || !window.RemoteSource.client) { this.root().innerHTML = `<div class="empty">Supabase isn't reachable — use the <b>Local</b> tab.</div>`; return; }
      if (this.view === "report" && this.data) return this.cur ? this.renderPaper() : this.renderReport();
      if (this.sweeps) this.renderList(); else this.loadList();
    },
    async loadList() {
      if (this.busy) return; this.busy = true;
      this.root().innerHTML = `<div class="empty">Loading analyses…</div>`;
      try { this.sweeps = await window.RemoteSource.listSweeps(); }
      catch (e) { this.root().innerHTML = `<div class="empty">Could not load analyses: ${esc(e.message || e)}</div>`; return; }
      finally { this.busy = false; }
      this.renderList();
    },

    // ---- list of sweeps ------------------------------------------------------
    renderList() {
      const el = this.root(); this.view = "list"; this.data = null; this.cur = null;
      const s = this.sweeps || [];
      el.innerHTML = `<div class="ov-head"><div><h1>Analysis</h1><div class="ov-sub">Post-hoc dissections of finished repro-agent sweeps — one card per report. Each drills into a per-paper read of what the agent did, what the S7 auditor found, and where the two diverge.</div></div></div>
        ${s.length ? `<div class="an-sweeps">${s.map((sw) => this.sweepCard(sw)).join("")}</div>`
          : `<div class="empty">No sweeps uploaded yet. Run the <code>analyze-sweep</code> skill's <code>upload.py</code> to publish one.</div>`}`;
      el.querySelectorAll("[data-slug]").forEach((c) => c.onclick = () => this.openReport(c.dataset.slug));
    },
    sweepCard(sw) {
      const agg = sw.aggregates || {}, mean = sw.mean_audit_score;
      return `<button class="an-sweep-card" data-slug="${esc(sw.slug)}">
        <div class="an-sc-top">${tierBadge(sw.tier)}${freezeChip(sw.frozen)}<span class="an-sc-count">${sw.run_count || 0} papers</span></div>
        <div class="an-sc-title">${esc(sw.title)}</div>
        ${sw.subtitle ? `<div class="an-sc-sub">${esc(sw.subtitle)}</div>` : ""}
        ${this.fmStrip(agg.failure_modes || {}, sw.run_count)}
        <div class="an-sc-foot"><span class="an-sc-mean"><b>${mean == null ? "—" : mean}</b><span>/10 mean</span></span>${sw.model ? `<span class="an-sc-model">${esc(sw.model)}</span>` : ""}</div>
      </button>`;
    },
    fmStrip(fm, total) {
      const keys = Object.keys(fm);
      if (!keys.length) return `<div class="an-fmbar empty"></div>`;
      const n = total || keys.reduce((a, k) => a + fm[k], 0) || 1;
      return `<div class="an-fmbar" title="failure-mode mix">${keys.map((k) => {
        const [v] = D().fmMeta(k);
        return `<span class="an-fmseg fmv-${v}" style="width:${100 * fm[k] / n}%" title="${esc(k)}: ${fm[k]}"></span>`;
      }).join("")}</div>`;
    },

    // ---- one sweep report ----------------------------------------------------
    async openReport(slug) {
      this.view = "report"; this.cur = null;
      const el = this.root(); el.innerHTML = `<div class="empty">Loading ${esc(slug)}…</div>`;
      try { this.data = await window.RemoteSource.loadSweep(slug); }
      catch (e) { el.innerHTML = `<div class="empty">Could not load: ${esc(e.message || e)}</div>`; return; }
      this.renderReport();
      if (window.scheduleJumpUpdate) window.scheduleJumpUpdate();
    },
    backToList() { this.view = "list"; this.data = null; this.cur = null; this.renderList(); },
    openPaper(runId) { this.cur = runId; this.renderPaper(); },
    backToReport() { this.cur = null; this.renderReport(); },

    renderReport() {
      const el = this.root(); const { sweep, analyses } = this.data;
      el.innerHTML = this.reportHtml(sweep, analyses, sweep.aggregates || {});
      el.querySelector("#an-back").onclick = () => this.backToList();
      el.querySelectorAll("[data-run]").forEach((c) => c.onclick = () => this.openPaper(c.dataset.run));
      if (window.scheduleJumpUpdate) window.scheduleJumpUpdate();
    },
    reportHtml(sweep, analyses, agg) {
      const cav = sweep.frozen
        ? `<div class="an-caveat frozen">Post-freeze — dataset (2026-07-13) and rubric (2026-07-16) frozen. Paper-eligible results.</div>`
        : `<div class="an-caveat pre">Pre-freeze — process validation, <b>not</b> a paper result. Numbers may shift after re-pin.</div>`;
      const pdf = sweep.report_pdf_url ? `<a class="an-link" href="${esc(sweep.report_pdf_url)}" target="_blank" rel="noopener">⬇ source PDF</a>` : "";
      const grid = analyses.map((a) => this.paperCard(a, this.data.runsById[a.run_id])).join("");
      return `<button class="crumb" id="an-back">‹ all analyses</button>
        <div class="an-r-head"><div class="an-r-tags">${tierBadge(sweep.tier)}${freezeChip(sweep.frozen)}${sweep.batch_id ? `<span class="schip">${esc(sweep.batch_id)}</span>` : ""}<span class="an-r-links">${pdf}</span></div>
          <h1 class="an-r-title">${esc(sweep.title)}</h1>
          ${sweep.subtitle ? `<div class="an-r-sub">${esc(sweep.subtitle)}${sweep.model ? ` · ${esc(sweep.model)}` : ""}</div>` : ""}</div>
        ${cav}${this.reportFacts(agg)}
        <div class="an-r-grid2">${panel("by budget band", this.bandsTable(agg))}${panel("failure modes", this.fmDist(agg, sweep.run_count))}</div>
        <div class="ps-head"><span class="plate">papers</span><span class="ps-count">${analyses.length}</span><span class="an-legend">click a paper for its full dissection</span></div>
        <div class="paper-grid an-paper-grid">${grid}</div>`;
    },
    reportFacts(agg) {
      const v = agg.verdicts || {}, sc = agg.self_claim || {};
      const cards = [
        ["mean score", agg.mean_audit_score == null ? "—" : `${agg.mean_audit_score}<span class="an-u">/10</span>`],
        ["papers", agg.n_papers != null ? agg.n_papers : (agg.n_runs != null ? agg.n_runs : "—")],
        ["reproduced", agg.n_reproduced != null ? agg.n_reproduced : 0],
        ["disqualified", v.disqualified || 0, (v.disqualified || 0) > 0 ? "warn" : ""],
        ["overclaimed", sc.not_honest != null ? sc.not_honest : 0, (sc.not_honest || 0) > 0 ? "warn" : ""],
        ["compute", `${fmtHM(agg.spent_h100_total)}<span class="an-u"> / ${fmtHM(agg.budget_h100_total)}</span>`],
      ];
      return `<div class="stat-cards">${cards.map(([l, vv, w]) => `<div class="stat-card ${w || ""}"><div class="sc-v">${vv}</div><div class="sc-l">${esc(l)}</div></div>`).join("")}</div>`;
    },
    bandsTable(agg) {
      const b = agg.by_budget_band || {}, keys = Object.keys(b);
      if (keys.length < 2) return `<p class="muted an-pad">Single budget band — see the headline cards.</p>`;
      const rows = keys.map((k) => {
        const x = b[k], vd = Object.entries(x.verdicts || {}).map(([n, c]) => `${n} ${c}`).join(", ");
        return `<tr><td>${esc(k)}</td><td class="num">${x.n}</td><td class="num">${x.mean_audit_score == null ? "—" : x.mean_audit_score}</td><td class="an-vd-cell">${esc(vd)}</td><td class="num">${fmtHM(x.spent_h100)}</td></tr>`;
      }).join("");
      return `<table class="stats-table an-band-table"><thead><tr><th>band</th><th class="num">n</th><th class="num">mean</th><th>verdicts</th><th class="num">spent</th></tr></thead><tbody>${rows}</tbody></table>`;
    },
    fmDist(agg, total) {
      const fm = agg.failure_modes || {}, keys = Object.keys(fm);
      if (!keys.length) return `<p class="muted an-pad">—</p>`;
      const max = Math.max.apply(null, keys.map((k) => fm[k]));
      return `<div class="an-fmrows">${keys.map((k) => {
        const [v, l] = D().fmMeta(k);
        return `<div class="an-fmrow"><span class="an-fmlabel">${esc(l)}</span><span class="an-fmtrack"><i class="fmv-${v}" style="width:${100 * fm[k] / max}%"></i></span><span class="an-fmn">${fm[k]}</span></div>`;
      }).join("")}</div>`;
    },
    paperCard(a, run) {
      const dd = D(), verdict = (run && run.audit_verdict) || (a.audit_summary || {}).verdict;
      const fam = dd.verdictFam(verdict), m = V().meta(fam);
      const score = run && run.audit_score != null ? run.audit_score : (a.audit_summary || {}).score;
      return `<button class="paper-card an-paper-card" data-run="${esc(a.run_id)}">
        <div class="pcd-top"><span class="vg vd ${fam}" title="${esc(verdict || "")}">${m.glyph}</span>${dd.fmBadge(a.failure_mode)}${dd.scoreChip(score)}</div>
        <div class="pcd-claim">${esc(a.target_claim || a.paper_gist || a.arxiv_id || a.run_id)}</div>
        <div class="pcd-foot"><span class="pcd-arx">${esc(a.arxiv_id || "")}</span></div>
      </button>`;
    },

    // ---- one paper's dissection ----------------------------------------------
    renderPaper() {
      const el = this.root(); const a = (this.data.analyses || []).find((x) => x.run_id === this.cur);
      if (!a) { this.cur = null; return this.renderReport(); }
      const run = this.data.runsById[a.run_id];
      el.innerHTML = `<button class="crumb" id="an-pback">‹ ${esc(this.data.sweep.title)}</button><div class="an-detail">${D().html(a, run)}</div>`;
      el.querySelector("#an-pback").onclick = () => this.backToReport();
      D().wire(el.querySelector(".an-detail"), a, run);
      if (window.scheduleJumpUpdate) window.scheduleJumpUpdate();
    },
  };

  window.Analysis = Analysis;
})();
