/* audits.js — the AUDITS page: S7 auditor runs streamed from Supabase, rendered
   with the SAME transcript machinery as Live (render.js). Mirrors app.js's run
   list + open + realtime stream, scoped to audit_runs / audit_events. An audit
   row links to the reproduce run it graded via graded_run_id. */
"use strict";

(function () {
  const R = window.RENDER;

  const Audits = {
    byId: {}, runs: [], currentId: null, live: null, events: [], seen: new Set(),
    ch: null, booted: false,

    list() { return document.querySelector("#audit-list"); },
    detail() { return document.querySelector("#audit-detail"); },

    async open() {
      if (!this.detail()) return;
      if (!window.RemoteSource || !window.RemoteSource.client) {
        this.detail().innerHTML = `<div class="empty">Supabase isn't reachable — no audits to stream.</div>`;
        return;
      }
      if (!this.booted) {
        this.booted = true;
        window.RemoteSource.subscribeAuditList((run) => { this.upsert(run); this.renderList(); });
      }
      this.load();
    },

    async load() {
      try {
        const runs = await window.RemoteSource.listAudits();
        this.byId = {}; runs.forEach((r) => this.upsert(r)); this.renderList();
      } catch (e) {
        this.renderList();
        this.detail().innerHTML = `<div class="empty">error loading audits: ${R.esc(e.message || e)}</div>`;
      }
    },

    upsert(run) {
      if (!run || !run.audit_run_id) return;
      this.byId[run.audit_run_id] = Object.assign(this.byId[run.audit_run_id] || {}, run);
      this.runs = Object.values(this.byId).sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
    },

    visibleRuns() { return window.Freeze ? window.Freeze.filter(this.runs) : this.runs; },
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
        if (run.audit_run_id === this.currentId) item.classList.add("active");
        item.addEventListener("click", () => this.openAudit(run.audit_run_id));
        host.appendChild(item);
      }
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
