/* stats.js — the Stats tab. Pulls every run + every transcript event, tokenizes
   the text with tokens.js, and shows a sortable per-run table so you can see, at
   a glance, which runs are burning tokens and why.

   Token buckets (all derived from the transcript the viewer already has):
     generated   = what the model produced   (reasoning + assistant + tool calls)
     tool output = what was fed back to it    (stdout + stderr + errors)
     transcript  = generated + tool output    (size of the whole log)
     est. input  = cumulative context the model read across rounds — the running
                   transcript total re-sent each round. Excludes the system prompt
                   and ignores prompt caching, so it's an upper-ish proxy for how
                   much prefill the run cost; the single best "what's going on" number. */
"use strict";

(function () {
  const R = window.RENDER;
  const esc = R.esc;
  const fmt = (n) => (n == null ? "—" : Math.round(n).toLocaleString());
  const fmtH = (n) => (n == null ? "—" : (Math.round(n * 1000) / 1000).toLocaleString());
  const fmtK = (n) => {
    if (n == null) return "—";
    if (n < 1000) return String(Math.round(n));
    if (n < 1e6) return (n / 1e3).toFixed(n < 1e4 ? 1 : 0) + "k";
    return (n / 1e6).toFixed(2) + "M";
  };
  const DEAD_H = (window.APP_CONFIG && window.APP_CONFIG.DEAD_AFTER_HOURS) || 12;

  const COLS = [
    { key: "arxiv_id", label: "run" },
    { key: "model", label: "model" },
    { key: "rounds", label: "rounds", num: true, tip: "model turns (round + final events)" },
    { key: "calls", label: "tool calls", num: true },
    { key: "gen", label: "generated", num: true, tip: "model output: reasoning + assistant + tool calls" },
    { key: "obs", label: "tool output", num: true, tip: "stdout + stderr + errors fed back to the model" },
    { key: "total", label: "transcript", num: true, tip: "generated + tool output" },
    { key: "ctx", label: "est. input", num: true, tip: "cumulative context re-read across all rounds (excl. system prompt & prompt caching)" },
    { key: "spent", label: "H100·h", num: true, tip: "compute spent (from the run row)" },
    { key: "status", label: "status" },
  ];

  const argsStr = (a) => (a == null ? "" : typeof a === "string" ? a : JSON.stringify(a));

  function buildRow(run, evs) {
    const T = window.Tokens.count.bind(window.Tokens);
    let reasoning = 0, content = 0, callsTok = 0, stdout = 0, stderr = 0, errTok = 0;
    let calls = 0, truncated = false;
    const rounds = new Map();
    let ord = 0;
    const roundOf = (e) => {
      const k = (e.kind === "final" ? "f" : "r") + (e.round_index == null ? "x" : e.round_index);
      let r = rounds.get(k);
      if (!r) { r = { gen: 0, obs: 0, ord: ord++ }; rounds.set(k, r); }
      return r;
    };
    for (const e of evs) {
      if (e.kind === "round_open" || e.kind === "final") {
        const a = T(e.reasoning), b = T(e.content);
        reasoning += a; content += b; roundOf(e).gen += a + b;
      } else if (e.kind === "call_start") {
        calls++;
        const c = T(e.command) + T(argsStr(e.args));
        callsTok += c; roundOf(e).gen += c;
      } else if (e.kind === "call_result") {
        if (e.truncated) truncated = true;
        const so = T(e.stdout), se = T(e.stderr), er = T(e.error) + T(e.path);
        stdout += so; stderr += se; errTok += er; roundOf(e).obs += so + se + er;
      }
    }
    const gen = reasoning + content + callsTok;
    const obs = stdout + stderr + errTok;
    const ordered = [...rounds.values()].sort((a, b) => a.ord - b.ord);
    let ctx = 0, cumIn = 0;
    for (const r of ordered) { cumIn += ctx; ctx += r.gen + r.obs; }
    const si = R.statusInfo(run);
    return {
      run_id: run.run_id, arxiv_id: run.arxiv_id || "?", model: run.model || "—",
      cls: si.cls, status: si.label, statusLabel: si.label,
      rounds: rounds.size, calls, gen, obs, total: gen + obs, ctx: cumIn,
      spent: run.spent_h100 != null ? Number(run.spent_h100) : null, truncated,
      brk: { reasoning, content, callsTok, stdout, stderr, err: errTok },
    };
  }

  const Stats = {
    rows: null, sig: null, sortKey: "ctx", sortDir: -1, busy: false, msg: "",

    root() { return document.querySelector("#stats-root"); },

    async open() {
      const el = this.root();
      if (!el) return;
      if (!window.RemoteSource || !window.RemoteSource.client) {
        el.innerHTML = `<div class="empty">Supabase isn't reachable, so there's nothing to tally. Configure <code>config.js</code> or use the <b>Local file</b> tab.</div>`;
        return;
      }
      if (this.rows) { this.render(); return; }
      await this.compute(false);
    },

    async compute(force) {
      if (this.busy) return;
      this.busy = true;
      this.msg = "loading runs…";
      this.render();
      try {
        const runs = await window.RemoteSource.listRuns();
        const sig = runs.map((r) => r.run_id + ":" + (r.updated_at || "")).join("|");
        if (!force && sig === this.sig && this.rows) { this.busy = false; this.render(); return; }
        await window.Tokens.ready();
        this.msg = "fetching transcript events…";
        this.render();
        const events = await window.RemoteSource.fetchAllEvents((n) => { this.msg = `fetched ${n} events…`; this.setStatusLine(); });
        const byRun = new Map();
        for (const e of events) {
          let a = byRun.get(e.run_id);
          if (!a) { a = []; byRun.set(e.run_id, a); }
          a.push(e);
        }
        this.msg = "tokenizing…";
        this.render();
        await new Promise((r) => setTimeout(r, 0)); // let the "tokenizing…" line paint
        this.rows = runs.map((run) => buildRow(run, byRun.get(run.run_id) || []));
        this.sig = sig;
        this.msg = "";
      } catch (e) {
        this.msg = "error: " + (e.message || e);
      } finally {
        this.busy = false;
        this.render();
      }
    },

    setStatusLine() {
      const s = document.querySelector("#stats-status");
      if (s) s.textContent = this.msg;
    },

    sorted() {
      const c = COLS.find((x) => x.key === this.sortKey) || COLS[0];
      const dir = this.sortDir;
      return [...(this.rows || [])].sort((a, b) => {
        let x = a[c.key], y = b[c.key];
        if (c.num) { x = x == null ? -Infinity : x; y = y == null ? -Infinity : y; return (x - y) * dir; }
        return String(x).localeCompare(String(y)) * dir;
      });
    },

    setSort(key) {
      const col = COLS.find((c) => c.key === key);
      if (this.sortKey === key) this.sortDir *= -1;
      else { this.sortKey = key; this.sortDir = col && col.num ? -1 : 1; }
      this.render();
    },

    summaryHtml(rows) {
      const sum = (k) => rows.reduce((t, r) => t + (r[k] || 0), 0);
      const dead = rows.filter((r) => r.cls === "dead").length;
      const cards = [
        ["runs", String(rows.length), ""],
        ["dead", String(dead), `no update ${DEAD_H}h+`],
        ["rounds", fmt(sum("rounds")), ""],
        ["generated", fmtK(sum("gen")), "tokens"],
        ["tool output", fmtK(sum("obs")), "tokens"],
        ["transcript", fmtK(sum("total")), "tokens"],
        ["est. input", fmtK(sum("ctx")), "cumulative tokens"],
        ["compute", fmtH(sum("spent")), "H100·h"],
      ];
      return `<div class="stat-cards">${cards.map(([l, v, s]) =>
        `<div class="stat-card ${l === "dead" && dead ? "warn" : ""}"><div class="sc-v">${v}</div><div class="sc-l">${esc(l)}</div>${s ? `<div class="sc-s">${esc(s)}</div>` : ""}</div>`).join("")}</div>`;
    },

    rowHtml(r) {
      const b = r.brk;
      const chips = [["reasoning", b.reasoning], ["assistant", b.content], ["tool-calls", b.callsTok],
        ["stdout", b.stdout], ["stderr", b.stderr], ["errors", b.err]]
        .map(([l, v]) => `<span class="s-chip">${l} <b>${fmtK(v)}</b></span>`).join("");
      const warn = r.truncated ? `<span class="s-chip warn">⚠ output truncated — tool-output tokens are a lower bound</span>` : "";
      return `<tr>
        <td class="s-run"><details><summary><span class="dot ${r.cls}"></span>${esc(r.arxiv_id)}</summary>
          <div class="s-break">${chips}${warn}</div><div class="s-rid">${esc(r.run_id)}</div></details></td>
        <td class="s-model">${esc(r.model)}</td>
        <td class="num">${fmt(r.rounds)}</td>
        <td class="num">${fmt(r.calls)}</td>
        <td class="num">${fmt(r.gen)}</td>
        <td class="num">${fmt(r.obs)}</td>
        <td class="num">${fmt(r.total)}</td>
        <td class="num">${fmt(r.ctx)}</td>
        <td class="num">${r.spent == null ? "—" : fmtH(r.spent)}</td>
        <td><span class="badge ${R.statusBadgeClass(r.cls)}">${esc(r.statusLabel)}</span></td>
      </tr>`;
    },

    tableHtml() {
      const ths = COLS.map((c) => {
        const arrow = this.sortKey === c.key ? (this.sortDir < 0 ? " ▼" : " ▲") : "";
        return `<th class="${c.num ? "num" : ""} ${this.sortKey === c.key ? "sorted" : ""}" data-k="${c.key}"${c.tip ? ` title="${esc(c.tip)}"` : ""}>${esc(c.label)}${arrow}</th>`;
      }).join("");
      const body = this.sorted().map((r) => this.rowHtml(r)).join("");
      return `<table class="stats-table"><thead><tr>${ths}</tr></thead><tbody>${body}</tbody></table>`;
    },

    render() {
      const el = this.root();
      if (!el) return;
      const method = window.Tokens ? window.Tokens.method : "loading…";
      const note = `Tokens via <b>${esc(method)}</b> — estimates for comparing runs, not billing.`;
      let main;
      if (!this.rows) {
        main = `<div class="empty">${this.busy ? esc(this.msg || "working…") : "No stats yet."}</div>`;
      } else if (!this.rows.length) {
        main = `<div class="empty">No runs found.</div>`;
      } else {
        main = this.summaryHtml(this.rows) + this.tableHtml();
      }
      el.innerHTML = `
        <div class="stats-head">
          <h2>Run stats</h2>
          <div class="stats-controls">
            <span id="stats-status" class="muted">${esc(this.busy ? this.msg : "")}</span>
            <button id="stats-recompute" class="filt" ${this.busy ? "disabled" : ""}>↻ recompute</button>
          </div>
        </div>
        <div class="s-note">${note}</div>
        ${main}`;
      const rc = document.querySelector("#stats-recompute");
      if (rc) rc.addEventListener("click", () => this.compute(true));
      el.querySelectorAll(".stats-table th").forEach((th) =>
        th.addEventListener("click", () => this.setSort(th.dataset.k)));
    },
  };

  window.Stats = Stats;
})();
