/* report.js — the Reproduced tab. Groups runs by paper (arxiv_id) and uses the
   user's "success" tag (set from the Live / Stats views) as the reproduced
   signal: a paper counts as reproduced once any of its runs carries that tag.
   For each paper it shows the H100·h the successful run *took* (its spent
   compute) against what was *predicted* — the lockfile's h100_hours_estimate
   from the Mithilss/reprobench-splits dataset (see estimates.js), falling back
   to the run budget when a paper isn't in the dataset. Exports the table as CSV.
   Kept separate so app.js stays a wiring layer; reuses the Stats classes. */
"use strict";

(function () {
  const R = window.RENDER;
  const esc = R.esc;
  const num = (v) => (v == null || v === "" ? null : Number(v));
  const round = (n) => (n == null ? null : Math.round(n * 1000) / 1000);
  const fmtH = (n) => (n == null ? "—" : round(n).toLocaleString());
  const pct = (a, b) => (a == null || !b ? null : Math.round((a / b) * 100));
  const DEFAULT_SUCCESS = "success";

  // lockfile difficulty tiers — colour + ordering (Easy < Medium < Hard)
  const TIER_CLASS = { Easy: "yes", Medium: "unk", Hard: "no" };
  const TIER_RANK = { Easy: 1, Medium: 2, Hard: 3 };
  const TIER_ORDER = ["Easy", "Medium", "Hard"];

  const budgetOf = (run) => num(run.budget) ?? num(run.total_h100);
  function tookOf(run) {
    let s = num(run.spent_h100);
    if (s == null) {
      const t = num(run.total_h100), rem = num(run.remaining_h100);
      if (t != null && rem != null) s = t - rem;
    }
    return s;
  }
  const maxOf = (runs, f) => runs.reduce((m, r) => { const v = f(r); return v != null && (m == null || v > m) ? v : m; }, null);
  const csvCell = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };

  const COLS = [
    { key: "arxiv_id", label: "paper" },
    { key: "reproduced", label: "reproduced", num: true, tip: "has a run tagged with the success tag" },
    { key: "successCount", label: "runs ✓ / n", num: true, tip: "successful runs / total runs for this paper" },
    { key: "model", label: "model" },
    { key: "tier", label: "tier", tip: "lockfile difficulty tier (Easy / Medium / Hard), set from the audited H100·h band" },
    { key: "predicted", label: "predicted H100·h", num: true, tip: "lockfile h100_hours_estimate (Mithilss/reprobench-splits); falls back to the run budget" },
    { key: "took", label: "took H100·h", num: true, tip: "compute the successful run actually spent" },
    { key: "delta", label: "Δ vs predicted", num: true, tip: "took − predicted (negative = came in under budget)" },
  ];

  const Report = {
    rows: null, papers: null, busy: false, msg: "",
    search: "", successTag: DEFAULT_SUCCESS, onlyRepro: false,
    sortKey: "reproduced", sortDir: -1,

    root() { return document.querySelector("#report-root"); },

    async open() {
      const el = this.root();
      if (!el) return;
      if (!window.RemoteSource || !window.RemoteSource.client) {
        el.innerHTML = `<div class="empty">Supabase isn't reachable, so there are no runs to report on. Configure <code>config.js</code> or use the <b>Local file</b> tab.</div>`;
        return;
      }
      if (this.rows) { this.render(); this.load(true); }   // show cached, refresh in background
      else this.load(false);
    },

    async load(force) {
      if (this.busy) return;
      if (this.rows && !force) { this.render(); return; }
      this.busy = true; this.msg = "loading runs…"; this.render();
      try {
        this.rows = await window.RemoteSource.listRuns();
        this.msg = "";
      } catch (e) { this.msg = "error: " + (e.message || e); }
      finally { this.busy = false; this.render(); }
    },

    // ---- grouping: one row per paper -----------------------------------------
    buildPapers() {
      const T = window.Tags, tag = this.successTag;
      const groups = new Map();
      for (const run of (this.rows || [])) {
        const id = run.arxiv_id || "?";
        if (!groups.has(id)) groups.set(id, []);
        groups.get(id).push(run);
      }
      const papers = [];
      for (const [arxiv_id, runs] of groups) {
        const successRuns = runs.filter((r) => T && T.has(r.run_id, tag));
        const reproduced = successRuns.length > 0;
        // canonical reproduction = the cheapest successful run
        const chosen = reproduced
          ? successRuns.slice().sort((a, b) => (tookOf(a) ?? Infinity) - (tookOf(b) ?? Infinity))[0]
          : null;
        const models = [...new Set(runs.map((r) => r.model).filter(Boolean))];
        // predicted = lockfile h100_hours_estimate; fall back to the run budget
        const estRow = window.Estimates ? window.Estimates.row(arxiv_id) : null;
        const fromDataset = estRow ? estRow.estimate : null;
        const predicted = fromDataset != null ? fromDataset : (chosen ? budgetOf(chosen) : maxOf(runs, budgetOf));
        const took = chosen ? tookOf(chosen) : null;
        papers.push({
          arxiv_id, reproduced, successCount: successRuns.length, totalRuns: runs.length,
          model: chosen ? (chosen.model || "—") : (models.join(", ") || "—"),
          tier: estRow ? estRow.tier : null, band: estRow ? estRow.band : null,
          predicted, predictedFromDataset: fromDataset != null, took,
          delta: (took != null && predicted != null) ? round(took - predicted) : null,
          run_id: chosen ? chosen.run_id : null,
        });
      }
      this.papers = papers;
    },

    visible() {
      const q = this.search.trim().toLowerCase();
      return (this.papers || []).filter((p) =>
        (!this.onlyRepro || p.reproduced) &&
        (!q || (`${p.arxiv_id} ${p.model}`).toLowerCase().includes(q)));
    },
    sortPapers(rows) {
      const c = COLS.find((x) => x.key === this.sortKey) || COLS[0], dir = this.sortDir;
      return [...rows].sort((a, b) => {
        let x = a[c.key], y = b[c.key];
        if (c.key === "reproduced") { x = a.reproduced ? 1 : 0; y = b.reproduced ? 1 : 0; }
        if (c.key === "tier") { x = TIER_RANK[a.tier] || Infinity; y = TIER_RANK[b.tier] || Infinity; return (x - y) * dir; }
        if (c.num) { x = x == null ? -Infinity : x; y = y == null ? -Infinity : y; return (x - y) * dir; }
        return String(x).localeCompare(String(y)) * dir;
      });
    },
    setSort(key) {
      const col = COLS.find((c) => c.key === key);
      if (this.sortKey === key) this.sortDir *= -1;
      else { this.sortKey = key; this.sortDir = col && col.num ? -1 : 1; }
      this.renderBody();
    },

    // ---- CSV -----------------------------------------------------------------
    csv() {
      const head = ["arxiv_id", "reproduced", "success_runs", "total_runs", "model", "tier", "h100_band",
        "predicted_h100", "took_h100", "delta_h100", "ratio_pct", "success_run_id"];
      const body = this.sortPapers(this.visible()).map((p) => [
        p.arxiv_id, p.reproduced ? "yes" : "no", p.successCount, p.totalRuns, p.model, p.tier ?? "", p.band ?? "",
        p.predicted ?? "", p.took ?? "", p.delta ?? "", pct(p.took, p.predicted) ?? "", p.run_id ?? "",
      ]);
      return [head, ...body].map((r) => r.map(csvCell).join(",")).join("\n");
    },
    download() {
      const blob = new Blob([this.csv()], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "repro-report.csv";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },

    tagOptions() {
      const set = new Set(window.Tags ? window.Tags.all() : []);
      set.add(DEFAULT_SUCCESS);
      if (this.successTag) set.add(this.successTag);
      return [...set].sort((a, b) => a.localeCompare(b));
    },

    // ---- render --------------------------------------------------------------
    summaryHtml(papers) {
      const repro = papers.filter((p) => p.reproduced);
      const sum = (rows, k) => { let any = false, t = 0; for (const r of rows) if (r[k] != null) { any = true; t += r[k]; } return any ? t : null; };
      const predSum = sum(repro, "predicted"), tookSum = sum(repro, "took");
      const eff = pct(tookSum, predSum);
      const cards = [
        ["papers", String(papers.length), ""],
        ["reproduced", String(repro.length), papers.length ? `${pct(repro.length, papers.length)}% of papers` : ""],
        ["not reproduced", String(papers.length - repro.length), ""],
        ["predicted", fmtH(predSum), "H100·h (reproduced)"],
        ["took", fmtH(tookSum), "H100·h (reproduced)"],
        ["efficiency", eff == null ? "—" : eff + "%", "took / predicted"],
      ];
      return `<div class="stat-cards">${cards.map(([l, v, s]) =>
        `<div class="stat-card"><div class="sc-v">${esc(v)}</div><div class="sc-l">${esc(l)}</div>${s ? `<div class="sc-s">${esc(s)}</div>` : ""}</div>`).join("")}</div>`;
    },

    // reproduced / total split by difficulty tier — answers "how hard were these?"
    tierBreakdownHtml(papers) {
      const stats = {};
      for (const p of papers) {
        const t = p.tier || "untiered";
        (stats[t] || (stats[t] = { total: 0, repro: 0 })).total++;
        if (p.reproduced) stats[t].repro++;
      }
      const keys = TIER_ORDER.filter((k) => stats[k]).concat(Object.keys(stats).filter((k) => !TIER_ORDER.includes(k)));
      if (!keys.length || (keys.length === 1 && keys[0] === "untiered")) return "";
      const chips = keys.map((k) => {
        const s = stats[k], cls = k === "untiered" ? "unk" : (TIER_CLASS[k] || "accent");
        return `<span class="tier-stat"><span class="badge ${cls}">${esc(k)}</span>
          <b>${s.repro}</b><span class="s-sub">/${s.total} reproduced</span></span>`;
      }).join("");
      return `<div class="tier-breakdown"><span class="s-sub">by difficulty:</span>${chips}</div>`;
    },

    rowHtml(p) {
      const ratio = pct(p.took, p.predicted);
      const reproCell = p.reproduced
        ? `<span class="badge yes">✓ yes</span>`
        : `<span class="badge no">✗ no</span>`;
      const runs = `${p.successCount} / ${p.totalRuns}`;
      const deltaCell = p.delta == null ? "—"
        : `<span class="${p.delta > 0 ? "rep-over" : "rep-under"}">${p.delta > 0 ? "+" : ""}${fmtH(p.delta)}</span>${ratio != null ? ` <span class="s-sub">${ratio}%</span>` : ""}`;
      const arx = p.run_id
        ? `<a class="s-arx rep-jump" href="#" data-run="${esc(p.run_id)}" title="open this run in the Live tab">${esc(p.arxiv_id)}</a>`
        : `<span class="s-arx">${esc(p.arxiv_id)}</span>`;
      const tierCell = p.tier
        ? `<span class="badge ${TIER_CLASS[p.tier] || "accent"}"${p.band ? ` title="${esc(p.band)} H100·h band"` : ""}>${esc(p.tier)}</span>`
        : `<span class="s-sub">—</span>`;
      return `<tr>
        <td class="s-run">${arx}${p.run_id ? `<div class="s-rid">${esc(p.run_id)}</div>` : ""}</td>
        <td>${reproCell}</td>
        <td class="num">${runs}</td>
        <td class="s-model">${esc(p.model)}</td>
        <td>${tierCell}</td>
        <td class="num">${fmtH(p.predicted)}${p.predicted != null && !p.predictedFromDataset ? ` <span class="s-sub" title="not in the lockfile dataset — using the run budget">budget</span>` : ""}</td>
        <td class="num">${p.took == null ? "—" : fmtH(p.took)}</td>
        <td class="num">${deltaCell}</td>
      </tr>`;
    },
    tableHtml(rows) {
      const ths = COLS.map((c) => {
        const arrow = this.sortKey === c.key ? (this.sortDir < 0 ? " ▼" : " ▲") : "";
        return `<th class="${c.num ? "num" : ""} ${this.sortKey === c.key ? "sorted" : ""}" data-k="${c.key}"${c.tip ? ` title="${esc(c.tip)}"` : ""}>${esc(c.label)}${arrow}</th>`;
      }).join("");
      const body = this.sortPapers(rows).map((r) => this.rowHtml(r)).join("");
      return `<table class="stats-table"><thead><tr>${ths}</tr></thead><tbody>${body}</tbody></table>`;
    },

    render() {
      const el = this.root();
      if (!el) return;
      const opts = this.tagOptions().map((t) =>
        `<option value="${esc(t)}" ${t === this.successTag ? "selected" : ""}>${esc(t)}</option>`).join("");
      el.innerHTML = `
        <div class="stats-head">
          <h2>Reproduced papers</h2>
          <div class="stats-controls">
            <span class="muted">${esc(this.busy ? this.msg : "")}</span>
            <button id="report-csv" class="filt">⬇ CSV</button>
            <button id="report-refresh" class="filt" ${this.busy ? "disabled" : ""}>↻ refresh</button>
          </div>
        </div>
        <div class="s-note">Grouped by paper across all runs. A paper is <b>reproduced</b> once any of its runs is tagged
          <b>${esc(this.successTag)}</b> — tag runs from the Live or Stats tabs. <b>Took</b> is the cheapest successful run's
          spent compute; <b>predicted</b> is the lockfile <code>h100_hours_estimate</code>. ${esc(this.estimateNote())}</div>
        <div class="stats-filters">
          <div class="filters-row">
            <label class="rep-tagsel">success tag
              <select id="report-tag">${opts}</select></label>
            <label class="excl-dead"><input type="checkbox" id="report-only" ${this.onlyRepro ? "checked" : ""} /> only reproduced</label>
          </div>
          <input id="report-search" class="s-search" type="search" placeholder="filter by arxiv id or model…" value="${esc(this.search)}" />
        </div>
        <div id="report-body"></div>`;
      el.querySelector("#report-csv").addEventListener("click", () => this.download());
      el.querySelector("#report-refresh").addEventListener("click", () => this.load(true));
      el.querySelector("#report-tag").addEventListener("change", (e) => { this.successTag = e.target.value; this.renderBody(); });
      el.querySelector("#report-only").addEventListener("change", (e) => { this.onlyRepro = e.target.checked; this.renderBody(); });
      el.querySelector("#report-search").addEventListener("input", (e) => { this.search = e.target.value; this.renderBody(); });
      this.renderBody();
    },

    renderBody() {
      const body = document.querySelector("#report-body");
      if (!body) return;
      if (!this.rows) { body.innerHTML = `<div class="empty">${this.busy ? esc(this.msg || "working…") : "No runs yet."}</div>`; return; }
      this.buildPapers();
      const rows = this.visible();
      if (!rows.length) { body.innerHTML = `<div class="empty">No papers match this filter.</div>`; return; }
      body.innerHTML = this.summaryHtml(rows) + this.tierBreakdownHtml(rows) + this.tableHtml(rows);
      body.querySelectorAll(".stats-table th").forEach((th) =>
        th.addEventListener("click", () => this.setSort(th.dataset.k)));
      body.querySelectorAll(".rep-jump").forEach((a) => a.addEventListener("click", (e) => {
        e.preventDefault();
        const runId = a.getAttribute("data-run");
        if (window.setView) window.setView("live");
        if (window.openRun && runId) window.openRun(runId);
      }));
    },

    estimateNote() {
      const E = window.Estimates;
      if (!E) return "";
      if (E.error) return `(lockfile estimates unavailable: ${E.error} — using run budgets)`;
      if (!E.ready) return "(loading lockfile estimates…)";
      return `(${E.count()} lockfile estimates loaded)`;
    },

    // tags, success-tag, or loaded estimates changed while the tab is open
    onTags() { if (this.root() && !this.busy) this.render(); },
  };

  window.Report = Report;
})();
