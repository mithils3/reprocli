/* verdict.js — the single source of truth that collapses the 11 freeform outcome
   tags (+ status/exit_reason) into FOUR semantic verdict families, each with a
   glyph, a word and a colour. Every view reads verdicts from here so a run looks
   the same in the run list, the paper page, the transcript and the trace cap.
   Also home to the two Greenbar grafts: the BALANCE delta and the rotated stamp.
     reproduced ● green   miss ◐ amber   fault ✕ coral   idle ○ slate   running ◍ cyan */
"use strict";

(function () {
  const esc = window.RENDER.esc;

  const FAMILY = {
    reproduced: { glyph: "●", cssvar: "--yes", word: "reproduced", stamp: "REPRODUCED" },
    miss:       { glyph: "◐", cssvar: "--over", word: "miss",       stamp: "OVER BUDGET" },
    fault:      { glyph: "✕", cssvar: "--no",  word: "fault",       stamp: "NOT REPRODUCED" },
    idle:       { glyph: "○", cssvar: "--slate", word: "idle",      stamp: "NEVER RAN" },
    running:    { glyph: "◍", cssvar: "--accent", word: "running",  stamp: "RUNNING" },
    done:       { glyph: "◌", cssvar: "--slate", word: "unjudged",  stamp: "UNJUDGED" },
  };
  // known tag -> family (everything else is ignored for colour)
  const TAG_FAMILY = {
    success: "reproduced", reproduced: "reproduced",
    partial: "miss", "honest-miss": "miss", honest_miss: "miss", round_limit: "miss",
    "round-limit": "miss", random_stop: "miss", "random-stop": "miss",
    failure: "fault", error: "fault", "wrong-target": "fault", wrong_target: "fault",
    dataset_error: "fault", "dataset-error": "fault", dataset_error_: "fault",
    "never-executed": "idle", never_executed: "idle", orphaned: "idle",
  };
  const PRECEDENCE = ["reproduced", "miss", "fault", "idle"]; // strongest first when a run has several

  function familyFromTags(tags) {
    if (!tags || !tags.length) return null;
    const fams = new Set(tags.map((t) => TAG_FAMILY[String(t).toLowerCase().trim()]).filter(Boolean));
    for (const f of PRECEDENCE) if (fams.has(f)) return f;
    return null;
  }

  // Stage-7 auditor verdict -> family. Authoritative when a run has been graded
  // (repro_runs.audit_*, set by reprocli_repro.audit_upload); tags are the fallback.
  // The auditor's full 6-verdict vocabulary (0–10 scale): disqualified (cheat/0),
  // reproduced (8–10), partial (6–7), blocked (honest availability ceiling),
  // unverifiable (never executed), not_reproduced (failed/low score).
  const AUDIT_FAMILY = {
    reproduced: "reproduced", partial: "miss", blocked: "miss",
    not_reproduced: "fault", unverifiable: "fault", disqualified: "fault",
  };
  function familyFromAudit(run) {
    if (!run) return null;
    if (run.audit_verdict) return AUDIT_FAMILY[String(run.audit_verdict).toLowerCase().trim()] || null;
    if (run.audit_reproduced === true) return "reproduced";
    if (run.audit_reproduced === false) return "fault";
    return null;
  }

  const Verdict = {
    FAMILY,
    tagFamily(tag) { return TAG_FAMILY[String(tag).toLowerCase().trim()] || null; },

    auditFamily(run) { return familyFromAudit(run); },

    // a single run -> family key: the auditor verdict wins, then tags, then status
    ofRun(run) {
      if (!run) return "idle";
      const byAudit = familyFromAudit(run);
      if (byAudit) return byAudit;
      const tags = window.Tags ? window.Tags.get(run.run_id) : [];
      const byTag = familyFromTags(tags);
      if (byTag) return byTag;
      if (window.RENDER && window.RENDER.isDead && window.RENDER.isDead(run)) return "idle";
      if (run.status === "running") return "running";
      if (run.status === "error") return "fault";
      if (run.exit_reason === "round_limit") return "miss";
      if (run.status === "finished") return "done";
      return "idle";
    },

    // a paper -> family: reproduced if any run is; else closest-to-success of its runs
    ofPaper(reproduced, runFamilies) {
      if (reproduced) return "reproduced";
      const set = new Set(runFamilies);
      for (const f of ["miss", "fault", "idle", "done"]) if (set.has(f)) return f;
      return "idle";
    },

    meta(fam) { return FAMILY[fam] || FAMILY.idle; },

    // inline verdict: glyph + word (word overridable to show the specific tag/exit)
    inline(fam, wordOverride) {
      const m = this.meta(fam);
      const w = wordOverride || m.word;
      return `<span class="vd ${fam}"><span class="vg">${m.glyph}</span>${esc(w)}</span>`;
    },

    // the most specific human word for a run (auditor verdict wins, then a known tag)
    word(run) {
      const fam = this.ofRun(run);
      if (run && run.audit_verdict && familyFromAudit(run) === fam) return run.audit_verdict;
      const tags = window.Tags ? window.Tags.get(run.run_id) : [];
      const specific = tags.find((t) => TAG_FAMILY[String(t).toLowerCase().trim()] === fam);
      if (specific) return specific;
      return this.meta(fam).word;
    },
    runInline(run) { return this.inline(this.ofRun(run), this.word(run)); },

    // rotated double-entry stamp (graft from Greenbar Ledger)
    stamp(fam, labelOverride) {
      const m = this.meta(fam);
      return `<span class="stamp ${fam}">${esc(labelOverride || m.stamp)}</span>`;
    },

    // BALANCE: took - predicted as a signed number + IN THE BLACK / IN THE RED
    balance(took, predicted, opts) {
      if (took == null || predicted == null) return "";
      const d = Math.round((took - predicted) * 1000) / 1000;
      const black = d <= 0;
      const sign = d > 0 ? "+" : d < 0 ? "−" : "";
      const cls = black ? "black" : "red";
      const word = black ? "in the black" : "in the red";
      const lead = opts && opts.lead ? `<span class="bal-l">balance</span>` : "";
      const hm = window.RENDER.fmtHM(Math.abs(d));
      return `<span class="balance ${cls}" title="${sign}${Math.abs(d)} H100·h">${lead}<span class="bal-d tnum">${sign}${hm}</span>` +
        `<span class="bal-w">${word}</span></span>`;
    },
  };

  window.Verdict = Verdict;
})();
