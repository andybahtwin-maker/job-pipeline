#!/usr/bin/env python3
import os, re, imaplib, email, datetime, time, json, yaml
from email.header import decode_header
from urllib.parse import urlparse
from dotenv import load_dotenv
from notion_client import Client
from slugify import slugify

from pathlib import Path
load_dotenv(dotenv_path=str(Path(__file__).resolve().parent.parent/".env"), override=True)
NTOK  = os.getenv("NOTION_TOKEN")
DB_ID = os.getenv("NOTION_DATABASE_ID")
PAGE  = os.getenv("NOTION_PAGE_ID")
U     = os.getenv("GMAIL_USER") or ""
P     = os.getenv("GMAIL_APP_PASSWORD") or ""
HOST  = os.getenv("GMAIL_IMAP_HOST","imap.gmail.com")
PORT  = int(os.getenv("GMAIL_IMAP_PORT","993"))
LOOKBACK = int(os.getenv("LINKER_LOOKBACK_DAYS","30"))

if not NTOK: raise SystemExit("[!] NOTION_TOKEN missing in .env")
notion = Client(auth=NTOK)

# Ensure DB exists (create minimal if needed)
NEEDED = {
  "Title": {"title": {}},
  "Company": {"rich_text": {}},
  "Apply URL": {"url": {}},
  "UID": {"rich_text": {}},
  "Last Email": {"date": {}},
  "Email Count": {"number": {}},
  "Email Threads": {"rich_text": {}},
}
def ensure_db(db_id):
    if db_id:
        try:
            notion.databases.retrieve(db_id=db_id)
            return db_id
        except Exception:
            pass
    if not PAGE:
        raise SystemExit("[!] Provide NOTION_DATABASE_ID or NOTION_PAGE_ID to create DB")
    db = notion.databases.create(
        parent={"type":"page_id","page_id":PAGE},
        title=[{"type":"text","text":{"content":"Job Postings"}}],
        properties=NEEDED
    )
    return db["id"]

DB_ID = ensure_db(DB_ID or "")

def load_overrides():
    try:
        with open(os.path.join(os.path.dirname(__file__),"../config/overrides.yaml"),"r",encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

OV = load_overrides()
ALIASES = {k.lower():[a.lower() for a in v] for k,v in (OV.get("aliases") or {}).items()}
DOMAINS = {k.lower():[d.lower() for d in v] for k,v in (OV.get("domains") or {}).items()}

def norm_company(s):
    return re.sub(r'\s+',' ', (s or "").strip().lower())

def company_keys(name):
    name = norm_company(name)
    keys = {name}
    for k,alts in ALIASES.items():
        if name==k or name in alts:
            keys |= {k, *alts}
    return keys

def get_domain(u):
    if not u: return ""
    host = urlparse(u).netloc.lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts)>=2 else host

def fetch_index():
    idx=[]
    cursor=None
    while True:
        resp = notion.databases.query(database_id=DB_ID, start_cursor=cursor) if cursor else notion.databases.query(database_id=DB_ID)
        for page in resp["results"]:
            pid = page["id"]; props = page["properties"]
            title = "".join([t["plain_text"] for t in props.get("Title",{}).get("title",[])])
            company = "".join([t["plain_text"] for t in props.get("Company",{}).get("rich_text",[])]).strip()
            applyu = props.get("Apply URL",{}).get("url")
            uid = "".join([t["plain_text"] for t in props.get("UID",{}).get("rich_text",[])]) or slugify(f"{company}-{title}")[:200]
            dom = get_domain(applyu)
            idx.append({"pid":pid,"company":norm_company(company),"domain":dom,"uid":uid})
        if not resp.get("has_more"): break
        cursor = resp.get("next_cursor")
    return idx

def open_imap():
    if not (U and P):
        print("[i] Gmail creds not set; skipping email linker.")
        return None
    im = imaplib.IMAP4_SSL(HOST, PORT); im.login(U,P); im.select("INBOX"); return im

def utf8(s):
    if not s: return ""
    out=""; 
    for part,enc in decode_header(s):
        out += (part.decode(enc or "utf-8","ignore") if isinstance(part,bytes) else part)
    return out

def search_since(im, days):
    since = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = im.search(None, f'(SINCE "{since}")')
    return data[0].split() if (typ=="OK" and data and data[0]) else []

def sender_domain(addr):
    m = re.search(r'@([A-Za-z0-9.-]+)', addr or "")
    if not m: return ""
    host = m.group(1).lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts)>=2 else host

def match_candidates(company, domain, idx):
    keys = company_keys(company)
    doms = set()
    # Add override domains
    for k in keys:
        doms |= set(DOMAINS.get(k,[]))
    if domain: doms.add(domain)
    out=[]
    for it in idx:
        if it["company"] in keys: out.append(it); continue
        if it["domain"] and it["domain"] in doms: out.append(it); continue
    return out

def update_notion(matches):
    upd=0
    for uid, info in matches.items():
        q = notion.databases.query(database_id=DB_ID, filter={"property":"UID","rich_text":{"equals": uid}}, page_size=1)
        res = q.get("results",[])
        if not res: continue
        pid = res[0]["id"]
        props = {
          "Last Email": {"date":{"start": info["last"]}},
          "Email Count": {"number": info["count"]},
        }
        if info.get("threads"):
          props["Email Threads"] = {"rich_text":[{"type":"text","text":{"content":"\n".join(info["threads"])[:1999]}}]}
        notion.pages.update(page_id=pid, properties=props)
        upd+=1; time.sleep(0.05)
    print(f"[ok] Updated {upd} job(s) with email signals")

def main():
    idx = fetch_index()
    im = open_imap()
    if im is None: 
        return
    ids = search_since(im, int(os.getenv("LOOKER_LOOKBACK_DAYS", os.getenv("LINKER_LOOKBACK_DAYS","30"))))
    matches = {}  # uid -> info
    for msgid in ids:
        typ, data = im.fetch(msgid, '(RFC822)')
        if typ!='OK' or not data or not data[0]: continue
        msg = email.message_from_bytes(data[0][1])
        from_h = utf8(msg.get("From"))
        subj   = utf8(msg.get("Subject"))
        date_h = msg.get("Date","")
        try:
            d = datetime.datetime(*email.utils.parsedate(date_h)[:6]).date().isoformat()
        except Exception:
            d = datetime.date.today().isoformat()
        sdom = sender_domain(from_h)

        # naive company guess from subject/from
        m = re.search(r'([A-Za-z0-9][A-Za-z0-9 ._-]{2,40})', subj) or re.search(r'([A-Za-z0-9][A-Za-z0-9 ._-]{2,40})', from_h)
        comp_guess = (m.group(1) if m else "").strip().lower()

        cands = match_candidates(comp_guess, sdom, idx)
        for it in set((c["uid"], c["pid"]) for c in cands):
            uid, pid = it
            rec = matches.setdefault(uid, {"last":"1970-01-01","count":0,"threads":[]})
            if d > rec["last"]: rec["last"]=d
            rec["count"] += 1
            # you can insert web Gmail URLs here if you have message-id mappings; omitted for now
    try: im.logout()
    except: pass
    update_notion(matches)

if __name__ == "__main__":
    main()
