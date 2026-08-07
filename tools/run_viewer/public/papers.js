/* papers.js — the Papers tab. Two modes in one container:
   • list  — every paper shown BY ITS CLAIM, sortable, click to drill in;
   • specimen — one paper: claim hero + arxiv/links/predicted band + BALANCE +
     verdict stamp, then a runs table (each run = model · verdict glyph+word ·
     took/predicted ledger · rounds). Click a run to open its transcript. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict, Tr = () => window.Trace;
  const fmtHM = (n) => R.fmtHM(n);
  const TIER_CLS = { Easy: "yes", Medium: "over", Hard: "no" };

  const num = (v) => (v == null || v === "" ? null : Number(v));
  const tookOf = (run) => { let s = num(run.spent_h100); if (s == null) { const t = num(run.total_h100), rem = num(run.remaining_h100); if (t != null && rem != null) s = t - rem; } return s; };

  const Papers = {
    rows: null, busy: false, current: null, sortKey: "verdict", sortDir: -1, search: "", set: "all",

    root() { return document.querySelector("#papers-root"); },
    async open() {
      if (!this.root()) return;
      if (!window.RemoteSource || !window.RemoteSource.client) { this.root().innerHTML = `<div class="empty">Supabase isn't reachable — use the <b>Local</b> tab.</div>`; return; }
      if (window.Overview && window.Overview.rows) this.rows = window.Overview.rows;
      if (this.rows) { this.render(); } else { await this.load(); }
    },
    async load() {
      if (this.busy) return; this.busy = true;
      try { this.rows = await window.RemoteSource.listRuns(); } catch (e) {} finally { this.busy = false; this.render(); }
    },
    onTags() { if (this.root() && this.rows) this.render(); },
    onFreeze() { if (this.root() && this.rows) this.render(); },
    allPapers() {
      const rows = window.Freeze ? window.Freeze.filter(this.rows || []) : (this.rows || []);
      return window.Report.papers(rows).filter((p) => p.inDataset);
    },
    papers() { const ps = this.allPapers(); return this.set === "all" ? ps : ps.filter((p) => p.set === this.set); },

    openPaper(arxiv) { this.current = arxiv; if (this.rows) this.render(); else this.load(); },
    back() { this.current = null; this.render(); },

    // ---- list mode -----------------------------------------------------------
    COLS: [
      { k: "claim", l: "paper" }, { k: "verdict", l: "verdict" }, { k: "successCount", l: "runs ✓/n", num: true },
      { k: "model", l: "model" }, { k: "tier", l: "tier" }, { k: "set", l: "set" },
      { k: "predicted", l: "predicted", num: true }, { k: "took", l: "took", num: true }, { k: "delta", l: "Δ budget", num: true },
    ],
    sortPapers(papers) {
      const rank = { Easy: 1, Medium: 2, Hard: 3 }, k = this.sortKey, dir = this.sortDir;
      return [...papers].sort((a, b) => {
        if (k === "verdict") return ((b.reproduced ? 1 : 0) - (a.reproduced ? 1 : 0)) * dir;
        if (k === "tier") return ((rank[a.tier] || 9) - (rank[b.tier] || 9)) * dir;
        let x = a[k], y = b[k];
        const col = this.COLS.find((c) => c.k === k);
        if (col && col.num) { x = x == null ? -Infinity : x; y = y == null ? -Infinity : y; return (x - y) * dir; }
        return String(x || "").localeCompare(String(y || "")) * dir;
      });
    },
    listHtml() {
      const allP = this.allPapers(), all = this.papers();
      const q = this.search.trim().toLowerCase();
      const papers = this.sortPapers(all.filter((p) => !q || (`${p.claim || ""} ${p.arxiv_id} ${p.model}`).toLowerCase().includes(q)));
      const ths = this.COLS.map((c) => `<th class="${c.num ? "num" : ""} ${this.sortKey === c.k ? "sorted" : ""}" data-k="${c.k}">${esc(c.l)}${this.sortKey === c.k ? (this.sortDir < 0 ? " ▼" : " ▲") : ""}</th>`).join("");
      const body = papers.map((p) => {
        const m = V().meta(p.verdict);
        const dCls = p.delta == null ? "" : p.delta > 0 ? "rep-over" : "rep-under";
        return `<tr data-arx="${esc(p.arxiv_id)}">
          <td class="pl-claim-cell"><span class="vg vd ${p.verdict}">${m.glyph}</span><span class="pcell-claim">${esc(p.claim || p.arxiv_id)}</span><span class="s-rid">${esc(p.arxiv_id)}</span></td>
          <td>${V().inline(p.verdict)}</td>
          <td class="num tnum">${p.successCount}/${p.totalRuns}</td>
          <td class="s-model">${esc(p.model)}</td>
          <td>${p.tier ? `<span class="badge ${TIER_CLS[p.tier] || "slate"}">${esc(p.tier)}</span>` : "<span class='s-sub'>—</span>"}</td>
          <td>${p.set ? `<span class="set-badge ${p.set}">${esc(p.set)}</span>` : ""}</td>
          <td class="num tnum" title="${p.predicted} H100·h">${fmtHM(p.predicted)}${p.predicted != null && !p.predictedFromDataset ? ` <span class="s-sub">budget</span>` : ""}</td>
          <td class="num tnum" title="${p.took} H100·h">${fmtHM(p.took)}</td>
          <td class="num tnum ${dCls}">${p.delta == null ? "—" : (p.delta > 0 ? "+" : "−") + fmtHM(Math.abs(p.delta))}</td>
        </tr>`;
      }).join("");
      const cnt = (s) => allP.filter((p) => p.set === s).length;
      const seg = [["all", "all", allP.length], ["test", "test", cnt("test")], ["dev", "dev", cnt("dev")]]
        .map(([v, l, c]) => `<button class="seg-btn ${this.set === v ? "active" : ""}" data-set="${v}">${l}<span class="seg-c">${c}</span></button>`).join("");
      return `<div class="ov-head"><div><h1>Papers</h1><div class="ov-sub">${allP.length} papers in reprobench-splits — shown by the claim each agent is reproducing.</div></div>
        <div class="ov-actions"><div class="set-seg">${seg}</div><input id="pp-search" class="s-search" type="search" placeholder="search claim / arxiv / model…" value="${esc(this.search)}" /></div></div>
        <table class="stats-table papers-table"><thead><tr>${ths}</tr></thead><tbody>${body || `<tr><td colspan="9" class="empty small">No papers match.</td></tr>`}</tbody></table>`;
    },

    // ---- specimen mode -------------------------------------------------------
    specimenHtml(p) {
      const links = p.links || {};
      const linkBar = `${links.paper ? `<a href="${esc(links.paper)}" target="_blank" rel="noopener">⬇ paper</a>` : ""}${links.code ? `<a href="${esc(links.code)}" target="_blank" rel="noopener">⬇ code</a>` : ""}`;
      const est = window.Estimates ? window.Estimates.row(p.arxiv_id) : null;
      const band = est ? `<div class="spec-band"><span class="plate">predicted band</span> predicted <b class="tnum" title="${est.estimate} H100·h">${fmtHM(est.estimate)}</b> · audited <b class="tnum" title="${est.audited} H100·h">${fmtHM(est.audited)}</b>${est.band ? ` · band ${esc(est.band)} H100·h` : ""}${p.set ? ` · <span class="set-badge ${p.set}">${esc(p.set)}</span>` : ""}</div>` : "";
      const runs = p.runs.slice().sort((a, b) => (tookOf(a) ?? Infinity) - (tookOf(b) ?? Infinity));
      const rowsHtml = runs.map((run) => {
        const fam = V().ofRun(run), took = tookOf(run);
        const rl = run.exit_reason === "round_limit";
        return `<tr data-run="${esc(run.run_id)}">
          <td>${V().inline(fam, V().word(run))}</td>
          <td class="s-model">${esc(run.model || "—")}</td>
          <td>${Tr().ledger(took, p.predicted, { pct: true })}</td>
          <td class="num tnum" title="${took} / ${p.predicted} H100·h">${fmtHM(took)} / ${fmtHM(p.predicted)}</td>
          <td class="num tnum">${run.tool_rounds_used ?? "—"}${rl ? ` <span class="badge over" title="hit the tool-round limit">⚠</span>` : ""}</td>
          <td class="s-rid">${esc(run.run_id)}</td></tr>`;
      }).join("");
      return `<button class="crumb" id="pp-back">‹ all papers</button>
        <div class="spec-hero">
          <div class="spec-main">
            <div class="spec-tags">${p.tier ? `<span class="badge ${TIER_CLS[p.tier] || "slate"}">${esc(p.tier)}</span>` : ""}${p.kind ? `<span class="schip">${esc(p.kind)}</span>` : ""}<span class="spec-arx">${esc(p.arxiv_id)}</span><span class="spec-links">${linkBar}</span></div>
            <h1 class="spec-claim">${esc(p.claim || p.arxiv_id)}</h1>
            ${band}
            <div class="spec-balance">${V().balance(p.took, p.predicted, { lead: true }) || `<span class="s-sub">not reproduced yet — no spent compute to balance</span>`}</div>
          </div>
          <div class="spec-stamp">${V().stamp(p.verdict, p.reproduced ? "REPRODUCED" : null)}</div>
        </div>
        <div class="ps-head"><span class="plate">runs on this paper</span><span class="ps-count">${p.totalRuns}</span></div>
        <table class="stats-table runs-table"><thead><tr><th>verdict</th><th>model</th><th>took vs predicted</th><th class="num">H100·h</th><th class="num">rounds</th><th>run id</th></tr></thead><tbody>${rowsHtml}</tbody></table>`;
    },

    render() {
      const el = this.root(); if (!el) return;
      if (this.current) {
        const p = this.papers().find((x) => x.arxiv_id === this.current);
        if (!p) { this.current = null; return this.render(); }
        el.innerHTML = this.specimenHtml(p);
        el.querySelector("#pp-back").onclick = () => this.back();
        el.querySelectorAll(".runs-table tbody tr").forEach((tr) => tr.onclick = () => window.openRun && window.openRun(tr.dataset.run));
      } else {
        el.innerHTML = this.listHtml();
        const s = el.querySelector("#pp-search");
        if (s) {
          if (this._refocus) { s.focus(); const v = s.value; s.setSelectionRange(v.length, v.length); this._refocus = false; }
          s.oninput = () => { this.search = s.value; this._refocus = true; this.render(); };
        }
        el.querySelectorAll(".seg-btn").forEach((b) => b.onclick = () => { this.set = b.dataset.set; this.render(); });
        el.querySelectorAll(".papers-table thead th").forEach((th) => th.onclick = () => {
          if (this.sortKey === th.dataset.k) this.sortDir *= -1; else { this.sortKey = th.dataset.k; this.sortDir = this.COLS.find((c) => c.k === th.dataset.k).num ? -1 : 1; }
          this.render();
        });
        el.querySelectorAll(".papers-table tbody tr[data-arx]").forEach((tr) => tr.onclick = () => this.openPaper(tr.dataset.arx));
      }
    },
  };

  window.Papers = Papers;
})();
