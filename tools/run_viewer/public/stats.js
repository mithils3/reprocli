/* stats.js — the Stats tab. A sortable, filterable table of every run built from
   the run rows alone (no event fetch, no tokenizer): the harness records the
   model's *real* token usage onto repro_runs, so we show that and nothing
   estimated. Runs from before usage logging show "—".

   Columns: rounds + tool calls, then prompt / completion / total / cached /
   uncached tokens (summed over the run's rounds — i.e. the actual billed
   context, which in an agent loop re-sends the transcript each round, so cached
   counts the re-sent context and uncached = prompt − cached is the fresh input
   actually processed), and H100·h compute. */
"use strict";

(function () {
  const R = window.RENDER;
  const esc = R.esc;
  const DEAD_H = (window.APP_CONFIG && window.APP_CONFIG.DEAD_AFTER_HOURS) || 12;
  const num = (v) => (v == null || v === "" ? null : Number(v));
  const fmt = (n) => (n == null ? "—" : Math.round(n).toLocaleString());
  const fmtH = (n) => (n == null ? "—" : (Math.round(n * 1000) / 1000).toLocaleString());
  const fmtK = (n) => {
    if (n == null) return "—";
    if (n < 1000) return String(Math.round(n));
    if (n < 1e6) return (n / 1e3).toFixed(n < 1e4 ? 1 : 0) + "k";
    return (n / 1e6).toFixed(2) + "M";
  };
  const pct = (a, b) => (a == null || !b ? null : Math.round((a / b) * 100));

  const FILTERS = [["all", "All"], ["running", "Running"], ["dead", "Dead"], ["finished", "Finished"], ["error", "Error"]];
  const COLS = [
    { key: "arxiv_id", label: "run" },
    { key: "model", label: "model" },
    { key: "rounds", label: "rounds", num: true, tip: "tool rounds used" },
    { key: "tool_calls", label: "tool calls", num: true },
    { key: "prompt", label: "prompt tok", num: true, tip: "real input tokens, summed over rounds (the agent re-sends the transcript each round)" },
    { key: "completion", label: "completion tok", num: true, tip: "real output tokens the model generated" },
    { key: "total", label: "total tok", num: true, tip: "prompt + completion" },
    { key: "cached", label: "cached tok", num: true, tip: "prompt tokens served from cache (re-sent context)" },
    { key: "uncached", label: "uncached tok", num: true, tip: "fresh input actually processed: prompt − cached (excludes re-sent context served from cache)" },
    { key: "spent", label: "H100·h", num: true, tip: "compute spent" },
    { key: "tags", label: "tags" },
    { key: "status", label: "status" },
  ];

  function toRow(run) {
    const si = R.statusInfo(run);
    const prompt = num(run.prompt_tokens), completion = num(run.completion_tokens);
    let total = num(run.total_tokens);
    if (total == null && (prompt != null || completion != null)) total = (prompt || 0) + (completion || 0);
    const cached = num(run.cached_tokens);
    const uncached = prompt == null ? null : prompt - (cached || 0);
    return {
      run_id: run.run_id, arxiv_id: run.arxiv_id || "?", model: run.model || "—",
      cls: si.cls, statusLabel: si.label, status: si.label,
      rounds: num(run.tool_rounds_used), tool_calls: num(run.tool_calls),
      prompt, completion, total, cached, uncached,
      spent: num(run.spent_h100),
      stats_url: run.stats_url || run.full_log_url || null,
      hasTokens: total != null,
    };
  }

  const Stats = {
    rows: null, sortKey: "total", sortDir: -1, filter: "all", search: "", busy: false, msg: "",
    tagFilter: null, excludeDead: false,

    root() { return document.querySelector("#stats-root"); },

    async open() {
      const el = this.root();
      if (!el) return;
      if (!window.RemoteSource || !window.RemoteSource.client) {
        el.innerHTML = `<div class="empty">Supabase isn't reachable, so there's nothing to tally. Configure <code>config.js</code> or use the <b>Local file</b> tab.</div>`;
        return;
      }
      if (this.rows) { this.render(); this.load(true); } // show cached, refresh in the background
      else this.load(false);
    },

    async load(force) {
      if (this.busy) return;
      if (this.rows && !force) { this.render(); return; }
      this.busy = true; this.msg = "loading runs…"; this.render();
      try {
        const runs = await window.RemoteSource.listRuns();
        this.rows = runs.map(toRow);
        this.msg = "";
      } catch (e) { this.msg = "error: " + (e.message || e); }
      finally { this.busy = false; this.render(); }
    },

    visible() {
      const q = this.search.trim().toLowerCase(), T = window.Tags;
      return (this.rows || []).filter((r) =>
        (this.filter === "all" || r.cls === this.filter) &&
        (!this.tagFilter || (T && T.has(r.run_id, this.tagFilter))) &&
        (!q || (`${r.arxiv_id} ${r.model} ${r.run_id}`).toLowerCase().includes(q)));
    },
    sortRows(rows) {
      const c = COLS.find((x) => x.key === this.sortKey) || COLS[0], dir = this.sortDir, T = window.Tags;
      return [...rows].sort((a, b) => {
        if (c.key === "tags") {
          return ((T ? T.get(a.run_id) : []).join(",")).localeCompare((T ? T.get(b.run_id) : []).join(",")) * dir;
        }
        let x = a[c.key], y = b[c.key];
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

    summaryHtml(active, deadCount, excluded) {
      const sum = (k) => { let any = false, t = 0; for (const r of active) if (r[k] != null) { any = true; t += r[k]; } return any ? t : null; };
      const prompt = sum("prompt"), cached = sum("cached"), rate = pct(cached, prompt);
      const uncached = sum("uncached"), urate = pct(uncached, prompt);
      const cards = [
        ["runs", String(active.length), excluded && deadCount ? `${deadCount} dead hidden` : ""],
        ["dead", String(deadCount), excluded ? "excluded" : `no update ${DEAD_H}h+`],
        ["rounds", fmt(sum("rounds")), ""],
        ["prompt", fmtK(prompt), "tokens"],
        ["completion", fmtK(sum("completion")), "tokens"],
        ["total", fmtK(sum("total")), "tokens"],
        ["cached", fmtK(cached), rate != null ? `${rate}% of prompt` : "tokens"],
        ["uncached", fmtK(uncached), urate != null ? `${urate}% of prompt` : "tokens"],
        ["compute", fmtH(sum("spent")), "H100·h"],
      ];
      return `<div class="stat-cards">${cards.map(([l, v, s]) =>
        `<div class="stat-card ${l === "dead" && deadCount && !excluded ? "warn" : ""}"><div class="sc-v">${v}</div><div class="sc-l">${esc(l)}</div>${s ? `<div class="sc-s">${esc(s)}</div>` : ""}</div>`).join("")}</div>`;
    },

    rowHtml(r) {
      const cacheSub = r.cached != null && r.prompt ? ` <span class="s-sub">${pct(r.cached, r.prompt)}%</span>` : "";
      const uncSub = r.uncached != null && r.prompt ? ` <span class="s-sub">${pct(r.uncached, r.prompt)}%</span>` : "";
      const link = r.stats_url ? ` <a class="link" href="${esc(r.stats_url)}" target="_blank" rel="noopener" title="download detailed stats / full log">⬇</a>` : "";
      return `<tr>
        <td class="s-run"><span class="dot ${r.cls}"></span><span class="s-arx">${esc(r.arxiv_id)}</span>${link}<div class="s-rid">${esc(r.run_id)}</div></td>
        <td class="s-model">${esc(r.model)}</td>
        <td class="num">${fmt(r.rounds)}</td>
        <td class="num">${fmt(r.tool_calls)}</td>
        <td class="num">${fmt(r.prompt)}</td>
        <td class="num">${fmt(r.completion)}</td>
        <td class="num">${fmt(r.total)}</td>
        <td class="num">${fmt(r.cached)}${cacheSub}</td>
        <td class="num">${fmt(r.uncached)}${uncSub}</td>
        <td class="num">${r.spent == null ? "—" : fmtH(r.spent)}</td>
        <td class="s-tags">${window.Tags ? window.Tags.chipsHtml(r.run_id) : ""}</td>
        <td><span class="badge ${R.statusBadgeClass(r.cls)}">${esc(r.statusLabel)}</span></td>
      </tr>`;
    },
    tableHtml(rows) {
      const ths = COLS.map((c) => {
        const arrow = this.sortKey === c.key ? (this.sortDir < 0 ? " ▼" : " ▲") : "";
        return `<th class="${c.num ? "num" : ""} ${this.sortKey === c.key ? "sorted" : ""}" data-k="${c.key}"${c.tip ? ` title="${esc(c.tip)}"` : ""}>${esc(c.label)}${arrow}</th>`;
      }).join("");
      const body = this.sortRows(rows).map((r) => this.rowHtml(r)).join("");
      return `<table class="stats-table"><thead><tr>${ths}</tr></thead><tbody>${body}</tbody></table>`;
    },

    render() {
      const el = this.root();
      if (!el) return;
      const noTok = (this.rows || []).filter((r) => !r.hasTokens).length;
      const note = ["Token columns are the model's <b>real usage</b> recorded by the harness."]
        .concat(noTok ? [`${noTok} run${noTok > 1 ? "s" : ""} predate usage logging and show <b>—</b>.`] : []).join(" ");
      el.innerHTML = `
        <div class="stats-head">
          <h2>Run stats</h2>
          <div class="stats-controls">
            <span id="stats-status" class="muted">${esc(this.busy ? this.msg : "")}</span>
            <button id="stats-recompute" class="filt" ${this.busy ? "disabled" : ""}>↻ refresh</button>
          </div>
        </div>
        <div class="s-note">${note}</div>
        <div class="stats-filters">
          <div class="filters-row">${FILTERS.map(([k, l]) =>
            `<button class="filt ${this.filter === k ? "active" : ""}" data-f="${k}">${l}</button>`).join("")}
            <label class="excl-dead" title="drop dead runs from the cards, graphs and table">
              <input type="checkbox" id="excl-dead" ${this.excludeDead ? "checked" : ""} /> exclude dead</label>
          </div>
          <input id="stats-search" class="s-search" type="search" placeholder="filter by arxiv id, model, or run id…" value="${esc(this.search)}" />
        </div>
        <div class="stats-tagfilters" id="stats-tagfilters"></div>
        <div id="stats-body"></div>`;
      const rc = document.querySelector("#stats-recompute");
      if (rc) rc.addEventListener("click", () => this.load(true));
      el.querySelectorAll(".stats-filters .filt").forEach((b) => b.addEventListener("click", () => {
        this.filter = b.dataset.f;
        el.querySelectorAll(".stats-filters .filt").forEach((x) => x.classList.toggle("active", x.dataset.f === this.filter));
        this.renderBody();
      }));
      const ex = document.querySelector("#excl-dead");
      if (ex) ex.addEventListener("change", () => { this.excludeDead = ex.checked; this.renderBody(); });
      const s = document.querySelector("#stats-search");
      if (s) s.addEventListener("input", () => { this.search = s.value; this.renderBody(); });
      this.renderTagFilters();
      this.renderBody();
    },

    // tag filter chips (stats) — union of all tags; click to filter, click to clear
    renderTagFilters() {
      const host = document.querySelector("#stats-tagfilters");
      if (!host) return;
      const tags = window.Tags ? window.Tags.all() : [];
      if (this.tagFilter && !tags.includes(this.tagFilter)) this.tagFilter = null;
      host.innerHTML = tags.length
        ? `<span class="tag-flt-lead">tag</span>` + tags.map((t) =>
            `<button class="tag-flt ${this.tagFilter === t ? "active" : ""}" data-t="${esc(t)}">${esc(t)}</button>`).join("")
        : "";
      host.querySelectorAll(".tag-flt").forEach((b) => b.addEventListener("click", () => {
        this.tagFilter = this.tagFilter === b.dataset.t ? null : b.dataset.t;
        this.renderTagFilters(); this.renderBody();
      }));
    },

    // tags changed elsewhere while the Stats tab is open
    onTags() { if (this.root()) { this.renderTagFilters(); this.renderBody(); } },

    renderBody() {
      const body = document.querySelector("#stats-body");
      if (!body) return;
      if (!this.rows) { body.innerHTML = `<div class="empty">${this.busy ? esc(this.msg || "working…") : "No stats yet."}</div>`; return; }
      if (!this.rows.length) { body.innerHTML = `<div class="empty">No runs found.</div>`; return; }
      const rows = this.visible();
      if (!rows.length) { body.innerHTML = `<div class="empty">No runs match this filter.</div>`; return; }
      const deadCount = rows.filter((r) => r.cls === "dead").length;
      const active = this.excludeDead ? rows.filter((r) => r.cls !== "dead") : rows;
      const charts = window.Charts ? window.Charts.render(active) : "";
      body.innerHTML = this.summaryHtml(active, deadCount, this.excludeDead) + charts + this.tableHtml(active);
      body.querySelectorAll(".stats-table th").forEach((th) =>
        th.addEventListener("click", () => this.setSort(th.dataset.k)));
    },
  };

  window.Stats = Stats;
})();
