#!/usr/bin/env python3
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client

ROOT = Path(__file__).resolve().parents[1]
ENV  = ROOT / ".env"
load_dotenv(ENV, override=True)

tok = os.getenv("NOTION_TOKEN")
parent_page_id = os.getenv("NOTION_PAGE_ID")
if not tok or not parent_page_id:
    sys.exit("[!] NOTION_TOKEN or NOTION_PAGE_ID missing")

cli = Client(auth=tok)

# Try to retrieve an existing DB under the page
db_id = os.getenv("NOTION_DATABASE_ID")
if db_id:
    try:
        cli.databases.retrieve(database_id=db_id)
        print(f"[ok] Using existing NOTION_DATABASE_ID={db_id}")
        sys.exit(0)
    except Exception:
        pass  # fall through to discover

def find_job_db_under_page(page_id: str):
    # Notion API: list child blocks; discover child_database blocks
    try:
        blocks = cli.blocks.children.list(block_id=page_id)
    except Exception as e:
        sys.exit(f"[!] Cannot list children of page {page_id}: {e}")
    found = []
    for blk in blocks.get("results", []):
        if blk["type"] == "child_database":
            title = blk["child_database"].get("title", "").strip()
            found.append((blk["id"], title))
    # Prefer title containing "Job" or "Posting"
    for id_, title in found:
        if "job" in title.lower() or "posting" in title.lower():
            return id_, title
    return found[0] if found else (None, None)

db_id, title = find_job_db_under_page(parent_page_id)
if not db_id:
    sys.exit("[!] Could not find a child database under the ApplyPilot page. Run sync once manually, then re-run this.")

# Write back to .env (idempotent; replace line if present)
lines = ENV.read_text().splitlines() if ENV.exists() else []
out = []
wrote = False
for ln in lines:
    if ln.startswith("NOTION_DATABASE_ID="):
        out.append(f"NOTION_DATABASE_ID={db_id}")
        wrote = True
    else:
        out.append(ln)
if not wrote:
    out.append(f"NOTION_DATABASE_ID={db_id}")
ENV.write_text("\n".join(out) + "\n")
print(f"[ok] Locked NOTION_DATABASE_ID={db_id} (\"{title}\") in {ENV}")
