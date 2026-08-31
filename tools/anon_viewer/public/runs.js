/* runs.js: the runs table. Every published run as one sortable row: the claim it
   was asked to reproduce, the paper id, the agent, the tier, the audit score and
   verdict, the primary failure mode, rounds, spend against budget and tokens.
   The verdict, mode and text filters sit on top of the global Agent and Tier
   selects, and the resulting order is what the run page's prev and next follow. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict;
  const TIER_CLS = { run: "yes", retrain: "over", reimplement: "no" };

  const COLS = [
    { k: "claim", l: "claim" },
    { k: "arxiv_id", l: "paper" },
    { k: "model", l: "agent" },
    { k: "tier", l: "tier" },
    { k: "score", l: "score", num: true },
    { k: "verdict", l: "verdict" },
    { k: "mode", l: "failure mode" },
    { k: "rounds", l: "rounds", num: true },
    { k: "spent", l: "spent / budget", num: true },
    { k: "tokens", l: "tokens", num: true },
  ];

  const val = (r, k) => {
    switch (k) {
      case "score": return r.audit_score == null ? -1 : r.audit_score;
      case "verdict": return r.audit_verdict || "";
      case "mode": return window.Modes.rank(r.mode);
      case "spent": return r.spent_h100 == null ? -1 : r.spent_h100;
      case "tokens": return (r.tokens && r.tokens.total) || 0;
      case "model": return r.model_name || r.model || "";
      case "tier": return window.Data.tierRank(r.tier);
      default: return r[k] == null ? "" : r[k];
    }
  };
  const NUMERIC = { score: 1, rounds: 1, spent: 1, tokens: 1, tier: 1, mode: 1 };

  const Runs = {
    sortKey: "score", sortDir: -1,

    root() { return document.querySelector("#runs-root"); },

    ordered() {
      const S = window.State, q = (S.q || "").trim().toLowerCase();
      const rows = window.Data.runs.filter((r) =>
        (S.model === "all" || r.model === S.model) &&
        (S.tier === "all" || r.tier === S.tier) &&
        (S.verdict === "all" || r.audit_verdict === S.verdict) &&
        (S.mode === "all" || r.mode === S.mode) &&
        (!q || `${r.claim || ""} ${r.arxiv_id} ${r.model_name || ""} ${r.mode_name || ""} ${r.audit_verdict || ""}`.toLowerCase().includes(q)));
      const k = this.sortKey, dir = this.sortDir;
      return rows.sort((a, b) => {
        const x = val(a, k), y = val(b, k);
        const c = NUMERIC[k] ? (x - y) * dir : String(x).localeCompare(String(y)) * dir;
        return c || String(a.id).localeCompare(String(b.id));
      });
    },

    rowHtml(r) {
      const fam = V().ofRun(r);
      const score = r.audit_score == null ? "·"
        : `<span class="an-score ${r.audit_score >= 8 ? "yes" : r.audit_score >= 6 ? "over" : r.audit_score <= 0 ? "no" : "slate"}">${esc(r.audit_score)}<span>/10</span></span>`;
      const tok = (r.tokens && r.tokens.total) || null;
      return `<tr data-run="${esc(r.id)}" tabindex="0">
        <td class="pl-claim-cell"><span class="vg vd ${fam}">${V().meta(fam).glyph}</span><span class="pcell-claim">${esc(r.claim || r.arxiv_id)}</span></td>
        <td class="s-rid">${esc(r.arxiv_id)}</td>
        <td class="s-model">${esc(r.model_name || r.model)}</td>
        <td><span class="badge ${TIER_CLS[r.tier] || "slate"}">${esc(window.Data.tierName(r.tier))}</span></td>
        <td class="num">${score}</td>
        <td>${V().inline(fam, V().word(r))}</td>
        <td class="mode-cell">${window.Modes.chip(r.mode)}</td>
        <td class="num tnum">${r.rounds == null ? "·" : esc(r.rounds)}</td>
        <td class="fuel-cell">${R.microFuelHtml(r)}</td>
        <td class="num tnum">${R.fmtTok(tok)}</td>
      </tr>`;
    },

    bodyHtml(rows) {
      if (!rows.length) return `<tr><td colspan="${COLS.length}" class="empty small">No runs match these filters.</td></tr>`;
      return rows.map((r) => this.rowHtml(r)).join("");
    },

    headHtml() {
      return COLS.map((c) => {
        const on = this.sortKey === c.k;
        return `<th class="${c.num ? "num" : ""} ${on ? "sorted" : ""}" data-k="${c.k}" tabindex="0" role="button">${esc(c.l)}${on ? (this.sortDir < 0 ? " ▼" : " ▲") : ""}</th>`;
      }).join("");
    },

    filtersHtml() {
      const S = window.State;
      const verdicts = [...new Set(window.Data.runs.map((r) => r.audit_verdict).filter(Boolean))].sort();
      const modes = window.Modes.all.filter((m) => window.Data.runs.some((r) => r.mode === m.key));
      const opt = (v, l, cur) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(l)}</option>`;
      return `<div class="ps-filters">
        <select id="rn-verdict" aria-label="verdict">${[opt("all", "all verdicts", S.verdict)].concat(verdicts.map((v) => opt(v, v.replace(/_/g, " "), S.verdict))).join("")}</select>
        <select id="rn-mode" aria-label="failure mode">${[opt("all", "all failure modes", S.mode)].concat(modes.map((m) => opt(m.key, m.name, S.mode))).join("")}</select>
        <input id="rn-q" class="s-search" type="search" placeholder="search claim, paper or agent…" value="${esc(S.q)}" />
      </div>`;
    },

    render() {
      const host = this.root();
      if (!host) return;
      const rows = this.ordered();
      host.innerHTML = `
        <div class="ov-head">
          <div><h1>Runs</h1><div class="ov-sub">One row per reproduction run. Open a row for the transcript, the audit and the dissection.</div></div>
        </div>
        <div class="ps-head"><span class="plate">runs</span><span class="ps-count" id="rn-count">${rows.length} of ${window.Data.runs.length}</span>${this.filtersHtml()}</div>
        <div class="tscroll"><table class="stats-table runs-table"><thead><tr>${this.headHtml()}</tr></thead>
          <tbody id="rn-body">${this.bodyHtml(rows)}</tbody></table></div>`;
      this.wire();
    },

    renderBody() {
      const rows = this.ordered();
      const body = document.querySelector("#rn-body");
      const count = document.querySelector("#rn-count");
      if (body) body.innerHTML = this.bodyHtml(rows);
      if (count) count.textContent = `${rows.length} of ${window.Data.runs.length}`;
      this.wireRows();
      history.replaceState(null, "", window.runsHash());
    },

    wireRows() {
      document.querySelectorAll("#rn-body tr[data-run]").forEach((tr) => {
        const open = () => window.go("#/run/" + encodeURIComponent(tr.dataset.run));
        tr.onclick = open;
        tr.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); open(); } };
      });
    },

    wire() {
      const host = this.root();
      host.querySelectorAll("thead th[data-k]").forEach((th) => {
        const sort = () => {
          const k = th.dataset.k;
          if (this.sortKey === k) this.sortDir *= -1;
          else { this.sortKey = k; this.sortDir = COLS.find((c) => c.k === k).num ? -1 : 1; }
          this.render();
        };
        th.onclick = sort;
        th.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); } };
      });
      const v = host.querySelector("#rn-verdict");
      if (v) v.onchange = () => { window.State.verdict = v.value; this.renderBody(); };
      const m = host.querySelector("#rn-mode");
      if (m) m.onchange = () => { window.State.mode = m.value; this.renderBody(); };
      const q = host.querySelector("#rn-q");
      if (q) q.oninput = () => { window.State.q = q.value; this.renderBody(); };
      this.wireRows();
    },
  };

  window.Runs = Runs;
})();
