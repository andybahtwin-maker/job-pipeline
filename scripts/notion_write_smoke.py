#!/usr/bin/env python3
"""
Minimal write smoke-test:
- Auto-detects the title property name
- Creates a tiny test row, then deletes it (idempotent)
- DRY-RUN by default; require --go to perform writes
"""
import os, sys, argparse, datetime, time
from notion_client import Client

DBS = {
    "All Jobs":        "2779c46ac8fd810aaca3d8fbe1bb59db",
    "Last 30 Days":    "2779c46ac8fd81748a6ac1f4fd464475",
    "Daily":           "2779c46ac8fd81f7a02de166acf82edc",
    "Monthly":         "2779c46ac8fd81db8b75fe9d792e78b0",
    "Job Postings A":  "2779c46ac8fd814093f8ecc3f60a2938",
    "Job Postings B":  "2789c46ac8fd81818e6af1917fd81997",
}

parser = argparse.ArgumentParser()
parser.add_argument("--db", choices=list(DBS.keys()), default="All Jobs")
parser.add_argument("--go", action="store_true", help="actually write+delete")
args = parser.parse_args()

token = os.environ.get("NOTION_TOKEN")
if not token:
    sys.exit("ERROR: NOTION_TOKEN not set.")

client = Client(auth=token)
dbid = DBS[args.db]

# Determine title prop
meta = client.databases.retrieve(dbid)
props = meta.get("properties", {})
title_prop = next((k for k,v in props.items() if v.get("type")=="title"), None)
if not title_prop:
    sys.exit("ERROR: Could not find a title property in this DB.")

title_text = f"SMOKE TEST {datetime.datetime.utcnow().isoformat()}"

print(f"DB: {args.db} ({dbid}) | title prop: {title_prop}")
if not args.go:
    print("DRY-RUN: would create and then delete a row titled:", title_text)
    sys.exit(0)

# Create a page
page = client.pages.create(
    parent={"database_id": dbid},
    properties={title_prop: {"title": [{"type":"text", "text":{"content": title_text}}]}},
)

page_id = page["id"]
print("Created page:", page_id)

# Clean up (delete = archive)
client.pages.update(page_id=page_id, archived=True)
print("Deleted (archived) page:", page_id)
