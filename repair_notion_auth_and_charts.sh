#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)/applypilot"
ENVFILE="$ROOT/.env"
VENV="$ROOT/.venv-applypilot"

mkdir -p "$ROOT" "$ROOT/logs" "$ROOT/scripts" "$ROOT/outputs"

# --- 1) Ask for proper Notion token + page link ---
echo "Enter your Notion Internal Integration Token (should start with secret_)."
read -rsp "NOTION_TOKEN: " TOKEN; echo
read -rp  "Paste your Notion page link (the one that owns Job Postings): " PAGE_URL

# normalize page id (hyphenated UUID)
rawid="$(echo "$PAGE_URL" | sed -E 's#.*/([0-9a-fA-F]{32,}).*#\1#')"
if [[ -z "$rawid" ]]; then
  rawid="$(basename "$PAGE_URL" | tr -cd '[:xdigit:]')"
fi
if [[ ${#rawid} -lt 32 ]]; then
  echo "[!] Could not extract a 32-char page id from the URL."
  exit 1
fi
PAGE_ID="${rawid:0:8}-${rawid:8:4}-${rawid:12:4}-${rawid:16:4}-${rawid:20:12}"
PAGE_ID="$(echo "$PAGE_ID" | tr 'A-Z' 'a-z')"

# --- 2) Write .env (pin token & page; clear DB id to avoid stale 404s) ---
touch "$ENVFILE"
awk -v tok="NOTION_TOKEN=$TOKEN" -v pid="NOTION_PAGE_ID=$PAGE_ID" '
  BEGIN{t=0;p=0}
  /^NOTION_TOKEN=/{print tok; t=1; next}
  /^NOTION_PAGE_ID=/{print pid; p=1; next}
  /^NOTION_DATABASE_ID=/{next}  # remove old DB id (will repin)
  {print}
  END{if(!t) print tok; if(!p) print pid}
' "$ENVFILE" > "$ENVFILE.tmp" && mv "$ENVFILE.tmp" "$ENVFILE"
chmod 600 "$ENVFILE"
echo "[ok] Updated $ENVFILE with token + page id; cleared NOTION_DATABASE_ID."

# Warn if token format looks wrong
if [[ "$TOKEN" != secret_* ]]; then
  echo "[warn] Token does not start with 'secret_'. This is likely not an Internal Integration Token."
fi

# --- 3) Ensure venv active + deps ---
if [[ ! -d "$VENV" ]]; then python3 -m venv "$VENV"; fi
# shellcheck disable=SC1090
. "$VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install notion-client python-dotenv python-slugify matplotlib pandas >/dev/null

# --- 4) Creds check (creates checker if missing) ---
CHECK="$ROOT/scripts/check_notion_creds.py"
if [[ ! -x "$CHECK" ]]; then
  cat > "$CHECK" <<'PY'
#!/usr/bin/env python3
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client
load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent / ".env"), override=True)
tok=os.getenv("NOTION_TOKEN"); pid=os.getenv("NOTION_PAGE_ID"); db=os.getenv("NOTION_DATABASE_ID")
if not tok: sys.exit("[!] NOTION_TOKEN missing")
cli=Client(auth=tok)
me=cli.users.me(); print(f"[ok] Token valid for: {me.get('name') or me.get('id')}")
if pid:
    try:
        pg=cli.pages.retrieve(page_id=pid)
        print(f"[ok] Can access Page: {pid}")
    except Exception as e:
        print(f"[warn] Page access failed: {e}\nInvite this integration to the page (Share → Can edit).")
if db:
    try:
        cli.databases.retrieve(db_id=db); print(f"[ok] Can access DB: {db}")
    except Exception as e:
        print(f"[warn] DB id in .env might be stale: {e}")
PY
  chmod +x "$CHECK"
fi
python3 "$CHECK"

# --- 5) Sync DB (creates/updates 'Job Postings' and repins DB id) ---
SYNC="$ROOT/scripts/notion_sync.py"
if [[ ! -x "$SYNC" ]]; then
  echo "[!] notion_sync.py missing; cannot proceed."
  exit 1
fi
python3 "$SYNC"

# Pin DB id via the charts script’s self-heal or a pin helper
if [[ -x "$ROOT/scripts/make_job_charts.py" ]]; then
  echo "[i] Letting chart script pin NOTION_DATABASE_ID if needed…"
else
  echo "[i] Chart script not found; skipping."
fi

# --- 6) Generate charts (script will auto-find/pin DB id) ---
python3 "$ROOT/../scripts/make_job_charts.py" || {
  # fallback path if you placed it under applypilot/scripts
  python3 "$ROOT/scripts/make_job_charts.py"
}

echo "[done] If charts succeeded, check applypilot/outputs/ for PNGs + summary.json."
echo "       If you still see auth errors, open the Notion page and Share → invite the integration with 'Can edit'."
