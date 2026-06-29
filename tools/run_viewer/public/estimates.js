/* estimates.js — per-paper lockfile facts, pulled from the canonical dataset
   (Mithilss/reprobench-splits) via the public, CORS-enabled HF datasets-server.
   Maps custom_id (= arxiv_id) -> predicted H100·h (+ audited / tier / band) AND
   the human-readable central_claim, the paper/code links and the paper kind — so
   the viewer can show papers by WHAT they claim instead of an opaque arxiv id.
   On any failure callers fall back to the arxiv id + run budget. */
"use strict";

(function () {
  const DATASET = "Mithilss/reprobench-splits";
  const CONFIG = "default";
  const SPLITS = ["test", "validation"];
  const BASE = "https://datasets-server.huggingface.co/rows";
  const numOrNull = (v) => (typeof v === "number" && isFinite(v) ? v : null);

  // verified_links arrives as an object, an array, or a python-dict string — be liberal
  function parseLinks(raw) {
    let urls = [];
    if (Array.isArray(raw)) urls = raw;
    else if (raw && typeof raw === "object") urls = Object.values(raw).flat();
    else if (typeof raw === "string") urls = raw.match(/https?:\/\/[^\s'"\]]+/g) || [];
    urls = urls.filter((u) => typeof u === "string");
    const code = urls.find((u) => /github\.com|gitlab\.com|bitbucket\.org|huggingface\.co/.test(u));
    const paper = urls.find((u) => /arxiv\.org|openreview\.net|doi\.org|\.pdf(\?|$)/.test(u)) || urls.find((u) => u !== code);
    return { paper: paper || null, code: code || null };
  }

  const Estimates = {
    byId: {},          // arxiv_id -> { estimate, audited, split, tier, band, claim, links, kind }
    ready: false,
    error: null,
    listeners: [],

    onChange(fn) { this.listeners.push(fn); },
    emit() { for (const fn of this.listeners) { try { fn(); } catch (e) {} } },

    get(arxivId) { const r = this.byId[arxivId]; return r ? r.estimate : null; },
    row(arxivId) { return this.byId[arxivId] || null; },
    claim(arxivId) { const r = this.byId[arxivId]; return r ? r.claim : null; },
    links(arxivId) { const r = this.byId[arxivId]; return r ? r.links : null; },
    kind(arxivId) { const r = this.byId[arxivId]; return r ? r.kind : null; },
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
              const claim = typeof row.central_claim === "string" ? row.central_claim.trim() : null;
              // splits are disjoint; keep the first occurrence so a duplicate can't silently flip its set
              if (next[row.custom_id]) continue;
              next[row.custom_id] = {
                estimate: numOrNull(row.h100_hours_estimate),
                audited: numOrNull(row.audited_h100_hours),
                split: row.split || split, set: split === "validation" ? "dev" : "test",
                tier: row.tier || null, band: row.h100_band || null,
                claim: claim || null, links: parseLinks(row.verified_links), kind: row.paper_kind || null,
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
