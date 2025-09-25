#!/usr/bin/env python3
import os, csv, time, argparse, glob, re, sys
from datetime import datetime
from dotenv import load_dotenv
from notion_client import Client
from slugify import slugify

load_dotenv()
TOKEN   = os.getenv("NOTION_TOKEN")
DB_ID   = os.getenv("NOTION_DATABASE_ID")
PAGE_ID = os.getenv("NOTION_PAGE_ID")
CSV_GLOBS = os.getenv("CSV_GLOBS","").split()

if not TOKEN:
    sys.exit("[!] NOTION_TOKEN missing in .env")

notion = Client(auth=TOKEN)

SCHEMA = {
  "Title":     {"title": {}},
  "Company":   {"rich_text": {}},
  "Location":  {"rich_text": {}},
  "Remote":    {"checkbox": {}},
  "Posted":    {"date": {}},
  "Apply URL": {"url": {}},
  "Source":    {"rich_text": {}},
  "Score":     {"number": {}},
  "Tags":      {"multi_select": {}},
  "UID":       {"rich_text": {}},   # dedupe key
  "Raw":       {"rich_text": {}},
}

def ensure_db():
    global DB_ID
    if DB_ID:
        return DB_ID
    if not PAGE_ID:
        sys.exit("[!] Provide NOTION_DATABASE_ID or NOTION_PAGE_ID in .env")
    db = notion.databases.create(
        parent={"type":"page_id","page_id":PAGE_ID},
        title=[{"type":"text","text":{"content":"Job Postings"}}],
        properties=SCHEMA
    )
    DB_ID = db["id"]
    print(f"[ok] Created Notion DB: {DB_ID}")
    return DB_ID

def norm_bool(v):
    return str(v).strip().lower() in ("1","y","yes","true","t")

def parse_date(v):
    s = str(v or "").strip()
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00")).date().isoformat()
    except Exception:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
        return m.group(1) if m else None

def pick(row, *names):
    for n in names:
        if n in row and str(row[n]).strip():
            return row[n]
    return ""

def choose_uid(row):
    # preference: explicit id/url; fallback: title-company-date
    for k in ("id","job_id","gh_id","lever_id","url","apply_url"):
        v = row.get(k)
        if v: return str(v).strip()
    return slugify(f"{pick(row,'title')} {pick(row,'company')} {pick(row,'posted_at','date')}")[:200]

def text_prop(s): return {"rich_text":[{"type":"text","text":{"content":str(s)[:1999]}}]} if s else {"rich_text":[]}
def tags_prop(v):
    if not v: return {"multi_select":[]}
    if isinstance(v,str):
        if v.startswith("[") and v.endswith("]"):
            vals = [x.strip(" '\"") for x in v.strip("[]").split(",") if x.strip(" '\"")]
        else:
            vals = [x.strip() for x in v.split(",") if x.strip()]
    else:
        vals = list(v)
    return {"multi_select":[{"name":t[:100]} for t in vals]}

def build_props(row):
    title   = pick(row,"title","role","position") or "(untitled)"
    company = pick(row,"company","org","employer")
    location= pick(row,"location","city","region")
    remote  = pick(row,"remote","is_remote","work_mode")
    posted  = pick(row,"posted_at","date","posted","created_at")
    applyu  = pick(row,"apply_url","url","apply","job_url")
    source  = pick(row,"source","board","platform")
    score   = pick(row,"score")
    tags    = pick(row,"tags","labels","skills")

    props = {
      "Title":     {"title":[{"type":"text","text":{"content":title}}]},
      "Company":   text_prop(company),
      "Location":  text_prop(location),
      "Remote":    {"checkbox": norm_bool(remote)},
      "Apply URL": {"url": (applyu or None)},
      "Source":    text_prop(source),
      "Tags":      tags_prop(tags),
      "UID":       text_prop(choose_uid(row)),
      "Raw":       text_prop(str(row)),
    }
    pd = parse_date(posted)
    if pd: props["Posted"] = {"date":{"start": pd}}
    if str(score).replace(".","",1).isdigit(): props["Score"] = {"number": float(score)}
    return props

def find_existing(db_id, uid):
    q = notion.databases.query(
      **{"database_id": db_id,
         "filter": {"property":"UID","rich_text":{"equals": uid}},
         "page_size": 1}
    )
    res = q.get("results",[])
    return res[0]["id"] if res else None

def upsert(db_id, row):
    uid = choose_uid(row)
    props = build_props(row)
    page = find_existing(db_id, uid)
    if page:
        notion.pages.update(page_id=page, properties=props)
        return "update"
    notion.pages.create(parent={"database_id": db_id}, properties=props)
    return "create"

def sync_csv(db_id, path):
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        rows = list(rdr)
    if not rows:
        print(f"[i] {path}: 0 rows, skipping")
        return
    c=u=0
    for r in rows:
        try:
            op = upsert(db_id, r)
            if op=="create": c+=1
            else: u+=1
        except Exception as e:
            print(f"[warn] {path}: {e} : {r.get('title','')[:80]}")
        time.sleep(0.1)  # gentle rate limit
    print(f"[ok] {path}: +{c} created, ~{u} updated")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="append", default=[], help="CSV file(s) (repeatable)")
    ap.add_argument("--glob", action="append", default=[], help="Glob(s) for CSVs (repeatable)")
    args = ap.parse_args()

    db_id = ensure_db()
    targets = []
    for g in (args.glob or CSV_GLOBS):
        targets += glob.glob(os.path.expanduser(g))
    targets += [p for p in args.csv if p]

    if not targets:
        sys.exit("[!] No CSVs found. Set CSV_GLOBS in .env or pass --glob/--csv")

    for p in sorted(set(targets)):
        sync_csv(db_id, os.path.expanduser(p))

if __name__ == "__main__":
    main()
