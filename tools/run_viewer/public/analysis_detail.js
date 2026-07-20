/* analysis_detail.js — the per-paper dissection view + the shared failure-mode /
   verdict / score helpers the Analysis tab reads from here. Turns one
   repro_analyses.data object (the subagent's dissection) into an instrument-panel
   read of one run: claim hero, key-facts strip, self-claim-vs-audit split, the
   agent's trajectory, cheat flags, compute and evidence quotes — the same content
   the source PDF carries, but themed, searchable and copyable. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, V = () => window.Verdict;

  // failure-mode taxonomy -> [badge variant, human label]. Variant drives colour
  // (yes/over/no/slate/predicted) so a mode reads the same in every Analysis view.
  const FM = {
    success: ["yes", "success"],
    near_miss_partial: ["over", "near-miss / partial"],
    reimplement_without_validating: ["no", "reimplemented, unvalidated"],
    killed_before_the_number: ["slate", "killed before the number"],
    artifact_unavailable_wall: ["predicted", "availability wall"],
    environment_setup_spiral: ["over", "environment spiral"],
    fabrication_or_provenance_break: ["no", "fabrication / provenance break"],
    context_or_round_exhaustion: ["slate", "context / round exhaustion"],
  };
  const fmMeta = (m) => FM[m] || ["slate", (m || "—").replace(/_/g, " ")];
  const fmBadge = (m) => { const [v, l] = fmMeta(m); return `<span class="badge ${v}" title="failure mode: ${esc(m || "")}">${esc(l)}</span>`; };
  const verdictFam = (v) => (window.Verdict && window.Verdict.auditFamily({ audit_verdict: v })) || "idle";
  const scoreChip = (s) => { if (s == null) return ""; const c = s >= 8 ? "yes" : s >= 6 ? "over" : s <= 0 ? "no" : "slate"; return `<span class="an-score ${c}">${s}<span>/10</span></span>`; };
  const fmtTok = (n) => n == null ? "—" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "k" : String(n);

  // freeform text (often multi-paragraph) -> escaped <p> blocks, \n -> <br>
  function para(t) {
    if (t == null || t === "") return `<p class="muted">—</p>`;
    return String(t).trim().split(/\n\s*\n/).map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("");
  }
  function section(title, body, note) {
    if (!body) return "";
    const n = note ? `<span class="an-sec-note">${esc(note)}</span>` : "";
    return `<section class="panel-card an-sec"><div class="pc-head"><span class="plate">${esc(title)}</span>${n}</div>${body}</section>`;
  }

  function spent(run) {
    if (!run) return null;
    if (run.spent_h100 != null) return run.spent_h100;
    if (run.total_h100 != null && run.remaining_h100 != null) return run.total_h100 - run.remaining_h100;
    return null;
  }
  function keyFacts(a, run) {
    const au = a.audit_summary || {};
    const score = run && run.audit_score != null ? run.audit_score : au.score;
    const cards = [
      ["audit score", score == null ? "—" : `${score}<span class="an-u">/10</span>`],
      ["verdict", esc((run && run.audit_verdict) || au.verdict || "—")],
      ["failure mode", esc(fmMeta(a.failure_mode)[1])],
    ];
    if (run) {
      const bud = run.total_h100 != null ? run.total_h100 : run.budget;
      cards.push(["compute", `${R.fmtHM(spent(run))}<span class="an-u"> / ${bud != null ? Math.round(bud) + "h" : "—"}</span>`]);
      if (run.tool_rounds_used != null) cards.push(["rounds", String(run.tool_rounds_used)]);
      if (run.total_tokens != null) cards.push(["tokens", fmtTok(run.total_tokens)]);
    }
    return `<div class="stat-cards an-facts">${cards.map(([l, v]) => `<div class="stat-card"><div class="sc-v">${v}</div><div class="sc-l">${esc(l)}</div></div>`).join("")}</div>`;
  }

  function selfClaim(a, run) {
    const sc = a.agent_final_selfclaim || {}, au = a.audit_summary || {};
    const honest = sc.honest_about_failure;
    const chip = honest === true ? `<span class="badge yes">honest about failure</span>`
      : honest === false ? `<span class="badge no">overclaimed</span>` : "";
    const verdict = (run && run.audit_verdict) || au.verdict, fam = verdictFam(verdict);
    return `<div class="an-claim2">
      <div class="an-claim-col claimed"><div class="an-claim-h"><span class="plate">agent claimed</span>${chip}</div>${para(sc.claimed_outcome)}
        ${sc.claimed_numbers ? `<div class="an-nums"><span class="plate">numbers</span>${para(sc.claimed_numbers)}</div>` : ""}</div>
      <div class="an-claim-col audited"><div class="an-claim-h"><span class="plate">auditor found</span>${V().inline(fam, verdict || "—")}${scoreChip(au.score)}</div>${para(au.rationale_gist)}</div>
    </div>${a.self_claim_gap ? `<div class="an-gap"><span class="plate">the gap</span>${para(a.self_claim_gap)}</div>` : ""}`;
  }

  function wall(a) {
    const w = a.genuine_wall || {};
    const hit = !!w.is_wall;
    return `<div class="an-wall ${hit ? "hit" : "none"}"><span class="badge ${hit ? "predicted" : "slate"}">${hit ? "genuine wall" : "no hard wall"}</span>${para(w.what)}</div>`;
  }
  function flags(a, run) {
    const s = run && Array.isArray(run.audit_flags) ? run.audit_flags : null;
    if (s && s.length) return s.map((f) => {
      const sev = String(f.severity || "").toLowerCase();
      const c = sev === "high" ? "no" : (sev === "med" || sev === "medium") ? "over" : "slate";
      return `<div class="an-flag ${c}"><div class="an-flag-h"><span class="an-flag-kind">${esc(f.kind || "flag")}</span><span class="badge ${c}">${esc(sev || "flag")}</span></div><div class="an-flag-ev">${esc(f.evidence || "")}</div></div>`;
    }).join("");
    const cf = (a.audit_summary || {}).cheat_flags || [];
    if (!cf.length) return `<p class="muted">No cheat flags fired.</p>`;
    return cf.map((x) => `<div class="an-flag slate"><div class="an-flag-ev">${esc(x)}</div></div>`).join("");
  }
  function insights(a) {
    const ins = a.notable_insights || [];
    return ins.length ? `<ul class="an-insights">${ins.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "";
  }
  function quotes(a) {
    const qs = a.evidence_quotes || [];
    return qs.length ? `<div class="an-quotes">${qs.map((q) => `<blockquote class="an-q"><span class="an-q-round">round ${esc(q.round)}</span><span class="an-q-txt">${esc(q.quote)}</span></blockquote>`).join("")}</div>` : "";
  }

  const AnalysisDetail = {
    fmMeta, fmBadge, verdictFam, scoreChip,

    html(a, run) {
      const au = a.audit_summary || {};
      const verdict = (run && run.audit_verdict) || au.verdict, fam = verdictFam(verdict);
      const arx = a.arxiv_id || (run && run.arxiv_id) || "";
      const stamp = V().stamp(fam, verdict ? verdict.replace(/_/g, " ").toUpperCase() : null);
      const hero = `<div class="an-d-hero">
        <div class="an-d-top">${fmBadge(a.failure_mode)}${stamp}${arx ? `<a class="an-arx" href="https://arxiv.org/abs/${esc(arx)}" target="_blank" rel="noopener">${esc(arx)} ↗</a>` : ""}
          <span class="an-d-actions"><button class="an-link" data-act="transcript"${run ? "" : " disabled"}>▷ transcript</button><button class="an-link" data-act="copy">⧉ copy JSON</button></span></div>
        <h1 class="an-d-claim">${esc(a.target_claim || arx || a.run_id)}</h1>
        ${a.paper_gist ? `<p class="an-d-gist">${esc(a.paper_gist)}</p>` : ""}</div>`;
      return hero + [
        keyFacts(a, run),
        section("self-claim vs audit", selfClaim(a, run)),
        section("artifact availability", para(a.artifact_availability)),
        section("genuine wall", wall(a)),
        section("what the agent did", para(a.agent_trajectory_summary)),
        section("failure mode", para(a.failure_mode_detail), fmMeta(a.failure_mode)[1]),
        section("cheat flags", flags(a, run)),
        a.suspected_grading_error ? section("suspected grading error", para(a.suspected_grading_error)) : "",
        section("compute pattern", para(a.compute_pattern)),
        insights(a) ? section("notable insights", insights(a)) : "",
        quotes(a) ? section("evidence", quotes(a)) : "",
      ].join("");
    },

    wire(el, a, run) {
      const t = el.querySelector('[data-act="transcript"]');
      if (t && run) t.onclick = () => window.openRun && window.openRun(run.run_id);
      const c = el.querySelector('[data-act="copy"]');
      if (c) c.onclick = () => navigator.clipboard.writeText(JSON.stringify(a, null, 2))
        .then(() => { c.textContent = "✓ copied"; setTimeout(() => c.textContent = "⧉ copy JSON", 1200); })
        .catch(() => { c.textContent = "copy failed"; });
    },
  };

  window.AnalysisDetail = AnalysisDetail;
})();
