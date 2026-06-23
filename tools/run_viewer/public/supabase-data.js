/* supabase-data.js — the Live data source. Reads repro_runs / repro_events
   (anon, read-only) and subscribes to Realtime. rowsToRounds() reconstructs the
   exact same Round/Call shape parser.js produces, so render.js is source-agnostic. */
"use strict";

const RemoteSource = {
  client: null,

  init() {
    const cfg = window.APP_CONFIG || {};
    if (!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY || !window.supabase) return false;
    try {
      this.client = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY,
        { realtime: { params: { eventsPerSecond: 20 } } });
      return true;
    } catch (e) { return false; }
  },

  async listRuns() {
    const { data, error } = await this.client.from("repro_runs")
      .select("*").order("updated_at", { ascending: false }).limit(300);
    if (error) throw error;
    return data || [];
  },

  async loadRun(runId) {
    const [runRes, evRes] = await Promise.all([
      this.client.from("repro_runs").select("*").eq("run_id", runId).limit(1),
      this.client.from("repro_events").select("*").eq("run_id", runId).order("seq", { ascending: true }),
    ]);
    if (evRes.error) throw evRes.error;
    const run = (runRes.data && runRes.data[0]) || { run_id: runId };
    const events = evRes.data || [];
    return { run, events, rounds: this.rowsToRounds(events) };
  },

  subscribeRun(runId, onEvent, onRunPatch) {
    return this.client.channel("run:" + runId)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "repro_events",
        filter: `run_id=eq.${runId}` }, (p) => onEvent(p.new))
      .on("postgres_changes", { event: "*", schema: "public", table: "repro_runs",
        filter: `run_id=eq.${runId}` }, (p) => onRunPatch(p.new))
      .subscribe();
  },

  subscribeRunList(onChange) {
    return this.client.channel("runs")
      .on("postgres_changes", { event: "*", schema: "public", table: "repro_runs" },
        (p) => onChange(p.new || p.old, p.eventType))
      .subscribe();
  },

  unsubscribe(ch) { if (ch && this.client) this.client.removeChannel(ch); },

  // event key → which Round a row belongs to (mirrors render.js's data-key)
  roundKey(e) { return (e.kind === "final" ? "final:" : "round:") + e.round_index; },

  rowsToRounds(rows) {
    const byKey = new Map(), order = [];
    const ensure = (kind, idx) => {
      const key = kind + ":" + idx;
      let r = byKey.get(key);
      if (!r) {
        r = { round_index: idx, kind, arxiv_id: null, ts: null, exit_reason: null,
          reasoning: "", content: "", calls: [] };
        byKey.set(key, r); order.push(r);
      }
      return r;
    };
    for (const e of rows) {
      if (e.kind === "round_open" || e.kind === "final") {
        const r = ensure(e.kind === "final" ? "final" : "round", e.round_index);
        if (e.reasoning) r.reasoning = e.reasoning;
        if (e.content) r.content = e.content;
        if (e.kind === "final") r.exit_reason = e.exit_reason || r.exit_reason;
        if (!r.ts && e.created_at) r.ts = e.created_at;
      } else if (e.kind === "call_start") {
        const r = ensure("round", e.round_index);
        r.calls.push({ tool_name: e.tool_name, command: e.command, detail_kind: e.detail_kind,
          args: e.args, stdout: "", stderr: "", truncated: false });
      } else if (e.kind === "call_result") {
        const r = ensure("round", e.round_index);
        let c = r.calls[r.calls.length - 1];
        if (!c) { c = { tool_name: e.tool_name || "?", stdout: "", stderr: "", truncated: false }; r.calls.push(c); }
        c.ok = e.ok; c.rc = e.rc; c.duration_s = e.duration_s;
        c.cost_h100 = e.cost_h100; c.remaining_h100 = e.remaining_h100;
        c.error = e.error; c.path = e.path;
        c.stdout = e.stdout || ""; c.stderr = e.stderr || ""; c.truncated = !!e.truncated;
      }
    }
    return order;
  },
};

window.RemoteSource = RemoteSource;
