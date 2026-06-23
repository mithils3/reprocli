/* parser.js — turn an agent transcript (agent.log / agent.full.log / first_try.log)
   into the normalized rounds[] the renderer consumes. Pure: no DOM, no network.
   Grammar mirrors src/reprocli_repro/live_log.py exactly. */
"use strict";

const RX = {
  rule:    /^[─-]{8,}\s*$/,
  round:   /^\s*round\s+(\d+)\s+·\s+(\S+)\s+·\s+(\S+)\s*$/,
  final:   /^\s*✅\s*FINAL(?:\s*\(round\s+(\d+)\))?\s+·\s+(\S+)\s+·\s+exit=(\S+)\s+·\s+(\S+)\s*$/,
  reason:  /^\s*💭\s*reasoning\s*$/,
  assist:  /^\s*🗒\s+assistant\s*$/,
  call:    /^\s*⏺\s+(.+?)\s*$/,
  result:  /^ {2,6}([✓✗])\s+ok=(\w+)(?:\s+rc=(-?\d+))?(?:\s+([\d.]+)s)?(?:\s+([\d.]+)s)?(?:\s+\(retried\))?\s*$/,
  kv:      /^ {2,6}·\s*([A-Za-z0-9_]+)=(.*)$/,
  err:     /^ {2,6}!\s?(.*)$/,
  out:     /^ {2,6}│ ?(.*)$/,
  errout:  /^ {2,6}┊ ?(.*)$/,
  trunc:   /^…\s*\(\+(\d+)\s+more lines?\)\s*$/,
};

function newRound(kind, idx, arxiv, ts, exit) {
  return { round_index: idx, kind, arxiv_id: arxiv, ts: ts || null,
    exit_reason: exit || null, reasoning: "", content: "", calls: [] };
}

function classifyDetail(s) {
  if (s.startsWith("$ ")) return { detail_kind: "command", command: s.slice(2) };
  if (s.startsWith("(apply diff")) return { detail_kind: "diff", command: s };
  if (s.startsWith("{") || s.startsWith("[")) {
    try { return { detail_kind: "json", args: JSON.parse(s), command: null }; } catch (e) {}
  }
  return { detail_kind: "path", path: s, command: s };
}

function applyResult(call, m) {
  call.ok = m[2] === "True" || m[1] === "✓";
  if (m[3] !== undefined) call.rc = parseInt(m[3], 10);
  if (m[4] !== undefined) call.duration_s = parseFloat(m[4]);
  if (m[5] !== undefined) call.run_seconds = parseFloat(m[5]);
}

function applyKv(call, key, val) {
  val = val.trim();
  if (key === "cost_h100_hours") call.cost_h100 = parseFloat(val);
  else if (key === "remaining_h100_hours") call.remaining_h100 = parseFloat(val);
  else if (key === "bytes_written") call.bytes_written = parseInt(val, 10);
  else if (key === "path") call.path = val;
}

window.parseTranscript = function parseTranscript(text) {
  const lines = String(text || "").split(/\r?\n/);
  const rounds = [];
  let cur = null, call = null, mode = null, cmdStarted = false;
  const meta = { arxiv_id: null, total_h100: null, last_remaining_h100: null,
    last_cost_h100: null, final_exit_reason: null };

  const pushRound = () => { if (cur) rounds.push(cur); };

  for (const line of lines) {
    let m;
    if (RX.rule.test(line)) continue;

    if ((m = RX.round.exec(line))) {
      pushRound(); call = null; mode = null;
      cur = newRound("round", parseInt(m[1], 10), m[2], m[3]);
      if (!meta.arxiv_id) meta.arxiv_id = m[2];
      continue;
    }
    if ((m = RX.final.exec(line))) {
      pushRound(); call = null; mode = null;
      cur = newRound("final", m[1] != null ? parseInt(m[1], 10) : null, m[2], m[4], m[3]);
      if (!meta.arxiv_id) meta.arxiv_id = m[2];
      meta.final_exit_reason = m[3];
      continue;
    }
    if (RX.reason.test(line)) { call = null; mode = "reasoning"; continue; }
    if (RX.assist.test(line)) { mode = "content"; continue; }
    if ((m = RX.call.exec(line))) {
      if (!cur) cur = newRound("round", null, meta.arxiv_id);
      call = { tool_name: m[1], command: null, detail_kind: null, args: null,
        stdout: "", stderr: "", truncated: false };
      cur.calls.push(call); mode = "command"; cmdStarted = false;
      continue;
    }
    if (call && (m = RX.result.exec(line))) { applyResult(call, m); mode = null; continue; }
    if (call && (m = RX.kv.exec(line))) {
      applyKv(call, m[1], m[2]);
      if (call.cost_h100 != null) meta.last_cost_h100 = call.cost_h100;
      if (call.remaining_h100 != null) {
        meta.last_remaining_h100 = call.remaining_h100;
        if (meta.total_h100 == null && call.cost_h100 != null)
          meta.total_h100 = +(call.remaining_h100 + call.cost_h100).toFixed(4);
      }
      continue;
    }
    if (call && (m = RX.err.exec(line))) { call.error = m[1]; continue; }
    if (call && (m = RX.out.exec(line))) {
      if (RX.trunc.test(m[1])) call.truncated = true; else call.stdout += m[1] + "\n";
      continue;
    }
    if (call && (m = RX.errout.exec(line))) {
      if (RX.trunc.test(m[1])) call.truncated = true; else call.stderr += m[1] + "\n";
      continue;
    }

    // body text
    if (mode === "reasoning" && cur) cur.reasoning += line.replace(/^ {4}/, "") + "\n";
    else if (mode === "content" && cur) cur.content += line.replace(/^ {4}/, "") + "\n";
    else if (mode === "command" && call) {
      if (!cmdStarted) {
        Object.assign(call, classifyDetail(line.replace(/^ {1,3}/, "")));
        cmdStarted = true;
      } else if (call.command != null) {
        call.command += "\n" + line;
      }
    }
  }
  pushRound();

  for (const r of rounds) { r.reasoning = r.reasoning.trimEnd(); r.content = r.content.trimEnd();
    for (const c of r.calls) { c.stdout = c.stdout.trimEnd(); c.stderr = c.stderr.trimEnd();
      if (c.command != null) c.command = c.command.trimEnd(); } }
  return { rounds, meta };
};
