#!/usr/bin/env python3
import pandas as pd, json, datetime as dt
from pathlib import Path

ROOT   = Path.home() / "applypilot"
MASTER = ROOT / "data" / "master.csv"
AI     = ROOT / "ai"
AI.mkdir(parents=True, exist_ok=True)

if not MASTER.exists():
    print("[!] master.csv missing"); raise SystemExit(1)

df = pd.read_csv(MASTER, dtype=str).fillna("")
def dparse(s):
    try: return dt.date.fromisoformat(s)
    except: return None
df["date_collected_dt"] = df["date_collected"].map(dparse)

today = dt.date.today()
last7  = today - dt.timedelta(days=7)
last30 = today - dt.timedelta(days=30)

def subset_start(start): return df[df["date_collected_dt"].ge(start)]
def top(series, n=15):   return series.value_counts().head(n).reset_index().values.tolist()

def rows_to_list(s, limit=None):
    cols = ["date_collected","date_posted","title","company","location","source","url"]
    s = s[cols]
    if limit: s = s.head(limit)
    return [dict(zip(cols, [str(r.get(c,"")) for c in cols])) for _,r in s.iterrows()]

# index (summary)
idx = {
  "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
  "totals": {
    "all": int(len(df)),
    "last_30d": int(len(subset_start(last30))),
    "last_7d": int(len(subset_start(last7))),
    "today": int(len(subset_start(today)))
  },
  "by_day": subset_start(last30).groupby("date_collected").size().reset_index(name="count").sort_values("date_collected").to_dict(orient="records"),
  "top_30d": {
    "companies": top(subset_start(last30)["company"]),
    "locations": top(subset_start(last30)["location"]),
    "sources":   top(subset_start(last30)["source"])
  },
  "latest_100": rows_to_list(df.sort_values(["date_collected_dt"], ascending=False), limit=100)
}

# today / last_30d rows
(Path(AI / "index.json")).write_text(json.dumps(idx, indent=2))
(Path(AI / "today.json")).write_text(json.dumps(rows_to_list(subset_start(today)), indent=2))
(Path(AI / "last_30d.json")).write_text(json.dumps(rows_to_list(subset_start(last30)), indent=2))

# --- all-time summary + latest rows (for forever tracking without huge files) ---
all_time = {
  "generated_at": idx["generated_at"],
  "total": int(len(df)),
  "top_all_time": {
    "companies": top(df["company"]),
    "locations": top(df["location"]),
    "sources":   top(df["source"])
  },
  "latest_1000": rows_to_list(df.sort_values(["date_collected_dt"], ascending=False), limit=1000)
}
(Path(AI / "all_time.json")).write_text(json.dumps(all_time, indent=2))

print("[ok] Wrote ai/index.json, ai/today.json, ai/last_30d.json, ai/all_time.json")
