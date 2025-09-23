#!/usr/bin/env python3
import os, glob, base64, json, sys, urllib.request, urllib.error, urllib.parse, time

OWNER_REPO = os.environ.get("GITHUB_REPO", "andybahtwin-maker/job-pipeline")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")
TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    print("[!] GITHUB_TOKEN missing"); sys.exit(1)

owner, repo = OWNER_REPO.split("/", 1)
API = "https://api.github.com"
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

def req(method, path, payload=None):
    url = API + path
    data = None if payload is None else json.dumps(payload).encode()
    r = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise

def list_dir_sha(path):
    q = urllib.parse.quote(path)
    res = req("GET", f"/repos/{owner}/{repo}/contents/{q}?ref={BRANCH}")
    if isinstance(res, list): return {i["name"]: i.get("sha") for i in res}
    if isinstance(res, dict) and res.get("sha"): return {res["name"]: res["sha"]}
    return {}

def put_file(path, bytes_data, message, sha=None):
    payload = {"message": message, "content": base64.b64encode(bytes_data).decode(), "branch": BRANCH}
    if sha: payload["sha"] = sha
    return req("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)

def url_ok(u):
    try:
        req_ = urllib.request.Request(u, headers={"User-Agent":"curl/8"})
        with urllib.request.urlopen(req_, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception:
        return False

ROOT = os.path.expanduser("~/applypilot")
CHARTDIR = os.path.join(ROOT, "outputs", "charts")
files = sorted(glob.glob(os.path.join(CHARTDIR, "*.png")))
if not files: print("[!] No local charts"); sys.exit(0)

remote = list_dir_sha("charts") or {}
for f in files:
    name = os.path.basename(f)
    with open(f, "rb") as fh:
        put_file(f"charts/{name}", fh.read(), f"ensure charts/{name} on {BRANCH}", sha=remote.get(name))
    print(f"[ok] ensured charts/{name} in repo")

ts = int(time.time())
urls = []
for f in files:
    name = os.path.basename(f)
    candidates = [
        f"https://raw.githubusercontent.com/{OWNER_REPO}/{BRANCH}/charts/{name}?v={ts}",
        f"https://github.com/{owner}/{repo}/raw/{BRANCH}/charts/{name}?v={ts}",
        f"https://cdn.jsdelivr.net/gh/{OWNER_REPO}@{BRANCH}/charts/{name}?v={ts}",
    ]
    chosen = None
    for u in candidates:
        if url_ok(u.split('?')[0]): chosen = u; break
    if not chosen: chosen = candidates[0]
    urls.append(chosen)

out = os.path.join(ROOT, "outputs", "chart_urls.json")
with open(out, "w") as o: json.dump(urls, o, indent=2)
print("[ok] Wrote public URLs to", out)
