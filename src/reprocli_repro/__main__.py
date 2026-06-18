"""Entry point: ``python -m reprocli_repro``.

Phase 0 stood up the package skeleton (CLI, forked tool loop, ExecutionContext,
microcompact). Phase 1 adds the input pipeline: one audited lockfile row becomes
one fully-rendered reproduction episode (opening prompt + resolved run directory).
The phases that *run* the episode — workspace/reference/evidence (Phase 2), budget
meter + SLURM (Phase 3), the repro toolset (Phase 4), and post-loop re-execution
into ``result.json`` (Phase 5) — wire on top of these inputs.
"""

from __future__ import annotations

import sys

from reprocli_repro.cli_args import parse_args
from reprocli_repro.inputs import EpisodeInput, band_of, prepare_episodes


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    episodes = prepare_episodes(args)
    for ep in episodes:
        print(_summary(ep), file=sys.stderr)
        sys.stdout.write(f"\n===== reproduction prompt: {ep.arxiv_id} =====\n")
        sys.stdout.write(ep.prompt)
        sys.stdout.write("\n")
    print(
        f"\nPrepared {len(episodes)} episode(s) from {args.lockfile}. Phase 1 renders "
        "the episode input only; the reproduce loop (workspace, tools, metered GPU "
        "execution) is wired in Phases 2-5.",
        file=sys.stderr,
    )
    return 0


def _summary(ep: EpisodeInput) -> str:
    tier = ep.row.get("tier") or "(untiered)"
    return (
        f"[{ep.arxiv_id}] tier={tier} band={band_of(ep.row)} "
        f"budget={ep.budget:g}h run_dir={ep.run_paths.run_dir}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
