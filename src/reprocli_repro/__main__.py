"""Entry point: ``python -m reprocli_repro``.

Phases 0-3 stood up the package: CLI, forked tool loop, ``ExecutionContext``,
microcompact, the lockfile->episode input pipeline, the per-paper
workspace/reference/evidence, and the budget meter + JIT-SLURM substrate. Phase 4
closes the loop: each prepared episode becomes an ``ExecutionContext`` (workspace +
budget + cluster + evidence), and ``run_reproduce_loop`` drives the model through
the execution toolset (``workspace_bash`` / file ops / the metered ``run_gpu``)
until it submits or the compute budget is spent.

The brain is an already-served vLLM endpoint (``--vllm-server-url`` /
``$REPROCLI_SERVER_URL`` / ``$REPROCLI_ENDPOINT_FILE``); this agent never
self-hosts a model. With no endpoint configured the command falls back to a dry
run -- it still prepares every episode's bundle and prints the rendered prompt, so
the inputs can be inspected offline. Phase 5 adds the post-loop re-execution that
writes the graded ``result.json`` the loop deliberately does not.
"""

from __future__ import annotations

import sys

from reprocli_vllm.vllm.endpoint import resolve_served_model, resolve_server_url

from reprocli_repro.cli_args import parse_args
from reprocli_repro.context import ExecutionContext
from reprocli_repro.inputs import EpisodeInput, band_of, build_context, prepare_episodes
from reprocli_repro.loop import run_reproduce_loop
from reprocli_repro.workspace import WorkspaceResult, prepare_workspace


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    episodes = prepare_episodes(args)
    contexts: list[ExecutionContext] = []
    for ep in episodes:
        print(_summary(ep), file=sys.stderr)
        result = prepare_workspace(
            ep.run_paths,
            arxiv_id=ep.arxiv_id,
            bundle_dataset=args.bundle_dataset,
            make_venv=args.build_venv,
            materialize_ref=args.reference,
            system_site_packages=True,
            venv_python=args.venv_python,
        )
        print(_setup_summary(result), file=sys.stderr)
        ctx = build_context(ep)
        ctx.cluster = args.cluster_profile
        contexts.append(ctx)

    server_url = resolve_server_url(args.vllm_server_url)
    if server_url is None:
        return _dry_run(args, episodes)

    model_id = resolve_served_model(server_url, args.served_model_name)
    print(
        f"Attached to brain at {server_url} (model {model_id!r}); "
        f"cluster={args.cluster_profile.name} hw={args.cluster_profile.hw}",
        file=sys.stderr,
    )
    run_reproduce_loop(args, contexts, [ep.prompt for ep in episodes], server_url, model_id)
    print(
        f"\nReproduce loop finished {len(episodes)} episode(s); responses in "
        f"{args.output}. Phase 5 re-executes each repro.yaml to write result.json.",
        file=sys.stderr,
    )
    return 0


def _dry_run(args, episodes: list[EpisodeInput]) -> int:
    for ep in episodes:
        sys.stdout.write(f"\n===== reproduction prompt: {ep.arxiv_id} =====\n")
        sys.stdout.write(ep.prompt)
        sys.stdout.write("\n")
    print(
        f"\nPrepared {len(episodes)} episode(s) from {args.lockfile} (dry run: no brain "
        "attached). Pass --vllm-server-url (or set $REPROCLI_SERVER_URL / "
        "$REPROCLI_ENDPOINT_FILE) to drive the reproduce loop.",
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
