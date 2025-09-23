#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv-applypilot/bin/activate
set -a; [ -f .env ] && . .env; set +a
mkdir -p logs
/usr/bin/flock -n logs/notion_sync.lock python3 scripts/notion_sync.py >> logs/notion_sync.log 2>&1 || true
# email linker only if Gmail creds present
if [[ -n "${GMAIL_USER:-}" && -n "${GMAIL_APP_PASSWORD:-}" ]]; then
  /usr/bin/flock -n logs/linker.lock python3 scripts/link_emails_to_notion.py >> logs/linker.log 2>&1 || true
fi
