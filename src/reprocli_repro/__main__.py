"""Entry point: ``python -m reprocli_repro``.

Phase 0 ships the package skeleton — its own CLI (``cli_args``), the forked tool
loop (``loop.run_reproduce_loop``), the per-episode ``ExecutionContext``, and the
``microcompact`` context-management tier. The end-to-end run pipeline that feeds
the loop lands in later phases: lockfile-row inputs (Phase 1),
workspace/reference/evidence (Phase 2), budget meter + SLURM (Phase 3), the repro
toolset (Phase 4), and post-loop re-execution into ``result.json`` (Phase 5).
"""

from __future__ import annotations

import sys

from reprocli_repro.cli_args import parse_args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(
        "reprocli_repro: Phase 0 scaffolding is in place (CLI, reproduce loop, "
        "ExecutionContext, microcompact). The end-to-end run pipeline "
        "(inputs -> workspace -> tools -> re-execution) is wired in Phases 1-5; "
        f"nothing to run yet for paper-id={args.paper_id!r}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
