#!/usr/bin/env python3
import os, csv, time, argparse, glob, re, sys, json
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
from notion_client import Client
from slugify import slugify

from pathlib import Path
load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent/".env"), override=True)
TOKEN   = os.getenv("NOTION_TOKEN")
DB_ID   = os.getenv("NOTION_DATABASE_ID")
PAGE_ID = os.getenv("NOTION_PAGE_ID")
CSV_GLOBS = os.getenv("CSV_GLOBS","").split()
SLEEP   = float(os.getenv("SYNC_SLEEP_SEC","0.10"))

if not TOKEN:
    sys.exit("[!] NOTION_TOKEN missing in .env")

notion = Client(auth=TOKEN)

# Rich schema for portfolio-grade tracking
SCHEMA = {
  "Title":            {"title": {}},
  "Company":          {"rich_text": {}},
  "Company Domain":   {"rich_text": {}},
  "Recruiter":        {"rich_text": {}},
  "Recruiter Email":  {"rich_text": {}},
  "Location":         {"rich_text": {}},
  "Remote":           {"select": {"options":[
                       {"name":"Yes","color":"green"},
                       {"name":"No","color":"red"},
                       {"name":"Hybrid","color":"yellow"}]}},
  "Posted":           {"date": {}},
  "Scraped At":       {"date": {}},
  "Last Seen":        {"date": {}},
  "Apply URL":        {"url": {}},
  "Job URL":          {"url": {}},
  "Job ID":           {"rich_text": {}},
  "Source":           {"select": {}},     # greenhouse/lever/boards
  "Board Company":    {"rich_text": {}},
  "Seniority":        {"select": {}},
  "Salary Min":       {"number": {}},
  "Salary Max":       {"number": {}},
  "Currency":         {"select": {}},
  "Comp Text":        {"rich_text": {}},
  "Tech":             {"multi_select": {}},
  "Keywords":         {"multi_select": {}},
  "Signals":          {"multi_select": {}},
  "Status":           {"select": {"options":[
                       {"name":"New","color":"blue"},
                       {"name":"Qualified","color":"green"},
                       {"name":"Applied","color":"yellow"},
                       {"name":"In Pipeline","color":"purple"},
                       {"name":"Paused","color":"gray"},
                       {"name":"Rejected","color":"red"}]}},
  "Stage":            {"select": {}},
  "Priority":         {"number": {}},
  "Score":            {"number": {}},
  "Tags":             {"multi_select": {}},
  "UID":              {"rich_text": {}},  # primary dedupe key
  "Email Count":      {"number": {}},
  "Last Email":       {"date": {}},
  "Email Threads":    {"rich_text": {}},
  "Notes":            {"rich_text": {}},
  "Raw":              {"rich_text": {}},
}

def ensure_db():
    global DB_ID
    if DB_ID:
        # update DB to include missing properties
        try:
            current = notion.databases.retrieve(db_id=DB_ID)
            props = current.get("properties",{})
            missing = {k:v for k,v in SCHEMA.items() if k not in props}
            if missing:
                notion.databases.update(database_id=DB_ID, properties=missing)
            return DB_ID
        except Exception as e:
            print(f"[warn] retrieve/update DB failed: {e}")
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
    s = str(v).strip().lower()
    if s in ("true","1","y","yes","remote","fully remote"): return "Yes"
    if s in ("hybrid","partly remote"): return "Hybrid"
    if s in ("false","0","n","no","onsite"): return "No"
    return ""  # unknown

def parse_date(v):
    s = str(v or "").strip()
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00")).date().isoformat()
    except Exception:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
        return m.group(1) if m else None

def domain_from_url(u):
    if not u: return ""
    try:
        host = urlparse(u).netloc.lower()
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts)>=2 else host
    except Exception:
        return ""

def pick(row, *names):
    for n in names:
        v = row.get(n)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""

def to_float(v):
    s = str(v).strip().replace(",","")
    return float(s) if s.replace(".","",1).isdigit() else None

def text_prop(s): return {"rich_text":[{"type":"text","text":{"content":str(s)[:1999]}}]} if s else {"rich_text":[]}
def select_prop(s): return {"select":{"name":str(s)[:90]}} if s else None
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

def choose_uid(row):
    for k in ("id","job_id","gh_id","lever_id","apply_url","url"):
        v = row.get(k)
        if v: return str(v).strip()
    return slugify(f"{pick(row,'title')} {pick(row,'company')} {pick(row,'posted_at','date')} {pick(row,'location')}")[:200]

def build_props(row):
    title   = pick(row,"title","role","position") or "(untitled)"
    company = pick(row,"company","org","employer")
    location= pick(row,"location","city","region")
    remoteS = norm_bool(pick(row,"remote","is_remote","work_mode"))
    posted  = parse_date(pick(row,"posted_at","date","posted","created_at"))
    scraped = parse_date(pick(row,"scraped_at","seen_at"))
    lastseen= parse_date(pick(row,"last_seen"))
    applyu  = pick(row,"apply_url","url","apply","job_url")
    jobu    = pick(row,"job_url")
    jobid   = pick(row,"id","job_id","gh_id","lever_id")
    source  = pick(row,"source","board","platform")
    boardco = pick(row,"board_company","company_slug")
    senior  = pick(row,"seniority","level")
    smin    = to_float(pick(row,"salary_min","comp_min"))
    smax    = to_float(pick(row,"salary_max","comp_max"))
    curr    = pick(row,"currency","comp_currency")
    compT   = pick(row,"salary","comp_text","comp")
    tech    = pick(row,"tech","stack","skills")
    keyw    = pick(row,"keywords")
    sigs    = pick(row,"signals")
    status  = pick(row,"status")
    stage   = pick(row,"stage")
    prio    = to_float(pick(row,"priority"))
    score   = to_float(pick(row,"score"))
    tags    = pick(row,"tags","labels")

    props = {
      "Title":            {"title":[{"type":"text","text":{"content":title}}]},
      "Company":          text_prop(company),
      "Company Domain":   text_prop(domain_from_url(applyu or jobu)),
      "Location":         text_prop(location),
      "Remote":           select_prop(remoteS),
      "Apply URL":        {"url": (applyu or None)},
      "Job URL":          {"url": (jobu or None)},
      "Job ID":           text_prop(jobid),
      "Source":           select_prop(source),
      "Board Company":    text_prop(boardco),
      "Seniority":        select_prop(senior),
      "Currency":         select_prop(curr),
      "Comp Text":        text_prop(compT),
      "Tech":             tags_prop(tech),
      "Keywords":         tags_prop(keyw),
      "Signals":          tags_prop(sigs),
      "Status":           select_prop(status or "New"),
      "Stage":            select_prop(stage),
      "Priority":         {"number": prio} if prio is not None else None,
      "Score":            {"number": score} if score is not None else None,
      "Tags":             tags_prop(tags),
      "UID":              text_prop(choose_uid(row)),
      "Raw":              text_prop(json.dumps(row)[:1999]),
    }
    if posted:  props["Posted"]    = {"date":{"start": posted}}
    if scraped: props["Scraped At"]= {"date":{"start": scraped}}
    if lastseen:props["Last Seen"] = {"date":{"start": lastseen}}
    if smin is not None: props["Salary Min"] = {"number": smin}
    if smax is not None: props["Salary Max"] = {"number": smax}
    return {k:v for k,v in props.items() if v is not None}

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
    # ensure UID property exactly matches
    props["UID"] = {"rich_text":[{"type":"text","text":{"content":uid}}]}
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
        time.sleep(SLEEP)
    print(f"[ok] {path}: +{c} created, ~{u} updated")

def main():
    db_id = ensure_db()
    globs_env = [g for g in CSV_GLOBS if g]
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="append", default=[], help="CSV file(s)")
    ap.add_argument("--glob", action="append", default=[], help="Glob(s)")
    args = ap.parse_args()

    targets = []
    for g in (args.glob or globs_env):
        targets += glob.glob(os.path.expanduser(g))
    targets += [p for p in (args.csv or []) if p]

    if not targets:
        sys.exit("[!] No CSVs found. Set CSV_GLOBS in .env or use --csv/--glob")

    for p in sorted(set(targets)):
        sync_csv(db_id, os.path.expanduser(p))

if __name__ == "__main__":
    main()
