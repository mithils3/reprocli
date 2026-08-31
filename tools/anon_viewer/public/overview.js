/* overview.js: the landing worksheet. Headline tiles and a reproduced-rate
   gauge, then the agent x tier matrix (mean audit score, reproduced share, n)
   whose cells route into the filtered runs table, a failure-mode stack per
   agent in the fixed vocabulary order, the 0 to 10 score histogram and the
   budget row that puts reproduced runs next to the rest, tier by tier. The
   matrix always shows the full three by three; everything under it is
   recomputed from the run rows under the global Agent and Tier filter. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, C = () => window.Charts;
  const TIER_CLS = { run: "yes", retrain: "over", reimplement: "no" };
  const pct1 = (x) => (Math.round(x * 1000) / 10).toFixed(1) + "%";
  const pct0 = (x) => Math.round(x * 100) + "%";

  function scoreColour(s) {
    const n = Number(s);
    return n >= 8 ? "--yes" : n >= 6 ? "--over" : n <= 0 ? "--no" : "--slate";
  }
  const meanOf = (arr) => (arr.length ? arr.reduce((a, x) => a + x, 0) / arr.length : null);
  // fraction of its own granted budget one run spent
  const spentFrac = (r) => (r.budget_h100 ? (r.spent_h100 || 0) / r.budget_h100 : null);

  const OverviewView = {
    root() { return document.querySelector("#overview-root"); },

    rows() {
      const D = window.Data, S = window.State;
      return D.runs.filter((r) =>
        (S.model === "all" || r.model === S.model) &&
        (S.tier === "all" || r.tier === S.tier));
    },

    // headline tiles read the collection, not the filter; the gauge reads the filter
    tilesHtml(rows) {
      const D = window.Data;
      const papers = D.benchmark.papers != null ? D.benchmark.papers : D.papers.length;
      const all = D.runs.length;
      const reproAll = D.runs.filter((r) => r.audit_reproduced).length;
      const repro = rows.filter((r) => r.audit_reproduced).length;
      const tile = (l, v, sub, cls) =>
        `<div class="ov-tile ${cls || ""}"><div class="ovt-l">${esc(l)}</div><div class="ovt-v tnum">${v}</div>${sub ? `<div class="ovt-s">${esc(sub)}</div>` : ""}</div>`;
      const tiles = [
        tile("PAPERS", papers, "target papers"),
        tile("RUNS", all, "one per paper and tier"),
        tile("AGENTS", D.models.length, "under test"),
        tile("REPRODUCED", all ? pct1(reproAll / all) : "·", `${reproAll} of ${all} runs`, "yes"),
      ].join("");
      const scope = rows.length === all ? "across the whole set" : "in this selection";
      return `<section class="ov-tiles">
        <div class="ov-tilerow">${tiles}</div>
        <div class="thesis-card gauge-card">
          ${C().arcGauge(repro, rows.length || 1, {
            num: `${repro}/${rows.length}`,
            pct: rows.length ? pct1(repro / rows.length) : "no runs",
            label: `${repro} of ${rows.length} runs reproduced`,
          })}
          <div class="gauge-cap"><b>reproduced runs</b><span>${esc(scope)}, graded by ${esc(window.Data.auditor.name)} at 8 and above</span></div>
        </div>
      </section>`;
    },

    matrixHtml() {
      const D = window.Data, S = window.State;
      const cell = (mk, tk) => {
        const rs = D.runs.filter((r) => r.model === mk && r.tier === tk);
        const off = (S.model !== "all" && S.model !== mk) || (S.tier !== "all" && S.tier !== tk);
        if (!rs.length) return `<td class="mt-cell empty">·</td>`;
        const mean = meanOf(rs.filter((r) => r.audit_score != null).map((r) => r.audit_score));
        const rep = rs.filter((r) => r.audit_reproduced).length;
        const share = (rep / rs.length) * 100;
        return `<td class="mt-cell live ${off ? "off" : ""}" data-model="${esc(mk)}" data-tier="${esc(tk)}" tabindex="0" role="button"
            title="open the ${esc(rs.length)} run${rs.length === 1 ? "" : "s"} behind this cell">
          <span class="mt-mean tnum">${mean == null ? "·" : mean.toFixed(2)}</span>
          <span class="mt-frac tnum">${rep}/${rs.length} reproduced</span>
          <span class="mt-bar"><i style="width:${share.toFixed(0)}%"></i></span></td>`;
      };
      const head = `<tr><th></th>${D.tiers.map((t) =>
        `<th class="mt-tier"><span class="badge ${TIER_CLS[t.key] || "slate"}">${esc(t.name)}</span>` +
        `<span class="mt-what">${esc(t.what || "")}</span></th>`).join("")}</tr>`;
      const body = D.models.map((m) => {
        const rs = D.runs.filter((r) => r.model === m.key);
        const mean = meanOf(rs.filter((r) => r.audit_score != null).map((r) => r.audit_score));
        const chip = mean == null ? "" : `<span class="mt-score tnum" title="mean audit score over this agent's runs">${mean.toFixed(2)}</span>`;
        return `<tr><td class="mt-model">${esc(m.name)}${chip}</td>${D.tiers.map((t) => cell(m.key, t.key)).join("")}</tr>`;
      }).join("");
      return `<div class="panel-card">
        <div class="pc-head"><span class="plate">audit score by agent and tier</span><span class="lc-sub">mean audit score out of 10 · reproduced share · click a cell for its runs</span></div>
        <div class="tscroll"><table class="matrix mt-big">${head}${body}</table></div>
      </div>`;
    },

    modesHtml(rows) {
      const D = window.Data, S = window.State;
      const present = window.Modes.all.filter((m) => D.runs.some((r) => r.mode === m.key));
      if (!present.length || !rows.length) return C().empty("failure modes");
      const total = {};
      rows.forEach((r) => { if (r.mode) total[r.mode] = (total[r.mode] || 0) + 1; });
      const agents = D.models.filter((m) => S.model === "all" || m.key === S.model);
      const bars = agents.map((m) => {
        const rs = rows.filter((r) => r.model === m.key);
        if (!rs.length) return "";
        const counts = {};
        rs.forEach((r) => { const k = r.mode || "other"; counts[k] = (counts[k] || 0) + 1; });
        const segs = present.filter((x) => counts[x.key]).map((x) => ({
          colour: x.colour, pct: (counts[x.key] / rs.length) * 100,
          title: `${x.name}: ${counts[x.key]} of ${rs.length}`,
        }));
        return C().barRow(m.name, segs, String(rs.length), `${m.name} · ${rs.length} runs`);
      }).join("");
      const lg = C().legend(present.map((x) => ({ colour: x.colour, label: `${x.name} (${total[x.key] || 0})` })));
      return C().card("primary failure mode by agent", "share of each agent's runs", lg, bars);
    },

    histogramHtml(rows) {
      const counts = {};
      for (let i = 0; i <= 10; i++) counts[i] = 0;
      rows.forEach((r) => { if (r.audit_score != null) counts[r.audit_score] = (counts[r.audit_score] || 0) + 1; });
      const keys = Object.keys(counts).sort((a, b) => Number(a) - Number(b));
      return `<div class="chart-card">
        <div class="chart-h"><span class="chart-t">score distribution</span><span class="chart-s">runs per audit score</span></div>
        ${C().histogram(counts, { keys, colour: scoreColour })}</div>`;
    },

    // budget: mean share of a run's own budget, reproduced runs against the rest
    computeHtml(rows) {
      const D = window.Data, S = window.State;
      const tiers = D.tiers.filter((t) => S.tier === "all" || t.key === S.tier);
      const groups = tiers.map((t) => {
        const rs = rows.filter((r) => r.tier === t.key);
        if (!rs.length) return "";
        const line = (label, subset, colour) => {
          const fr = meanOf(subset.map(spentFrac).filter((x) => x != null));
          if (fr == null) return C().barRow(label, [], `· ${subset.length} runs`, `${t.name} · ${label} · no runs`);
          return C().barRow(label, [{ colour, pct: Math.max(0, Math.min(100, fr * 100)), title: `${pct0(fr)} of budget` }],
            `${pct0(fr)} · ${subset.length} runs`, `${t.name} · ${label} · mean ${pct0(fr)} of budget over ${subset.length} runs`);
        };
        return `<div class="cmp-group">
          <div class="cmp-tier"><span class="badge ${TIER_CLS[t.key] || "slate"}">${esc(t.name)}</span><span class="cmp-what">${esc(t.what || "")}</span></div>
          ${line("reproduced", rs.filter((r) => r.audit_reproduced), "--yes")}
          ${line("not reproduced", rs.filter((r) => !r.audit_reproduced), "--no")}
        </div>`;
      }).join("");
      return C().card("budget spent", "mean share of a run's own budget", "",
        groups || `<div class="chart-empty">no data</div>`);
    },

    render() {
      const host = this.root();
      if (!host) return;
      const rows = this.rows();
      host.innerHTML = `
        <div class="ov-head">
          <div><h1>Reproduction run traces</h1>
            <div class="ov-sub">Agents reproducing the central claim of a machine learning paper under a fixed budget in H100 hours. Every run below is a full transcript, graded by ${esc(window.Data.auditor.name)} against the claim it was asked to hit.</div></div>
        </div>
        ${this.tilesHtml(rows)}
        ${this.matrixHtml()}
        <section class="grid2 ov-grid">${this.modesHtml(rows)}${this.histogramHtml(rows)}</section>
        <section class="ov-compute">${this.computeHtml(rows)}</section>`;
      host.querySelectorAll(".mt-cell.live").forEach((td) => {
        const open = () => window.go(window.runsHash({ model: td.dataset.model, tier: td.dataset.tier, verdict: "all", mode: "all", q: "" }));
        td.addEventListener("click", open);
        td.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
      });
    },
  };

  window.OverviewView = OverviewView;
})();
