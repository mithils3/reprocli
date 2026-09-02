# Anonymous reviewer viewer

Static, anonymized copy of the run viewer for double-blind review, serving the RECLAIM run set with every identifier removed. SPEC.md is the contract. The live viewer under `tools/run_viewer/` is untouched.

Regenerate, after `python3 scrub.py --selftest` passes:

    source <(grep -E '^export SUPABASE_SERVICE_KEY' ~/.bashrc)
    python3 export.py --cache

`--cache` keeps the transcript rows under `.scratch/cache/` so a second run that only changes the text rules takes a minute instead of half an hour; delete the folder to refetch.

`export.py` reads the database and the dissection records, rewrites `public/data/`, runs the leak gate, and refreshes `manifest.json` and `export_report.md`. `redactions.json` names runs to drop and dotted fields to blank; the exporter reads it on every run and applies it last.

Deploy: `cd public && vercel link --yes --project reclaim-traces && vercel --prod --yes`.
