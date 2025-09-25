#!/usr/bin/env python3
import os, sys, csv, json, datetime
from notion_client import Client

FIELDS = ["Title","Company","Role","URL","Source","Date","last_edited_time","id"]

def env(k):
    v=os.environ.get(k)
    if not v: sys.exit(f"[!] Missing {k}")
    return v

def find_title_prop(props):
    for k,v in props.items():
        if v.get("type") == "title":
            return k
    return None

def text_from_rich(r):
    return "".join(t.get("plain_text","") for t in r.get("rich_text",[])).strip()

def fetch_all(cli, dbid):
    out=[]; cursor=None
    while True:
        resp=cli.databases.query(database_id=dbid, start_cursor=cursor, page_size=100)
        out.extend(resp.get("results",[]))
        cursor=resp.get("next_cursor")
        if not cursor: break
    return out

def rows_from_pages(cli, dbid):
    meta = cli.databases.retrieve(dbid)
    props = meta.get("properties",{})
    title_key = find_title_prop(props) or "Name"
    pages = fetch_all(cli, dbid)
    rows=[]
    for p in pages:
        pr = p.get("properties",{})
        def get_title():
            t = pr.get(title_key, {})
            return "".join(tt.get("plain_text","") for tt in t.get("title",[])).strip()
        def get_rich(name):
            if name in pr: return text_from_rich(pr[name])
            return ""
        def get_url(name):
            if name in pr: return pr[name].get("url") or ""
            return ""
        def get_date(name):
            if name in pr and pr[name].get("date"):
                return pr[name]["date"].get("start") or ""
            return ""
        row = {
            "Title": get_title(),
            "Company": get_rich("Company"),
            "Role": get_rich("Role"),
            "URL": get_url("URL"),
            "Source": get_rich("Source"),
            "Date": get_date("Date"),
            "last_edited_time": p.get("last_edited_time",""),
            "id": p.get("id",""),
        }
        rows.append(row)
    return rows

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k,"") for k in FIELDS})

def write_ndjson(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")

def main():
    # Args: DB_ENV_KEY OUT_DIR BASENAME
    if len(sys.argv) < 4:
        sys.exit("Usage: export_db_to_files.py <DB_ENV_KEY> <OUT_DIR> <BASENAME>")
    db_env_key, out_dir, base = sys.argv[1:4]
    token = env("NOTION_TOKEN")
    dbid  = env(db_env_key)

    os.makedirs(out_dir, exist_ok=True)
    cli = Client(auth=token)
    rows = rows_from_pages(cli, dbid)

    csv_path  = os.path.join(out_dir, f"{base}.csv")
    ndj_path  = os.path.join(out_dir, f"{base}.ndjson")
    write_csv(csv_path, rows)
    write_ndjson(ndj_path, rows)
    print(f"[ok] Exported {len(rows)} rows -> {csv_path} and {ndj_path}")

if __name__=="__main__":
    main()
