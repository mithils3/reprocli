r"""Text scrub and leak gate for the anonymized reviewer viewer.

Implements SPEC.md section 3.2 (ordered rewrite rules over every string field)
and section 3.3 (the hard-fail leak gate). Import from export.py, or run
`python3 scrub.py --selftest` to exercise the rules.

Three deviations from a literal reading of 3.2, all to preserve its intent:

  * The raw-id replace (SPEC 3.1) runs BEFORE rule 1. Raw run ids carry a job-id
    prefix, so letting rule 9 fire first would shred the id and defeat the
    lookup.
  * Rule 5 rewrites the account name inside `github.com/<account>/...` and
    `Mithilss/reprobench-splits` before rule 11 can see them, so rule 11 also
    matches the post-rule-5 forms `github.com/[user]/...` and
    `[user]/reprobench-splits`. Without that the repo and dataset paths survive.
  * Rule 4's node pattern `\bgh\d{3}\b` is case-insensitive and so swallows
    GH200 before rule 10 can turn it into `[GPU]`. The node pattern carries a
    negative lookahead for 200; no compute node is named gh200.

A second red-team pass added rules 13 to 15 and widened rules 4 to 12. Three of
those additions are deliberately narrow, because the transcripts are full of
text that reads like the leak:

  * STEP is matched case-sensitively. The slurm cancellation banner writes
    `*** STEP 2919367.3 ON ... CANCELLED`, and a training log writes
    `Step   100000 | TAR=`, so a case-insensitive rule would eat the log.
  * `groups=` yields an account id only in the output of `id`, where a group
    name in parentheses follows. `groups=1` is a torch convolution argument, so
    the rule needs the parenthesis.
  * A bare `Grace` is the CPU half of the SKU in almost every occurrence, but
    not in "the saving grace", so the rule reads a 100-character window for a
    hardware word instead of firing on the name alone.

A third red-team pass added rules 16 to 29. Most of them read a bracketed token
an earlier rule wrote, because what leaked was the residue of a rule that fired
rather than text no rule saw: `delta_bfvr` left `delta_[proj]`, `/dltawork`
left `[fs]` beside four NIDs, `/u/yjian1` left `/[u]/yjian1`. The rest are
fragments a truncated log line cut below a rule's floor (`gh20`, `/work/nv`,
`reprocl`, `hf_NehEDLK`). Four of the new rules are narrow on purpose:

  * `orgs:` is a GitHub API path in most of the transcripts, so the whoami
    banner is matched through the ANSI escape the CLI prints it behind.
  * `reproc` is a package in a conda lock file, so the repo-name rule needs
    at least the l of reprocl.
  * `test partitions` in the plural is a train/validation/test split in a
    benchmark paper, so the partition rule needs the singular.
  * an `hf_` prefix is a filename (hf_xet, hf_models_lrm.json) unless it
    carries mixed case, so that rule and its gate are case-sensitive.

Rule 26's host-memory pattern reads a window the way rules 9 and 10 do, and
its window is wider than the paired gate's filler, so the rule fires wherever
the gate would.

The facing pass (SPEC 8.4) added rules 30 to 42 and widened two earlier rules
that were eating ordinary text:

  * The email pattern read `Acc@22.5` as an address, because its domain half
    accepted digits with no letter in them. The domain now needs a letter and
    a dot and the local half needs a letter, so `Acc@22.5` and `Acc@1` stay.
  * The `sk-` secret pattern read the tail of any hyphenated word whose second
    half ran twenty characters, so `task-conditioned_policy_network_v2` came
    back as `[redacted]`. The pattern now needs a non-word character or the
    start of the string in front of the s.

Three of the new rules are deliberately wide and take ordinary text with them.
The collateral is listed here rather than narrowed away, because each of the
three hides the shape of the machine and the shape is what a reviewer could
match against a site's public specifications:

  * The ps and top USER column is any lowercase token that opens a line in
    front of three numeric columns, so a three-column results table whose row
    label is lowercase loses that label. The anchor is written as a lookbehind
    and not as `^`, because the prefilter compiles every pattern without re.M
    and a bare `^` would only ever match the first line there.
  * A count of 72, 144 or 288 cores or threads is the node's shape wherever it
    appears, so a paper's own sentence about 288 threads reads `[cpu]` too.
  * A two or three digit gigabyte figure inside 80 characters of GPU, VRAM or
    HBM is the board's capacity, so a paper's own "8xA100 80GB GPUs" loses its
    number. The same figure with no GPU word beside it survives.

Two of the new rules are narrowed against the data they were measured on, the
way the second and third passes narrow theirs:

  * The bare `/u` root is not matched behind an angle bracket. Ten of the
    twelve occurrences in the export are the `</u>` that closes an underline
    in an HTML results table the agent pasted out of a paper, and rewriting
    those to `</home>` corrupts a passage a reviewer reads.
  * The nvidia-smi csv row must end its number at a comma or at the end of the
    line. Without that guard it also takes "2x[GPU], 28794.6s wall" and
    "on 1 [GPU], 40000 steps", which are a wall clock and a step count and are
    five of the six occurrences in the export.

`SGI Tempo` now yields `[vendor]` rather than `[cluster-sw]`, which is what
SPEC 8.4 asks for; it is a vendor name and not a software stack version.
"""

import gzip
import json
import os
import re
import sys

# Every 7-digit job id we know of: the slurm-* batch ids in repro_runs, the job
# prefixes that appear in run ids, and the three ids SPEC 3.2 rule 9 names.
JOB_IDS = {
    "2599138", "2602811", "2611235", "2635067", "2640098", "2652648", "2666353",
    "2672018", "2678961", "2687371", "2690187", "2698678", "2759663", "2766342",
    "2799428", "2859889", "2883229", "2889476", "2889575", "2896059", "2918306",
    "2936132",
}

_job_ids = set(JOB_IDS)
_id_map = {}
_id_re = None
_rules = []
_prefilter = None


# --------------------------------------------------------------------------
# raw id replace (SPEC 3.1)
# --------------------------------------------------------------------------
def _trie_add(root, word):
    node = root
    for ch in word:
        node = node.setdefault(ch, {})
    node["$"] = True


def _trie_pattern(node):
    if "$" in node and len(node) == 1:
        return ""
    alts = []
    for ch in sorted(k for k in node if k != "$"):
        alts.append(re.escape(ch) + _trie_pattern(node[ch]))
    body = alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")"
    # a terminal node with children may stop here, so the tail is optional as a
    # whole; grouping it is what makes the "?" apply to the tail and not its
    # last character.
    return "(?:" + body + ")?" if "$" in node else body


def set_id_map(mapping):
    """Install the raw run id / audit run id replace table.

    Keys are raw ids from anywhere in the DB, values are the anon id when the
    run is in the export and "[run]" otherwise.
    """
    global _id_map, _id_re
    _id_map = dict(mapping)
    if not _id_map:
        _id_re = None
        return
    root = {}
    for word in _id_map:
        _trie_add(root, word)
    _id_re = re.compile(_trie_pattern(root))


def add_job_ids(ids):
    """Extend the known-job-id set (rule 9) and recompile."""
    _job_ids.update(str(i) for i in ids)
    _compile()


# --------------------------------------------------------------------------
# rules (SPEC 3.2), applied in order
# --------------------------------------------------------------------------
# A bare "Grace" is the CPU half of the SKU that rule 10 exists to hide, but it
# is also an ordinary English word. Read a window on both sides for a hardware
# word rather than firing on the name alone.
_GRACE = r"\bgrace\b"
_GRACE_CTX = re.compile(
    r"aarch64|\barm\b|\bcpu\b|\bcores?\b|\bnode\b|\bgpu\b|\[GPU\]"
    r"|hopper|superchip|cluster|nvidia", re.I)


# The harness's own id space. A 7-digit number starting 25 to 29 is a job,
# step or session id when a job word sits near it, and a pid, a byte count or a
# git short hash when none does. Both shapes are everywhere in the transcripts,
# so the rule reads a window instead of the number alone, and the gate below
# looks for the same pairing.
_JOBNUM = r"(?<![0-9.])2[5-9][0-9]{5}(?:\.\d{1,3})?(?![0-9])"
_JOBWORD = (r"job|jobs|jobid|job_id|slurm|srun|sbatch|step|steps|stepid|session"
            r"|sessions|allocation|alloc|scancel|squeue|sacct|cancel|cancelled"
            r"|queue|queued|held|holding|hold|released|release|expired|node")
_JOB_CTX = re.compile(r"\b(?:" + _JOBWORD + r")\b", re.I)


def _job_repl(m):
    text = m.string
    a = max(0, m.start() - 130)
    b = min(len(text), m.end() + 130)
    around = text[a:m.start()] + " " + text[m.end():b]
    return "[job]" if _JOB_CTX.search(around) else m.group(0)


def _grace_repl(m):
    text = m.string
    a = max(0, m.start() - 100)
    b = min(len(text), m.end() + 100)
    around = text[a:m.start()] + " " + text[m.end():b]
    return "[GPU]" if _GRACE_CTX.search(around) else m.group(0)


# The board's capacity, which is only a leak beside the token that names the
# board. Written as a window rather than as a pattern that captures the text
# between the two, because a capture is emitted verbatim and a second capacity
# inside it would ride out untouched: "94GB on the 120GB [GPU]" left the 120.
# The window stops at a sentence end, so a paper's own hardware a sentence away
# keeps its number, and it is wider than the paired gate's filler.
_GPUCAP = r"\b1?\d{2}\s?GB\b"


def _gpucap_repl(m):
    text = m.string
    before = text[max(0, m.start() - 60):m.start()]
    after = text[m.end():m.end() + 60]
    before = before.rsplit("\n", 1)[-1].rsplit(".", 1)[-1]
    after = after.split("\n", 1)[0].split(".", 1)[0]
    return "[GPU-spec]" if "[GPU]" in before or "[GPU]" in after else m.group(0)


# The host's memory, which sizes the node the same way the GPU capacity sizes
# the board. A three-digit gigabyte figure is a tensor or a checkpoint far more
# often than it is a machine, so the rule reads a window for the word that says
# whose memory it is. The window is wider than the gate's filler below, so the
# rule fires wherever the gate would.
_RAMSIZE = r"\b[45]\d{2}\s?GB\b"
_RAM_WORD = r"\bnode\b|\bnodes\b|\bhost\b|\bRAM\b|\blogin\b"
_RAM_CTX = re.compile(_RAM_WORD, re.I)


def _ram_repl(m):
    text = m.string
    a = max(0, m.start() - 100)
    b = min(len(text), m.end() + 100)
    around = text[a:m.start()] + " " + text[m.end():b]
    return "[node-spec]" if _RAM_CTX.search(around) else m.group(0)


# SPEC 8.4 widens both windows. The board's capacity is named by VRAM and HBM
# as often as by the token rule 25 reads, and the figure is not always three
# digits with a leading 1, so rule 33 reads 80 characters of one line for any
# of the three words. The window stops at a newline and not at a sentence end,
# because the text that carries this is a table row and not a sentence.
# The figure takes a decimal tail with it. Without that, the 80 places where
# an evidence table reports "14.00 GB (14.72%)" of usage came back as
# "14.[GPU-mem] (14.72%)", which is corrupted text on a page a reviewer reads,
# and the leading guard is what stops the split from happening at all.
_GPUMEM = r"(?<![\d.])\d{2,3}(?:\.\d{1,3})?\s?GB\b"
_GPUMEM_CTX = re.compile(r"\bGPUs?\b|\bVRAM\b|\bHBM|\[GPU\]", re.I)


def _gpumem_repl(m):
    text = m.string
    before = text[max(0, m.start() - 80):m.start()].rsplit("\n", 1)[-1]
    after = text[m.end():m.end() + 80].split("\n", 1)[0]
    if _GPUMEM_CTX.search(before) or _GPUMEM_CTX.search(after):
        return "[GPU-mem]"
    return m.group(0)


# The host's memory in the spellings rule 26 does not reach: a Gi or a bare G
# suffix, a figure in the 200s or 300s, and the words `free` and the meminfo
# keys print beside it. The window is 40 characters, which is what SPEC 8.4
# asks for and is tighter than rule 26's, so an ordinary three-digit gigabyte
# figure a clause away from the word host keeps its number.
_RAM8 = r"\b[2-5]\d{2}\s?(?:Gi|GB|G)\b"
_RAM8_WORD = (r"\bfree\b|MemAvailable|MemTotal|\bavailable\b|\bRAM\b"
              r"|\bhost\b|\bnode\b")
_RAM8_CTX = re.compile(_RAM8_WORD, re.I)


def _ram8_repl(m):
    text = m.string
    a = max(0, m.start() - 40)
    b = min(len(text), m.end() + 40)
    around = text[a:m.start()] + " " + text[m.end():b]
    return "[RAM]" if _RAM8_CTX.search(around) else m.group(0)


def _rule_sources():
    jobs = "|".join(sorted(_job_ids))
    return [
        # 1. secrets
        (r"hf_[A-Za-z0-9]{20,}", "[redacted]", re.I),
        # SPEC 8.4: a non-word character or the start of the string in front of
        # the s, or else `task-conditioned_policy_network_v2` is a key.
        (r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{20,}", "[redacted]", re.I),
        (r"ghp_[A-Za-z0-9]{30,}", "[redacted]", re.I),
        (r"AKIA[0-9A-Z]{16}", "[redacted]", re.I),
        (r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}", "[redacted]", re.I),
        # 2. emails. SPEC 8.4: a letter in the local half and a letter plus a
        # dot in the domain, so a metric written `Acc@22.5` is not an address.
        (r"[A-Za-z0-9._%+-]*[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+\.[A-Za-z]{2,}",
         "[email]", re.I),
        # 3. env dumps
        (r"(USER|LOGNAME|HOME|MAIL|HOSTNAME|SLURM_CLUSTER_NAME|SLURM_SUBMIT_HOST"
         r"|SLURMD_NODENAME|SLURM_JOB_NODELIST|SLURM_NODELIST|SLURM_JOB_PARTITION"
         r"|SLURM_JOB_ACCOUNT|SLURM_JOB_QOS|SLURM_JOB_USER|SLURM_TOPOLOGY_ADDR"
         r"|NCCL_SOCKET_IFNAME)=\S*", r"\1=[redacted]", re.I),
        # 4. hostnames
        (r"[\w.-]*\.(?:delta\.internal\.ncsa\.edu|ncsa\.illinois\.edu"
         r"|illinois\.edu|ncsa\.edu)", "[host]", re.I),
        (r"\bgh-login0?\d\b", "[login-node]", re.I),
        # the GH200 negative lookahead keeps rule 10's [GPU] from being eaten
        # here; no node is named gh200.
        (r"\bgh(?!200)\d{3}(?:\.hsn\.cm)?\b", "[node]", re.I),
        (r"\bcm\.delta\b", "[host]", re.I),
        # an /etc/hosts dump of the management network, and the driver banner
        (r"\bx\d{3,5}c\d+[rs]\d+b\d+\b", "[node]", 0),
        (r"\boscar_server\b", "[host]", re.I),
        (r"\bSGI\s+Tempo\b", "[vendor]", re.I),
        # 5. people
        (r"msalunkhe|msalunke|mithils3|mithilss|salunkhe|salunke|mithil",
         "[user]", re.I),
        # the spellings a ps or ls listing leaves: msalunk, msalunk+, msalunkiwl
        (r"m?salunk[\w+.-]*", "[user]", re.I),
        (r"/u/\[user\]", "/home/[user]", re.I),
        # anything still sitting on /u/ is either another home directory or a
        # third-party url path; the gate forbids the prefix either way.
        (r"/u/", "/[u]/", re.I),
        # 6. project / account
        (r"bfvr-dtai-gh|betw-dtai-gh|bfvr-delta-\w+|betw-delta-\w+", "[account]", re.I),
        # the same prefix used as a hostname: dtai-prov02, dtai-sched
        (r"(?:root@)?\bdtai[\w.-]*", "[host]", re.I),
        (r"/work/nvme/bfvr", "/work", re.I),
        # the same project root as the mount table prints it, without /work
        (r"/nvme/(?:bfvr|betw)(?![\w-])", "/work", re.I),
        (r"/work/hdd/bfvr", "/work-hdd", re.I),
        # the roots on their own, for the paths where the agent elided the
        # project segment as "..."
        (r"/work/(?:nvme|hdd)(?![\w-])", "/work", re.I),
        (r"/?\bdlta\w*", "[fs]", re.I),
        (r"/(projects|scratch)/bfvr", r"/\1/[proj]", re.I),
        (r"bfvr|\bbetw\b", "[proj]", re.I),
        # site POSIX account identifiers, from `id` and every `ls -l`
        (r"\bgrp_\d+\b", "[group]", 0),
        (r"\b(uid|gid)=\d+", r"\1=[id]", re.I),
        (r"\bgroups=\d+(?=\()", "groups=[id]", re.I),
        # 7. cluster software / partitions
        (r"/sw/spack/\S+", "/sw/[redacted]", re.I),
        (r"\bdeltas?\d{2}[\w-]*", "[cluster-sw]", re.I),
        (r"\bghx4(?:-interactive)?\b|\bgpu[AH]100x[48](?:-interactive)?\b",
         "[partition]", re.I),
        (r"\bhsn[0-3]\b", "[iface]", re.I),
        # 8. institution
        (r"DeltaAI|Delta AI", "[cluster]", re.I),
        (r"\bDelta\b(?=\s+(?:cluster|login|GPU|node|system|HPC|account|allocation))",
         "[cluster]", 0),
        (r"NCSA|University of Illinois|Illinois|UIUC|Urbana[- ]Champaign|Urbana",
         "[institution]", re.I),
        # 9. slurm ids
        # the raw run id shape, for an id the id map never saw
        (r"\b\d{6,8}-\d{4}\.\d{4,5}-[0-9a-f]{6,8}(?:-\d{4}\.\d{4,5}-audit)?\b",
         "[run]", re.I),
        (r"slurm-\d{6,8}", "sweep", re.I),
        (r"(SLURM_JOB_ID|SLURM_JOBID|--jobid|jobid|job id|job)\s*[=: ]\s*\d{6,8}",
         r"\1=[job]", re.I),
        (r"slurm-?\d+\.(out|err)", r"job.\1", re.I),
        # interactive step and session ids, which are not batch ids and so are
        # not in the known list: the cancellation banner, a cgroup path, a
        # report field and the agent's own prose. STEP stays case-sensitive so
        # that "Step   100000 | TAR=" in a training log survives.
        (r"(StepId=)\d{6,8}(?:\.\d{1,3})?", r"\1[job]", re.I),
        (r"(\bSTEP\s+)\d{6,8}(?:\.\d{1,3})?", r"\1[job]", 0),
        (r"(\bjob_)\d{6,8}", r"\1[job]", re.I),
        (r"(\b(?:jobs?|jobid|job_id|slurm_jobs?|sessions?|allocations?|scancel"
         r"|squeue\s+-j|sacct\s+-j)[\"\'\s:=(,_-]{0,6})\d{6,8}(?:\.\d{1,3})?",
         r"\1[job]", re.I),
        # a second id in the same sentence: "SLURM jobs [job] and 2886437"
        (r"(\[job\](?:\s*,\s*|\s+and\s+))\d{6,8}(?:\.\d{1,3})?", r"\1[job]", re.I),
        # the known ids. No word boundary, because job_2896059 has none.
        (r"(?<![0-9])(?:" + jobs + r")(?![0-9])(?:\.\d{1,3})?", "[job]", 0),
        # an id the agent mentions a clause away from the word that names it:
        # "the session is still the same one (2920217)", "the jobid changed
        # from 2697063 to 2697082", "the generation ran on GPU node #2699237"
        (_JOBNUM, _job_repl, 0),
        # the <arxiv>-<hex> tail of a raw run id whose job prefix is now [job]
        (r"(?:\[job\]-|\[run\]-|agent_runs/)\d{4}\.\d{4,5}-[0-9a-f]{6,8}\b",
         "[run]", re.I),
        # 10. hardware
        (r"\bGPU-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", "[gpu-uuid]", re.I),
        (r"GH200(?:[\s_-]*\d{2,3}\s*GB)?", "[GPU]", re.I),
        # the spaced spelling needs its own boundary, or "through 200" matches
        (r"\bGH[\s_-]200(?:[\s_-]*\d{2,3}\s*GB)?", "[GPU]", re.I),
        # the capacity left standing beside an already-replaced SKU
        (r"\[GPU\][\s_-]*\d{2,3}\s*GB", "[GPU]", re.I),
        (r"grace[\s_-]?hopper", "[GPU]", re.I),
        (r"\bgrace[\s_-]+(?:cpu|superchip|cores?|node)s?\b", "[GPU]", re.I),
        (_GRACE, _grace_repl, re.I),
        # 11. repos / datasets / harness
        (r"Mithilss/reprobench-splits|\[user\]/reprobench-splits", "[dataset]", re.I),
        (r"github\.com/mithils3\S*|github\.com/\[user\]\S*", "[repo]", re.I),
        (r"reprocli\w*", "harness", re.I),
        (r"rjnkpoxwdslkgxjliakq", "[storage]", re.I),
        (r"agent-logs\.vercel\.app", "[viewer]", re.I),
        # the benchmark's development name; the paper and the site say RECLAIM
        (r"ReproBench", "RECLAIM", re.I),
        # Retired agents. SPEC 1 keeps their runs out of the export and SPEC 3.3
        # gates their names, but a listing of the shared model cache still names
        # a checkpoint, so the names need a rule of their own. Each pattern is
        # tight enough to leave a paper's own text alone: GLM matches only the
        # versioned model, and Laguna only the checkpoint, never the surname
        # Lagunas or a LagunaConfig class.
        (r"(?:models--)?poolside(?:--|/)Laguna[\w.-]*", "[model]", re.I),
        (r"\bLaguna-S[\w.-]*", "[model]", re.I),
        (r"\bpoolside\b", "[vendor]", re.I),
        (r"(?:zai-org(?:--|/))?\bGLM-5(?:\.\d+)?\b", "[model]", re.I),
        # 12. private / campus IPs
        (r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
         r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
         r"|192\.168\.\d{1,3}\.\d{1,3}"
         r"|141\.142\.\d{1,3}\.\d{1,3})\b", "[ip]", 0),
        # the forms the agent wrote by hand when it quoted df or mount output:
        # a truncated 172.28.52 and an x-masked 172.28.87.x or 172.28.x.x. The
        # 10 and 192.168 spaces need a literal x octet, because "vLLM 0.10.x"
        # and "CUDA 12.x" are everywhere and an address is not.
        (r"\b172\.(?:1[6-9]|2\d|3[01])\.[0-9x]{1,3}(?:\.[0-9x]{1,3})?\b", "[ip]", re.I),
        (r"(?<![\d.])(?:10|192\.168)(?:\.[0-9x]{1,3}){1,2}\.x{1,3}(?![\w.])",
         "[ip]", re.I),
        # 13. wall-clock stamps. SPEC 3.1 reduces time to t_rel_s, and a shell
        # `date` inside the sandbox prints the site's timezone with it.
        (r"\[?\b20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"
         r"(?:Z|[+-]\d{2}:?\d{2})?\]?", "[timestamp]", re.I),
        (r"\b[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+"
         r"(?:[AP]M\s+)?(?:CDT|CST|EDT|EST|MDT|MST|PDT|PST|UTC|GMT)\s+\d{4}\b",
         "[timestamp]", 0),
        # 14. the retired difficulty vocabulary, where it is bound to the word
        # it labels. A bare "hard" belongs to the agent and stays.
        (r"(?:\bdifficulty\s+)?\btier\s*[:=]\s*(?:easy|medium|hard)\b",
         "tier: [tier]", re.I),
        (r"\btier\s+(?:easy|medium|hard)\b", "tier [tier]", re.I),
        (r"\b(?:easy|medium|hard)([\s_-])(tier|sweep|split|band)\b",
         r"[tier]\1\2", re.I),
        # 15. internal table and column names
        (r"\b(?:repro_(?:runs|events|analyses|sweeps|tags)|audit_runs"
         r"|audit_events|host_probe)\b", "[internal]", re.I),
        # ------------------------------------------------------------------
        # A third red-team pass added rules 16 to 29. Every one of them reads
        # text the rules above already rewrote, so the patterns spell the
        # bracketed token and not the original name. Four are deliberately
        # narrow, again because the transcripts carry text that reads like the
        # leak: `orgs:` is a GitHub API path, `reproc` is a conda package,
        # `test partitions` is a dataset split in a paper's own words, and an
        # `hf_` prefix is usually a filename.
        # ------------------------------------------------------------------
        # 16. the account's org memberships, from `hf auth whoami`. The banner
        # is the one place the word names a person; the CLI prints it behind an
        # ANSI bold escape, which is what separates it from the API path.
        (r"\x1b\[[0-9;]*m\s*orgs\s*:[^\r\n]*", "orgs: [redacted]", re.I),
        (r"lmsys-kaggler-team|CitationComp|\[institution\]-hack-5",
         "[redacted]", re.I),
        # 17. a token prefix too short for rule 1's 20-character minimum. The
        # second pattern is case-sensitive: every benign hf_ token in the
        # transcripts is a lowercase filename (hf_xet, hf_models_lrm.json) and
        # a real key carries mixed case.
        (r"HF_TOKEN\s+prefix\s*:\s*\S+", "[redacted]", re.I),
        (r"\bhf_[A-Za-z0-9]*[A-Z][A-Za-z0-9]*(?:\.{3})?", "[redacted]", 0),
        # 18. the harness repo name, cut off at a field boundary. `reproc` on
        # its own is a package in a conda lock file, so the rule needs the l.
        (r"\breprocl\w*", "harness", re.I),
        # 19. the site filesystem roots, cut off the same way
        (r"/work/(?:nvm|nv|hd)(?![\w-])", "/work", re.I),
        # 20. the SKU and a node name, cut off the same way: a log line ends
        # `1 gpu x 5 min gh20`, and the agent writes a host range as gh0xx.
        (r"\bgh[\s_-]?2\d{0,2}\b(?![\w.])", "[GPU]", re.I),
        (r"\bgh-?0?x{2,3}\b", "[node]", re.I),
        # 21. the site's POSIX group, which is the cluster name joined to the
        # project. The project half is a token by now, so reading the token is
        # what leaves an ordinary identifier like delta_matrix alone.
        (r"\bdelta_\[\w+\]", "[group]", re.I),
        # 22. the numeric owner ids, in the parenthesised spelling `stat`
        # prints and rule 6's uid= pattern does not reach.
        (r"\b(Uid|Gid):\s*\(\s*\d+/", r"\1: ([id]/", re.I),
        # 23. the retired difficulty vocabulary in the spellings rule 14 does
        # not reach: quoted, and paired with the word difficulty.
        (r"\b(tier|difficulty)(\s*[:=]\s*|\s+)[\"'“”]?"
         r"(?:easy|medium|hard)\b[\"'“”]?", r"\1\2[tier]", re.I),
        (r"[\"'“”]?\b(?:easy|medium|hard)\b[\"'“”]?"
         r"(\s*)(tier|difficulty)\b", r"[tier]\1\2", re.I),
        # 24. the scheduler partition the agent named. The singular is what
        # makes it the site's partition: `test partitions` in the plural is a
        # train/validation/test split in a benchmark paper.
        (r"[\"'`]?\btest\b[\"'`]?(?=[\s_-]*partition\b)", "[partition]", re.I),
        (r"(\bpartition)([\s:=]{1,3})[\"'`]?test\b[\"'`]?",
         r"\1\2[partition]", re.I),
        # 25. the device's own numbers, which name the SKU as surely as the SKU
        # string does: the memory total nvidia-smi prints, the power cap, the
        # non-zero PCI domain of a board, and the capacity the agent writes
        # beside the token. The last two keep their surroundings, so a nearby
        # sentence about the paper's own hardware still reads.
        (r"\b\d{4,6}\s?MiB\b", "[GPU-spec]", re.I),
        (r"\b900\s?W\b", "[GPU-spec]", re.I),
        (r"\b0000[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.\d\b", "[GPU-spec]", re.I),
        (_GPUCAP, _gpucap_repl, re.I),
        # 26. the shape of the machine: how many nodes are idle, how many GPUs
        # a node carries, how much memory the host has. The memory figure is
        # only a leak next to the word that says it is a host's, so the rule
        # reads a window the way rule 9 and rule 10 do.
        (r"\b\d{1,4}\s+(?:idle|allocated)\s+nodes?\b", "[node-spec]", re.I),
        (r"\b\d{1,4}\s+allocated,\s*\d{1,4}\s+idle\b", "[node-spec]", re.I),
        (r"\b\d\s?GPUs?\s?(?:/|per\s)node\b", "[node-spec]", re.I),
        (_RAMSIZE, _ram_repl, re.I),
        # 27. the run id shape that survived the id map: the job prefix is a
        # token by now and the hex tail can be as short as three characters,
        # which is under rule 9's floor of six.
        (r"\[(?:job|run)\]-\d{4}\.\d{4,5}(?:-[0-9a-f]{1,8})?", "[run]", re.I),
        # 28. the site software tree. Rule 7 shortens a spack path, and the
        # shortened form is itself the giveaway when a traceback prints where
        # the interpreter lives.
        (r"/sw/[\w.+\[\]/-]*", "[syspath]", re.I),
        # 29. a co-tenant's home directory, left by a ps listing on a shared
        # node, and the storage fabric's own address. Four Lustre NIDs, the
        # mount and the root under it are one filesystem's fingerprint.
        (r"/\[u\]/[A-Za-z][\w.-]*", "[path]", re.I),
        (r"(?:\[ip\]@tcp\d*:)+\[fs\](?:\[?/[\w\[\]./-]*)?", "[filesystem]", re.I),
        # ------------------------------------------------------------------
        # The facing pass (SPEC 8.4) added rules 30 to 42. Most of them read a
        # bracketed token an earlier rule wrote, the way rules 16 to 29 do.
        # Three are deliberately wide and the docstring lists what they take
        # with them: the ps USER column, the core count, and the gigabyte
        # figure beside a GPU word.
        # ------------------------------------------------------------------
        # 30. the USER column of a ps or top listing, which names whoever else
        # held the node, and the one co-tenant the transcripts name outright.
        (r"\byjian1\b", "[user]", re.I),
        (r"(?<![^\n])([ \t]*)[a-z][a-z0-9_-]{1,15}"
         r"([ \t]+\d+[ \t]+[\d.]+[ \t]+[\d.]+)", r"\1[user]\2", 0),
        # 31. the site's data export tree
        (r"/harbor\b", "[export]", re.I),
        # 32. the timezone offset rule 13 leaves standing when a space splits
        # it from the stamp
        (r"\[timestamp\]\s*[+-]\d{2}:?\d{2}\b", "[timestamp]", 0),
        # 33. the board's capacity in the window and the spellings rule 25 does
        # not reach: named by VRAM or HBM rather than by the token, and four
        # hundred and eighty rather than one hundred and twenty.
        (_GPUMEM, _gpumem_repl, re.I),
        # 34. the host's memory, in the shapes free and /proc/meminfo print
        (r"\bMem:[ \t]+\d{3}(?:Gi|GB|G)?\b", "[RAM]", re.I),
        (_RAM8, _ram8_repl, re.I),
        # 35. the node's core count. The three numbers are the site's, and a
        # paper's own sentence carrying one of them is scrubbed with it.
        (r"\b(?:72|144|288)\s?(?:CPU\s+)?(?:cores?|threads?|CPUs?)\b",
         "[cpu]", re.I),
        # 36. the retired difficulty vocabulary in the plural, which rule 14
        # cannot see because its noun ends that pattern on a word boundary
        (r"\b(?:easy|medium|hard)_sweeps?\b", "sweeps", re.I),
        (r"\bmuse_spark_sweeps\b", "sweeps", re.I),
        # 37. the home root on its own, where no account name follows it. The
        # lookbehind excludes an angle bracket, because `</u>` closes an
        # underline in the HTML results tables the agent pastes from a paper,
        # and 10 of the 12 occurrences in the data are that tag.
        (r"(?<![<\w./])/u(?![\w/])", "/home", 0),
        # 38. the site filesystem roots in every prefix a truncated log line
        # cut them to. The lookahead is what leaves /work/benchmarks alone.
        (r"/work/(?:bfv|bf|bet|be|b|hdd|hd|h|nvme|nvm|nv|n)(?![\w-])",
         "/work", re.I),
        # 39. the one or two characters left standing behind the token rule 5
        # wrote, from an account name a column width cut short
        (r"\[user\][A-Za-z0-9]{1,2}(?=[/\s\"'])", "[user]", 0),
        # 40. the device's own numbers in the two shapes rule 25 does not
        # reach: the row nvidia-smi --format=csv prints, and the memory line
        # of the serving banner. A csv field ends at a comma or at the end of
        # the line, so the guard drops "2x[GPU], 28794.6s wall" and
        # "on 1 [GPU], 40000 steps", which are five of the six occurrences in
        # the data and are a wall clock and a step count, not a board.
        (r"\[GPU\]\s*,\s*\d{4,6}(?:\s*,\s*\d{1,6})*(?![\d.]|[ \t]*[A-Za-z])",
         "[GPU], [GPU-spec]", 0),
        (r"total\s+mem\s+GB\s*:\s*[\d.]+", "total mem GB: [GPU-spec]", re.I),
        # 41. the account's own repositories in the cache layout, and the
        # bundle archive the run controller downloads
        (r"(datasets|models)--\[user\]--[\w.-]+", r"\1--[user]--[dataset]", re.I),
        (r"neurips-20\d\d-paper-bundles", "[dataset]", re.I),
        # 42. the retired difficulty vocabulary joined to the word it labels by
        # a hyphen or an underscore, which rule 23 reads as two separate words
        (r"\b(?:easy|medium|hard)[-_](?=difficulty)", "", re.I),
        # 43. the job window once more, after every other rule has run, so a
        # [job] an earlier rule wrote is the job word for the ids beside it.
        (_JOBNUM, _job_repl, 0),
    ]


def _compile():
    global _rules, _prefilter
    src = _rule_sources()
    _rules = [(re.compile(p, f), r) for p, r, f in src]
    # one cheap pass that decides whether any rule can fire at all
    _prefilter = re.compile("|".join("(?:" + p + ")" for p, _, _ in src), re.I)


_compile()


def scrub_text(value):
    """Apply the raw-id replace and every rule 1-15, in order."""
    if not value:
        return value
    if _id_re is not None:
        value = _id_re.sub(lambda m: _id_map.get(m.group(0), "[run]"), value)
    if not _prefilter.search(value):
        return value
    for rx, rep in _rules:
        value = rx.sub(rep, value)
    return value


def scrub(obj):
    """Scrub every string in a nested structure. Dict keys are schema, left as is."""
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(scrub(v) for v in obj)
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------------
# leak gate (SPEC 3.3)
# --------------------------------------------------------------------------
GATE_LITERALS = [
    "ncsa", "illinois", "uiuc", "urbana", "deltaai", "delta.internal",
    "gh-login", "msalunkhe", "mithil", "salunkhe", "bfvr", "betw-dtai", "/u/",
    "rjnkpoxwdslkgxjliakq", "slurm-2", "ghx4", "gh200", "reprocli",
    "agent-logs", "reprobench", "eyJhbGci", "@illinois",
    # second red-team pass
    "salunk", "dlta", "dtai", "oscar_server", "sgi tempo",
    "/work/nvme", "/work/hdd",
    # third red-team pass. The two truncated roots subsume the two above, and
    # "reprocl" subsumes "reprocli"; both pairs stay, because a literal that
    # names the whole word is what the SPEC's gate list asks for.
    "reprocl", "/work/nv", "/work/hd", "/sw/",
    "lmsys-kaggler-team", "citationcomp",
    # the facing pass (SPEC 8.4). "oscar_server" is already above, so the list
    # carries it once. "grace-hopper" shares its name with the shape below, and
    # a hit under that name can come from either; both stay, because a literal
    # that names the whole word is what the SPEC's gate list asks for.
    "yjian1", "/harbor", "dltawork", "dtai-", "grace-hopper", "_sweeps",
]

# Shapes rather than words, for the same pass. Each one is paired with a rule
# above, so a hit means the rule missed. Three carry a deliberate narrowing that
# the rule carries too: STEP is case-sensitive, `groups=` needs its
# parenthesis, and the private-address patterns stay inside the RFC1918 and
# campus prefixes so that a version string like 0.10.x is not an address.
GATE_SHAPES = [
    ("posix-group", r"\bgrp_\d"),
    ("posix-id", r"\b(?:uid|gid)=\d|\bgroups=\d+\("),
    ("blade-node", r"\bx\d{3,5}c\d+[rs]\d+b\d+\b"),
    ("grace-hopper", r"grace[\s_-]?hopper|\bgrace[\s_-]+(?:cpu|superchip|cores?)"
                     r"|aarch64[\s/(]*grace"),
    ("gh200-spaced", r"\bgh[\s_-]200\b"),
    ("gpu-capacity", r"\[GPU\][\s_-]*\d{2,3}\s*GB"),
    ("gpu-uuid", r"\bGPU-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b"),
    ("private-ip", r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
                   r"|172\.(?:1[6-9]|2\d|3[01])\.[0-9x]{1,3}"
                   r"|192\.168\.[0-9x]{1,3}|141\.142\.\d{1,3})\b"),
    ("timestamp", r"\b20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"),
    ("date-line", r"\b[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
                  r"\s+(?:[AP]M\s+)?(?:CDT|CST|EDT|EST|MDT|MST|PDT|PST|UTC|GMT)\s+\d{4}\b"),
    ("job-context", r"(?:\bjob_|\bjobid|\bjob_id|\bslurm_jobs?|\bjobs\s+"
                    r"|\bsessions?|\ballocations?)"
                    r"[\s:=(,_'\"-]{0,6}\d{6,8}"),
    ("run-id-shape", r"\b\d{6,8}-\d{4}\.\d{4,5}-[0-9a-f]{6,8}\b"),
    ("run-id-tail", r"(?:\[job\]-|\[run\]-|agent_runs/)\d{4}\.\d{4,5}-[0-9a-f]{6,8}\b"),
    ("tier-vocab", r"\b(?:difficulty\s+)?tier\s*[:=]?\s*(?:easy|medium|hard)\b"
                   r"|\b(?:easy|medium|hard)[\s_-](?:tier|sweep|split|band)\b"
                   # third pass: quoted, and paired with the word difficulty
                   r"|\b(?:tier|difficulty)(?:\s*[:=]\s*|\s+)[\"'“”]?"
                   r"(?:easy|medium|hard)\b"
                   r"|[\"'“”]\b(?:easy|medium|hard)\b[\"'“”]?"
                   r"\s*(?:tier|difficulty)\b"
                   r"|\b(?:easy|medium|hard)\b\s*difficulty\b"),
    ("internal-schema", r"\b(?:repro_(?:runs|events|analyses|sweeps|tags)"
                        r"|audit_runs|host_probe)\b"),
    # ----------------------------------------------------------------------
    # third red-team pass. Each shape is paired with one of rules 16 to 29, so
    # a hit means that rule missed. Two of them read the same window their rule
    # reads, and the filler excludes a backslash so that the pair has to sit
    # inside one line of one JSON string: the rules run on the decoded text,
    # where an escaped newline is a newline and stops them.
    # ----------------------------------------------------------------------
    ("org-membership", r"(?:\x1b|\\u001b)\[[0-9;]*m\s*orgs\b"
                       r"|\[institution\]-hack-5"),
    ("hf-token-prefix", r"HF_TOKEN\s+prefix\s*:"),
    ("gpu-model-fragment", r"\bgh[\s_-]?2\d{0,2}\b(?![\w.])"),
    ("node-placeholder", r"\bgh-?0?x{2,3}\b"),
    ("cluster-group", r"\bdelta_\[\w+\]"),
    ("stat-owner-id", r"\b(?:Uid|Gid):\s*\(\s*\d+/"),
    ("partition-name", r"[\"'`]?\btest\b[\"'`]?(?=[\s_-]*partition\b)"
                       r"|\bpartition[\s:=]{1,3}[\"'`]?test\b"),
    ("gpu-spec", r"\b\d{4,6}\s?MiB\b|\b900\s?W\b"
                 r"|\b0000[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.\d\b"
                 r"|\[GPU\][^.\\\n]{0,40}?\b1?\d{2}\s?GB\b"
                 r"|\b1?\d{2}\s?GB\b[^.\\\n]{0,40}?\[GPU\]"),
    ("node-spec", r"\b\d{1,4}\s+(?:idle|allocated)\s+nodes?\b"
                  r"|\b\d{1,4}\s+allocated,\s*\d{1,4}\s+idle\b"
                  r"|\b\d\s?GPUs?\s?(?:/|per\s)node\b"),
    ("node-ram-in-context",
     r"(?:" + _RAM_WORD + r")[^\"\\]{0,60}" + _RAMSIZE
     + r"|" + _RAMSIZE + r"[^\"\\]{0,60}(?:" + _RAM_WORD + r")"),
    ("run-id-token", r"\[(?:job|run)\]-\d{4}\.\d{4,5}(?:-[0-9a-f]{1,8})?"),
    ("co-tenant-home", r"/\[u\]/[A-Za-z]"),
    ("storage-fingerprint", r"(?:\[ip\]@tcp\d*:)+\[fs\]|/nvme/\[proj\]"),
]
# audit_events is scrubbed out of every string but stays a key of the bundle
# schema, so it is a rule without a gate.

# Case-sensitive, because a training log writes "Step   100000 | TAR=" and the
# slurm banner writes "*** STEP 2919367.3 ON".
GATE_SHAPES_CASED = [
    ("job-step", r"StepId=\d{6,8}|\bSTEP\s+\d{6,8}"),
    # Case-sensitive for the same reason rule 17 is: hf_xet and
    # hf_models_lrm.json are filenames, and a key carries mixed case.
    ("hf-token-mixedcase", r"\bhf_[A-Za-z0-9]*[A-Z][A-Za-z0-9]*"),
]

# The windowed pairing of the rule above, as a plain regex. The filler excludes
# a quote so the pair has to sit inside one JSON string, which is what keeps a
# token count in a numeric field from reading as an id.
_GATE_JOBNUM = r"(?<![0-9.])2[5-9][0-9]{5}(?![0-9])"
GATE_SHAPES.append(
    ("job-number-in-context",
     r"\b(?:" + _JOBWORD + r")\b[^\"]{0,120}" + _GATE_JOBNUM
     + r"|" + _GATE_JOBNUM + r"[^\"]{0,120}\b(?:" + _JOBWORD + r")\b"))
# The retired Laguna brand is six letters long, short enough that a substring
# match lands inside ordinary words a transcript is entitled to carry: Lagunas
# is the surname of an author of one of the benchmark papers and LagunaConfig
# is a model-config class. Matching it as a whole token keeps every real
# spelling (poolside--Laguna-S-2.1) and drops those. report_benign() accounts
# for what a plain substring grep would still surface. Muse Spark 1.2 joined
# the roster on 2026-09-03, so its name is no longer gated.
WORD_LITERALS = ["laguna"]
# Checked in the site's own source only. The data may legitimately carry some of
# these: SPEC 3.2 leaves srun/slurm standing inside tool output, and an agent
# quoting a paper may write "hard". The site's copy may not.
FRONTEND_LITERALS = [
    "supabase", "huggingface", "Mithilss", "freeze", "frozen", "self-grade",
    "sbatch", "slurm", "Anthropic", "trace.paper", "dev split",
]
TIER_WORDS = ["Easy", "Medium", "Hard"]


def gate_patterns():
    pats = [(lit, re.compile(re.escape(lit), re.I)) for lit in GATE_LITERALS]
    pats += [(name, re.compile(pat, re.I)) for name, pat in GATE_SHAPES]
    pats += [(name, re.compile(pat)) for name, pat in GATE_SHAPES_CASED]
    for lit in WORD_LITERALS:
        pats.append((lit, re.compile(r"(?<![A-Za-z0-9_])" + re.escape(lit)
                                     + r"(?![A-Za-z0-9_])", re.I)))
    pats.append(("hf_[A-Za-z0-9]{20}", re.compile(r"hf_[A-Za-z0-9]{20}")))
    # digit boundaries, not word boundaries: \b does not fire after the
    # underscore of job_2896059, which is how two known ids walked past this.
    pats.append(("job-id", re.compile(r"(?<![0-9])(?:" + "|".join(sorted(_job_ids))
                                      + r")(?![0-9])")))
    if _id_re is not None:
        pats.append(("raw-run-id", _id_re))
    return pats


def frontend_patterns():
    pats = [(lit, re.compile(re.escape(lit), re.I)) for lit in FRONTEND_LITERALS]
    # the retired tier vocabulary, as whole words, in the site's own copy
    pats.append(("tier-word", re.compile(r"\b(?:" + "|".join(TIER_WORDS) + r")\b")))
    return pats


def scan(text, patterns, per_pattern=20, width=60):
    """Return {pattern name: [context, ...]} for every pattern that hits."""
    hits = {}
    for name, rx in patterns:
        found = []
        for m in rx.finditer(text):
            a = max(0, m.start() - width)
            b = min(len(text), m.end() + width)
            found.append(text[a:b].replace("\n", " "))
            if len(found) >= per_pattern:
                break
        if found:
            hits[name] = found
    return hits


def benign_words(text):
    """Longer words that merely contain a WORD_LITERALS brand name.

    These are what separates the token gate from a plain substring grep, so the
    export report names every one of them rather than leaving the difference
    unexplained.
    """
    counts = {}
    for lit in WORD_LITERALS:
        for m in re.finditer(r"[A-Za-z0-9_]*" + re.escape(lit)
                             + r"[A-Za-z0-9_]*", text, re.I):
            word = m.group(0)
            if word.lower() == lit:
                continue
            counts[word] = counts.get(word, 0) + 1
    return counts


_ESCAPES = {"n": "\\u000a", "t": "\\u0009", "r": "\\u000d",
            "b": "\\u0008", "f": "\\u000c"}


def deescape(text, patterns=None):
    r"""Re-escape a control character whose JSON escape letter spells a gate
    literal with the text that follows it.

    A newline inside a JSON string is the two characters \ and n, so the value
    "coqa\ncsatqa" reads as "ncsa" to a raw grep of the file. Writing that
    newline as a \uXXXX escape keeps the decoded string identical and the file
    clean.
    """
    patterns = patterns or gate_patterns()
    for _ in range(8):
        cuts = set()
        for _name, rx in patterns:
            for m in rx.finditer(text):
                i = m.start()
                if text[i] not in _ESCAPES:
                    continue
                back = 0
                while i - 1 - back >= 0 and text[i - 1 - back] == "\\":
                    back += 1
                if back % 2 == 1:
                    cuts.add(i)
        if not cuts:
            return text
        for i in sorted(cuts, reverse=True):
            text = text[:i - 1] + _ESCAPES[text[i]] + text[i + 1:]
    return text


def read_any(path):
    """File text, gunzipping .gz in memory."""
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            return fh.read().decode("utf-8", "replace")
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8", "replace")


def gate_tree(root, per_pattern=20):
    """Run the gate over every file under root.

    Returns (hits, n_files, n_bytes, benign): `benign` maps a longer word that
    merely contains a brand name to the files it occurs in, so the report can
    account for what a plain substring grep would surface.
    """
    data_pats = gate_patterns()
    front_pats = frontend_patterns()
    hits, allowed, n_files, n_bytes = {}, {}, 0, 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".vercel"]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            n_files += 1
            n_bytes += os.path.getsize(path)
            text = read_any(path)
            rel = os.path.relpath(path, root)
            pats = data_pats
            if not rel.startswith("data" + os.sep):
                pats = data_pats + front_pats
            for key, ctxs in scan(text, pats, per_pattern).items():
                bucket = hits.setdefault(key, [])
                for c in ctxs:
                    if len(bucket) < per_pattern:
                        bucket.append(rel + ": " + c)
            for word, n in benign_words(text).items():
                entry = allowed.setdefault(word, {"n": 0, "files": []})
                entry["n"] += n
                if len(entry["files"]) < 20 and rel not in entry["files"]:
                    entry["files"].append(rel)
    return hits, n_files, n_bytes, allowed


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
CASES = [
    # 1 secrets
    ("export HF_TOKEN=hf_QWERTYuiopASDFGHjklZXCVB1234",
     "export HF_TOKEN=[redacted]"),
    ("OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz0123",
     "OPENAI_API_KEY=[redacted]"),
    ("token ghp_abcdefghijklmnopqrstuvwxyz0123456789 used",
     "token [redacted] used"),
    ("aws key AKIAIOSFODNN7EXAMPLE rotated", "aws key [redacted] rotated"),
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
     "eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
     "Authorization: Bearer [redacted]"),
    # 2 emails
    ("contact mithils3@illinois.edu for access", "contact [email] for access"),
    # 3 env dumps
    ('declare -x USER="msalunkhe"', "declare -x USER=[redacted]"),
    ("HOME=/u/msalunkhe", "HOME=[redacted]"),
    ("SLURM_JOB_NODELIST=gh012", "SLURM_JOB_NODELIST=[redacted]"),
    ("SLURM_JOB_ACCOUNT=bfvr-dtai-gh", "SLURM_JOB_ACCOUNT=[redacted]"),
    ("NCCL_SOCKET_IFNAME=hsn", "NCCL_SOCKET_IFNAME=[redacted]"),
    # 4 hostnames
    ("runs/tb/events.out.tfevents.1755123456.gh012.delta.internal.ncsa.edu.3186294.0",
     "runs/tb/[host].3186294.0"),
    ("ssh gh-login03.delta.ncsa.illinois.edu", "ssh [host]"),
    ("connected to gh-login02 ok", "connected to [login-node] ok"),
    ("worker on gh023.hsn.cm ready", "worker on [node] ready"),
    ("routed via cm.delta today", "routed via [host] today"),
    # 5 people
    ("/u/msalunkhe/scratch/run", "/home/[user]/scratch/run"),
    # 6 project / account
    ("#SBATCH --account=bfvr-dtai-gh", "#SBATCH --account=[account]"),
    ("cd /work/nvme/bfvr/runs", "cd /work/runs"),
    ("cd /work/hdd/bfvr/data", "cd /work-hdd/data"),
    ("ls /projects/bfvr/shared", "ls /projects/[proj]/shared"),
    ("the bfvr allocation is full", "the [proj] allocation is full"),
    # 7 cluster software / partitions
    # rule 28 now takes the shortened form the whole way
    ("module use /sw/spack/deltas11-2023-03/modulefiles",
     "module use [syspath]"),
    ("stack deltas11-2023-03 loaded", "stack [cluster-sw] loaded"),
    ("#SBATCH --partition=ghx4-interactive", "#SBATCH --partition=[partition]"),
    ("#SBATCH --partition=gpuA100x4", "#SBATCH --partition=[partition]"),
    ("bound to hsn2 interface", "bound to [iface] interface"),
    # 8 institution
    ("DeltaAI is an NCSA system at the University of Illinois",
     "[cluster] is an [institution] system at the [institution]"),
    ("the Delta cluster was busy", "the [cluster] cluster was busy"),
    ("UIUC and Urbana-Champaign", "[institution] and [institution]"),
    ("delta between the two runs was small", "delta between the two runs was small"),
    # 9 slurm ids
    ("logs for slurm-2652648 are here", "logs for sweep are here"),
    ("srun --jobid 2652648 --pty bash", "srun --jobid=[job] --pty bash"),
    ("tail -f slurm-1234.out", "tail -f job.out"),
    ("batch 2687371 finished", "batch [job] finished"),
    # the three ids SPEC 3.2 rule 9 names by hand
    ("batch 2666353 finished", "batch [job] finished"),
    ("batch 2678961 and 2889476 finished", "batch [job] and [job] finished"),
    # 10 hardware
    # the memory total is rule 25's now, not standing text
    ("nvidia-smi shows NVIDIA GH200 480GB, 97871MiB free",
     "nvidia-smi shows NVIDIA [GPU], [GPU-spec] free"),
    ("a Grace Hopper superchip", "a [GPU] superchip"),
    # 11 repos / datasets / harness
    ("hf download Mithilss/reprobench-splits", "hf download [dataset]"),
    ("git clone https://github.com/mithils3/reprocli.git",
     "git clone https://[repo]"),
    ("python -m reprocli_repro.audit_upload", "python -m harness.audit_upload"),
    ("https://rjnkpoxwdslkgxjliakq.supabase.co/rest/v1",
     "https://[storage].supabase.co/rest/v1"),
    ("see agent-logs.vercel.app for the run", "see [viewer] for the run"),
    ("the ReproBench lockfile pins the claim", "the RECLAIM lockfile pins the claim"),
    ("reprobench-splits/eval_100.jsonl", "RECLAIM-splits/eval_100.jsonl"),
    ("REPROBENCH_HOME is unset", "RECLAIM_HOME is unset"),
    # retired agents, in the shapes a cache listing writes them
    ("/work/[user]/.cache/hub/models--poolside--Laguna-S-2.1-INT4",
     "/work/[user]/.cache/hub/[model]"),
    ("served poolside/Laguna-S-2.1-INT4 on vllm", "served [model] on vllm"),
    ("the muse-spark-1.2-contributor endpoint", "the muse-spark-1.2-contributor endpoint"),
    ("graded by zai-org/GLM-5.2 earlier", "graded by [model] earlier"),
    # shapes the Muse Spark sweeps added on 2026-09-03
    ("--output /work/nvme/bfvr/msalunkhe/harness/muse_spark_sweeps/medium/20260816T133804Z/reproduce_2506.08898.jsonl",
     "--output /work/[user]/harness/sweeps/medium/20260816T133804Z/reproduce_2506.08898.jsonl"),
    ("3190:803230 /nvme/bfvr/msalunkhe/harness/agent_runs/2505.14827/8h/muse-run-2505.14827/workspace",
     "3190:803230 /work/[user]/harness/agent_runs/2505.14827/8h/muse-run-2505.14827/workspace"),
    ("0:00:30  114Mmsalunk+ 2775316  0.0", "0:00:30  114M[user] 2775316  0.0"),
    ("outage (attempted `2958455`, `2958456`, `[job]` etc.)",
     "outage (attempted `[job]`, `[job]`, `[job]` etc.)"),
    # 12 IPs
    ("bind 10.0.1.23 and 192.168.1.1 and 141.142.145.1",
     "bind [ip] and [ip] and [ip]"),
    ("/u/msalunke/.cache/torch/hub", "/home/[user]/.cache/torch/hub"),
    ("https://avatars.githubusercontent.com/u/77676725?v=4",
     "https://avatars.githubusercontent.com/[u]/77676725?v=4"),
    # the group name goes whole, rather than leaving the cluster half
    ("drwxrws---+ 2 msalunkhe delta_bfvr 4096 evidence",
     "drwxrws---+ 2 [user] [group] 4096 evidence"),
    ("\\definecolor{urbanablue}{RGB}{19,41,75}",
     "\\definecolor{[institution]blue}{RGB}{19,41,75}"),
    # must survive
    ("git clone https://github.com/TinyPART/msf-CNN.git",
     "git clone https://github.com/TinyPART/msf-CNN.git"),
    ("arXiv:2505.11483 reports 3.0% WER", "arXiv:2505.11483 reports 3.0% WER"),
    ("budget 96 H100-hours on aarch64", "budget 96 H100-hours on aarch64"),
    ("srun and slurm are the execution environment",
     "srun and slurm are the execution environment"),
    ("hf download datasets/TIGER-Lab/MMEB-eval --repo-type dataset",
     "hf download datasets/TIGER-Lab/MMEB-eval --repo-type dataset"),
    ("the authors report a Hardy-Weinberg check", "the authors report a Hardy-Weinberg check"),
    # benign words that contain a gated brand name; the scrub leaves them alone
    # and the gate excuses them by name
    ("scenes: Ballroom, Church, Museum, Panther",
     "scenes: Ballroom, Church, Museum, Panther"),
    ("authors Michael Niemeyer and Manuel Lagunas",
     "authors Michael Niemeyer and Manuel Lagunas"),
    ("JambaConfig, LagunaConfig, Lfm2Config", "JambaConfig, LagunaConfig, Lfm2Config"),
    ("a generalized linear model (GLM) baseline", "a generalized linear model (GLM) baseline"),
    # ------------------------------------------------------------------
    # second red-team pass: one case per finding, plus the text that looks
    # like the finding and has to survive
    # ------------------------------------------------------------------
    # job and step ids outside the known batch list
    ("*** STEP 2919367.3 ON [node] CANCELLED AT 2026-08-10T01:15:34 DUE TO TIME LIMIT ***",
     "*** STEP [job] ON [node] CANCELLED AT [timestamp] DUE TO TIME LIMIT ***"),
    ("srun: error: StepId=2890784.1 task 0 exited",
     "srun: error: StepId=[job] task 0 exited"),
    ("{\"jobid\": \"2919207\", \"slurm_job\": \"2884980\"}",
     "{\"jobid\": \"[job]\", \"slurm_job\": \"[job]\"}"),
    ("the current session (2920740) has ~10 min left, a new allocation (2902507)",
     "the current session ([job]) has ~10 min left, a new allocation ([job])"),
    ("SLURM jobs 2884980 and 2886437 were queued",
     "SLURM jobs [job] and [job] were queued"),
    # the same ids where the word that names them sits a clause away
    ("The session is still the same one (2920217) with only 274s left",
     "The session is still the same one ([job]) with only 274s left"),
    ("the jobid changed from 2697063 to 2697082, so it is a new session",
     "the jobid changed from [job] to [job], so it is a new session"),
    ("the generation ran on GPU node #2699237, then the eval lost the files",
     "the generation ran on GPU node #[job], then the eval lost the files"),
    ("the offline metric was step 2890784.4 which loaded gt + preds",
     "the offline metric was step [job] which loaded gt + preds"),
    # a known id behind an underscore, where the gate's word boundary failed
    ("0::/system.slice/slurmstepd.scope/job_2896059/step_batch/user/task_0",
     "0::/system.slice/slurmstepd.scope/job_[job]/step_batch/user/task_0"),
    # cluster filesystem and management network
    # the NIDs and the mount are one fingerprint, so they go together
    ("[ip]@tcp10:[ip]@tcp10:/dltawork  9.8T  5.1T  4.8T  52% /repro/workspace",
     "[filesystem]  9.8T  5.1T  4.8T  52% /repro/workspace"),
    ("Kernel Module for aarch64  595.71.05  Release Build  (root@dtai-prov02)",
     "Kernel Module for aarch64  595.71.05  Release Build  ([host])"),
    ("[ip]     [host] dtai-testsched", "[ip]     [host] [host]"),
    ("[ip]\tadmin oscar_server host\n[ip]\t[host] x8101c0r1b0",
     "[ip]\tadmin [host] host\n[ip]\t[host] [node]"),
    ("# SGI Tempo manages and rewrites everything below here",
     "# [vendor] manages and rewrites everything below here"),
    # the site filesystem roots with the project segment elided
    ("HF downloads default to the shared cache /work/nvme/.../hub",
     "HF downloads default to the shared cache /work/.../hub"),
    ("is /repro/workspace the same as /work/nvme?",
     "is /repro/workspace the same as /work?"),
    # POSIX account identifiers
    ("uid=91115([user]) gid=202(grp_202) groups=202(grp_202),65534(nogroup)",
     "uid=[id]([user]) gid=[id]([group]) groups=[id]([group]),65534(nogroup)"),
    ("drwx------ 2 [user] grp_202 4096 evidence",
     "drwx------ 2 [user] [group] 4096 evidence"),
    # the author's username, truncated by ps and by a column width
    ("msalunk+ 2148584  0.0  0.0  32704 ?  Ss   /home/[user]/harness",
     "[user] 2148584  0.0  0.0  32704 ?  Ss   /home/[user]/harness"),
    ("drwxrws---+ 4 msalunk", "drwxrws---+ 4 [user]"),
    ("cd /work/msalunkiwl 2>/dev/null", "cd /work/[user] 2>/dev/null"),
    # wall clock and timezone
    ("=== START bio Thu Aug  6 02:06:17 CDT 2026 ===", "=== START bio [timestamp] ==="),
    ("Release Build Mon Jun  1 03:57:01 PM CDT 2026 gcc",
     "Release Build [timestamp] gcc"),
    ("[2026-08-10T01:15:35.005] error: job step aborted",
     "[timestamp] error: job step aborted"),
    ("the repo was cloned at 2026-08-08T06:15:22Z, well before",
     "the repo was cloned at [timestamp], well before"),
    # the storage fabric address the agent masked by hand
    ("mounted from 172.28.87.x@tcp, also 172.28.x.x and 172.28.52",
     "mounted from [ip]@tcp, also [ip] and [ip]"),
    # hardware: the spellings that escaped GH200 and Grace Hopper
    ("The cluster is [GPU] which is Grace-Hopper, aarch64",
     "The cluster is [GPU] which is [GPU], aarch64"),
    ("**Hardware:** 1x [GPU] (aarch64 gracehopper)",
     "**Hardware:** 1x [GPU] (aarch64 [GPU])"),
    # the core count is rule 35's now, not standing text
    ("[GPU] typically has 72 cores (Grace)", "[GPU] typically has [cpu] ([GPU])"),
    ("the environment here is aarch64/Grace with CUDA torch",
     "the environment here is aarch64/[GPU] with CUDA torch"),
    ("the aarch64 Grace CPU is the bottleneck", "the aarch64 [GPU] is the bottleneck"),
    ("2 NVIDIA GH200-120GB nodes", "2 NVIDIA [GPU] nodes"),
    ("gres gpu:nvidia_gh200_120gb:4 on the node", "gres gpu:nvidia_[GPU]:4 on the node"),
    ("[GPU] 120 GB HBM3e", "[GPU] HBM3e"),
    ("GPU 0: NVIDIA [GPU] (UUID: GPU-7e58e92a-1765-a91b-5060-930deb107803)",
     "GPU 0: NVIDIA [GPU] (UUID: [gpu-uuid])"),
    # the raw run id tail the whole-id map could not see
    ("cat /work/[user]/harness/agent_runs/2510.09485/8h/[job]-2510.09485-8d9ab694/report.json",
     "cat /work/[user]/harness/agent_runs/2510.09485/8h/[run]/report.json"),
    (".../agent_runs/2506.10351-832e14/workspace/evidence/run_expB.sh",
     ".../[run]/workspace/evidence/run_expB.sh"),
    # the retired difficulty vocabulary
    ("The task says difficulty tier: Hard, compute band 8-32 H100-hours.",
     "The task says tier: [tier], compute band 8-32 H100-hours."),
    ("this is a Hard tier task with 0-8 H100-hours",
     "this is a [tier] tier task with 0-8 H100-hours"),
    ("the EASY-tier rows and the medium sweep",
     "the [tier]-tier rows and the [tier] sweep"),
    ("the same class of rc-masking bug flagged in the Easy-sweep OOM cascade",
     "the same class of rc-masking bug flagged in the [tier]-sweep OOM cascade"),
    # internal table and column names
    ("per audit_runs target_metric/target_scope, threshold match_bar_kind, op >=",
     "per [internal] target_metric/target_scope, threshold match_bar_kind, op >="),
    ("consistent with the project's known repro_events metering behaviour",
     "consistent with the project's known [internal] metering behaviour"),
    # must survive: the transcript text that reads like one of the rules above
    ("  Step   100000 | TAR=   2.27", "  Step   100000 | TAR=   2.27"),
    ("no cuDNN crash through 200 steps", "no cuDNN crash through 200 steps"),
    ("F.conv2d(x, w, groups=1, dilation=1)", "F.conv2d(x, w, groups=1, dilation=1)"),
    ("RuntimeError: Given groups=1, weight of size [1, 1, 11, 11]",
     "RuntimeError: Given groups=1, weight of size [1, 1, 11, 11]"),
    ("here's the saving grace: the cached reference was computed the same way",
     "here's the saving grace: the cached reference was computed the same way"),
    ("vLLM 0.10.x needs torch 2.9 and CUDA 12.x",
     "vLLM 0.10.x needs torch 2.9 and CUDA 12.x"),
    ("OApackage is not installed, can not use CDT.",
     "OApackage is not installed, can not use CDT."),
    ("Coptidice, BC, BCQ and CDT on MetaDrive", "Coptidice, BC, BCQ and CDT on MetaDrive"),
    ("a hard problem of medium size", "a hard problem of medium size"),
    ("(EngineCore pid=2753302) ImportError: libnvrtc.so.13 not found",
     "(EngineCore pid=2753302) ImportError: libnvrtc.so.13 not found"),
    ("EngineCore pid=2753302 shut down", "EngineCore pid=2753302 shut down"),
    ("#parameters: 2570692 B, 2510.44140625 KB", "#parameters: 2570692 B, 2510.44140625 KB"),
    # ------------------------------------------------------------------
    # third red-team pass: one case per finding, each followed by the
    # transcript text that reads like it and has to survive
    # ------------------------------------------------------------------
    # the account's org memberships, from the hf CLI banner
    (" + prompt-toolkit==3.0.53\n\x1b[1muser: \x1b[0m [user]\n"
     "\x1b[1morgs: \x1b[0m lmsys-kaggler-team,CitationComp,[institution]-hack-5\n"
     "--- check SD3 access ---",
     " + prompt-toolkit==3.0.53\n\x1b[1muser: \x1b[0m [user]\n"
     "orgs: [redacted]\n--- check SD3 access ---"),
    ("curl -s https://api.github.com/orgs/google-research/repos",
     "curl -s https://api.github.com/orgs/google-research/repos"),
    ("google/google-research orgs: nothing relevant",
     "google/google-research orgs: nothing relevant"),
    # a token prefix under rule 1's length floor
    ("HF_TOKEN prefix: hf_NehEDLK PWD=/repro/workspace",
     "[redacted] PWD=/repro/workspace"),
    ("The `HF_TOKEN` is `hf_NehEDLK...`, a HuggingFace token",
     "The `HF_TOKEN` is `[redacted]`, a HuggingFace token"),
    ("pip install huggingface_hub[cli,hf_xet]", "pip install huggingface_hub[cli,hf_xet]"),
    ("curl -o hf_models_lrm.json -s https://huggingface.co/api/models",
     "curl -o hf_models_lrm.json -s https://huggingface.co/api/models"),
    # the harness repo name and the filesystem roots, cut off mid-token
    ("rc=143 1769.5s cwd=/work/[user]/reprocl \u2026(+13439 chars truncated)",
     "rc=143 1769.5s cwd=/work/[user]/harness \u2026(+13439 chars truncated)"),
    ("  - reproc=14.2.4=h313beb8_2\n  - reproc-cpp=14.2.4=h313beb8_2",
     "  - reproc=14.2.4=h313beb8_2\n  - reproc-cpp=14.2.4=h313beb8_2"),
    ("--bind /tmp --bind /work/nv", "--bind /tmp --bind /work"),
    # the SKU and a node name, cut off the same way
    ("run_gpu (1 gpu x 5 min gh20 \u2026(+710 chars truncated)",
     "run_gpu (1 gpu x 5 min [GPU] \u2026(+710 chars truncated)"),
    ("aarch64 ([GPU], 'gh0xx' nodes) partition the agent had access to",
     "aarch64 ([GPU], '[node]' nodes) partition the agent had access to"),
    # the site group name and the numeric owner ids stat prints
    ("loss = delta_matrix - delta_theta_mode", "loss = delta_matrix - delta_theta_mode"),
    ("Access: (0660/-rw-rw----)  Uid: (91115/[user])   Gid: (20421/delta_[proj])",
     "Access: (0660/-rw-rw----)  Uid: ([id]/[user])   Gid: ([id]/[group])"),
    # the retired difficulty vocabulary, quoted and beside the word difficulty
    ('This is a "Hard" tier.', "This is a [tier] tier."),
    ('the difficulty tier "Hard"', "the difficulty tier [tier]"),
    ("the paper is Hard difficulty", "the paper is [tier] difficulty"),
    ("task difficulty: easy", "task difficulty: [tier]"),
    # the scheduler partition the agent named
    ('let me try the "test" partition (2h wall, 2 idle)',
     "let me try the [partition] partition (2h wall, 2 idle)"),
    ("the GPU allocation failed with partition=test",
     "the GPU allocation failed with partition=[partition]"),
    ("split by subject into train/validation/test partitions",
     "split by subject into train/validation/test partitions"),
    # the device's own numbers
    ("|   0  NVIDIA [GPU]             On  |   00000029:01:00.0 Off |     0 |",
     "|   0  NVIDIA [GPU]             On  |   [GPU-spec] Off |     0 |"),
    ("| N/A   20C    P0   80W /  900W |   0MiB /  97871MiB |   0%  Default |",
     "| N/A   20C    P0   80W /  [GPU-spec] |   0MiB /  [GPU-spec] |   0%  Default |"),
    ("the [GPU] has 120GB of HBM3e", "the [GPU] has [GPU-spec] of HBM3e"),
    ("120GB [GPU] nodes are the default", "[GPU-spec] [GPU] nodes are the default"),
    ("the paper used 8xA100 80GB for 300 epochs",
     "the paper used 8xA100 80GB for 300 epochs"),
    # two capacities in one window: the second one rode out of the first
    # version of this rule inside its captured filler
    ("Prometheus at 94GB on the 120GB [GPU] fits in one GPU",
     "Prometheus at [GPU-spec] on the [GPU-spec] [GPU] fits in one GPU"),
    # the shape of the machine
    ("- [GPU] nodes, up to 4 GPUs/node, hw=1.0",
     "- [GPU] nodes, up to [node-spec], hw=1.0"),
    ("default partition [partition] (143 allocated, 5 idle), walltime up to 2 days",
     "default partition [partition] ([node-spec]), walltime up to 2 days"),
    ("Login node RAM was 478GB total", "Login node RAM was [node-spec] total"),
    ("that materializes 110B elements, way too big (440GB) for one tensor",
     "that materializes 110B elements, way too big (440GB) for one tensor"),
    # the run id shape the id map could not see, and the site software tree
    ("evidence/[job]-2505.24680-4fd9/report.json", "evidence/[run]/report.json"),
    ("the run [job]-2412.11979 never finished", "the run [run] never finished"),
    ('  File "/sw/[redacted] line 293, in load', '  File "[syspath] line 293, in load'),
    # a co-tenant's home and the storage fabric's own address
    ("python src/simulate/fennol_npt.py /[u]/yjian1/project/electrolytes/",
     "python src/simulate/fennol_npt.py [path]/project/electrolytes/"),
    ("[ip]@tcp10:[ip]@tcp10:[ip]@tcp10:[ip]@tcp10:[fs]  9.8T  4.7T  5.1T  48% /repro/workspace",
     "[filesystem]  9.8T  4.7T  5.1T  48% /repro/workspace"),
    ("[ip]@tcp10:[fs][/nvme/[proj]/[user]/harness/agent_runs/2511.01463/32h/"
     "dsv4-reimplement-2511.01463/workspace]", "[filesystem]"),
    ("the workspace is a network filesystem ([fs]) shared",
     "the workspace is a network filesystem ([fs]) shared"),
    # ------------------------------------------------------------------
    # the facing pass (SPEC 8.4): one case per new rule, each followed by
    # the transcript text that reads like it and has to survive
    # ------------------------------------------------------------------
    # 30. the USER column of a ps or top listing, and the named co-tenant
    ("  ktanaka  31245  99.9  2.1 python train.py",
     "  [user]  31245  99.9  2.1 python train.py"),
    ("the workspace under yjian1 was still mounted",
     "the workspace under [user] was still mounted"),
    # three numeric columns is what the rule reads, so a two-column log line
    # keeps its label
    ("epoch 12 loss 0.41 acc 0.93", "epoch 12 loss 0.41 acc 0.93"),
    # 31. the export tree
    ("staged to /harbor/exports/run.tar", "staged to [export]/exports/run.tar"),
    ("the harbor master problem in the paper",
     "the harbor master problem in the paper"),
    # 32. the offset a space split from the stamp
    ("last modified 2026-08-10 01:15:35 +00:00 by the controller",
     "last modified [timestamp] by the controller"),
    ("the offset was +05:30 in the table", "the offset was +05:30 in the table"),
    # 33. the board's capacity named by a word other than the token
    ("each card reports 24GB of VRAM in the log",
     "each card reports [GPU-mem] of VRAM in the log"),
    ("the dataset shard is 24GB on disk", "the dataset shard is 24GB on disk"),
    # the decimal tail goes with the figure rather than splitting it
    ("VRAM usage was 14.00 GB (14.72%) at peak",
     "VRAM usage was [GPU-mem] (14.72%) at peak"),
    # 34. the host's memory
    ("Mem:  478Gi total on the login node", "[RAM] total on the login node"),
    ("MemAvailable: 312 Gi", "MemAvailable: [RAM]"),
    ("the model checkpoint is 480 GB in fp32",
     "the model checkpoint is 480 GB in fp32"),
    # 35. the node's core count, and the paper sentence it takes with it
    ("the hardware table lists 72 cores", "the hardware table lists [cpu]"),
    # deliberate collateral: the number is the node's shape wherever it sits
    ("288 threads of computation in the paper's model",
     "[cpu] of computation in the paper's model"),
    ("we used 64 cores for preprocessing", "we used 64 cores for preprocessing"),
    # 36. the retired vocabulary in the plural
    ("the easy_sweeps table was dropped", "the sweeps table was dropped"),
    ("we ran hyperparameter sweeps over the seed",
     "we ran hyperparameter sweeps over the seed"),
    # 37. the home root on its own
    ("df -h /u shows 90% used", "df -h /home shows 90% used"),
    ("the path lib/utils.py was edited", "the path lib/utils.py was edited"),
    ("<th><a href=\"x\"><nobr>T2M</nobr></a></u></th>",
     "<th><a href=\"x\"><nobr>T2M</nobr></a></u></th>"),
    # 38. the filesystem roots cut to two letters
    ("--bind /work/bf --bind /tmp", "--bind /work --bind /tmp"),
    ("ls /work/benchmarks/data", "ls /work/benchmarks/data"),
    # 39. the residue behind the account token
    ("cd /work/[user]2/runs", "cd /work/[user]/runs"),
    ("the [user] account was disabled", "the [user] account was disabled"),
    # 40. the device's own numbers, in a csv row and a serving banner
    ("name, memory.total\n[GPU], 97871", "name, memory.total\n[GPU], [GPU-spec]"),
    ("NVIDIA [GPU], 97871, 97359, 0, 0", "NVIDIA [GPU], [GPU-spec]"),
    ("on 1 [GPU], 40000 steps at 0.5s each",
     "on 1 [GPU], 40000 steps at 0.5s each"),
    ("2x[GPU], 28794.6s wall", "2x[GPU], 28794.6s wall"),
    ("total mem GB: 95.00", "total mem GB: [GPU-spec]"),
    ("the total memory GB column was empty",
     "the total memory GB column was empty"),
    # 41. the account's cache layout and the bundle archive
    ("ls hub/datasets--[user]--eval-100", "ls hub/datasets--[user]--[dataset]"),
    ("wget neurips-2025-paper-bundles.tar", "wget [dataset].tar"),
    ("models--facebook--opt-125m is cached", "models--facebook--opt-125m is cached"),
    # 42. the retired vocabulary joined by a hyphen
    ("the hard-difficulty rows were dropped", "the difficulty rows were dropped"),
    ("a hard optimization difficulty", "a hard optimization difficulty"),
    # the two widened rules, and the text that made them too wide
    ("write to first.last@example.org for the code",
     "write to [email] for the code"),
    ("Acc@22.5° is 61.4 and Acc@1 is 0.83",
     "Acc@22.5° is 61.4 and Acc@1 is 0.83"),
    ("mAP@0.5 and Recall@50 on the val split",
     "mAP@0.5 and Recall@50 on the val split"),
    ("the task-conditioned_policy_network_v2 checkpoint",
     "the task-conditioned_policy_network_v2 checkpoint"),
]

ID_CASES = [
    # anon ids carry the site's tier keys, so the run id above is minimax-run-*
    ("run 2652648-2505.11483-b70632 finished", "run minimax-run-2505.11483 finished"),
    ("graded by 2652648-2505.11483-b70632-2505.11483-audit",
     "graded by [run]"),
    ("older run 2599138-2505.11483-aaaaaa", "older run [run]"),
]

# What the data gate (SPEC 3.3) must catch, and what it must leave alone.
GATE_CASES = [
    ("the RECLAIM lockfile pins the claim", []),
    ("the ReproBench lockfile pins the claim", ["reprobench"]),
    ("hf download Mithilss/reprobench-splits", ["mithil", "reprobench"]),
    # Muse Spark 1.2 is on the roster since 2026-09-03, so its name passes
    ("served Muse Spark on eight nodes", []),
    ("served muse-spark-1.2 on eight nodes", []),
    ("scenes: Ballroom, Church, Museum, Panther", []),
    ("authors Michael Niemeyer and Manuel Lagunas", []),
    ("checkpoint Laguna-S-2.1 loaded", ["laguna"]),
    ("JambaConfig, LagunaConfig, Lfm2Config", []),
    ("batch 2666353 finished", ["job-id"]),
    ("bound to ghx4 on a GH200", ["ghx4", "gh200", "gpu-model-fragment"]),
    ("run on RECLAIM at 96 H100-hours", []),
    # second red-team pass: the shapes the first gate list could not see
    ("*** STEP 2919367.3 ON [node] CANCELLED", ["job-number-in-context", "job-step"]),
    ("srun: error: StepId=2890784.1 task 0", ["job-number-in-context", "job-step"]),
    ("slurmstepd.scope/job_2896059/step_batch", ["job-context", "job-id"]),
    ("the current session (2920740) is held", ["job-context", "job-number-in-context"]),
    ("The session is still the same one (2920217)", ["job-number-in-context"]),
    ("the generation ran on GPU node #2699237", ["job-number-in-context"]),
    ("mount shows :/dltawork on /repro/workspace", ["dlta", "dltawork"]),
    ("Release Build (root@dtai-prov02)", ["dtai", "dtai-"]),
    ("[ip] [host] x8101c0r1b0", ["blade-node"]),
    ("[ip] admin oscar_server host", ["oscar_server"]),
    ("# SGI Tempo manages everything below", ["sgi tempo"]),
    ("the node is aarch64 Grace-Hopper", ["grace-hopper"]),
    ("[GPU] typically has 72 Grace cores", ["grace-hopper"]),
    ("uid=91115([user]) gid=202(grp_202)", ["posix-group", "posix-id"]),
    ("drwx------ 2 [user] grp_202 4096 .", ["posix-group"]),
    ("=== START bio Thu Aug  6 02:06:17 CDT 2026 ===", ["date-line"]),
    ("[2026-08-10T01:15:35.005] error: aborted", ["timestamp"]),
    ("the fabric is 172.28.87.x@tcp", ["private-ip"]),
    ("ps shows msalunk+ 2148584", ["salunk"]),
    ("2 NVIDIA [GPU]-120GB nodes", ["gpu-capacity", "gpu-spec"]),
    ("UUID: GPU-7e58e92a-1765-a91b-5060-930deb107803", ["gpu-uuid"]),
    ("cache under /work/nvme/.../hub", ["/work/nvme", "/work/nv"]),
    ("[job]-2510.09485-8d9ab694/report.json", ["run-id-tail", "run-id-token"]),
    ("2919367-2510.09485-8d9ab694/report.json", ["run-id-shape"]),
    ("difficulty tier: Hard, compute band", ["tier-vocab"]),
    ("flagged in the Easy-sweep OOM cascade", ["tier-vocab"]),
    ("per audit_runs target_metric/target_scope", ["internal-schema"]),
    ("known repro_events metering behaviour", ["internal-schema"]),
    # and what the same gate must not fire on
    ("  Step   100000 | TAR=   2.27", []),
    ("no cuDNN crash through 200 steps", []),
    ("RuntimeError: Given groups=1, weight of size [1, 1]", []),
    ("here's the saving grace: the cached reference", []),
    ("vLLM 0.10.x needs torch 2.9 and CUDA 12.x", []),
    ("Coptidice, BC, BCQ and CDT on MetaDrive", []),
    ("a hard problem of medium size", []),
    ("EngineCore pid=2753302 shut down", []),
    ("(EngineCore pid=2753302) ImportError: libnvrtc.so.13", []),
    ("the bundle carries audit_events for the pinned pass", []),
    # third red-team pass: the shapes the second gate list could not see
    ("\x1b[1morgs: \x1b[0m lmsys-kaggler-team,CitationComp",
     ["org-membership", "lmsys-kaggler-team", "citationcomp"]),
    ("HF_TOKEN prefix: hf_NehEDLK", ["hf-token-prefix", "hf-token-mixedcase"]),
    ("cwd=/work/[user]/reprocl", ["reprocl"]),
    ("--bind /tmp --bind /work/nv", ["/work/nv"]),
    ("run_gpu (1 gpu x 5 min gh20", ["gpu-model-fragment"]),
    ("aarch64 ([GPU], 'gh0xx' nodes)", ["node-placeholder"]),
    ("drwxrws---+ 2 [user] delta_[proj] 4096 evidence", ["cluster-group"]),
    ("Uid: (91115/[user])   Gid: (20421/delta_[proj])",
     ["cluster-group", "stat-owner-id"]),
    ('This is a "Hard" tier.', ["tier-vocab"]),
    ("the paper is Hard difficulty", ["tier-vocab"]),
    ('let me try the "test" partition (2h wall)', ["partition-name"]),
    ("the GPU allocation failed with partition=test", ["partition-name"]),
    ("0MiB /  97871MiB |   0%  Default |", ["gpu-spec"]),
    ("the [GPU] has 120GB of HBM3e", ["gpu-spec"]),
    ("- [GPU] nodes, up to 4 GPUs/node", ["node-spec"]),
    ("Login node RAM was 478GB total", ["node-ram-in-context"]),
    ("the run [job]-2412.11979 never finished", ["run-id-token"]),
    ('File "/sw/[redacted] line 293', ["/sw/"]),
    ("/[u]/yjian1/project/electrolytes", ["co-tenant-home", "yjian1"]),
    ("[ip]@tcp10:[ip]@tcp10:[fs]  9.8T", ["storage-fingerprint"]),
    # and what the same gate must not fire on
    ("curl -s https://api.github.com/orgs/google-research/repos", []),
    ("pip install huggingface_hub[cli,hf_xet]", []),
    ("  - reproc=14.2.4=h313beb8_2", []),
    ("loss = delta_matrix - delta_theta_mode", []),
    ("split by subject into train/validation/test partitions", []),
    ("the paper used 8xA100 80GB for 300 epochs", []),
    ("that materializes 110B elements, way too big (440GB)", []),
    ("the workspace is a network filesystem ([fs]) shared", []),
    # the facing pass (SPEC 8.4) gate additions
    ("the co-tenant was yjian1 that night", ["yjian1"]),
    ("staged to /harbor/exports/run.tar", ["/harbor"]),
    ("mount | grep dltawork", ["dlta", "dltawork"]),
    ("the dtai-sched host answered", ["dtai", "dtai-"]),
    ("the node is Grace-Hopper aarch64", ["grace-hopper"]),
    ("the easy_sweeps table was dropped", ["_sweeps"]),
    # and what the same additions must not fire on
    ("we ran hyperparameter sweeps over the seed", []),
    ("the harbor master problem in the paper", []),
    ("a graceful shutdown of the hopper queue", []),
]

# Source-only literals (SPEC 3.3). The site's own files may not carry them; the
# data may, because an agent quoting a paper writes Hard and reads slurm output.
FRONTEND_CASES = [
    ("Difficulty tier: Hard", ["tier-word"]),
    ("the Easy and Medium sweeps", ["tier-word"]),
    ("a hard problem of medium size", []),
    ("rows come from supabase", ["supabase"]),
    ("the frozen selection of 100", ["frozen"]),
    ("Run, Retrain and Reimplement", []),
    # gated in the data too, by tier-vocab; see the note in selftest()
    ("the Easy-sweep dissection", ["tier-word"]),
]


def _check_gate(cases, patterns, label, fails):
    for text, want in cases:
        got = sorted(scan(text, patterns, per_pattern=1))
        if got != sorted(want):
            fails.append((label + ": " + text, sorted(want), got))


def selftest():
    fails = []
    for text, want in CASES:
        got = scrub_text(text)
        if got != want:
            fails.append((text, want, got))
    set_id_map({
        "2652648-2505.11483-b70632": "minimax-run-2505.11483",
        "2652648-2505.11483-b70632-2505.11483-audit": "[run]",
        "2599138-2505.11483-aaaaaa": "[run]",
    })
    for text, want in ID_CASES:
        got = scrub_text(text)
        if got != want:
            fails.append((text, want, got))
    # the gate must be clean on every scrubbed case
    pats = gate_patterns()
    for text, _ in CASES + ID_CASES:
        hits = scan(scrub_text(text), pats, per_pattern=1)
        if hits:
            fails.append((text, "no gate hit", str(hits)))
    set_id_map({})
    _check_gate(GATE_CASES, gate_patterns(), "gate", fails)
    _check_gate(FRONTEND_CASES, frontend_patterns(), "source-only", fails)
    # The source-only literals are not gated in the data, with one exception
    # the second red-team pass introduced: a tier word bound to the thing it
    # labels ("difficulty tier: Hard", "Easy-sweep") is a data leak as well,
    # while a bare "hard" stays the agent's own word in both places.
    both = re.compile(dict(GATE_SHAPES)["tier-vocab"], re.I)
    for text, want in FRONTEND_CASES:
        if want and not both.search(text) and scan(text, gate_patterns(), per_pattern=1):
            fails.append(("data gate: " + text, [], "gated in the data too"))
    n = (len(CASES) + len(ID_CASES) + len(GATE_CASES)
         + len(FRONTEND_CASES) * 2 + 1)
    payload = json.dumps({"t": "coqa\ncsatqa\ndrop"})
    fixed = deescape(payload)
    if scan(fixed, gate_patterns(), 1) or json.loads(fixed)["t"] != "coqa\ncsatqa\ndrop":
        fails.append((payload, "gate-clean json with the same value", fixed))
    for text, want, got in fails:
        print("FAIL  in:   " + repr(text))
        print("      want: " + repr(want))
        print("      got:  " + repr(got))
    print("selftest: %d cases, %d failures" % (n, len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
