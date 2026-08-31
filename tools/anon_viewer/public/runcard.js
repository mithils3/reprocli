/* runcard.js: the small telemetry helpers shared by the runs table and the paper
   page: the agent short name and the micro fuel bar (spent/budget with an indigo
   predicted tick, readable H100·h numbers, no raw decimals). Attaches onto
   window.RENDER. */
"use strict";

(function () {
  const R = window.RENDER, esc = R.esc;
  const clamp = (v) => Math.max(0, Math.min(100, v));

  // agent short name: strip everything through the last "/"
  function shortModel(m) { if (!m) return ""; const i = String(m).lastIndexOf("/"); return i >= 0 ? String(m).slice(i + 1) : String(m); }

  // micro fuel bar (6px) = spent/budget + indigo predicted tick; omitted with no budget data
  function microFuelHtml(run) {
    const { total, spent, predicted } = R.fuelNums(run);
    if (total == null || spent == null) return "";
    const over = predicted != null && spent > predicted;
    const pct = total ? clamp((spent / total) * 100) : 0;
    const predPct = (total && predicted != null) ? clamp((predicted / total) * 100) : null;
    const fillCls = over ? "over" : "done";
    return `<span class="mfuel"><span class="mfuel-bar" title="${esc(R.fmtHM(spent))} of ${esc(R.fmtHM(total))} H100·h">` +
      `<i class="mfuel-fill ${fillCls}" style="width:${pct.toFixed(1)}%"></i>` +
      (predPct != null ? `<i class="mfuel-pred" style="left:${predPct.toFixed(1)}%"></i>` : "") +
      `</span><span class="mfuel-v tnum">${R.fmtHM(spent)} / ${R.fmtHM(total)}</span></span>`;
  }

  Object.assign(window.RENDER, { microFuelHtml, shortModel });
})();
