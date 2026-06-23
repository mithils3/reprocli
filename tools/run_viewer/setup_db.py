#!/usr/bin/env python3
"""Create the Repro Run Viewer tables + Storage bucket in Supabase.

The anon/service keys go through PostgREST, which can't run DDL — so this script
needs a credential that can. In order of preference:

  1. SUPABASE_ACCESS_TOKEN — a personal access token from
     https://supabase.com/dashboard/account/tokens (preferred; dependency-free).
     Runs the schema via the Supabase Management API.
  2. SUPABASE_DB_URL — the Postgres connection string (Settings > Database).
     Runs the schema via psycopg (if installed).

If neither is set, prints the paste-into-SQL-Editor fallback.

Usage:
    SUPABASE_ACCESS_TOKEN=sbp_xxx python3 tools/run_viewer/setup_db.py
    # optional: --ref <project-ref>   --sql <path>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_SQL = Path(__file__).with_name("supabase_schema.sql")
DEFAULT_REF = "rjnkpoxwdslkgxjliakq"   # the reprobench Supabase project (shared with verify_app)


def project_ref(args) -> str:
    if args.ref:
        return args.ref
    if os.environ.get("SUPABASE_PROJECT_REF"):
        return os.environ["SUPABASE_PROJECT_REF"]
    url = os.environ.get("SUPABASE_URL", "")
    if "//" in url and ".supabase.co" in url:
        return url.split("//", 1)[1].split(".supabase.co", 1)[0]
    return DEFAULT_REF


def run_via_management_api(ref: str, token: str, sql: str) -> int:
    api = f"https://api.supabase.com/v1/projects/{ref}/database/query"
    body = json.dumps({"query": sql}).encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(api, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(f"✓ schema applied to project {ref} (HTTP {resp.status})")
            return 0
    except urllib.error.HTTPError as e:
        print(f"✗ Management API error (HTTP {e.code}): {e.read().decode()[:600]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"✗ could not reach the Management API: {e}", file=sys.stderr)
        return 1


def run_via_db_url(db_url: str, sql: str) -> int:
    try:
        import psycopg  # type: ignore
        with psycopg.connect(db_url) as conn:
            conn.execute(sql)
            conn.commit()
        print("✓ schema applied via SUPABASE_DB_URL (psycopg)")
        return 0
    except ImportError:
        pass
    try:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        conn.cursor().execute(sql)
        conn.close()
        print("✓ schema applied via SUPABASE_DB_URL (psycopg2)")
        return 0
    except ImportError:
        print("✗ SUPABASE_DB_URL is set but neither psycopg nor psycopg2 is installed.\n"
              f"  Run it yourself:  psql \"$SUPABASE_DB_URL\" -f {DEFAULT_SQL}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"✗ DB error: {e}", file=sys.stderr)
        return 1


def fallback_message(ref: str, sql_path: Path) -> int:
    print(
        "No DDL credential found. Do ONE of:\n\n"
        "  A) Personal access token (recommended):\n"
        "       1. https://supabase.com/dashboard/account/tokens  -> Generate new token\n"
        "       2. export SUPABASE_ACCESS_TOKEN=sbp_...\n"
        f"       3. python3 {Path(__file__).as_posix()}\n\n"
        "  B) DB connection string:\n"
        "       export SUPABASE_DB_URL='postgresql://postgres:...@db." + ref + ".supabase.co:5432/postgres'\n"
        f"       python3 {Path(__file__).as_posix()}      (needs psycopg)\n\n"
        "  C) Manual paste:\n"
        f"       open Supabase > SQL Editor, paste all of {sql_path}, hit Run.\n",
        file=sys.stderr,
    )
    return 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Create Repro Run Viewer Supabase tables.")
    ap.add_argument("--sql", default=str(DEFAULT_SQL), help="path to the schema .sql file")
    ap.add_argument("--ref", default=None, help="Supabase project ref (else from SUPABASE_URL / default)")
    args = ap.parse_args(argv)

    sql_path = Path(args.sql)
    if not sql_path.exists():
        print(f"✗ schema file not found: {sql_path}", file=sys.stderr)
        return 1
    sql = sql_path.read_text(encoding="utf-8")
    ref = project_ref(args)

    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if token:
        return run_via_management_api(ref, token, sql)
    db_url = os.environ.get("SUPABASE_DB_URL")
    if db_url:
        return run_via_db_url(db_url, sql)
    return fallback_message(ref, sql_path)


if __name__ == "__main__":
    raise SystemExit(main())
