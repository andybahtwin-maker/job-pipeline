#!/usr/bin/env bash
set -euo pipefail
VENV="$HOME/.venvs/applypilot"
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate"
python3 - <<'PY'
import sys
print("[ok] python:", sys.version)
try:
    import httpx, bs4, lxml, tldextract, readability
    print("[ok] deps: httpx, bs4, lxml, tldextract, readability")
except Exception as e:
    print("[err] deps:", e); raise
try:
    import pipeline, pipeline.enrichment.vibe as vibe
    print("[ok] package import:", pipeline.__name__, vibe.__name__)
except Exception as e:
    print("[err] package:", e); raise
PY
