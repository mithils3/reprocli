/* tagfilter.js — tri-state tag include/exclude filter, shared by the Live sidebar
   and the Stats page. Each chip cycles neutral → include → exclude → neutral.
   Semantics: a run passes when it has NONE of the excluded tags AND (no includes
   are set OR it has at least one included tag). Exclude wins over include; with
   includes set, untagged runs drop out ("show only these labels"). Each page owns
   its own instance (separate state for Live vs Stats). */
"use strict";

(function () {
  const esc = window.RENDER.esc;

  function create() {
    return {
      modes: {}, // tag -> "include" | "exclude"  (absent = neutral)

      modeOf(tag) { return this.modes[tag] || null; },
      cycle(tag) {
        const m = this.modes[tag];
        if (!m) this.modes[tag] = "include";
        else if (m === "include") this.modes[tag] = "exclude";
        else delete this.modes[tag];
      },
      clear() { this.modes = {}; },
      active() { return Object.keys(this.modes).length > 0; },
      tagsOf(mode) { return Object.keys(this.modes).filter((t) => this.modes[t] === mode); },

      // forget filters for tags that no longer exist anywhere
      prune(allTags) {
        const set = new Set(allTags);
        for (const t of Object.keys(this.modes)) if (!set.has(t)) delete this.modes[t];
      },

      // does the run (by id) pass the current include/exclude sets?  T = window.Tags
      pass(runId, T) {
        const inc = this.tagsOf("include"), exc = this.tagsOf("exclude");
        if (!inc.length && !exc.length) return true;
        if (!T) return true;
        const has = (t) => T.has(runId, t);
        if (exc.some(has)) return false;          // exclude wins
        if (inc.length && !inc.some(has)) return false; // must match an include
        return true;
      },

      // render the chip bar into host; calls onChange() after any state change.
      // lead = optional label text shown before the chips.
      render(host, allTags, onChange, lead) {
        if (!host) return;
        this.prune(allTags);
        if (!allTags.length) { host.innerHTML = ""; return; }
        const chip = (t) => {
          const m = this.modeOf(t);
          const cls = m === "include" ? "inc" : m === "exclude" ? "exc" : "";
          const fam = (!cls && window.Verdict) ? window.Verdict.tagFamily(t) : null;
          const mark = m === "include" ? "✓ " : m === "exclude" ? "✕ " : "";
          const title = m === "include" ? `showing only runs tagged "${t}" — click to exclude`
            : m === "exclude" ? `hiding runs tagged "${t}" — click to clear`
            : `click to show only "${t}" · again to hide it`;
          return `<button class="tag-flt ${cls} ${fam ? "fam-" + fam : ""}" data-t="${esc(t)}" title="${esc(title)}">${mark}${esc(t)}</button>`;
        };
        const clearBtn = this.active()
          ? `<button class="tag-flt tag-flt-clear" data-clear="1" title="clear all tag filters">clear</button>` : "";
        host.innerHTML = (lead ? `<span class="tag-flt-lead">${esc(lead)}</span>` : "") +
          allTags.map(chip).join("") + clearBtn;
        host.querySelectorAll(".tag-flt[data-t]").forEach((b) =>
          b.addEventListener("click", () => { this.cycle(b.dataset.t); onChange(); }));
        const cb = host.querySelector(".tag-flt[data-clear]");
        if (cb) cb.addEventListener("click", () => { this.clear(); onChange(); });
      },
    };
  }

  window.TagFilter = { create };
})();
