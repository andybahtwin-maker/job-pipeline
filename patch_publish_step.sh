#!/usr/bin/env bash
set -euo pipefail
F="applypilot/daily_sync.sh"
tmp="$(mktemp)"
awk '{print} /make_job_charts.py/ {print "python3 \"$ROOT/scripts/publish_charts_to_github.py\""}' "$F" > "$tmp"
mv "$tmp" "$F"
chmod +x "$F"
echo "[ok] Added publish step."
