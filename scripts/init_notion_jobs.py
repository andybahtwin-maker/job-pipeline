#!/usr/bin/env python3
"""
Create (or re-use) a Notion database for job postings, and push CSV rows into it.

Usage:
  python3 scripts/init_notion_jobs.py --csv ~/Downloads/se_jobs_batch_1.csv

Requires:
  - .env with NOTION_TOKEN and (optional) NOTION_DATABASE_ID
  - `pip install notion-client python-dotenv`
"""

import os, csv, argparse
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("NOTION_TOKEN")
database_id = os.getenv("NOTION_DATABASE_ID")
page_id = os.getenv("NOTION_PAGE_ID")  # parent page to create DB under (if new)

if not token:
    raise SystemExit("[!] Please set NOTION_TOKEN in your .env file")
client = Client(auth=token)

def ensure_database():
    global database_id
    if database_id:
        print(f"[i] Using existing database {database_id}")
        return database_id
    if not page_id:
        raise SystemExit("[!] No NOTION_DATABASE_ID or NOTION_PAGE_ID set")
    print("[i] Creating new Notion database under page", page_id)
    db = client.databases.create(
        parent={"type":"page_id","page_id":page_id},
        title=[{"type":"text","text":{"content":"Job Postings"}}],
        properties={
            "Title": {"title": {}},
            "Company": {"rich_text": {}},
            "Location": {"rich_text": {}},
            "Remote": {"checkbox": {}},
            "Posted": {"date": {}},
            "Apply URL": {"url": {}},
            "Source": {"rich_text": {}},
            "Raw": {"rich_text": {}},
        }
    )
    database_id = db["id"]
    print("[ok] Created database", database_id)
    return database_id

def push_row(row):
    props = {}
    if row.get("title"): props["Title"] = {"title":[{"text":{"content":row["title"]}}]}
    if row.get("company"): props["Company"] = {"rich_text":[{"text":{"content":row["company"]}}]}
    if row.get("location"): props["Location"] = {"rich_text":[{"text":{"content":row["location"]}}]}
    if row.get("remote"): props["Remote"] = {"checkbox": str(row["remote"]).lower() in ["true","yes","1"]}
    if row.get("posted_at"): props["Posted"] = {"date":{"start":row["posted_at"]}}
    if row.get("apply_url"): props["Apply URL"] = {"url":row["apply_url"]}
    if row.get("source"): props["Source"] = {"rich_text":[{"text":{"content":row["source"]}}]}
    props["Raw"] = {"rich_text":[{"text":{"content":str(row)}}]}
    client.pages.create(parent={"database_id": database_id}, properties=props)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()

    ensure_database()
    with open(args.csv,newline="",encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[i] Pushing {len(rows)} rows into Notion…")
    for r in rows:
        push_row(r)
    print("[ok] Done.")

if __name__=="__main__":
    main()
