/* tags.js — user-authored run labels, backed by the synced repro_tags table
   (anon read + write). A small store (load/get/set/add/remove) plus the render
   helpers the Live + Stats views call into. Kept separate so render.js / stats.js
   stay lean. Optimistic writes: the UI updates immediately and rolls back if the
   Supabase write fails. Realtime keeps tags in sync across open browsers. */
"use strict";

(function () {
  const esc = window.RENDER.esc;

  const Tags = {
    byRun: {},          // run_id -> [tag, …]
    ready: false,
    listeners: [],

    onChange(fn) { this.listeners.push(fn); },
    emit() {
      this._syncSuggest();
      for (const fn of this.listeners) { try { fn(); } catch (e) {} }
    },

    get(runId) { return this.byRun[runId] || []; },
    has(runId, tag) { return this.get(runId).indexOf(tag) !== -1; },
    all() {
      const s = new Set();
      for (const ts of Object.values(this.byRun)) for (const t of ts) s.add(t);
      return [...s].sort((a, b) => a.localeCompare(b));
    },

    async load() {
      const rows = await window.RemoteSource.listTags();
      const next = {};
      for (const r of rows) if (r.tags && r.tags.length) next[r.run_id] = r.tags.slice();
      this.byRun = next;
      this.ready = true;
      this.emit();
    },

    // realtime row change (INSERT/UPDATE/DELETE)
    applyRow(row, evt) {
      if (!row || !row.run_id) return;
      if (evt === "DELETE" || !row.tags || !row.tags.length) delete this.byRun[row.run_id];
      else this.byRun[row.run_id] = row.tags.slice();
      this.emit();
    },

    async set(runId, tags) {
      const clean = [...new Set(tags.map((t) => String(t).trim()).filter(Boolean))];
      const prev = this.byRun[runId];                 // for rollback
      if (clean.length) this.byRun[runId] = clean; else delete this.byRun[runId];
      this.emit();
      try {
        await window.RemoteSource.setTags(runId, clean);
      } catch (e) {
        if (prev) this.byRun[runId] = prev; else delete this.byRun[runId];
        this.emit();
        throw e;
      }
    },
    add(runId, tag) { return this.set(runId, this.get(runId).concat(tag)); },
    remove(runId, tag) { return this.set(runId, this.get(runId).filter((t) => t !== tag)); },

    // ---- render helpers ------------------------------------------------------
    // read-only chips (sidebar list, stats table). "" when the run has no tags.
    chipsHtml(runId) {
      const ts = this.get(runId);
      if (!ts.length) return "";
      return `<span class="tag-chips">${ts.map((t) => `<span class="tag-chip">${esc(t)}</span>`).join("")}</span>`;
    },

    // editable tag bar: fills every <div class="tagbar" data-run="…"> in scope
    // with removable chips + an add-input, and wires the listeners.
    mount(scope) {
      if (!scope) return;
      scope.querySelectorAll(".tagbar[data-run]").forEach((bar) => this._fill(bar));
    },
    _fill(bar) {
      const runId = bar.getAttribute("data-run");
      const offline = !(window.RemoteSource && window.RemoteSource.client);
      const chips = this.get(runId).map((t) =>
        `<span class="tag-chip edit">${esc(t)}<button class="tag-x" data-tag="${esc(t)}" title="remove tag" aria-label="remove ${esc(t)}">×</button></span>`).join("");
      bar.innerHTML = `<span class="tag-lead">tags</span>${chips}` +
        (offline ? `<span class="tag-off">offline</span>`
                 : `<input class="tag-input" list="tag-suggest" placeholder="+ add" aria-label="add tag" />`);
      bar.querySelectorAll(".tag-x").forEach((b) =>
        b.addEventListener("click", () => { this.remove(runId, b.getAttribute("data-tag")).catch(() => {}); }));
      const input = bar.querySelector(".tag-input");
      if (input) input.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        e.preventDefault();
        const v = input.value.trim();
        if (!v || this.has(runId, v)) { input.value = ""; return; }
        input.value = "";
        this.add(runId, v).catch(() => {});
      });
    },

    _syncSuggest() {
      const dl = document.getElementById("tag-suggest");
      if (dl) dl.innerHTML = this.all().map((t) => `<option value="${esc(t)}"></option>`).join("");
    },
  };

  window.Tags = Tags;
})();
