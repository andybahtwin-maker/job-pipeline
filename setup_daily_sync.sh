#!/usr/bin/env bash
set -euo pipefail

# --- paths & basics ---
ROOT="$(pwd)/applypilot"
SCRIPTS="$ROOT/scripts"
ENVFILE="$ROOT/.env"
VENV="$ROOT/.venv-applypilot"
LOGDIR="$ROOT/logs"
mkdir -p "$ROOT" "$SCRIPTS" "$LOGDIR" "$ROOT/outputs" "$ROOT/outputs/charts"

# --- sanity for .env: must have TOKEN + PAGE ---
if ! grep -q '^NOTION_TOKEN=' "$ENVFILE"; then
  echo "[!] NOTION_TOKEN missing in $ENVFILE"; exit 1
fi
if ! grep -q '^NOTION_PAGE_ID=' "$ENVFILE"; then
  echo "[!] NOTION_PAGE_ID missing in $ENVFILE"; exit 1
fi
chmod 600 "$ENVFILE"

# --- venv + deps ---
if [ ! -f "$VENV/bin/activate" ]; then
  python3 -m venv "$VENV"
fi
. "$VENV/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade notion-client python-dotenv python-slugify matplotlib pandas

# --- write/update summary updater ---
cat > "$SCRIPTS/update_notion_summary.py" <<'PY'
#!/usr/bin/env python3
import os, sys, datetime as dt
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from notion_client import Client, APIResponseError

REPO = Path(__file__).resolve().parents[1]
ENV  = REPO / ".env"
OUT  = REPO / "outputs"
load_dotenv(ENV, override=True)

tok = os.getenv("NOTION_TOKEN")
page_id = os.getenv("NOTION_PAGE_ID")
if not tok or not page_id:
    sys.exit("[!] NOTION_TOKEN or NOTION_PAGE_ID missing")

cli = Client(auth=tok)

# confirm access
try:
    cli.pages.retrieve(page_id=page_id)
except Exception as e:
    sys.exit(f"[!] Cannot access NOTION_PAGE_ID={page_id}: {e}")

# Pick a CSV to compute quick stats (same heuristic as charts)
candidates = [
    OUT / "filtered_jobs.csv",
    Path.home() / "Downloads" / "jobs_batch_1.csv",
    Path.home() / "Downloads" / "se_jobs_batch_1.csv",
]
df = None
for p in candidates:
    if p.exists() and p.stat().st_size > 0:
        try:
            t = pd.read_csv(p)
            if not t.empty:
                df = t
                break
        except Exception:
            pass

rows = len(df) if df is not None else 0
uniq_companies = df["company"].nunique() if (df is not None and "company" in df.columns) else 0
uniq_sources   = df["source"].nunique()  if (df is not None and "source"  in df.columns) else 0

top_sources_list = []
if df is not None and "source" in df.columns:
    top_sources_list = df["source"].value_counts().head(10).reset_index().values.tolist()  # [[source, count], ...]

# ensure we have a child page "ApplyPilot Summary"
def get_or_create_summary_page(parent_page_id:str)->str:
    # list blocks (children) of parent page and find a child_page named "ApplyPilot Summary"
    blocks = cli.blocks.children.list(block_id=parent_page_id)
    for blk in blocks.get("results", []):
        if blk["type"] == "child_page" and blk["child_page"]["title"].strip().lower() == "applypilot summary":
            return blk["id"]
    # create it
    newp = cli.blocks.children.append(
        block_id=parent_page_id,
        children=[{
            "object":"block",
            "type":"child_page",
            "child_page":{"title":"ApplyPilot Summary"}
        }]
    )
    # appended child_page returns inside "results"; fetch the id
    return newp["results"][0]["id"]

summary_page_id = get_or_create_summary_page(page_id)

# replace content of summary page with fresh metrics
def overwrite_summary(page_block_id:str):
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    children = []

    # heading
    children.append({
        "object":"block","type":"heading_2",
        "heading_2":{"rich_text":[{"type":"text","text":{"content":"Daily Summary"}}]}
    })

    # metrics callout
    metrics_lines = [
        f"Rows: {rows}",
        f"Unique companies: {uniq_companies}",
        f"Unique sources: {uniq_sources}",
        f"Last updated: {now}",
    ]
    children.append({
        "object":"block","type":"callout",
        "callout":{
            "icon":{"emoji":"📊"},
            "rich_text":[{"type":"text","text":{"content":"\n".join(metrics_lines)}}]
        }
    })

    # Top sources (bulleted list)
    if top_sources_list:
        children.append({
            "object":"block","type":"heading_3",
            "heading_3":{"rich_text":[{"type":"text","text":{"content":"Top Sources (Top 10)"}}]}
        })
        for src, cnt in top_sources_list:
            children.append({
                "object":"block","type":"bulleted_list_item",
                "bulleted_list_item":{
                    "rich_text":[{"type":"text","text":{"content":f"{src}: {int(cnt)}"}}]
                }
            })

    # clear existing children by replacing with a toggle + then overwrite (safe approach)
    # Notion API does not have a "delete all children" endpoint; we can archive existing blocks.
    # We'll archive existing children to avoid growth.
    existing = cli.blocks.children.list(block_id=page_block_id).get("results", [])
    for blk in existing:
        try:
            cli.blocks.update(block_id=blk["id"], archived=True)
        except Exception:
            pass

    # append fresh blocks
    # (Notion API limits per request; split into chunks)
    CHUNK=50
    for i in range(0, len(children), CHUNK):
        cli.blocks.children.append(block_id=page_block_id, children=children[i:i+CHUNK])

overwrite_summary(summary_page_id)
print("[ok] Summary page updated.")
PY
chmod +x "$SCRIPTS/update_notion_summary.py"

# --- write daily runner ---
cat > "$ROOT/daily_sync.sh" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVFILE="$ROOT/.env"
VENV="$ROOT/.venv-applypilot"
LOGDIR="$ROOT/logs"
OUT="$ROOT/outputs"
mkdir -p "$OUT" "$OUT/charts" "$LOGDIR"

# activate
. "$VENV/bin/activate"
export MPLBACKEND=Agg

# export env via python (handles quotes safely)
eval "$(
python3 - <<'PY'
import shlex
from pathlib import Path
from dotenv import dotenv_values
vals = dotenv_values(Path("applypilot/.env"))
for k in ("NOTION_TOKEN","NOTION_PAGE_ID","NOTION_DATABASE_ID"):
    v = vals.get(k)
    if v is not None:
        print(f'export {k}={shlex.quote(v)}')
PY
)"

ts="$(date '+%Y%m%d_%H%M%S')"
LOG="$LOGDIR/daily_sync-$ts.txt"
exec > >(tee -a "$LOG") 2>&1

echo "[i] ApplyPilot daily sync started at $(date -Is)"

# 1) sync DB (your existing importer)
python3 "$ROOT/scripts/notion_sync.py"

# 2) charts
( cd "$ROOT/.." && python3 scripts/make_job_charts.py )

# 3) summary page update
python3 "$ROOT/scripts/update_notion_summary.py"

echo "[done] Daily sync complete at $(date -Is)"
RUN
chmod +x "$ROOT/daily_sync.sh"

# --- systemd user service + timer ---
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/applypilot-daily.service" <<SERVICE
[Unit]
Description=ApplyPilot daily Notion sync

[Service]
Type=oneshot
WorkingDirectory=$ROOT
ExecStart=$ROOT/daily_sync.sh
Environment=MPLBACKEND=Agg

[Install]
WantedBy=default.target
SERVICE

cat > "$HOME/.config/systemd/user/applypilot-daily.timer" <<TIMER
[Unit]
Description=Run ApplyPilot daily at 09:05 Africa/Casablanca

[Timer]
OnCalendar=*-*-* 09:05
Persistent=true
Unit=applypilot-daily.service

[Install]
WantedBy=timers.target
TIMER

# --- enable timer (user instance) ---
systemctl --user daemon-reload
systemctl --user enable --now applypilot-daily.timer

echo "[ok] Installed systemd user timer:"
systemctl --user list-timers applypilot-daily.timer --all || true

echo "[i] To test immediately, run:"
echo "    systemctl --user start applypilot-daily.service"
echo "[i] Logs live in: $LOGDIR/"
