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
from reprocli_repro.workspace import WorkspaceResult, prepare_workspace


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    episodes = prepare_episodes(args)
    for ep in episodes:
        print(_summary(ep), file=sys.stderr)
        result = prepare_workspace(
            ep.run_paths,
            arxiv_id=ep.arxiv_id,
            bundle_dataset=args.bundle_dataset,
            make_venv=args.build_venv,
            materialize_ref=args.reference,
            system_site_packages=(args.executor == "slurm"),
            venv_python=args.venv_python,
        )
        print(_setup_summary(result), file=sys.stderr)
        sys.stdout.write(f"\n===== reproduction prompt: {ep.arxiv_id} =====\n")
        sys.stdout.write(ep.prompt)
        sys.stdout.write("\n")
    print(
        f"\nPrepared + set up {len(episodes)} episode(s) from {args.lockfile}. Phase 2 "
        "materializes the per-paper workspace, reference, and evidence; the reproduce "
        "loop (toolset + metered GPU execution) is wired in Phases 4-5.",
        file=sys.stderr,
    )
    return 0


def _setup_summary(result: WorkspaceResult) -> str:
    ref = result.reference or {}
    venv = result.venv or {}
    ref_note = (
        f"reference ok ({ref.get('latex_files', '?')} tex, {ref.get('supplement_files', '?')} supp)"
        if ref.get("ok")
        else f"reference: {ref.get('error') or ref.get('reason') or 'skipped'}"
    )
    venv_note = "venv ok" if venv.get("ok") else f"venv: {venv.get('error') or venv.get('stderr') or 'skipped'}"
    return f"  set up {result.run_paths.run_dir}: {ref_note}; {venv_note}"


def _summary(ep: EpisodeInput) -> str:
    tier = ep.row.get("tier") or "(untiered)"
    return (
        f"[{ep.arxiv_id}] tier={tier} band={band_of(ep.row)} "
        f"budget={ep.budget:g}h run_dir={ep.run_paths.run_dir}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
