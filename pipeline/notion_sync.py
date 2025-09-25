from notion_client import Client
from typing import Dict, List
from datetime import datetime, timezone
from dateutil import tz

MARKER = "Jobs Dashboard (auto-updated)"

def _iso(dt):
    if not dt: return None
    if isinstance(dt, str): return dt
    if isinstance(dt, datetime):
        return dt.astimezone(tz.UTC).isoformat()
    return None

def upsert_jobs(notion: Client, db_id: str, jobs: List[Dict]):
    # One-by-one upsert by External ID (simple + robust)
    for j in jobs:
        eid = j["external_id"]
        q = notion.databases.query(
            database_id=db_id,
            filter={"property":"External ID","title":{"equals":eid}}
        )
        page_id = q["results"][0]["id"] if q["results"] else None
        props = {
          "External ID": {"title": [{"type":"text","text":{"content": eid}}]},
          "Company": {"rich_text":[{"type":"text","text":{"content": j.get("company","")}}]},
          "Title": {"rich_text":[{"type":"text","text":{"content": j.get("title","")}}]},
          "URL": {"url": j.get("url")},
          "Location": {"rich_text":[{"type":"text","text":{"content": j.get("location","") or ""}}]},
          "Remote": {"checkbox": bool(j.get("remote")) if j.get("remote") is not None else False},
          "Posted": {"date": {"start": _iso(j.get("posted_at"))}},
          "Salary Min": {"number": j.get("salary_min")},
          "Salary Max": {"number": j.get("salary_max")},
          "Currency": {"select": {"name": j.get("currency")}} if j.get("currency") else None,
          "First Seen": {"date": {"start": _iso(j.get("first_seen"))}},
          "Last Seen": {"date": {"start": _iso(j.get("last_seen"))}},
        }
        props = {k:v for k,v in props.items() if v is not None}

        if page_id:
            notion.pages.update(page_id=page_id, properties=props)
        else:
            notion.pages.create(parent={"database_id": db_id}, properties=props)

def update_portfolio_blocks(notion: Client, page_id: str, markdown_summary: str, todays_jobs: List[Dict]):
    """
    Replaces prior dashboard blocks with:
      - 📊 Callout (summary markdown)
      - Divider
      - Heading: "Today’s Jobs (N)"
      - Bulleted list items: **Title** — Company (Remote/On-site) • Posted YYYY-MM-DD  [Open]
    """
    # delete prior blocks that contain the marker
    blocks = notion.blocks.children.list(block_id=page_id)["results"]
    for b in blocks:
        plain = ""
        t = b["type"]
        rich = None
        if t in ("callout","paragraph","heading_2","toggle","bulleted_list_item"):
            rich = b[t].get("rich_text")
        if rich and len(rich)>0 and MARKER in (rich[0].get("plain_text") or ""):
            notion.blocks.delete(block_id=b["id"])

    # Build new content
    callout = {
        "object":"block","type":"callout",
        "callout":{
            "icon":{"type":"emoji","emoji":"📊"},
            "rich_text":[{"type":"text","text":{"content": f"{MARKER}\n\n{markdown_summary}"}}],
            "color":"default"
        }
    }

    divider = {"object":"block","type":"divider","divider":{}}

    heading = {
        "object":"block","type":"heading_2",
        "heading_2":{"rich_text":[{"type":"text","text":{"content":f"Today’s Jobs ({len(todays_jobs)}) — {MARKER}"}}]}
    }

    def bullet_for(job: Dict):
        title = job.get("title","").strip() or "Untitled"
        company = job.get("company","").strip()
        remote = job.get("remote")
        remote_txt = "Remote" if remote is True else ("On-site" if remote is False else "")
        posted = job.get("posted_at")
        posted_txt = (posted[:10] if isinstance(posted,str) else (posted.date().isoformat() if isinstance(posted,datetime) else ""))
        pieces = [f"**{title}**"]
        if company: pieces.append(f"— {company}")
        if remote_txt: pieces.append(f"({remote_txt})")
        if posted_txt: pieces.append(f"• Posted {posted_txt}")
        text = " ".join(pieces)
        rich: List[Dict] = [{"type":"text","text":{"content":text}, "annotations":{"bold":False}}]
        # add link if present
        if job.get("url"):
            rich.append({"type":"text","text":{"content":"  [Open]","link":{"url":job["url"]}}})
        return {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":rich}}

    bullets = [bullet_for(j) for j in todays_jobs[:50]]

    notion.blocks.children.append(block_id=page_id, children=[callout, divider, heading] + bullets)

# -------- ApplyPilot v2: Vibe Check properties --------
def build_vibe_properties(job: dict) -> dict:
    mission = (job.get("vibe_mission") or "").strip()
    keywords = job.get("vibe_keywords") or []
    links = job.get("vibe_links") or []
    talking_points = job.get("vibe_talking_points") or []

    link_texts = []
    for url in links:
        u = str(url).strip()
        if not u:
            continue
        link_texts.append({
            "type": "text",
            "text": {"content": u, "link": {"url": u}}
        })

    props = {}
    if mission:
        props["Mission"] = {"rich_text": [{"type": "text", "text": {"content": mission}}]}
    if keywords:
        props["Vibe"] = {"multi_select": [{"name": k} for k in keywords if isinstance(k, str) and k.strip()]}
    if link_texts:
        props["BrandLinks"] = {"rich_text": link_texts}
    if talking_points:
        props["TalkingPoints"] = {"rich_text": [{"type": "text","text":{"content": ", ".join([tp for tp in talking_points if isinstance(tp, str) and tp.strip()])}}]}
    return props


# --- Compatibility shim: expose a stable push_jobs_to_notion() API
def push_jobs_to_notion(jobs):
    for name in ("sync_jobs_to_notion","upsert_jobs_to_notion","create_or_update_jobs","write_jobs_to_notion","push"):
        fn = globals().get(name)
        if callable(fn):
            return fn(jobs)
    raise RuntimeError("No Notion push function found; implement push_jobs_to_notion(jobs) or one of the known names.")
