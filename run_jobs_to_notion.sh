#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/applypilot"
VENV="$ROOT/.venv-applypilot"
ENVFILE="$ROOT/.env"

mkdir -p "$ROOT/outputs"
cd "$ROOT"

. "$VENV/bin/activate"
python -m pip install --quiet --upgrade notion-client python-dotenv pandas python-slugify

# Export env vars
export $(grep -E '^(NOTION_TOKEN|NOTION_PAGE_ID|NOTION_DATABASE_ID)=' "$ENVFILE" | xargs || true)

echo "[i] Starting job sync..."

python3 - <<'PY'
import os, sys, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime

ROOT   = Path.home()/ "applypilot"
OUT    = ROOT / "outputs"
ENV    = ROOT / ".env"
DBCSV  = OUT / "filtered_jobs.csv"

load_dotenv(ENV, override=True)
tok  = os.getenv("NOTION_TOKEN")
pid  = os.getenv("NOTION_PAGE_ID")
dbid = os.getenv("NOTION_DATABASE_ID")

if not tok or not pid:
    sys.exit("[!] Missing NOTION_TOKEN or NOTION_PAGE_ID in .env")

cli = Client(auth=tok)

# Load new CSVs
downloads = Path.home()/ "Downloads"
frames=[]
for p in downloads.glob("*.csv"):
    try:
        df=pd.read_csv(p)
        if len(df): 
            frames.append(df)
            print(f"[ok] Loaded {p} ({len(df)} rows)")
    except Exception as e:
        print(f"[warn] Could not read {p}: {e}")

if not frames:
    sys.exit("[i] No new job rows found.")

newdf=pd.concat(frames,ignore_index=True)

# Merge with existing filtered_jobs.csv
if DBCSV.exists():
    old=pd.read_csv(DBCSV)
    merged=pd.concat([old,newdf],ignore_index=True).drop_duplicates(subset=["title","company","location","url"])
else:
    merged=newdf.drop_duplicates(subset=["title","company","location","url"])

merged.to_csv(DBCSV,index=False)
print(f"[ok] Master CSV now has {len(merged)} rows")

# Create Notion DB if missing
if not dbid:
    resp=cli.databases.create(parent={"type":"page_id","page_id":pid},
        title=[{"type":"text","text":{"content":"Job Postings"}}],
        properties={
            "Title":{"title":{}},
            "Company":{"rich_text":{}},
            "Location":{"rich_text":{}},
            "Date Added":{"date":{}},
            "Source":{"url":{}}
        })
    dbid=resp["id"]
    with open(ENV,"a") as f: f.write(f"\nNOTION_DATABASE_ID={dbid}\n")
    print(f"[ok] Created Notion DB: {dbid}")

# Find existing URLs to avoid dupes
old_urls=set()
try:
    pages=cli.databases.query(database_id=dbid).get("results",[])
    for pg in pages:
        url = pg["properties"].get("Source",{}).get("url")
        if url: old_urls.add(url)
except: pass

# Insert only new rows
added=0
for _,row in merged.iterrows():
    url=str(row.get("url") or "")
    if url in old_urls: continue
    try:
        cli.pages.create(
            parent={"database_id":dbid},
            properties={
                "Title":{"title":[{"type":"text","text":{"content":str(row.get('title') or 'Untitled')}}]},
                "Company":{"rich_text":[{"type":"text","text":{"content":str(row.get('company') or '')}}]},
                "Location":{"rich_text":[{"type":"text","text":{"content":str(row.get('location') or '')}}]},
                "Date Added":{"date":{"start":str(datetime.today().date())}},
                "Source":{"url":url}
            })
        added+=1
    except Exception as e:
        print(f"[warn] Could not insert row: {e}")

print(f"[ok] Added {added} new jobs to Notion")

# Update summary on the main page
now=datetime.now().strftime("%Y-%m-%d %H:%M")
summary=f"Jobs in DB: {len(merged)} | New today: {added} | Updated: {now}"
cli.blocks.children.append(block_id=pid, children=[
  {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":summary}}]}}
])
print("[ok] Summary updated on Notion page.")
PY

echo "[done] Job sync finished."
