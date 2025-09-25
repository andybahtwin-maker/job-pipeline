#!/usr/bin/env python3
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client
import pandas as pd
import matplotlib.pyplot as plt

# Resolve repo root and env path
REPO = Path(__file__).resolve().parents[1] if (Path(__file__).name == "make_job_charts.py") else Path.cwd()
ENV = REPO / "applypilot" / ".env"
if not ENV.exists():
    sys.exit(f"[!] Expected env at {ENV}, but it does not exist.")

load_dotenv(dotenv_path=str(ENV), override=True)

tok = os.getenv("NOTION_TOKEN")
pid = os.getenv("NOTION_PAGE_ID")
dbid = os.getenv("NOTION_DATABASE_ID")  # optional; script can self-heal if missing

if not tok:
    sys.exit("[!] NOTION_TOKEN missing after loading applypilot/.env")

cli = Client(auth=tok)

# Ensure we can reach the page; if DB id missing, regenerate it via a helper
try:
    cli.pages.retrieve(page_id=pid)
except Exception as e:
    sys.exit(f"[!] Cannot access NOTION_PAGE_ID={pid}: {e}")

# === Example chart generation below ===
# Expect a CSV merged/exported by your sync; fall back to Downloads batches if present.
csv_candidates = [
    REPO / "applypilot" / "outputs" / "filtered_jobs.csv",
    Path.home() / "Downloads" / "jobs_batch_1.csv",
    Path.home() / "Downloads" / "se_jobs_batch_1.csv",
]

df = None
for p in csv_candidates:
    if p.exists() and p.stat().st_size > 0:
        try:
            tmp = pd.read_csv(p)
            if not tmp.empty:
                df = tmp
                print(f"[ok] Using data from {p} ({len(tmp)} rows)")
                break
        except Exception:
            pass

if df is None:
    sys.exit("[!] No non-empty CSV found for charting. Make sure the sync produced rows.")

# Minimal example: role counts by source/company if present
outdir = REPO / "applypilot" / "outputs"
outdir.mkdir(parents=True, exist_ok=True)

def save_bar(series, title, fname):
    plt.figure()
    series.sort_values(ascending=False).head(15).plot(kind="bar")
    plt.title(title)
    plt.tight_layout()
    (outdir / fname).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outdir / fname, dpi=150)
    plt.close()
    print(f"[ok] Wrote {outdir / fname}")

for col, title, fname in [
    ("source", "Top Sources", "charts/top_sources.png"),
    ("company", "Top Companies", "charts/top_companies.png"),
    ("location", "Top Locations", "charts/top_locations.png"),
]:
    if col in df.columns:
        save_bar(df[col].value_counts(), title, fname)

# Summary CSV for quick drop-in to Notion
summary = {
    "rows": len(df),
    "unique_companies": df["company"].nunique() if "company" in df.columns else None,
    "unique_sources": df["source"].nunique() if "source" in df.columns else None,
}
pd.DataFrame([summary]).to_csv(outdir / "summary.csv", index=False)
print(f"[ok] Summary: {summary}")
print("[done] Charts + summary ready under applypilot/outputs/")
