/* freeze.js — benchmark-freeze policy shared by Overview and Live. Every run
   started before the first run in Slurm job 2652648 is non-frozen, including
   old ungrouped runs that do not carry a parseable batch_id. */
"use strict";

(function () {
  const FIRST_FROZEN_SLURM_JOB = 2652648;
  const FIRST_FROZEN_STARTED_AT = "2026-07-14T14:27:25Z";
  const runsById = new Map();
  const listeners = new Set();
  let excluded = true;

  function slurmJobId(batchId) {
    const match = /^slurm-(\d+)$/.exec(String(batchId || ""));
    return match ? Number(match[1]) : null;
  }

  function idFreezeState(runId) {
    const raw = String(runId || "");
    const job = /^(\d+)-/.exec(raw);
    if (job) return Number(job[1]) < FIRST_FROZEN_SLURM_JOB;
    const stamp = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z-/.exec(raw);
    if (!stamp) return null;
    const iso = `${stamp[1]}-${stamp[2]}-${stamp[3]}T${stamp[4]}:${stamp[5]}:${stamp[6]}Z`;
    return Date.parse(iso) < Date.parse(FIRST_FROZEN_STARTED_AT);
  }

  function isNonFrozen(run) {
    const jobId = slurmJobId(run && run.batch_id);
    if (jobId != null && jobId < FIRST_FROZEN_SLURM_JOB) return true;
    const idState = idFreezeState(run && run.run_id);
    if (idState != null) return idState;
    const started = Date.parse(run && run.started_at);
    return Number.isFinite(started) && started < Date.parse(FIRST_FROZEN_STARTED_AT);
  }

  function isNonFrozenRecord(record) {
    const linked = record && record.graded_run_id && runsById.get(record.graded_run_id);
    if (linked) return isNonFrozen(linked);
    const linkedState = idFreezeState(record && record.graded_run_id);
    return linkedState != null ? linkedState : isNonFrozen(record);
  }

  function renderButton() {
    const button = document.querySelector("#freeze-toggle");
    if (!button) return;
    const count = [...runsById.values()].filter(isNonFrozen).length;
    button.classList.toggle("active", excluded);
    button.textContent = `${excluded ? "Non-frozen excluded" : "Exclude non-frozen"}${count ? ` (${count})` : ""}`;
    button.title = `${excluded ? "Show" : "Exclude"} all runs started before sbatch ${FIRST_FROZEN_SLURM_JOB} across every remote tab`;
  }

  function notify() { for (const fn of listeners) { try { fn(); } catch (e) {} } }
  function setRuns(rows) {
    runsById.clear();
    for (const run of rows || []) if (run && run.run_id) runsById.set(run.run_id, run);
    renderButton(); notify();
  }
  function setExcluded(value) {
    const next = !!value;
    if (next === excluded) return;
    excluded = next; renderButton(); notify();
  }
  function mount() {
    const button = document.querySelector("#freeze-toggle");
    if (button && !button.__freezeWired) {
      button.__freezeWired = true;
      button.addEventListener("click", () => setExcluded(!excluded));
    }
    renderButton();
  }
  function setButtonVisible(visible) {
    const button = document.querySelector("#freeze-toggle");
    if (button) button.classList.toggle("hidden", !visible);
  }

  window.Freeze = {
    FIRST_FROZEN_SLURM_JOB, FIRST_FROZEN_STARTED_AT, slurmJobId, idFreezeState, isNonFrozen,
    isNonFrozenRecord, isExcluded: (record) => excluded && isNonFrozenRecord(record),
    filter: (rows) => excluded ? (rows || []).filter((r) => !isNonFrozenRecord(r)) : (rows || []),
    setRuns, setExcluded, mount, setButtonVisible,
    onChange: (fn) => listeners.add(fn),
    get excluded() { return excluded; },
  };
})();
