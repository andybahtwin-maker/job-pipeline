#!/usr/bin/env python3
import base64, json, os, time, glob, sys
import urllib.request, urllib.error, urllib.parse

OWNER_REPO = os.environ.get("GITHUB_REPO", "andybahtwin-maker/job-pipeline")
BRANCH_MAIN = os.environ.get("GITHUB_BRANCH", "main")
TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    print("[!] GITHUB_TOKEN missing"); sys.exit(1)

owner, repo = OWNER_REPO.split("/", 1)
API = "https://api.github.com"
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

def api_req(method, path, payload=None, raw=False):
    url = API + path
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req) as r:
        return r.read() if raw else json.load(r)

def api_get(path):
    try: return api_req("GET", path)
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise

def api_post(path, payload): return api_req("POST", path, payload)
def api_put(path, payload):  return api_req("PUT",  path, payload)

def ensure_branch(branch="gh-pages", from_branch=BRANCH_MAIN):
    ref = api_get(f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if ref: return
    src = api_get(f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}")
    if not src: raise RuntimeError(f"Source branch {from_branch} not found")
    sha = src["object"]["sha"]
    api_post(f"/repos/{owner}/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    print(f"[ok] Created branch {branch} from {from_branch}")

def get_existing_sha(branch, path):
    q = urllib.parse.quote(path)
    res = api_get(f"/repos/{owner}/{repo}/contents/{q}?ref={branch}")
    if res and isinstance(res, dict) and "sha" in res: return res["sha"]
    return None

def put_file(branch, path, bytes_data, message):
    content_b64 = base64.b64encode(bytes_data).decode()
    payload = {"message": message, "content": content_b64, "branch": branch}
    sha = get_existing_sha(branch, path)
    if sha: payload["sha"] = sha
    api_put(f"/repos/{owner}/{repo}/contents/{path}", payload)

ROOT = os.path.expanduser("~/applypilot")
CHARTDIR = os.path.join(ROOT, "outputs", "charts")
files = sorted(glob.glob(os.path.join(CHARTDIR, "*.png")))
if not files:
    print("[!] No charts to mirror"); sys.exit(0)

ensure_branch("gh-pages", BRANCH_MAIN)

ts = int(time.time())
for f in files:
    with open(f, "rb") as fh:
        put_file("gh-pages", f"charts/{os.path.basename(f)}", fh.read(),
                 f"publish {os.path.basename(f)} to gh-pages")

index = """<!doctype html><meta charset="utf-8"><title>job-pipeline charts</title>
<h1>ApplyPilot Charts</h1>
<ul>
%s
</ul>
""" % "\n".join(
    f'<li><a href="charts/{os.path.basename(f)}">{os.path.basename(f)}</a></li>' for f in files
)
put_file("gh-pages", "index.html", index.encode(), "publish index.html to gh-pages")

pages_base = f"https://{owner}.github.io/{repo}/charts"
urls = [f"{pages_base}/{os.path.basename(f)}?v={ts}" for f in files]
out_json = os.path.join(ROOT, "outputs", "chart_urls.json")
with open(out_json, "w") as o: json.dump(urls, o, indent=2)
print("[ok] Mirrored to GitHub Pages and wrote", out_json)
