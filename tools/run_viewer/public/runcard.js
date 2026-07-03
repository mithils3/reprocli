/* runcard.js — the Live-sidebar run card + the small card helpers reused by the
   Fleet board (fleet.js). A 3-line telemetry card: verdict word · model · recency,
   the claim (visually dominant), then a micro fuel bar with readable H100·h numbers
   (no raw decimals). Keeps the outer <button class="plitem" data-run> so batches.js
   and audits.js stay source-compatible. Attaches onto window.RENDER. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc, num = R.num;
  const clamp = (v) => Math.max(0, Math.min(100, v));

  // model short name: strip everything through the last "/" (MiniMaxAI/MiniMax-M2.7 → MiniMax-M2.7)
  function shortModel(m) { if (!m) return ""; const i = String(m).lastIndexOf("/"); return i >= 0 ? String(m).slice(i + 1) : String(m); }

  // micro fuel bar (6px) = spent/total + indigo predicted tick; omitted if no budget data
  function microFuelHtml(run) {
    const { total, spent, predicted } = R.fuelNums(run);
    if (total == null || spent == null) return "";
    const over = predicted != null && spent > predicted;
    const pct = total ? clamp((spent / total) * 100) : 0;
    const predPct = (total && predicted != null) ? clamp((predicted / total) * 100) : null;
    const fillCls = run.status === "finished" && !over ? "done" : over ? "over" : "";
    return `<span class="mfuel"><span class="mfuel-bar" title="${spent ?? "?"} / ${total ?? "?"} H100·h">` +
      `<i class="mfuel-fill ${fillCls}" style="width:${pct.toFixed(1)}%"></i>` +
      (predPct != null ? `<i class="mfuel-pred" style="left:${predPct.toFixed(1)}%"></i>` : "") +
      `</span><span class="mfuel-v tnum">${R.fmtHM(spent)} / ${R.fmtHM(total)}</span></span>`;
  }

  // Live sidebar item — verdict word · model · fmtAgo, claim, micro fuel bar, tag chips
  function renderRunListItem(run) {
    const si = R.statusInfo(run);
    const live = R.effectiveStatus(run) === "running";
    const claim = R.claimOf(run) || run.arxiv_id;
    const model = shortModel(run.model);
    const V = window.Verdict;
    const ago = R.fmtAgo(run.updated_at);
    const timeSlot = live
      ? `<span class="pl-ago live"><span class="dot running"></span>${ago}</span>`
      : `<span class="pl-ago">${ago}</span>`;
    const title = `${run.arxiv_id || ""}${run.run_id ? " · " + run.run_id : ""}`;
    return R.el(`<button class="plitem ${si.cls === "dead" ? "dead" : ""}" data-run="${esc(run.run_id)}" title="${esc(title)}">
      <span class="pl-l1">${V ? V.runInline(run) : ""}${model ? `<span class="pl-model tnum">${esc(model)}</span>` : ""}${timeSlot}</span>
      <span class="pl-claim">${esc(claim)}</span>
      <span class="pl-fuel">${microFuelHtml(run)}</span>
      ${window.Tags ? window.Tags.chipsHtml(run.run_id) : ""}</button>`);
  }

  Object.assign(window.RENDER, { renderRunListItem, microFuelHtml, shortModel });
})();
