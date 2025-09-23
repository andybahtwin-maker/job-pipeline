#!/usr/bin/env python3
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client

ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=str(ENV), override=True)

tok  = os.getenv("NOTION_TOKEN")
pid  = os.getenv("NOTION_PAGE_ID")  # parent page where we created the DB
if not tok:
    sys.exit("[!] NOTION_TOKEN missing in applypilot/.env")

client = Client(auth=tok)

# Find databases named "Job Postings"
resp = client.search(query="Job Postings", filter={"value": "database", "property": "object"})
candidates = [r for r in resp.get("results", []) if r.get("object") == "database"]

if not candidates:
    sys.exit("[!] Couldn’t find a 'Job Postings' database yet. Run notion_sync.py once to create it.")

# Prefer the DB under your NOTION_PAGE_ID, otherwise take the first.
db = None
if pid:
    for r in candidates:
        parent = r.get("parent", {})
        if parent.get("type") == "page_id" and parent.get("page_id") == pid:
            db = r
            break
db = db or candidates[0]

dbid = db["id"]

# Write NOTION_DATABASE_ID into .env (replace or append)
text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
lines = text.splitlines()
out, wrote = [], False
for L in lines:
    if L.startswith("NOTION_DATABASE_ID="):
        out.append(f"NOTION_DATABASE_ID={dbid}")
        wrote = True
    else:
        out.append(L)
if not wrote:
    out.append(f"NOTION_DATABASE_ID={dbid}")
ENV.write_text("\n".join(out) + "\n", encoding="utf-8")

print(f"[ok] Pinned NOTION_DATABASE_ID={dbid}")
