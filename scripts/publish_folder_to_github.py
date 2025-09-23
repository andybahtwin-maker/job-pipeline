#!/usr/bin/env python3
import os, json, base64, glob, sys, urllib.request, urllib.error, urllib.parse
from pathlib import Path

ROOT = Path.home() / "applypilot"
TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER_REPO = os.environ.get("GITHUB_REPO", "andybahtwin-maker/job-pipeline")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")
if not TOKEN: print("[!] GITHUB_TOKEN missing"); sys.exit(1)

owner, repo = OWNER_REPO.split("/", 1)
API = "https://api.github.com"
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

def req(method, path, payload=None):
    url = API + path
    data = None if payload is None else json.dumps(payload).encode()
    r = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(r) as resp:
        return json.load(resp)

def get_sha(path):
    q = urllib.parse.quote(path)
    try:
        res = req("GET", f"/repos/{owner}/{repo}/contents/{q}?ref={BRANCH}")
        return res.get("sha") if isinstance(res, dict) else None
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise

def put_file(path, bytes_data, message):
    payload = {"message": message,
               "content": base64.b64encode(bytes_data).decode(),
               "branch": BRANCH}
    sha = get_sha(path)
    if sha: payload["sha"] = sha
    req("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)

# publish master
master = ROOT / "data" / "master.csv"
if master.exists():
    put_file("archive/master.csv", master.read_bytes(), "update archive/master.csv")
    print("[ok] Pushed archive/master.csv")

# publish daily files
for f in sorted(glob.glob(str(ROOT / "data" / "archive" / "*.csv"))):
    name = os.path.basename(f)
    dst = f"archive/{name}"
    put_file(dst, Path(f).read_bytes(), f"update {dst}")
    print(f"[ok] Pushed {dst}")
