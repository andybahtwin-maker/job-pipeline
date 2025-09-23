#!/usr/bin/env bash
set -euo pipefail
# Append this call in daily_sync.sh *before* prep_new_jobs.py if you want the extra belt & suspenders.

python3 - <<'PY'
import os, json, re, urllib.parse as up
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path("applypilot")
ENV  = ROOT / ".env"
CACHE= ROOT / "outputs" / "seen_cache.json"
load_dotenv(ENV, override=True)

def canon_url(raw):
    if not raw: return None
    try:
        u = up.urlsplit(raw.strip())
        scheme = (u.scheme or "https").lower()
        netloc = u.netloc.lower()
        if netloc.endswith(":80") and scheme == "http":  netloc = netloc[:-3]
        if netloc.endswith(":443") and scheme == "https": netloc = netloc[:-4]
        q = up.parse_qsl(u.query, keep_blank_values=False)
        q = [(k,v) for (k,v) in q if not k.lower().startswith("utm_") and k.lower() not in {"gclid","fbclid","cmpid"}]
        path = u.path.rstrip("/")
        return up.urlunsplit((scheme, netloc, path, up.urlencode(q, doseq=True), ""))
    except Exception:
        return raw.strip()

# Create cache file if missing
if not CACHE.exists():
    CACHE.write_text(json.dumps({"urls": [], "sigs": []}))
PY
