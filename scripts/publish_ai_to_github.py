#!/usr/bin/env python3
import os, json, base64, glob, urllib.request, urllib.error, sys
from pathlib import Path

ROOT = Path.home() / "applypilot"
AI   = ROOT / "ai"
TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER_REPO = os.environ.get("GITHUB_REPO","andybahtwin-maker/job-pipeline")
BRANCH = os.environ.get("GITHUB_BRANCH","main")
if not TOKEN: print("[!] GITHUB_TOKEN missing"); sys.exit(1)

owner, repo = OWNER_REPO.split("/",1)
API="https://api.github.com"
HDR={"Authorization":f"token {TOKEN}","Accept":"application/vnd.github+json"}

def req(method, path, payload=None):
    url=API+path; data=None if payload is None else json.dumps(payload).encode()
    r=urllib.request.Request(url, data=data, headers=HDR, method=method)
    with urllib.request.urlopen(r) as resp: return json.load(resp)

def get_sha(path):
    try: return req("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={BRANCH}").get("sha")
    except urllib.error.HTTPError as e:
        if e.code==404: return None
        raise

for f in glob.glob(str(AI / "*.json")):
    name=os.path.basename(f); path=f"ai/{name}"
    payload={"message":f"update {path}","content":base64.b64encode(Path(f).read_bytes()).decode(),"branch":BRANCH}
    sha=get_sha(path); 
    if sha: payload["sha"]=sha
    req("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)
    print(f"[ok] Pushed {path}")
