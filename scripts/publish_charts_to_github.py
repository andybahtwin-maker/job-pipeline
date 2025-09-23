#!/usr/bin/env python3
import os, sys, base64, json
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT   = Path(__file__).resolve().parents[1]
ENV    = ROOT / ".env"
OUTDIR = ROOT / "outputs" / "charts"
META   = ROOT / "outputs" / "chart_urls.json"

# --- force load env ---
load_dotenv(ENV, override=True)

TOKEN  = os.getenv("GITHUB_TOKEN")
REPO   = os.getenv("GITHUB_REPO")
BRANCH = os.getenv("GITHUB_BRANCH", "main")

if not TOKEN or not REPO:
    print("[i] No GitHub config; skipping chart publish.")
    META.write_text(json.dumps({"published": False, "urls": []}, indent=2))
    sys.exit(0)

session = requests.Session()
session.headers.update({
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
})

def put_file(path, content_bytes):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    r = session.get(url, params={"ref": BRANCH})
    sha = r.json().get("sha") if r.status_code == 200 else None
    payload = {
        "message": f"update {path}",
        "content": base64.b64encode(content_bytes).decode(),
        "branch": BRANCH,
    }
    if sha: payload["sha"] = sha
    r = session.put(url, json=payload)
    if r.status_code not in (200,201):
        print(f"[warn] Upload failed {r.status_code}: {r.text}")
        return None
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"

urls = []
OUTDIR.mkdir(parents=True, exist_ok=True)
for p in sorted(OUTDIR.glob("*.png")):
    dest = f"charts/{p.name}"
    url = put_file(dest, p.read_bytes())
    if url:
        urls.append(url)
        print(f"[ok] Published {p} -> {url}")

META.write_text(json.dumps({"published": bool(urls), "urls": urls}, indent=2))
print(f"[ok] Chart publish done ({len(urls)} urls).")
