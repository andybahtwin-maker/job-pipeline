#!/usr/bin/env bash
set -euo pipefail
lastlog="$(ls -1t ~/applypilot/logs/daily_sync-*.txt 2>/dev/null | head -n1 || true)"
if [ -z "$lastlog" ]; then
  echo "[!] No logs yet in ~/applypilot/logs/"; exit 1
fi
echo "[i] Tailing: $lastlog"
tail -n 200 -f "$lastlog"
