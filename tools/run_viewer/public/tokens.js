/* tokens.js — a real BPE token counter for the Stats tab, loaded lazily from a
   CDN the first time the tab is opened (no build step, no bundle bloat).

   The served models (DeepSeek / MiniMax) ship their own tokenizers, which aren't
   available as a tiny browser lib, so we count with tiktoken's o200k_base (the
   GPT-4o vocab) — a close, consistent proxy. Treat the numbers as estimates
   (~±15%), useful for *comparing* runs, not for billing. If the CDN is blocked,
   we fall back to a chars/4 heuristic and say so. */
"use strict";

const Tokens = {
  _encode: null,
  method: "loading…",
  ready_: null,

  ready() {
    if (this.ready_) return this.ready_;
    const tryImport = async (url, name) => {
      const m = await import(url);
      const enc = m.encode || (m.default && m.default.encode);
      if (typeof enc !== "function") throw new Error("no encode export");
      this._encode = enc;
      this.method = name;
    };
    this.ready_ = (async () => {
      try {
        await tryImport("https://esm.sh/gpt-tokenizer@2.9.0/encoding/o200k_base", "o200k_base · tiktoken");
      } catch (e1) {
        try {
          await tryImport("https://esm.sh/gpt-tokenizer@2.9.0", "cl100k_base · tiktoken");
        } catch (e2) {
          this._encode = null;
          this.method = "≈ chars/4 (tokenizer CDN unreachable)";
        }
      }
      return this;
    })();
    return this.ready_;
  },

  // Token count for one string. Robust to special-token sequences in tool output.
  count(s) {
    if (!s) return 0;
    if (!this._encode) return Math.ceil(s.length / 4);
    try {
      return this._encode(s).length;
    } catch (e) {
      try { return this._encode(s, { allowedSpecial: "all" }).length; } catch (e2) {}
      return Math.ceil(s.length / 4);
    }
  },
};

window.Tokens = Tokens;
