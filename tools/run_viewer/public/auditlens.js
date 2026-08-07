/* auditlens.js — the CLAUDE-ONLY lens, a global filter over grading rather than
   over runs. A run's repro_runs.audit_* columns hold only the LAST audit uploaded
   (last-writer-wins), and for most sweeps that writer is the sweep's own model
   grading its own transcript — a self-grade. audit_runs keeps EVERY pass, so when
   the lens is on we re-point audit_verdict/score/reproduced/flag at the run's
   Claude (Anthropic) pass, and where no Claude pass exists we blank those fields
   instead of falling back to the self-grade. Blanking is the point: it makes the
   not-yet-re-audited runs visible instead of silently self-scored. Verdict, Report
   and Overview read every surface through view(); the per-grader table does not. */
"use strict";

(function () {
  const STORE_KEY = "audit_lens_claude";
  const claudeByRun = new Map(); // graded_run_id -> that run's Claude pass
  const listeners = new Set();
  let active = false;
  try { active = localStorage.getItem(STORE_KEY) === "1"; } catch (e) {}

  const isClaudeGrader = (model) => /claude/i.test(String(model || ""));
  const stamp = (row) => Date.parse((row && row.updated_at) || "") || 0;

  // A run may carry TWO Claude passes (the test-retest reruns). Keep the latest by
  // updated_at, mirroring repro_runs.audit_*'s own last-writer-wins semantics.
  // A pass counts only once it has an integer score — 0 is a real score, so the
  // guard is Number.isInteger, never truthiness.
  function consider(row) {
    if (!row || !row.graded_run_id) return;
    if (!isClaudeGrader(row.model) || !Number.isInteger(row.score)) return;
    const prev = claudeByRun.get(row.graded_run_id);
    if (!prev || stamp(row) >= stamp(prev)) claudeByRun.set(row.graded_run_id, row);
  }

  function setAudits(rows) {
    claudeByRun.clear();
    for (const row of rows || []) consider(row);
    renderButton(); notify();
  }
  function upsertAudit(row) {
    const before = row && row.graded_run_id ? claudeByRun.get(row.graded_run_id) : null;
    consider(row);
    if (before === (row && row.graded_run_id ? claudeByRun.get(row.graded_run_id) : null)) return;
    renderButton(); notify();
  }

  // The lens itself: a run seen through its Claude pass. Inactive → the same object
  // identity back, so callers can map() unconditionally. audit_reported_score is
  // always null here because audit_runs has no reported_score column — the cap the
  // stored row records is the self-grader's, and does not survive the lens.
  function view(run) {
    if (!active || !run) return run;
    const pass = claudeByRun.get(run.run_id);
    if (!pass) {
      return { ...run, audit_verdict: null, audit_score: null, audit_reported_score: null,
        audit_reproduced: null, audit_has_high_cheat_flag: null };
    }
    return { ...run,
      audit_verdict: pass.verdict ?? null,
      audit_score: pass.score ?? null,
      audit_reported_score: null,
      audit_reproduced: pass.reproduced ?? null,
      audit_has_high_cheat_flag: pass.has_high_cheat_flag ?? null };
  }

  // how much of a run set has been re-audited: finished runs are the ones an
  // auditor can grade at all, so they are the denominator.
  function coverage(runs) {
    let audited = 0, finished = 0;
    for (const run of runs || []) {
      if (!run || run.status !== "finished") continue;
      finished++;
      if (claudeByRun.has(run.run_id)) audited++;
    }
    return { audited, finished };
  }

  function renderButton() {
    const button = document.querySelector("#audit-lens-toggle");
    if (!button) return;
    button.classList.toggle("active", active);
    button.textContent = active ? "Claude-only scores" : "Claude audits only";
    button.title = `${active ? "Stop reading" : "Read"} every score and verdict from the Claude (Anthropic) audit passes in audit_runs, ignoring the self-graded audit fields stored on each run`;
  }

  function notify() { for (const fn of listeners) { try { fn(); } catch (e) {} } }
  function setActive(value) {
    const next = !!value;
    if (next === active) return;
    active = next;
    try { localStorage.setItem(STORE_KEY, active ? "1" : "0"); } catch (e) {}
    renderButton(); notify();
  }
  function mount() {
    const button = document.querySelector("#audit-lens-toggle");
    if (button && !button.__lensWired) {
      button.__lensWired = true;
      button.addEventListener("click", () => setActive(!active));
    }
    renderButton();
  }
  function setButtonVisible(visible) {
    const button = document.querySelector("#audit-lens-toggle");
    if (button) button.classList.toggle("hidden", !visible);
  }

  // subscribeAuditList delivers _auditRun()-aliased rows; they still carry the raw
  // model / graded_run_id / score / verdict fields the lens reads.
  function load(remote) {
    if (!remote || !remote.client) return;
    remote.listAudits().then((rows) => setAudits(rows)).catch(() => {});
    remote.subscribeAuditList((row) => upsertAudit(row));
  }

  window.AuditLens = {
    isClaudeGrader, setAudits, upsertAudit, view, coverage, load,
    hasClaudeAudit: (runId) => claudeByRun.has(runId),
    claudeAuditOf: (runId) => claudeByRun.get(runId) || null,
    mount, setButtonVisible, setActive,
    onChange: (fn) => listeners.add(fn),
    get active() { return active; },
  };
})();
