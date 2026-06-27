/* estimates.js — per-paper *predicted* H100·h, pulled from the canonical lockfile
   dataset (Mithilss/reprobench-splits) via the public HF datasets-server API.
   Maps custom_id (= arxiv_id) -> h100_hours_estimate (+ the audited hours / tier
   / band for context). The dataset is public and the API is CORS-enabled, so the
   browser fetches it directly; on any failure the report just falls back to the
   run budget. The Reproduced tab is the only consumer. */
"use strict";

(function () {
  const DATASET = "Mithilss/reprobench-splits";
  const CONFIG = "default";
  const SPLITS = ["test", "validation"];
  const BASE = "https://datasets-server.huggingface.co/rows";
  const numOrNull = (v) => (typeof v === "number" && isFinite(v) ? v : null);

  const Estimates = {
    byId: {},          // arxiv_id -> { estimate, audited, split, tier, band }
    ready: false,
    error: null,
    listeners: [],

    onChange(fn) { this.listeners.push(fn); },
    emit() { for (const fn of this.listeners) { try { fn(); } catch (e) {} } },

    get(arxivId) { const r = this.byId[arxivId]; return r ? r.estimate : null; },
    row(arxivId) { return this.byId[arxivId] || null; },
    count() { return Object.keys(this.byId).length; },

    async load() {
      try {
        const next = {};
        for (const split of SPLITS) {
          for (let offset = 0; ; offset += 100) {
            const url = `${BASE}?dataset=${encodeURIComponent(DATASET)}&config=${CONFIG}&split=${split}&offset=${offset}&length=100`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`${split}: HTTP ${res.status}`);
            const rows = (await res.json()).rows || [];
            for (const r of rows) {
              const row = r.row || {};
              if (!row.custom_id) continue;
              next[row.custom_id] = {
                estimate: numOrNull(row.h100_hours_estimate),
                audited: numOrNull(row.audited_h100_hours),
                split: row.split || split, tier: row.tier || null, band: row.h100_band || null,
              };
            }
            if (rows.length < 100) break;
          }
        }
        this.byId = next; this.ready = true; this.error = null;
      } catch (e) {
        this.error = e.message || String(e);
      }
      this.emit();
    },
  };

  window.Estimates = Estimates;
})();
