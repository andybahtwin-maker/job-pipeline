#!/usr/bin/env bash
set -euo pipefail
ENVFILE="$HOME/applypilot/.env"

# Strip out GitHub settings to stop upload attempts
grep -v '^GITHUB_' "$ENVFILE" > "$ENVFILE.tmp" || true
mv "$ENVFILE.tmp" "$ENVFILE"

echo "[ok] GitHub integration disabled. Sync will only push to Notion."
echo "[i] Next run will skip chart uploads to GitHub."
