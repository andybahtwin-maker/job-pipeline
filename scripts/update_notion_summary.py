#!/usr/bin/env python3
import os, json, datetime as dt
from pathlib import Path
from notion_client import Client

ROOT = Path.home() / "applypilot"
ENV  = ROOT / ".env"
if ENV.exists():
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k,v = line.split("=",1); os.environ.setdefault(k.strip(), v.strip())
TOKEN = os.environ["NOTION_TOKEN"]
PAGE  = os.environ["NOTION_PAGE_ID"]

CHART_URLS = (ROOT / "outputs" / "chart_urls.json")
MASTER     = ROOT / "data" / "master.csv"
ARCHDIR    = ROOT / "data" / "archive"

# ---------- helpers ----------
def load_csv(path):
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def fmt_job(row):
    t=(row.get("title") or "").strip() or "(untitled)"
    c=(row.get("company") or "").strip() or "(company?)"
    s=(row.get("source") or "").strip() or "source?"
    l=(row.get("location") or "").strip() or "location?"
    u=(row.get("url") or "").strip()
    dp=(row.get("date_posted") or "").strip()
    dc=(row.get("date_collected") or "").strip()
    suffix=f" • {c} • {l} • {s}"
    if dp: suffix+=f" • posted {dp}"
    if dc: suffix+=f" • added {dc}"
    if u:
        return [{"type":"text","text":{"content":t,"link":{"url":u}}},{"type":"text","text":{"content":suffix}}]
    return [{"type":"text","text":{"content":f"{t}{suffix}"}}]

def bullet(rich): return {"type":"bulleted_list_item","bulleted_list_item":{"rich_text":rich}}
def toggle(title, children): return {"type":"toggle","toggle":{"rich_text":[{"type":"text","text":{"content":title}}],"children":children}}
def image_block(url, caption):
    return {"type":"image","image":{"type":"external","external":{"url":url},
            "caption":[{"type":"text","text":{"content":caption}}]}}
def callout(title, children):
    return {"type":"callout","callout":{
        "icon":{"type":"emoji","emoji":"📦"},
        "rich_text":[{"type":"text","text":{"content":title}}],
        "color":"default","children":children}}
def link_to_page_block(page_id): return {"type":"link_to_page","link_to_page":{"page_id":page_id}}
def chunk(seq, n): 
    for i in range(0,len(seq),n): yield seq[i:i+n]

def clear_main_generated(notion, page_id):
    """Remove prior generated charts, Daily/Archive callouts, and legacy 'Recent Jobs'."""
    results = notion.blocks.children.list(page_id, page_size=200)["results"]
    def is_chart_image(b):
        if b.get("type")!="image": return False
        img=b["image"]
        if img.get("type")!="external": return False
        url=(img["external"].get("url") or "").lower()
        return ("/charts/" in url) and ("raw.githubusercontent.com" in url or "cdn.jsdelivr.net" in url or "github.com" in url)
    to_archive=set()
    for b in results:
        if b.get("type")=="callout":
            txt="".join([r["plain_text"] for r in b["callout"].get("rich_text", [])])
            if txt.startswith(("📦 Daily Haul","Daily Haul","📦 Archive — Last 30 Days","Archive — Last 30 Days")):
                to_archive.add(b["id"])
    for b in results:
        if is_chart_image(b): to_archive.add(b["id"])
    for i,b in enumerate(results):
        if b.get("type")=="paragraph":
            txt="".join([r["plain_text"] for r in b["paragraph"].get("rich_text", [])]).strip()
            if txt.lower().startswith("recent jobs"):
                to_archive.add(b["id"])
                j=i+1
                while j<len(results) and results[j].get("type")=="bulleted_list_item":
                    to_archive.add(results[j]["id"]); j+=1
    for bid in to_archive:
        notion.blocks.update(bid, archived=True)

def recreate_subpage(notion, parent_page_id, title):
    kids = notion.blocks.children.list(parent_page_id, page_size=100)["results"]
    for b in kids:
        if b.get("type")=="child_page" and b["child_page"]["title"]==title:
            notion.pages.update(b["id"], archived=True)
    created = notion.pages.create(parent={"page_id":parent_page_id},
        properties={"title":{"title":[{"type":"text","text":{"content":title}}]}})
    return created["id"]

# ---------- datasets ----------
today = dt.date.today().isoformat()
daily_rows = load_csv(ARCHDIR / f"{today}.csv") if (ARCHDIR / f"{today}.csv").exists() else []

last30_rows=[]
if MASTER.exists():
    rows=load_csv(MASTER)
    cutoff=dt.date.today()-dt.timedelta(days=30)
    for r in rows:
        d=r.get("date_collected") or ""
        try:
            if d and dt.date.fromisoformat(d)>=cutoff: last30_rows.append(r)
        except: pass

# ---------- subpages (full content) ----------
notion = Client(auth=TOKEN)
daily_title   = f"Daily Haul — {today}"
daily_page_id = recreate_subpage(notion, PAGE, daily_title)
archive_title = "Archive — Last 30 Days (full)"
archive_page_id = recreate_subpage(notion, PAGE, archive_title)

# Daily subpage
daily_blocks=[]
bul=[bullet(fmt_job(r)) for r in daily_rows]
if bul:
    for part_i, part in enumerate(chunk(bul,100),1):
        daily_blocks.append(toggle(f"Jobs (part {part_i})", part))
else:
    daily_blocks.append({"type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"No new jobs today."}}]}})
for i in range(0,len(daily_blocks),90):
    notion.blocks.children.append(daily_page_id, children=daily_blocks[i:i+90])

# 30-day subpage (grouped by day)
from collections import defaultdict
g=defaultdict(list)
for r in last30_rows: g[(r.get("date_collected") or today)].append(r)
arch_blocks=[]
for day in sorted(g.keys(), reverse=True):
    bullets=[bullet(fmt_job(r)) for r in g[day]]
    idx=1
    for part in chunk(bullets,100):
        arch_blocks.append(toggle(f"{day} — {len(g[day])} jobs (part {idx})", part)); idx+=1
for i in range(0,len(arch_blocks),90):
    notion.blocks.children.append(archive_page_id, children=arch_blocks[i:i+90])

# ---------- main page: charts + two links (no daily bullets here) ----------
clear_main_generated(notion, PAGE)

charts=[]
if CHART_URLS.exists():
    try:
        urls=json.loads(CHART_URLS.read_text())
        labels=["📊 Top Companies","📊 Top Locations","📊 Top Sources"]
        for u,lbl in zip(urls,labels):
            charts.append(image_block(u,lbl))
    except: pass

daily_callout = callout(f"📦 Daily Haul — {today} ({len(daily_rows)} new)", [link_to_page_block(daily_page_id)])
archive_callout = callout(f"📦 Archive — Last 30 Days ({len(last30_rows)} total)", [link_to_page_block(archive_page_id)])

payload = charts + [daily_callout, archive_callout]
for i in range(0,len(payload),90):
    notion.blocks.children.append(PAGE, children=payload[i:i+90])

print("[ok] Notion updated: charts + links to Daily + 30-day subpages (no daily bullets on main).")
