/* estimates.js — per-paper lockfile facts, pulled straight from the canonical
   dataset's raw JSONL files (Mithilss/reprobench-splits) served with CORS by
   the HF Hub. We fetch resolve/main/*.jsonl instead of the datasets-server
   /rows API because the datasets-server 503s during Hub viewer outages while
   file resolve stays up. Reloads periodically so a refreshed lockfile shows up
   without a page reload; an unchanged ETag pair skips the re-parse. Maps
   custom_id (= arxiv_id) -> predicted H100·h (+ audited / tier / band) AND the
   human-readable central_claim, the paper/code links and the paper kind — so
   the viewer can show papers by WHAT they claim instead of an opaque arxiv id.
   On any failure callers fall back to the arxiv id + run budget. */
"use strict";

(function () {
  const BASE = "https://huggingface.co/datasets/Mithilss/reprobench-splits/resolve/main/";
  const FILES = [
    { file: "eval_100.jsonl", set: "test" },
    { file: "dev_split.jsonl", set: "dev" },
  ];
  const REFRESH_MS = 5 * 60 * 1000; // recheck the Hub for a refreshed lockfile
  const RETRY_MS = 60 * 1000;       // faster retry until the first load lands
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

  function parseRows(text, set, next) {
    for (const line of text.split("\n")) {
      const s = line.trim();
      if (!s) continue;
      let row;
      try { row = JSON.parse(s); } catch (e) { continue; }
      if (!row.custom_id) continue;
      // sets are disjoint; keep the first occurrence so a duplicate can't silently flip its set
      if (next[row.custom_id]) continue;
      const claim = typeof row.central_claim === "string" ? row.central_claim.trim() : null;
      next[row.custom_id] = {
        estimate: numOrNull(row.h100_hours_estimate),
        audited: numOrNull(row.audited_h100_hours),
        split: row.split || set, set,
        tier: row.tier || null, band: row.h100_band || null,
        claim: claim || null, links: parseLinks(row.verified_links), kind: row.paper_kind || null,
      };
    }
  }

  const Estimates = {
    byId: {},          // arxiv_id -> { estimate, audited, split, tier, band, claim, links, kind }
    ready: false,
    error: null,
    listeners: [],
    etags: {},         // file -> ETag of the last parsed copy
    timer: null,

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
        // cache: "no-cache" lets the browser revalidate with its own conditional
        // headers (no CORS preflight); the exposed ETag tells us if anything moved
        const results = await Promise.all(FILES.map(async ({ file, set }) => {
          const res = await fetch(BASE + file, { cache: "no-cache" });
          if (!res.ok) throw new Error(`${file}: HTTP ${res.status}`);
          return { file, set, etag: res.headers.get("etag"), text: await res.text() };
        }));
        const unchanged = this.ready && results.every((r) => r.etag && r.etag === this.etags[r.file]);
        if (!unchanged) {
          const next = {};
          for (const r of results) parseRows(r.text, r.set, next);
          this.byId = next;
          this.etags = Object.fromEntries(results.map((r) => [r.file, r.etag]));
          this.ready = true; this.error = null;
          this.emit();
        }
        this.error = null;
      } catch (e) {
        this.error = e.message || String(e);
        if (!this.ready) this.emit(); // a stale-but-loaded table beats a re-render on every failed poll
      }
      clearTimeout(this.timer);
      this.timer = setTimeout(() => this.load(), this.ready ? REFRESH_MS : RETRY_MS);
    },
  };

  window.Estimates = Estimates;
})();
