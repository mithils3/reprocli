# v3 output viewer

Focused viewer for the v3 MiniMax output family:

```bash
python3 tools/v3_viewer/server.py
```

Open `http://127.0.0.1:8766`.

By default it loads:

- `outputs/v3/neurips_2025_minimax_m2_trial.jsonl`
- `outputs/v3/neurips_2025_minimax_m2_trial_extracted.jsonl`
- `outputs/v3/neurips_2025_minimax_m2_trial_trace.jsonl`

Use another v3 basename with:

```bash
python3 tools/v3_viewer/server.py --run outputs/v3/another_run_stem
```

The UI is intentionally v3-specific. It joins records by `custom_id`, shows
final/extracted/trace health, computes deterministic score/tier drift from the
current classifier signals, flags tool-round-limit hits, and renders the saved
conversation trace with long paper/tool payloads trimmed for browser performance.
