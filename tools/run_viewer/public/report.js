/* report.js — PURE per-paper aggregation (no DOM). Groups runs by paper, decides
   reproduced (any run tagged with the success tag), picks the cheapest successful
   run as canonical, and joins the lockfile prediction/claim/tier from estimates.js.
   Consumed by overview.js (the worksheet) and papers.js (specimen pages); the old
   standalone Reproduced tab is gone. CSV export kept here so it lives in one place. */
"use strict";

(function () {
  const num = (v) => (v == null || v === "" ? null : Number(v));
  const round = (n) => (n == null ? null : Math.round(n * 1000) / 1000);
  const DEFAULT_SUCCESS = "success";
  const TIER_ORDER = ["Easy", "Medium", "Hard"];

  const budgetOf = (run) => num(run.budget) ?? num(run.total_h100);
  function tookOf(run) {
    let s = num(run.spent_h100);
    if (s == null) { const t = num(run.total_h100), rem = num(run.remaining_h100); if (t != null && rem != null) s = t - rem; }
    return s;
  }
  const maxOf = (runs, f) => runs.reduce((m, r) => { const v = f(r); return v != null && (m == null || v > m) ? v : m; }, null);

  const Report = {
    successTag: DEFAULT_SUCCESS,

    // A run is graded once the Stage-7 auditor has written its verdict
    // (repro_runs.audit_*, via reprocli_repro.audit_upload). It counts as a success
    // when the auditor reproduced it OR — for ungraded runs — it carries the
    // hand-applied success tag. Shared by papers() and modelTier() so every surface
    // agrees. (window.Tags is the fallback source; pass the active tag.)
    graded(r) { return r.audit_verdict != null || r.audit_score != null || r.audit_reproduced != null; },
    isSuccess(r, tag) {
      const T = window.Tags;
      return r.audit_reproduced === true || (T && T.has(r.run_id, tag || this.successTag));
    },

    papers(runs, successTag) {
      const V = window.Verdict, E = window.Estimates;
      const tag = successTag || this.successTag;
      const groups = new Map();
      for (const run of (runs || [])) {
        const id = run.arxiv_id || "?";
        if (!groups.has(id)) groups.set(id, []);
        groups.get(id).push(run);
      }
      const out = [];
      for (const [arxiv_id, rs] of groups) {
        const successRuns = rs.filter((r) => this.isSuccess(r, tag));
        const reproduced = successRuns.length > 0;
        const auditedRun = rs.find((r) => this.graded(r)) || null;
        const chosen = reproduced
          ? successRuns.slice().sort((a, b) => (tookOf(a) ?? Infinity) - (tookOf(b) ?? Infinity))[0]
          : rs.slice().sort((a, b) => (tookOf(b) ?? -1) - (tookOf(a) ?? -1))[0];
        const models = [...new Set(rs.map((r) => r.model).filter(Boolean))];
        const runFamilies = V ? rs.map((r) => V.ofRun(r)) : [];
        const estRow = E ? E.row(arxiv_id) : null;
        const fromDataset = estRow ? estRow.estimate : null;
        const predicted = fromDataset != null ? fromDataset : (chosen ? budgetOf(chosen) : maxOf(rs, budgetOf));
        const took = reproduced && chosen ? tookOf(chosen) : null;
        out.push({
          arxiv_id, runs: rs, reproduced, successCount: successRuns.length, totalRuns: rs.length,
          chosen, run_id: chosen ? chosen.run_id : null,
          model: chosen ? (chosen.model || "—") : (models.join(", ") || "—"), models,
          claim: estRow ? estRow.claim : null, links: estRow ? estRow.links : null, kind: estRow ? estRow.kind : null,
          audited: !!auditedRun,
          auditScore: auditedRun ? auditedRun.audit_score : null,
          auditReportedScore: auditedRun ? auditedRun.audit_reported_score : null,
          auditVerdict: auditedRun ? auditedRun.audit_verdict : null,
          auditFlag: auditedRun ? !!auditedRun.audit_has_high_cheat_flag : false,
          inDataset: !!estRow, set: estRow ? estRow.set : null,
          tier: estRow ? estRow.tier : null, band: estRow ? estRow.band : null,
          predicted, predictedFromDataset: fromDataset != null, took,
          delta: (took != null && predicted != null) ? round(took - predicted) : null,
          verdict: V ? V.ofPaper(reproduced, runFamilies) : "idle", runFamilies,
        });
      }
      return out;
    },

    summary(papers) {
      const repro = papers.filter((p) => p.reproduced);
      const sum = (rows, k) => { let any = false, t = 0; for (const r of rows) if (r[k] != null) { any = true; t += r[k]; } return any ? t : null; };
      const predicted = sum(repro, "predicted"), took = sum(repro, "took");
      // audit scores are the Stage-7 auditor's 0–10 scale; aggregate over RUNS, not
      // papers (a paper may have several graded runs). 0 is a real score — use != null.
      let gradedRuns = 0, scoreSum = 0;
      for (const p of papers) for (const run of (p.runs || [])) if (run.audit_score != null) { gradedRuns++; scoreSum += run.audit_score; }
      const avgScore = gradedRuns ? Math.round((scoreSum / gradedRuns) * 10) / 10 : null;
      const scorePct = avgScore == null ? null : Math.round((avgScore / 10) * 100);
      return {
        total: papers.length, reproduced: repro.length, notReproduced: papers.length - repro.length,
        predicted, took, efficiency: (took != null && predicted) ? Math.round((took / predicted) * 100) : null,
        runs: papers.reduce((a, p) => a + p.totalRuns, 0),
        gradedRuns, scoreSum, avgScore, scorePct,
      };
    },

    tierStats(papers) {
      const stats = {};
      for (const p of papers) {
        const t = p.tier || "untiered";
        (stats[t] || (stats[t] = { total: 0, repro: 0 })).total++;
        if (p.reproduced) stats[t].repro++;
      }
      const keys = TIER_ORDER.filter((k) => stats[k]).concat(Object.keys(stats).filter((k) => !TIER_ORDER.includes(k)));
      return { keys, stats };
    },

    // model × tier matrix: per cell, reproduced / attempted papers
    modelTier(runs, successTag) {
      const E = window.Estimates, tag = successTag || this.successTag;
      const M = new Map();
      for (const run of (runs || [])) {
        const model = run.model || "—";
        const tier = (E && E.row(run.arxiv_id) && E.row(run.arxiv_id).tier) || "untiered";
        if (!M.has(model)) M.set(model, {});
        const row = M.get(model);
        const cell = row[tier] || (row[tier] = { papers: new Set(), repro: new Set() });
        cell.papers.add(run.arxiv_id);
        if (this.isSuccess(run, tag)) cell.repro.add(run.arxiv_id);
      }
      const tiers = TIER_ORDER.filter((t) => [...M.values()].some((r) => r[t]))
        .concat([...new Set([...M.values()].flatMap((r) => Object.keys(r)))].filter((t) => !TIER_ORDER.includes(t)));
      const models = [...M.keys()].sort();
      return { models, tiers, get: (m, t) => { const c = M.get(m) && M.get(m)[t]; return c ? { repro: c.repro.size, total: c.papers.size } : null; } };
    },

    csv(papers) {
      const pct = (a, b) => (a == null || !b ? "" : Math.round((a / b) * 100));
      const cell = (v) => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
      const head = ["arxiv_id", "claim", "reproduced", "audit_score", "audit_verdict", "success_runs", "total_runs",
        "model", "tier", "h100_band", "predicted_h100", "took_h100", "delta_h100", "ratio_pct", "success_run_id"];
      const body = papers.map((p) => [p.arxiv_id, p.claim || "", p.reproduced ? "yes" : "no",
        p.auditScore ?? "", p.auditVerdict ?? "", p.successCount, p.totalRuns,
        p.model, p.tier ?? "", p.band ?? "", p.predicted ?? "", p.took ?? "", p.delta ?? "", pct(p.took, p.predicted), p.run_id ?? ""]);
      return [head, ...body].map((r) => r.map(cell).join(",")).join("\n");
    },
    download(papers) {
      const blob = new Blob([this.csv(papers)], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "repro-report.csv";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  };

  window.Report = Report;
})();
