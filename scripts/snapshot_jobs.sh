#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
VENV="$HOME/.venvs/applypilot"
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate" || true
cd "$ROOT"
set -a; source .env 2>/dev/null || true; source .env.applypilot 2>/dev/null || true; set +a

date_dir="data/$(date -u +%F)"
mkdir -p "$date_dir"

echo "[snap] Export Job Postings B"
scripts/run_with_env.sh python scripts/export_db_to_files.py NOTION_DB_JOB_POSTINGS_B "$date_dir" jobs_b || echo "[warn] B export failed (check connection/share)"

echo "[snap] Export All Jobs"
scripts/run_with_env.sh python scripts/export_db_to_files.py NOTION_DB_ALL_JOBS "$date_dir" all_jobs || echo "[warn] All Jobs export failed (not shared yet?)"

echo "[done] Snapshots in $date_dir"
