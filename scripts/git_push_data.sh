#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
cd "$ROOT"

git add -A data || true
if ! git diff --cached --quiet; then
  msg="[data] snapshot $(date -u +'%F %T UTC')"
  git commit -m "$msg"
  git push
  echo "[ok] Pushed snapshots to remote"
else
  echo "[info] No snapshot changes to push"
fi
