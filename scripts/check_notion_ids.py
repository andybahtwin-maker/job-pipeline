#!/usr/bin/env python3
"""
Read-only Notion DB checker for ApplyPilot.
- Verifies the DB IDs wired on your Apply_Pilot page
- Prints row counts, last edited time, and a few sample titles
- No writes, no schema changes
"""
import os, sys, time, datetime
from notion_client import Client

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
if not NOTION_TOKEN:
    print("ERROR: Set NOTION_TOKEN environment variable first.", file=sys.stderr)
    sys.exit(1)

DBS = {
    "All Jobs":        "2779c46ac8fd810aaca3d8fbe1bb59db",
    "Last 30 Days":    "2779c46ac8fd81748a6ac1f4fd464475",
    "Daily":           "2779c46ac8fd81f7a02de166acf82edc",
    "Monthly":         "2779c46ac8fd81db8b75fe9d792e78b0",
    "Job Postings A":  "2779c46ac8fd814093f8ecc3f60a2938",
    "Job Postings B":  "2789c46ac8fd81818e6af1917fd81997",
}

client = Client(auth=NOTION_TOKEN)

def count_rows(dbid, max_preview=3):
    total = 0
    preview = []
    last_edited = None
    cursor = None
    while True:
        resp = client.databases.query(database_id=dbid, start_cursor=cursor, page_size=100)
        results = resp.get("results", [])
        total += len(results)

        for r in results[:max_preview-len(preview)]:
            props = r.get("properties", {})
            title_key = next((k for k,v in props.items() if v.get("type") == "title"), None)
            title = ""
            if title_key:
                title = "".join(t.get("plain_text","") for t in props[title_key].get("title", []))
            preview.append(title or "(no title)")

        # track most recent edit
        for r in results:
            le = r.get("last_edited_time")
            if le:
                ts = datetime.datetime.fromisoformat(le.replace("Z","+00:00"))
                if not last_edited or ts > last_edited:
                    last_edited = ts

        cursor = resp.get("next_cursor")
        if not cursor:
            break
        time.sleep(0.1)

    return total, preview, last_edited

print("\n=== ApplyPilot Notion Databases (READ-ONLY) ===")
for name, dbid in DBS.items():
    try:
        total, preview, last_edited = count_rows(dbid)
        pre = (" | previews: " + " • ".join(preview)) if preview else ""
        le = f" | last edit: {last_edited.isoformat()}" if last_edited else " | last edit: (none)"
        print(f"- {name}: {total} rows ({dbid}){le}{pre}")
    except Exception as e:
        msg = str(e)
        if "invalid" in msg.lower():
            msg += " (Tip: token wrong or DB not shared with the integration.)"
        print(f"- {name}: ERROR accessing {dbid} -> {msg}")

print("\nIf counts are 0, the tables are empty or your pipeline is writing to a different DB ID.")
print("Match your exporter’s target DB IDs to the ones above to populate the views.\n")
