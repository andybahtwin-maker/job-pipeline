#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)/applypilot"
ENVFILE="$ROOT/.env"
VENV="$ROOT/.venv-applypilot"

mkdir -p "$ROOT" "$ROOT/outputs"

# 1) Force Page ID; clear stale DB id
PAGE_ID="2679c46a-c8fd-8024-8e97-deedcff780be"
touch "$ENVFILE"
awk -v pid="NOTION_PAGE_ID=$PAGE_ID" '
  BEGIN{pset=0}
  /^NOTION_PAGE_ID=/{print pid; pset=1; next}
  /^NOTION_DATABASE_ID=/{next}
  {print}
  END{if(!pset) print pid}
' "$ENVFILE" > "$ENVFILE.tmp" && mv "$ENVFILE.tmp" "$ENVFILE"
chmod 600 "$ENVFILE"
echo "[ok] Pinned NOTION_PAGE_ID=$PAGE_ID and cleared NOTION_DATABASE_ID in .env"

# 2) Activate venv & deps (create if missing)
if [ ! -f "$VENV/bin/activate" ]; then
  python3 -m venv "$VENV"
fi
. "$VENV/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade notion-client python-dotenv python-slugify matplotlib pandas

# Headless backend for matplotlib
export MPLBACKEND=Agg

# 2.5) Export env vars robustly (no xargs footguns)
eval "$(
python3 - <<'PY'
import os, sys, shlex
from pathlib import Path
from dotenv import dotenv_values
envp = Path("applypilot/.env")
vals = dotenv_values(envp)
for k in ("NOTION_TOKEN","NOTION_PAGE_ID","NOTION_DATABASE_ID"):
    v = vals.get(k)
    if v is not None:
        print(f'export {k}={shlex.quote(v)}')
if not vals.get("NOTION_TOKEN"):
    sys.exit(1)
PY
)"

# 3) Quick creds check (differentiate 401/403/404)
python3 - <<'PY'
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client, APIResponseError

load_dotenv("applypilot/.env", override=True)
tok = os.getenv("NOTION_TOKEN")
pid = os.getenv("NOTION_PAGE_ID")
if not tok: sys.exit("[!] NOTION_TOKEN missing in applypilot/.env")
cli = Client(auth=tok)
try:
    me = cli.users.me()
    print(f"[ok] Token valid for: {me.get('name') or me.get('id')}")
except Exception as e:
    sys.exit(f"[!] Token check failed: {e}")

try:
    cli.pages.retrieve(page_id=pid)
    print(f"[ok] Can access Page: {pid}")
except APIResponseError as e:
    sys.exit(f"[!] Page access failed ({e.status}): {e}")
except Exception as e:
    sys.exit(f"[!] Page access error: {e}")
PY

# 4) Run the sync (creates/updates DB + writes NOTION_DATABASE_ID)
python3 "$ROOT/scripts/notion_sync.py"

# 5) Generate charts (script self-loads env; run from repo root)
( cd "$ROOT/.." && python3 scripts/make_job_charts.py )

# 6) Show results
ls -1 "$ROOT/outputs" | sed 's/^/[ok] outputs\//'
echo "[done] Charts + summary in applypilot/outputs/. Drag them into Notion."
