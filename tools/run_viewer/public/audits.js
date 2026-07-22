/* audits.js — the AUDITS page: S7 auditor runs streamed from Supabase, rendered
   with the SAME transcript machinery as Live (render.js). Mirrors app.js's run
   list + open + realtime stream, scoped to audit_runs / audit_events. An audit
   row links to the reproduce run it graded via graded_run_id.

   One run can now carry several audits — a sweep's own model graded it once, and
   a second grader (Claude) may have graded it again, each as its own row. So the
   list shows the score, not just the verdict word, filters by grader, and marks
   where a re-grade disagrees with the verdict currently stored on the run. */
"use strict";

(function () {
  const R = window.RENDER;

  const Audits = {
    byId: {}, runs: [], currentId: null, live: null, events: [], seen: new Set(),
    ch: null, booted: false, grader: "all", graded: {},

    list() { return document.querySelector("#audit-list"); },
    filters() { return document.querySelector("#audit-filters"); },
    detail() { return document.querySelector("#audit-detail"); },

    async open() {
      if (!this.detail()) return;
      if (!window.RemoteSource || !window.RemoteSource.client) {
        this.detail().innerHTML = `<div class="empty">Supabase isn't reachable — no audits to stream.</div>`;
        return;
      }
      if (!this.booted) {
        this.booted = true;
        window.RemoteSource.subscribeAuditList((run) => {
          this.upsert(run); this.renderFilters(); this.renderList();
        });
      }
      this.load();
    },

    async load() {
      try {
        const runs = await window.RemoteSource.listAudits();
        this.byId = {}; runs.forEach((r) => this.upsert(r));
        this.renderFilters(); this.renderList();
      } catch (e) {
        this.renderList();
        this.detail().innerHTML = `<div class="empty">error loading audits: ${R.esc(e.message || e)}</div>`;
      }
      // The reproduce runs are what an audit is graded AGAINST: they carry the
      // verdict currently stored on the row, which is what a re-grade may contradict.
      // (listRuns also seeds Freeze, so the non-frozen filter works on a cold open.)
      try {
        const runs = await window.RemoteSource.listRuns();
        this.graded = {};
        for (const run of runs || []) if (run && run.run_id) this.graded[run.run_id] = run;
        this.renderList();
      } catch (e) { /* the score still renders without the comparison */ }
    },

    upsert(run) {
      if (!run || !run.audit_run_id) return;
      this.byId[run.audit_run_id] = Object.assign(this.byId[run.audit_run_id] || {}, run);
      this.runs = Object.values(this.byId).sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
    },

    graderOf(run) { return (R.shortModel ? R.shortModel(run && run.model) : (run && run.model)) || "unknown"; },

    renderFilters() {
      const host = this.filters(); if (!host) return;
      const counts = new Map();
      for (const run of this.runs) counts.set(this.graderOf(run), (counts.get(this.graderOf(run)) || 0) + 1);
      const chips = [["all", `All (${this.runs.length})`]].concat(
        [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([g, n]) => [g, `${g} (${n})`]));
      host.innerHTML = chips.map(([key, label]) =>
        `<button class="filt ${this.grader === key ? "active" : ""}" data-grader="${R.esc(key)}">${R.esc(label)}</button>`
      ).join("");
      host.querySelectorAll(".filt[data-grader]").forEach((b) => b.addEventListener("click", () => {
        this.grader = b.dataset.grader; this.renderFilters(); this.renderList();
      }));
    },

    visibleRuns() {
      const byGrader = this.grader === "all"
        ? this.runs
        : this.runs.filter((run) => this.graderOf(run) === this.grader);
      return window.Freeze ? window.Freeze.filter(byGrader) : byGrader;
    },
    onFreeze() {
      if (this.live && window.Freeze && window.Freeze.isExcluded(this.live)) {
        if (this.ch) { window.RemoteSource.unsubscribe(this.ch); this.ch = null; }
        this.currentId = null; this.live = null;
        this.detail().innerHTML = `<div class="empty">The open audit is excluded by the non-frozen filter.</div>`;
      }
      this.renderList();
    },

    renderList() {
      const host = this.list(); if (!host) return;
      host.innerHTML = "";
      const runs = this.visibleRuns();
      if (!runs.length) {
        host.innerHTML = `<div class="empty small">${this.runs.length ? "No audits match the global filter." : "No audits yet — run one and watch the auditor grade it live."}</div>`;
        return;
      }
      for (const run of runs) {
        const item = R.renderRunListItem(run);
        this.decorate(item, run);
        if (run.audit_run_id === this.currentId) item.classList.add("active");
        item.addEventListener("click", () => this.openAudit(run.audit_run_id));
        host.appendChild(item);
      }
    },

    /* The score, and where this audit contradicts the verdict stored on the run it
       graded — the whole point of a second grader is the rows where they disagree,
       and those are invisible if the list only shows this audit's own word. */
    decorate(item, run) {
      const line = item.querySelector(".pl-l1"); if (!line) return;
      const chips = [];
      if (Number.isInteger(run.score)) chips.push(`<span class="schip tnum">${run.score}/10</span>`);
      const stored = (this.graded[run.graded_run_id] || {}).audit_verdict;
      if (stored && run.verdict && stored !== run.verdict) {
        chips.push(`<span class="schip regrade" title="verdict stored on the graded run">≠ ${R.esc(stored)}</span>`);
      }
      if (!chips.length) return;
      const anchor = line.querySelector(".vd");
      if (anchor) anchor.insertAdjacentHTML("afterend", chips.join(""));
      else line.insertAdjacentHTML("afterbegin", chips.join(""));
    },

    async openAudit(id) {
      this.currentId = id; this.renderList();
      this.detail().innerHTML = `<div class="empty">Loading ${R.esc(id)}…</div>`;
      if (this.ch) { window.RemoteSource.unsubscribe(this.ch); this.ch = null; }
      let data;
      try { data = await window.RemoteSource.loadAudit(id); }
      catch (e) { this.detail().innerHTML = `<div class="empty">Could not load audit: ${R.esc(e.message || e)}</div>`; return; }
      this.live = data.run; this.events = data.events; this.seen = new Set(data.events.map((e) => e.seq));
      R.renderRun(this.detail(), data.run, data.rounds);
      this.ch = window.RemoteSource.subscribeAudit(id, (e) => this.onEvent(e), (p) => this.onPatch(p));
      if (window.scheduleJumpUpdate) window.scheduleJumpUpdate();
    },

    onEvent(e) {
      if (!e || e.audit_run_id !== this.currentId || this.seen.has(e.seq)) return;
      this.seen.add(e.seq); this.events.push(e);
      const rounds = window.RemoteSource.rowsToRounds(this.events);
      const key = window.RemoteSource.roundKey(e);
      const round = rounds.find((r) => `${r.kind}:${r.round_index}` === key);
      if (!round || !this.detail().querySelector(".rounds")) return;
      const box = this.detail(), near = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
      R.appendRound(this.detail(), round, this.live, rounds);
      if (near) box.scrollTop = box.scrollHeight;
    },

    onPatch(patch) {
      if (!patch || patch.audit_run_id !== this.currentId) return;
      Object.assign(this.live, patch);
      const top = this.detail().querySelector(".run-top");
      if (top) top.innerHTML = R.topHtml(this.live, { rounds: this.detail().querySelectorAll(".rounds .rcard").length });
      this.upsert(this.live); this.renderList();
    },
  };

  window.Audits = Audits;
})();
