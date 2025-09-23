#!/usr/bin/env python3
import pandas as pd, hashlib, os, datetime as dt
from pathlib import Path

ROOT = Path.home() / "applypilot"
SRC  = ROOT / "outputs" / "filtered_jobs.csv"       # today's pipeline output
ARCH = ROOT / "data" / "archive"                    # per-day dumps
MASTER = ROOT / "data" / "master.csv"               # full history

ARCH.mkdir(parents=True, exist_ok=True)

def mk_key(row):
    url = str(row.get("url","")).strip().lower()
    title = str(row.get("title","")).strip().lower()
    company = str(row.get("company","")).strip().lower()
    loc = str(row.get("location","")).strip().lower()
    source = str(row.get("source","")).strip().lower()
    base = "|".join([url, title, company, loc, source])
    return hashlib.sha1(base.encode()).hexdigest()

if not SRC.exists():
    print(f"[!] Missing {SRC} — run your scraper first.")
    raise SystemExit(1)

today = dt.date.today().isoformat()
df = pd.read_csv(SRC)

# normalize expected columns
for c in ["title","company","location","source","url","date_posted"]:
    if c not in df.columns: df[c] = ""

df["date_collected"] = today
df["_key"] = df.apply(mk_key, axis=1)

# load master if exists
if MASTER.exists():
    master = pd.read_csv(MASTER, dtype=str)
    if "_key" not in master.columns:
        master["_key"] = master.apply(mk_key, axis=1)
else:
    master = pd.DataFrame(columns=df.columns)

existing_keys = set(master["_key"]) if not master.empty else set()
new = df[~df["_key"].isin(existing_keys)].copy()

# write per-day dump only for NEW rows
dayfile = ARCH / f"{today}.csv"
if not new.empty:
    # keep stable column order
    cols = ["date_collected","date_posted","title","company","location","source","url"]
    new[cols].to_csv(dayfile, index=False)
    master = pd.concat([master, new], ignore_index=True)
    master = master.drop_duplicates("_key")
    # write master without the technical key
    out_cols = ["date_collected","date_posted","title","company","location","source","url"]
    master[out_cols].to_csv(MASTER, index=False)
    print(f"[ok] Archived {len(new)} new jobs → {dayfile}")
    print(f"[ok] Master now has {len(master)} total jobs → {MASTER}")
else:
    print("[ok] No new jobs today; archive unchanged.")
