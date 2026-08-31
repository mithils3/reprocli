/* strip.js: the transcript's vertical burn-trace rail behaviour (drawing is
   trace.js). The rail IS the scrollbar and minimap: each round is a marker on the
   cumulative-compute curve, clicking one scrolls that round into view, and an
   IntersectionObserver slides a "you-are-here" tick as you scroll. A jump-to-
   verdict button drops you on the FINAL round. */
"use strict";

(function () {
  const Strip = {
    rootEl: null, run: null, rounds: null, rail: null, _io: null, _resize: null, _marks: null,

    cleanup() {
      if (this._io) { this._io.disconnect(); this._io = null; }
      if (this._resize) { window.removeEventListener("resize", this._resize); this._resize = null; }
    },
    mount(rootEl, run, rounds) {
      this.cleanup();
      this.rootEl = rootEl; this.run = run; this.rounds = rounds || [];
      this.rail = rootEl.querySelector(".strip-rail");
      if (!this.rail || !this.rounds.length) return;
      this._resize = () => this.draw();
      window.addEventListener("resize", this._resize);
      this.draw(); this.observe();
    },
    redraw(rootEl, run, rounds) {
      this.rootEl = rootEl; this.run = run; this.rounds = rounds || [];
      this.rail = rootEl.querySelector(".strip-rail");
      if (this.rail && this.rounds.length) { this.draw(); this.observe(); }
    },

    draw() {
      const rail = this.rail; if (!rail || !window.Trace) return;
      const w = rail.clientWidth || 64, h = rail.clientHeight || 360;
      const predicted = window.RENDER.predictedOf(this.run);
      const family = window.Verdict ? window.Verdict.ofRun(this.run) : "done";
      const n = this.rounds.length;
      const markerR = Math.max(1.6, Math.min(3.2, (h / Math.max(n, 1)) / 2.4));
      const svg = window.Trace.draw(this.rounds, { orientation: "v", vbW: w, vbH: h, pad: 8,
        predicted, family, markers: true, markerR, capR: 3.6 });
      rail.innerHTML = `<div class="rail-inner">${svg}<i class="rail-here" hidden></i>` +
        `<button class="rail-jump" title="jump to the final verdict" aria-label="jump to verdict">⤓</button></div>`;
      this._marks = {};
      rail.querySelectorAll(".trace-mark").forEach((mk) => {
        this._marks[mk.dataset.round] = mk;
        mk.addEventListener("click", () => this.scrollToRound(mk.dataset.round));
      });
      const jb = rail.querySelector(".rail-jump");
      if (jb) jb.addEventListener("click", () => this.scrollToVerdict());
    },

    scrollToRound(idx) {
      const card = this.rootEl.querySelector(`.rcard[data-round="${CSS.escape(String(idx))}"]`);
      if (card) { card.classList.remove("collapsed"); card.scrollIntoView({ behavior: "smooth", block: "center" }); }
    },
    scrollToVerdict() {
      const f = this.rootEl.querySelector(".rcard.final") || this.rootEl.querySelector(".rounds .rcard:last-child");
      if (f) f.scrollIntoView({ behavior: "smooth", block: "center" });
    },

    observe() {
      if (this._io) this._io.disconnect();
      const root = this.rootEl.closest(".detail") || null;
      this._io = new IntersectionObserver((entries) => {
        let best = null;
        for (const e of entries) if (e.isIntersecting && (!best || e.intersectionRatio > best.intersectionRatio)) best = e;
        if (best) this.setHere(best.target.getAttribute("data-round"));
      }, { root, threshold: [0, .35, .7, 1], rootMargin: "-42% 0px -42% 0px" });
      this.rootEl.querySelectorAll(".rcard").forEach((c) => this._io.observe(c));
    },
    setHere(idx) {
      const rail = this.rail; if (!rail || idx == null) return;
      rail.querySelectorAll(".trace-mark.here").forEach((m) => m.classList.remove("here"));
      const mk = this._marks && this._marks[idx];
      const here = rail.querySelector(".rail-here");
      if (mk && here) { mk.classList.add("here"); here.hidden = false; here.style.top = mk.getAttribute("cy") + "px"; }
    },
  };
  window.Strip = Strip;
})();
