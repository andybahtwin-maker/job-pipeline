#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(pwd)}"
OUT="${2:-.env}"

python3 - "$ROOT" "$OUT" <<'PY'
import sys, re, os
from pathlib import Path

root = Path(sys.argv[1]).resolve()
out_path = Path(sys.argv[2]).resolve()

def parse_env(text):
    out = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('export '):
            s = s[len('export '):]
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)=(.*)', s)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if (len(v) >= 2) and ((v[0]==v[-1]=='"') or (v[0]==v[-1]=="'")):
            v = v[1:-1]
        out[k] = v
    return out

def is_placeholder(val: str) -> bool:
    l = val.lower()
    return any(re.match(p, l) for p in [
        r"^replace", r"^your", r"^changeme", r"\$\{notion_token", r"\$\{github_token"
    ])

# gather .env* files
candidates = []
for p in root.rglob("*"):
    name = p.name.lower()
    if p.is_file() and (
        name == ".env" or
        name.startswith(".env") or
        name.endswith(".env") or
        ".env." in name or
        name.endswith(".env.example") or
        name.endswith(".env.applypilot") or
        ".env.before" in name or
        (p.parent.name == ".env.d")
    ):
        candidates.append(p)

merged = {}
src = {}
for f in candidates:
    try:
        text = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    kv = parse_env(text)
    for k, v in kv.items():
        if k not in merged:
            merged[k] = v; src[k] = str(f)
        else:
            cur = merged[k]
            if is_placeholder(cur) and not is_placeholder(v):
                merged[k] = v; src[k] = str(f)
            elif not is_placeholder(v) and len(v) > len(cur):
                merged[k] = v; src[k] = str(f)

lines = ["# Consolidated from local .env files under: "+str(root), ""]
for k in sorted(merged.keys()):
    v = merged[k]
    # quote if needed
    if any(ch.isspace() for ch in v) or any(ch in v for ch in ['#',';','"',"'",'`']):
        v = '"' + v.replace('"','\\"') + '"'
    lines.append(f"# from {src[k]}")
    lines.append(f"{k}={v}")
    lines.append("")

out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"[ok] wrote {out_path}")
PY
