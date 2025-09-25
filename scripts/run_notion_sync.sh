#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv-applypilot/bin/activate
# export env vars
set -a; [ -f .env ] && . .env; set +a
# ensure logs dir
mkdir -p logs
# do the sync, logging output
python3 scripts/notion_sync.py >> logs/notion_sync.log 2>&1
