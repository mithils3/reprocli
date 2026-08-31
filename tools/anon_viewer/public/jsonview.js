/* jsonview.js: turns the machine-generated JSON that closes a reproduction run
   or an audit run into a readable instrument card instead of a wall of text.
   parse() cheaply rejects prose and truncated payloads. blockHtml() sniffs the two
   known shapes, the agent's self-report and the auditor's verdict, and renders
   each as a card, falling back to a collapsible JSON tree for anything else. Also
   wires the one document-level click handler that toggles the .jnode carets the
   render_round.js tree emits. Attaches window.JsonView; leans on RENDER.esc and
   RENDER.nodeHtml. */
"use strict";

(function () {
  const R = () => window.RENDER;
  const esc = (s) => R().esc(s);
  const isNum = (v) => typeof v === "number" && isFinite(v);
  const numStr = (x) => (typeof x === "number" ? String(Math.round(x * 1e6) / 1e6) : String(x));

  // ---- parse: object/array or null ------------------------------------------
  function parse(text) {
    if (typeof text !== "string") return null;
    let s = text.trim();
    const fence = /^```(?:json)?\s*([\s\S]*?)\s*```$/i.exec(s);
    if (fence) s = fence[1].trim();
    const a = s[0], z = s[s.length - 1];
    if ((a !== "{" && a !== "[") || (z !== "}" && z !== "]")) return null;
    try { const v = JSON.parse(s); return (v && typeof v === "object") ? v : null; }
    catch (e) { return null; }
  }

  function treeHtml(obj) { return `<div class="jraw">${R().nodeHtml(obj, null, true)}</div>`; }
  function rawFooter(obj) {
    return `<div class="collapse"><details><summary>raw json</summary>` +
      `<pre class="stream jv-rawjson">${esc(JSON.stringify(obj, null, 2))}</pre></details></div>`;
  }
  // collapsible prose section, "" when empty; reuses the .collapse details look
  function sec(label, text, open) {
    if (text == null || String(text).trim() === "") return "";
    return `<details class="jv-sec"${open ? " open" : ""}><summary>${esc(label)}</summary>` +
      `<p class="rprose">${esc(text)}</p></details>`;
  }
  // leftover keys (not consumed by a card) rendered as a tree, when any remain
  function leftover(o, consumed) {
    const rest = {}; let any = false;
    for (const k of Object.keys(o)) {
      if (consumed.has(k)) continue;
      const v = o[k];
      if (v == null || v === "" || (Array.isArray(v) && !v.length)) continue;
      rest[k] = v; any = true;
    }
    return any ? `<details class="jv-sec"><summary>other fields</summary>${treeHtml(rest)}</details>` : "";
  }

  // ---- op humanizer + pass/fail --------------------------------------------
  function humanOp(op, tol) {
    switch (op) {
      case "abs_rel_within": return `within ±${numStr(tol * 100)}% relative`;
      case "abs_within": return `within ±${numStr(tol)}`;
      case "ge": case "gte": return "≥ reference";
      case "le": case "lte": return "≤ reference";
      case "eq": return "equals";
      default: return String(op == null ? "" : op) + (tol != null ? " " + numStr(tol) : "");
    }
  }
  // { cls, tag, delta }. Pass or fail only when both values are finite numbers
  function compare(op, m, r, tol) {
    if (!isNum(m) || !isNum(r)) return { cls: "", tag: "", delta: "" };
    let pass, delta;
    if (op === "abs_rel_within") {
      const rel = Math.abs(m - r) / Math.abs(r);
      pass = rel <= tol; delta = `Δ ${Math.round(rel * 10000) / 100}% rel`;
    } else if (op === "abs_within") {
      pass = Math.abs(m - r) <= tol; delta = `Δ ${numStr(Math.abs(m - r))}`;
    } else if (op === "ge" || op === "gte") {
      pass = m >= r; delta = `Δ ${numStr(Math.abs(m - r))}`;
    } else if (op === "le" || op === "lte") {
      pass = m <= r; delta = `Δ ${numStr(Math.abs(m - r))}`;
    } else if (op === "eq") {
      pass = m === r; delta = `Δ ${numStr(Math.abs(m - r))}`;
    } else return { cls: "", tag: "", delta: "" };
    return { cls: pass ? "pass" : "fail", tag: pass ? "WITHIN TOLERANCE" : "OUTSIDE TOLERANCE", delta };
  }

  // ---- audit verdict card ---------------------------------------------------
  const AUDIT_KEYS = new Set(["paper_id", "central_claim", "match_bar_kind", "target_metric",
    "target_scope", "reference_value", "op", "tolerance", "execution_verified", "execution_evidence",
    "measured_value", "measured_citation", "cheat_flags", "value_comparison", "methodology_notes",
    "score", "confidence", "rationale", "verdict"]);

  function scoreBand(s) { const n = isNum(s) ? s : 0; return n >= 8 ? "yes" : n >= 6 ? "over" : "no"; }
  function auditHead(o) {
    const band = scoreBand(o.score), val = o.score != null ? o.score : 0;
    let h = `<span class="jv-score ${band} tnum">${esc(val)}<i>/10</i></span>`;
    if (o.verdict) h += `<span class="schip jv-verdict">${esc(o.verdict)}</span>`;
    if (isNum(o.confidence)) h += `<span class="schip">confidence ${Math.round(o.confidence * 100)}%</span>`;
    if (o.execution_verified === true) h += `<span class="badge yes">execution verified</span>`;
    else if (o.execution_verified === false) h += `<span class="badge no">execution NOT verified</span>`;
    if (o.match_bar_kind) h += `<span class="schip">${esc(o.match_bar_kind)}</span>`;
    if (o.paper_id) h += `<span class="schip">${esc(o.paper_id)}</span>`;
    return `<div class="jv-head">${h}</div>`;
  }
  function compareStrip(o) {
    const c = compare(o.op, o.measured_value, o.reference_value, o.tolerance);
    const cell = (v, lab) => `<div class="jv-cell"><div class="jv-cv tnum">${esc(v != null ? v : "·")}</div>` +
      `<div class="jv-cl">${lab}</div></div>`;
    const rel = `<div class="jv-rel"><div class="jv-op">${esc(humanOp(o.op, o.tolerance))}</div>` +
      `${c.delta ? `<div class="jv-delta tnum">${esc(c.delta)}</div>` : ""}` +
      `${c.tag ? `<div class="jv-tag">${c.tag}</div>` : ""}</div>`;
    const metric = o.target_metric ? `<div class="jv-metric">${esc(o.target_metric)}</div>` : "";
    const scope = o.target_scope ? `<div class="jv-scope">${esc(o.target_scope)}</div>` : "";
    return `${metric}<div class="jv-compare ${c.cls}">${cell(o.measured_value, "measured")}${rel}` +
      `${cell(o.reference_value, "reference")}</div>${scope}`;
  }
  function cheatFlags(flags) {
    if (!Array.isArray(flags) || !flags.length) return `<span class="jv-noflags">✓ no integrity flags</span>`;
    return flags.map((f) => {
      let label;
      if (typeof f === "string") label = f;
      else if (f && typeof f === "object")
        label = (f.severity ? f.severity + " · " : "") + (f.flag || f.name || f.code || JSON.stringify(f));
      else label = String(f);
      return `<span class="schip jv-flag">${esc(label)}</span>`;
    }).join("");
  }
  function auditCard(o) {
    return `<div class="jv-card jv-audit">${auditHead(o)}` +
      `${o.central_claim ? `<p class="jv-claim">${esc(o.central_claim)}</p>` : ""}` +
      `${compareStrip(o)}<div class="jv-flags">${cheatFlags(o.cheat_flags)}</div>` +
      `${sec("value comparison", o.value_comparison, true)}` +
      `${sec("auditor rationale", o.rationale, true)}` +
      `${sec("execution evidence", o.execution_evidence, false)}` +
      `${sec("measured citation", o.measured_citation, false)}` +
      `${sec("methodology notes", o.methodology_notes, false)}` +
      `${leftover(o, AUDIT_KEYS)}${rawFooter(o)}</div>`;
  }

  // ---- agent self-report card -----------------------------------------------
  const REPORT_KEYS = new Set(["paper_id", "claim", "what_ran", "scoring_command", "measurements",
    "agent_assessment", "changes_made", "blockers", "evidence_files"]);
  const ASSESS = { reproduced: "yes", partial: "over", not_reproduced: "no", could_not_run: "slate" };

  function measurements(ms) {
    if (!Array.isArray(ms) || !ms.length) return `<p class="rprose muted">no measurements reported</p>`;
    const rows = ms.map((m) => {
      const ev = Array.isArray(m.evidence) ? m.evidence.map((e) => `<code>${esc(e)}</code>`).join(" ") : "";
      return `<tr><td>${esc(m.metric)}</td><td><b>${esc(m.observed_value)}</b></td>` +
        `<td>${esc(m.reference_value != null ? m.reference_value : "·")}</td>` +
        `<td>${esc(m.scope)}</td><td>${ev}</td></tr>`;
    }).join("");
    // the wrapper lets a wide measurements table scroll inside the card instead
    // of stretching the card past its column on a narrow screen
    return `<div class="jv-tscroll"><table class="jv-table"><thead><tr><th>metric</th><th>observed</th><th>reference</th>` +
      `<th>scope</th><th>evidence</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  function reportCard(o) {
    const badge = ASSESS[o.agent_assessment] || "slate";
    const cmd = o.scoring_command && String(o.scoring_command).trim()
      ? `<div class="jv-ml"><div class="block-l">scoring command</div><pre class="cmd">${esc(o.scoring_command)}</pre></div>` : "";
    const blockers = o.blockers && String(o.blockers).trim()
      ? `<details class="jv-sec jv-blockers" open><summary>blockers</summary><p class="rprose">${esc(o.blockers)}</p></details>` : "";
    const files = Array.isArray(o.evidence_files) && o.evidence_files.length
      ? `<div class="jv-ml"><div class="block-l">evidence files</div><div class="jv-files">` +
        `${o.evidence_files.map((f) => `<span class="schip">${esc(f)}</span>`).join("")}</div></div>` : "";
    return `<div class="jv-card jv-report"><div class="jv-head"><span class="badge ${badge}">${esc(o.agent_assessment)}</span>` +
      `<span class="jv-selfnote">the agent's own account of the run, graded separately by the auditor</span>` +
      `${o.paper_id ? `<span class="schip">${esc(o.paper_id)}</span>` : ""}</div>` +
      `${o.claim ? `<p class="jv-claim">${esc(o.claim)}</p>` : ""}${measurements(o.measurements)}${cmd}` +
      `${sec("what ran", o.what_ran, true)}` +
      `${sec("changes made", o.changes_made, String(o.changes_made || "").length <= 400)}` +
      `${blockers}${files}${leftover(o, REPORT_KEYS)}${rawFooter(o)}</div>`;
  }

  // ---- detect + dispatch ----------------------------------------------------
  function blockHtml(text) {
    const o = parse(text);
    if (!o) return null;
    if (typeof o.agent_assessment === "string" && Array.isArray(o.measurements))
      return { label: "🧾 final report, the agent's own account", html: reportCard(o) };
    if ((o.score !== undefined || o.verdict !== undefined) &&
        (o.central_claim !== undefined || o.rationale !== undefined || o.cheat_flags !== undefined))
      return { label: "⚖ audit verdict", html: auditCard(o) };
    return { label: null, html: treeHtml(o) + rawFooter(o) };
  }

  // ---- delegated caret toggle (fixes the render_round.js tree carets too) ---
  if (!document.__jvWired) {
    document.__jvWired = true;
    document.addEventListener("click", (e) => {
      const head = e.target.closest && e.target.closest(".jline.jhead");
      if (!head) return;
      const node = head.closest(".jnode.branch");
      if (node) node.classList.toggle("collapsed");
    });
  }

  window.JsonView = { parse, treeHtml, blockHtml, sec };
})();
