#!/usr/bin/env python3
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client

# Always load applypilot/.env regardless of cwd
load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent / ".env"), override=True)

tok  = os.getenv("NOTION_TOKEN")
dbid = os.getenv("NOTION_DATABASE_ID")
pid  = os.getenv("NOTION_PAGE_ID")

def red(s): return s[:6] + "…" + s[-4:] if s and len(s) > 12 else s

if not tok:
    sys.exit("[!] NOTION_TOKEN missing in applypilot/.env")

print(f"[i] NOTION_TOKEN: {red(tok)}")
print(f"[i] NOTION_DATABASE_ID: {dbid or '(not set)'}")
print(f"[i] NOTION_PAGE_ID: {pid or '(not set)'}")

client = Client(auth=tok)

# basic call to verify token
me = client.users.me()
print(f"[ok] Token valid. Hello, {me.get('name') or me.get('id')}")

# if DB set, try retrieving it; else if PAGE set, try retrieving the page
if dbid:
    try:
        db = client.databases.retrieve(db_id=dbid)
        print(f"[ok] Can access DB: {db.get('title',[{}])[0].get('plain_text','(untitled)')} ({db['id']})")
    except Exception as e:
        print(f"[warn] Could not retrieve DB {dbid}: {e}")
elif pid:
    try:
        pg = client.pages.retrieve(page_id=pid)
        print(f"[ok] Can access Page: {pg.get('id')}")
        print("    (You still need NOTION_DATABASE_ID or let the sync create a DB under this page.)")
    except Exception as e:
        print(f"[warn] Could not retrieve Page {pid}: {e}")
else:
    print("[i] Neither NOTION_DATABASE_ID nor NOTION_PAGE_ID set. The sync can create a DB if PAGE_ID is provided.")
