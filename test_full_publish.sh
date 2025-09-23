#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/applypilot"
VENV="$ROOT/.venv-applypilot"
. "$VENV/bin/activate"

echo "[i] Step 1: regenerate charts"
python3 "$ROOT/scripts/make_job_charts.py" || python3 scripts/make_job_charts.py

echo "[i] Step 2: publish charts to GitHub"
python3 "$ROOT/scripts/publish_charts_to_github.py"

echo "[i] Chart URLs:"
cat "$ROOT/outputs/chart_urls.json" || echo "[!] no chart_urls.json found"

echo "[i] Step 3: update Notion summary"
python3 "$ROOT/scripts/update_notion_summary.py"

echo "[done] End-to-end test complete."
