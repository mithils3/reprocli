# Setup & deploy

Step-by-step guide to stand up the Artifact Verification app. See
[`README.md`](README.md) for what it is and how reviewers use it.

## 1. Generate the data (already done once, re-run if outputs change)

```bash
python3 tools/verify_app/build_data.py
python3 tools/verify_app/fetch_arxiv_meta.py   # only needed for NEW paper ids
```

Produces `public/papers.json` (one record per pool paper) and
`traces_out/<arxiv_id>.json` (per-paper traces). Defaults to the v5 audit pool
(`outputs/v5/audit_pool`, from `python -m reprocli_vllm.audit.select_pool`); point at
another run with `--run <basename>`.

`build_data.py` automatically merges `arxiv_meta.json` (real titles, authors,
year, abstract from the arXiv API — the trace-derived titles are wrong for ~25%
of papers). Run `fetch_arxiv_meta.py` once whenever new paper ids appear; it
caches results and only fetches what's missing.

## 2. Create the Supabase project (free, ~3 min)

1. Sign up at <https://supabase.com> → **New project** (pick any region/password).
2. Open **SQL Editor** → paste all of `supabase_schema.sql` → **Run**.
   (Creates the `verifications` + `activity` tables and permissive policies.)
3. Open **Project Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_ANON_KEY` (safe to ship in client code; it's
     gated by the row-level-security policies in the schema)

## 3. Fill in `public/config.js`

```js
window.APP_CONFIG = {
  SUPABASE_URL: "https://YOURPROJECT.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGc...",        // anon public key
  ADMIN_NAMES: ["mithil"],                 // names that see the Dashboard tab
  TRACE_BASE_URL: "",                      // fill after step 5 (optional)
};
```

## 4. Preview locally

```bash
cd tools/verify_app/public
python3 -m http.server 8799
# open http://127.0.0.1:8799  — type a name, start reviewing
```

## 5. (Optional) Upload traces so "Show model trace" works

1. In Supabase → **Storage** → **New bucket** named `traces`, mark it **Public**.
2. Grab the **service_role** key (Settings → API) — server-side only, never put it in config.js.
3. Upload the split files:
   ```bash
   pip install requests
   export SUPABASE_URL="https://YOURPROJECT.supabase.co"
   export SUPABASE_SERVICE_KEY="service-role-key"
   python3 tools/verify_app/build_data.py --upload
   ```
4. Set in `config.js`:
   ```js
   TRACE_BASE_URL: "https://YOURPROJECT.supabase.co/storage/v1/object/public/traces",
   ```

## 6. Deploy to Vercel

**Lowest-friction (CLI, deploys the folder directly):**

```bash
npm i -g vercel
cd tools/verify_app/public
vercel            # first run: links/creates a project, accept defaults
vercel --prod     # promote to your production URL
```

That uploads just the `public/` folder as a static site — no build, no config.
Share the resulting URL with your team; each person types their name and starts.

**Git-based alternative (auto-deploy on every push):**

1. Push the repo to GitHub.
2. Vercel → **Add New Project** → import the repo.
3. Framework preset: **Other**. **Root Directory:** `tools/verify_app/public`.
   Build command: *(empty)*. Output directory: *(leave default / `.`)*.
4. Deploy.

> Note: `config.js` (with the anon key) ships to the browser. That's expected for
> Supabase client apps — the anon key only allows what the RLS policies allow.

## Notes / limits

- **Trust model:** name-only auth means anyone with the link can pick any name. Fine for a small internal team. To harden, switch to Supabase email auth and tighten the RLS policies to `auth.uid()`.
- Two source records (`score: null`) failed extraction upstream; the app shows them with empty signals so reviewers can flag them.
- Re-running `build_data.py` regenerates `papers.json`; redeploy to publish.
