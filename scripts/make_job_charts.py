#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path.home() / "applypilot"
MASTER = ROOT / "data" / "master.csv"
TODAY = ROOT / "outputs" / "filtered_jobs.csv"
CHARTDIR = ROOT / "outputs" / "charts"
CHARTDIR.mkdir(parents=True, exist_ok=True)

if MASTER.exists():
    df = pd.read_csv(MASTER)
else:
    df = pd.read_csv(TODAY)

def bar(series, title, out, topn=10):
    s = series.fillna("").replace("","(unknown)").value_counts().head(topn)
    plt.figure(figsize=(8,6))
    s.plot(kind="bar")
    plt.title(title); plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(CHARTDIR / out); plt.close()

bar(df.get("company", pd.Series(dtype=str)),  "Top Companies", "top_companies.png")
bar(df.get("location", pd.Series(dtype=str)), "Top Locations", "top_locations.png")
bar(df.get("source", pd.Series(dtype=str)),   "Top Sources",   "top_sources.png")
print(f"[ok] Charts written to {CHARTDIR}")
