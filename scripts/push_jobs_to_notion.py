#!/usr/bin/env python3
import os, csv, datetime as dt
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client

ROOT = Path(__file__).resolve().parents[1]
ENV  = ROOT / ".env"
CSV  = ROOT / "outputs" / "filtered_jobs.csv"

load_dotenv(ENV, override=True)
token   = os.getenv("NOTION_TOKEN")
page_id = os.getenv("NOTION_PAGE_ID")

cli = Client(auth=token)

def overwrite_jobs():
    jobs = []
    if CSV.exists():
        with open(CSV) as f:
            rdr = list(csv.DictReader(f))
            # latest 20
            jobs = rdr[-20:]
    else:
        print(f"[!] No CSV found: {CSV}")
        return

    children=[]
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    children.append({
        "object":"block",
        "type":"heading_2",
        "heading_2":{"rich_text":[{"type":"text","text":{"content":f"Jobs Update ({now})"}}]}
    })

    for row in jobs:
        title = row.get("title","(no title)")
        company = row.get("company","(no company)")
        location = row.get("location","")
        url = row.get("url","")

        text = f"{title} — {company} ({location})"
        rich = [{"type":"text","text":{"content":text}}]
        if url:
            rich = [{"type":"text","text":{"content":title,"link":{"url":url}}},
                    {"type":"text","text":{"content":f" — {company} ({location})"}}]

        children.append({"object":"block","type":"bulleted_list_item",
                         "bulleted_list_item":{"rich_text":rich}})

    # clear old blocks
    try:
        old=cli.blocks.children.list(block_id=page_id).get("results",[])
        for blk in old:
            cli.blocks.delete(blk["id"])
    except Exception as e:
        print(f"[warn] Could not clear old blocks: {e}")

    # add new blocks in chunks of 50
    for i in range(0,len(children),50):
        cli.blocks.children.append(block_id=page_id, children=children[i:i+50])

    print(f"[ok] Wrote {len(jobs)} jobs to Notion page {page_id}")

overwrite_jobs()
