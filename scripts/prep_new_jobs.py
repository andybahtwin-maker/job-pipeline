#!/usr/bin/env python3
import os, sys, csv, re, urllib.parse as up
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from notion_client import Client

ROOT = Path(__file__).resolve().parents[1]
ENV  = ROOT / ".env"
OUT  = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)
load_dotenv(ENV, override=True)

tok = os.getenv("NOTION_TOKEN")
dbid = os.getenv("NOTION_DATABASE_ID")
if not tok or not dbid:
    sys.exit("[!] NOTION_TOKEN/NOTION_DATABASE_ID missing; run lock_db_id first.")

cli = Client(auth=tok)

# -------- URL canonicalization helpers --------
UTM_RX = re.compile(r"^utm_", re.I)
REMOVE_QUERY_KEYS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","cmpid","gclid","fbclid","mc_cid","mc_eid"}

def canon_url(raw: str|None) -> str|None:
    if not raw or not isinstance(raw, str) or raw.strip() == "":
        return None
    try:
        u = up.urlsplit(raw.strip())
        # lowercase scheme/host, remove default ports
        scheme = (u.scheme or "https").lower()
        netloc = u.netloc.lower()
        if netloc.endswith(":80") and scheme == "http":  netloc = netloc[:-3]
        if netloc.endswith(":443") and scheme == "https": netloc = netloc[:-4]
        # prune tracking params
        q = up.parse_qsl(u.query, keep_blank_values=False)
        q = [(k,v) for (k,v) in q if k.lower() not in REMOVE_QUERY_KEYS and not UTM_RX.match(k)]
        query = up.urlencode(q, doseq=True)
        # trim trailing slash in path
        path = u.path.rstrip("/")
        # drop fragment
        frag = ""
        return up.urlunsplit((scheme, netloc, path, query, frag))
    except Exception:
        return raw.strip()

def sig_row(title, company, location):
    t = (title or "").strip().lower()
    c = (company or "").strip().lower()
    l = (location or "").strip().lower()
    return f"{t}|{c}|{l}"

# -------- Pull existing URLs/signatures from Notion DB --------
existing_urls: set[str] = set()
existing_sigs: set[str]  = set()

def get_prop(page, name_list):
    props = page.get("properties", {})
    for nm in name_list:
        if nm in props:
            return props[nm]
    return None

def extract_url_from_prop(prop):
    # URL property -> "url"; rich_text/title often contain plain URLs; we’ll try URL then rich_text
    if not prop: return None
    t = prop.get("type")
    if t == "url":
        return prop.get("url")
    if t in ("rich_text","title"):
        parts = prop.get(t, [])
        # prefer plain text that looks like a URL
        for p in parts:
            txt = (p.get("plain_text") or "").strip()
            if txt.startswith("http://") or txt.startswith("https://"):
                return txt
    return None

def extract_text(prop):
    if not prop: return ""
    t = prop.get("type")
    if t in ("title","rich_text"):
        return "".join([p.get("plain_text") or "" for p in prop.get(t, [])]).strip()
    if t == "select":
        val = prop.get("select") or {}
        return (val.get("name") or "").strip()
    if t == "multi_select":
        vals = prop.get("multi_select") or []
        return " / ".join([(v.get("name") or "").strip() for v in vals])
    if t == "url":
        return prop.get("url") or ""
    return ""

# try to guess property names
URL_PROPNAMES = ["URL","Url","Link","Job URL","Posting URL","Application URL"]
TITLE_PROPNAMES = ["Title","Job Title","Name"]
COMPANY_PROPNAMES = ["Company","Employer","Org"]
LOCATION_PROPNAMES = ["Location","City","Region"]

cursor = None
while True:
    res = cli.databases.query(database_id=dbid, start_cursor=cursor, page_size=100)
    for page in res.get("results", []):
        p_url  = extract_url_from_prop(get_prop(page, URL_PROPNAMES))
        p_t    = extract_text(get_prop(page, TITLE_PROPNAMES))
        p_c    = extract_text(get_prop(page, COMPANY_PROPNAMES))
        p_l    = extract_text(get_prop(page, LOCATION_PROPNAMES))
        cu = canon_url(p_url) if p_url else None
        if cu: existing_urls.add(cu)
        if p_t or p_c or p_l:
            existing_sigs.add(sig_row(p_t, p_c, p_l))
    if not res.get("has_more"): break
    cursor = res.get("next_cursor")

print(f"[i] Existing in Notion: {len(existing_urls)} URLs, {len(existing_sigs)} sigs")

# -------- Ingest candidate CSVs and filter to "new" --------
candidates = [
    Path.home() / "Downloads" / "filtered_jobs.csv",
    Path.home() / "Downloads" / "jobs_batch_1.csv",
    Path.home() / "Downloads" / "se_jobs_batch_1.csv",
]
frames = []
for p in candidates:
    if p.exists() and p.stat().st_size > 0:
        try:
            df = pd.read_csv(p)
            if not df.empty:
                frames.append(df)
                print(f"[i] loaded {p} ({len(df)} rows)")
        except Exception as e:
            print(f"[warn] failed to read {p}: {e}")

if not frames:
    # nothing to do; write empty filtered and exit 0
    out = OUT / "filtered_jobs.csv"
    pd.DataFrame().to_csv(out, index=False)
    print("[i] No source CSVs; wrote empty filtered_jobs.csv")
    sys.exit(0)

df = pd.concat(frames, ignore_index=True).drop_duplicates()

# Normalize column names we might see
cols = {c.lower(): c for c in df.columns}
def get(colnames):
    for c in colnames:
        lc = c.lower()
        if lc in cols: return cols[lc]
    return None

url_col = get(["url","link","job_url","posting_url","application_url"])
title_col = get(["title","job_title","position","role"])
company_col = get(["company","employer","org"])
location_col = get(["location","city","region"])

new_rows = []
seen_batch_urls: set[str] = set()
seen_batch_sigs: set[str]  = set()

for _, row in df.iterrows():
    url = canon_url(str(row[url_col])) if url_col and pd.notna(row.get(url_col)) else None
    t   = str(row[title_col]).strip() if title_col and pd.notna(row.get(title_col)) else ""
    c   = str(row[company_col]).strip() if company_col and pd.notna(row.get(company_col)) else ""
    l   = str(row[location_col]).strip() if location_col and pd.notna(row.get(location_col)) else ""

    sig = sig_row(t, c, l)

    # skip if already in Notion or duplicated in this batch
    if url and (url in existing_urls or url in seen_batch_urls):
        continue
    if (not url) and (sig in existing_sigs or sig in seen_batch_sigs):
        continue

    new_rows.append(row)
    if url: seen_batch_urls.add(url)
    else:   seen_batch_sigs.add(sig)

out = pd.DataFrame(new_rows)
out_path = OUT / "filtered_jobs.csv"
if not out.empty:
    out.to_csv(out_path, index=False)
    print(f"[ok] Prepared {len(out)} NEW rows -> {out_path}")
else:
    # write an empty file so downstream step will skip cleanly
    out.to_csv(out_path, index=False)
    print("[ok] No new rows; wrote empty filtered_jobs.csv")
