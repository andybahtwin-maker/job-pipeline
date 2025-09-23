#!/usr/bin/env python3
import os, sys
from notion_client import Client

TOKEN = os.environ["NOTION_TOKEN"]
PAGE  = os.environ["NOTION_PAGE_ID"]
notion = Client(auth=TOKEN)

def list_children(pid):
    res=[]; cursor=None
    while True:
        page = notion.blocks.children.list(pid, page_size=100, start_cursor=cursor) if cursor else notion.blocks.children.list(pid, page_size=100)
        res.extend(page["results"])
        cursor = page.get("next_cursor")
        if not page.get("has_more"): break
    return res

kids = list_children(PAGE)
for b in kids:
    t = b.get("type")
    bid = b["id"]
    try:
        if t == "child_page":
            notion.pages.update(bid, archived=True)
        else:
            notion.blocks.update(bid, archived=True)
    except Exception as e:
        print(f"[warn] failed to archive {t} {bid}: {e}", file=sys.stderr)

print(f"[ok] Archived {len(kids)} blocks under the page.")
