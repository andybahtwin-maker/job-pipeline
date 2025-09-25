#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
VENV="$HOME/.venvs/applypilot"
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate" || true
cd "$ROOT"
set -a; source .env 2>/dev/null || true; source .env.applypilot 2>/dev/null || true; set +a

echo "[run] push -> DB (Job Postings B)"
scripts/run_with_env.sh python scripts/push_jobs_to_notion.py

echo "[diag] retrieve vs query:"
scripts/run_with_env.sh python scripts/notion_db_diag.py || true

echo "[run] mirror B -> All Jobs (no dupes)"
scripts/run_with_env.sh python scripts/mirror_b_to_alljobs.py || true

echo "[run] update charts/summary"
scripts/run_with_env.sh python scripts/update_notion_summary.py || true

echo "[run] counts"
scripts/run_with_env.sh python scripts/check_notion_env_based.py || true

echo "[snap] export CSV + NDJSON"
scripts/snapshot_jobs.sh

echo "[publish] commit + push"
scripts/git_push_data.sh

echo "[done]"
