#!/usr/bin/env python3
"""
Push job rows from a CSV into a Notion database.

Usage:
  python3 scripts/push_to_notion.py --csv se_jobs_batch_1.csv

Requires:
  - .env with NOTION_TOKEN and NOTION_DATABASE_ID
  - `pip install notion-client python-dotenv`
"""

import os, csv, argparse
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("NOTION_TOKEN")
database_id = os.getenv("NOTION_DATABASE_ID")
if not token or not database_id:
    raise SystemExit("[!] Please set NOTION_TOKEN and NOTION_DATABASE_ID in your .env file")

client = Client(auth=token)

def push_row(row):
    props = {}
    if row.get("title"):
        props["Title"] = {"title": [{"text": {"content": row["title"]}}]}
    if row.get("company"):
        props["Company"] = {"rich_text": [{"text": {"content": row["company"]}}]}
    if row.get("location"):
        props["Location"] = {"rich_text": [{"text": {"content": row["location"]}}]}
    if row.get("remote"):
        props["Remote"] = {"checkbox": str(row["remote"]).lower() in ["true","yes","1"]}
    if row.get("posted_at"):
        props["Posted"] = {"date": {"start": row["posted_at"]}}
    if row.get("apply_url"):
        props["Apply URL"] = {"url": row["apply_url"]}

    client.pages.create(parent={"database_id": database_id}, properties=props)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[i] Pushing {len(rows)} rows into Notion…")
    for r in rows:
        push_row(r)
    print("[ok] Done.")

if __name__ == "__main__":
    main()
