"""Entry point: ``python -m reprocli_repro``.

Phases 0-3 stood up the package: CLI, forked tool loop, ``ExecutionContext``,
microcompact, the lockfile->episode input pipeline, the per-paper
workspace/reference/evidence, and the budget meter + JIT-SLURM substrate. Phase 4
closes the loop: each prepared episode becomes an ``ExecutionContext`` (workspace +
budget + cluster + evidence), and ``run_reproduce_loop`` drives the model through
the execution toolset (``workspace_bash`` / file ops / the metered ``run_gpu``)
until it finishes or the compute budget is spent.

The brain is an already-served vLLM endpoint (``--vllm-server-url`` /
``$REPROCLI_SERVER_URL`` / ``$REPROCLI_ENDPOINT_FILE``); this agent never
self-hosts a model. With no endpoint configured the command falls back to a dry
run -- it still prepares every episode's bundle and prints the rendered prompt, so
the inputs can be inspected offline. Phase 5 finalizes the agent's ``report.json``
bundle; the *verdict* over that bundle is the auditor's, not written here.
"""

from __future__ import annotations

import sys

from reprocli_vllm.vllm.endpoint import resolve_served_model, resolve_server_url

from reprocli_repro import gpu_session, sandbox, supabase_sink
from reprocli_repro.cli_args import parse_args
from reprocli_repro.context import ExecutionContext
from reprocli_repro.dataset import band_of
from reprocli_repro.inputs import EpisodeInput, build_context, prepare_episodes
from reprocli_repro.loop import run_reproduce_loop
from reprocli_repro.workspace import WorkspaceResult, prepare_workspace


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    episodes = prepare_episodes(args)
    image = args.cluster_profile.apptainer_image
    server_url = resolve_server_url(args.vllm_server_url)
    live = server_url is not None
    if live:
        # Refuse to run a single agent step unconfined: abort here if Apptainer can't
        # sandbox the image. Then forward HF auth/cache + proxy env into the --cleanenv
        # container (so gated HF downloads keep working) before any step runs.
        sandbox.require_apptainer(image)
        sandbox.forward_env()

    contexts: list[ExecutionContext] = []
    for ep in episodes:
        print(_summary(ep), file=sys.stderr)
        if args.reference:
            print(
                f"  materializing reference for {ep.arxiv_id} "
                "(first run downloads + caches the paper bundle)...",
                file=sys.stderr,
            )
        # Mandatory Apptainer write-confinement for every shell step this episode runs
        # (workspace_bash / run_gpu): the read-only image is /, with rw binds for the
        # workspace/evidence/caches and a ro bind for reference. Built only for a live
        # run; a dry run renders prompts without a sandbox.
        sb = sandbox.from_run_paths(ep.run_paths, image=image) if live else None
        result = prepare_workspace(
            ep.run_paths,
            arxiv_id=ep.arxiv_id,
            materialize_ref=args.reference,
        )
        print(_setup_summary(result), file=sys.stderr)
        ctx = build_context(ep)
        ctx.cluster = args.cluster_profile
        ctx.sandbox = sb
        contexts.append(ctx)

    if not live:
        return _dry_run(args, episodes)

    print(f"sandbox: {contexts[0].sandbox.status()}" if contexts else "sandbox: apptainer", file=sys.stderr)

    model_id = resolve_served_model(server_url, args.served_model_name)
    print(
        f"Attached to brain at {server_url} (model {model_id!r}); "
        f"cluster={args.cluster_profile.name} hw={args.cluster_profile.hw}",
        file=sys.stderr,
    )
    # Opt-in live upload to Supabase (no-op unless SUPABASE_URL + SUPABASE_SERVICE_KEY
    # are set); registers itself on the live_log seam so each round streams to the
    # dashboard. Best-effort — never affects the loop.
    sink = supabase_sink.install(supabase_sink.SinkConfig.from_env())
    if sink:
        for ctx in contexts:
            sink.upsert_run(ctx, model=model_id, status="running")
    try:
        run_reproduce_loop(args, contexts, [ep.prompt for ep in episodes], server_url, model_id)
    finally:
        # Never leak a held GPU allocation on a crash/interrupt — the loop releases
        # each episode's session on completion, this sweeps any that survived.
        gpu_session.teardown_all(contexts)
        if sink:
            sink.close()
    print(
        f"\nReproduce loop finished {len(episodes)} episode(s); responses in "
        f"{args.output}. Each run bundle's report.json is written for the auditor to grade.",
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
    ref_note = (
        f"reference ok ({ref.get('latex_files', '?')} tex, {ref.get('supplement_files', '?')} supp)"
        if ref.get("ok")
        else f"reference: {ref.get('error') or ref.get('reason') or 'skipped'}"
    )
    return f"  set up {result.run_paths.run_dir}: {ref_note}"


def _summary(ep: EpisodeInput) -> str:
    tier = ep.row.get("tier") or "(untiered)"
    return (
        f"[{ep.arxiv_id}] tier={tier} band={band_of(ep.row)} "
        f"budget={ep.budget:g}h run_dir={ep.run_paths.run_dir}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
