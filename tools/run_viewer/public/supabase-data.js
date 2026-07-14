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
    const rows = data || [];
    if (window.Freeze) window.Freeze.setRuns(rows);
    return rows;
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

  // ---- S7 auditor runs (audit_runs / audit_events) -------------------------
  // audit_events share repro_events' shape, so rowsToRounds/render just work. We
  // alias audit_run_id -> run_id and verdict -> audit_verdict so the run renderer
  // and Verdict.ofRun (which reads audit_verdict) light up unchanged.
  _auditRun(r) {
    if (!r) return r;
    return { ...r, run_id: r.audit_run_id, audit_verdict: r.verdict,
      audit_reproduced: r.reproduced, audit_score: r.score };
  },
  async listAudits() {
    const { data, error } = await this.client.from("audit_runs")
      .select("*").order("updated_at", { ascending: false }).limit(300);
    if (error) throw error;
    return (data || []).map((r) => this._auditRun(r));
  },
  async loadAudit(auditRunId) {
    const [runRes, evRes] = await Promise.all([
      this.client.from("audit_runs").select("*").eq("audit_run_id", auditRunId).limit(1),
      this.client.from("audit_events").select("*").eq("audit_run_id", auditRunId).order("seq", { ascending: true }),
    ]);
    if (evRes.error) throw evRes.error;
    const run = this._auditRun((runRes.data && runRes.data[0]) || { audit_run_id: auditRunId, arxiv_id: "" });
    const events = evRes.data || [];
    return { run, events, rounds: this.rowsToRounds(events) };
  },
  subscribeAudit(auditRunId, onEvent, onRunPatch) {
    return this.client.channel("audit:" + auditRunId)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "audit_events",
        filter: `audit_run_id=eq.${auditRunId}` }, (p) => onEvent(p.new))
      .on("postgres_changes", { event: "*", schema: "public", table: "audit_runs",
        filter: `audit_run_id=eq.${auditRunId}` }, (p) => onRunPatch(this._auditRun(p.new)))
      .subscribe();
  },
  subscribeAuditList(onChange) {
    return this.client.channel("audits")
      .on("postgres_changes", { event: "*", schema: "public", table: "audit_runs" },
        (p) => onChange(this._auditRun(p.new || p.old), p.eventType))
      .subscribe();
  },

  // ---- cluster telemetry (host_status / host_metrics; anon read-only) ------
  // The tables may not exist yet — callers (hosts.js / hoststrip.js) catch and
  // degrade silently. gpus is jsonb: [{i,util,mem,mem_total,power,temp}, ...].
  async listHosts() {
    const { data, error } = await this.client.from("host_status")
      .select("*").order("updated_at", { ascending: false });
    if (error) throw error;
    return data || [];
  },
  subscribeHosts(cb) {
    return this.client.channel("hosts")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "host_status" }, (p) => cb(p.new))
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "host_status" }, (p) => cb(p.new))
      .subscribe();
  },
  async loadHostMetrics({ host, run_id, sinceMinutes = 45 } = {}) {
    let q = this.client.from("host_metrics").select("*")
      .gte("created_at", new Date(Date.now() - sinceMinutes * 60e3).toISOString());
    if (host) q = q.eq("host", host);
    if (run_id) q = q.eq("run_id", run_id);
    const { data, error } = await q.order("created_at", { ascending: true }).limit(200);
    if (error) throw error;
    return data || [];
  },
  subscribeMetrics(cb) {
    // one channel for all hosts/runs — callers filter rows by host / run_id
    return this.client.channel("host-metrics")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "host_metrics" }, (p) => cb(p.new))
      .subscribe();
  },

  // ---- user-authored run tags (repro_tags: anon read + write) --------------
  async listTags() {
    if (!this.client) return [];
    const { data, error } = await this.client.from("repro_tags").select("run_id,tags");
    if (error) throw error;
    return data || [];
  },
  async setTags(runId, tags) {
    if (!this.client) throw new Error("offline");
    if (!tags.length) {
      const { error } = await this.client.from("repro_tags").delete().eq("run_id", runId);
      if (error) throw error;
      return;
    }
    const { error } = await this.client.from("repro_tags")
      .upsert({ run_id: runId, tags }, { onConflict: "run_id" });
    if (error) throw error;
  },
  subscribeTags(onChange) {
    return this.client.channel("tags")
      .on("postgres_changes", { event: "*", schema: "public", table: "repro_tags" },
        (p) => onChange(p.new || p.old, p.eventType))
      .subscribe();
  },

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
