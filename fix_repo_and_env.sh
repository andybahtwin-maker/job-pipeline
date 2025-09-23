#!/usr/bin/env bash
set -euo pipefail

ROOT=~/applypilot
ENVFILE="$ROOT/.env"

echo "[i] Making sure repo exists..."
if ! gh repo view andybahtwin-maker/job-pipeline >/dev/null 2>&1; then
  gh repo create andybahtwin-maker/job-pipeline --public --confirm
fi

echo "[i] Cloning repo locally if missing..."
mkdir -p ~/projects
cd ~/projects
if [ ! -d job-pipeline ]; then
  gh repo clone andybahtwin-maker/job-pipeline
fi

echo "[i] Ensuring charts/ folder is tracked..."
cd job-pipeline
mkdir -p charts
touch charts/.gitkeep
git add charts/.gitkeep || true
git commit -m "init charts folder" || true
git push origin main || true

echo "[i] Patching .env with GitHub values..."
grep -q '^GITHUB_TOKEN=' "$ENVFILE" || echo "GITHUB_TOKEN=github_pat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" >> "$ENVFILE"
grep -q '^GITHUB_REPO=' "$ENVFILE"   || echo "GITHUB_REPO=andybahtwin-maker/job-pipeline" >> "$ENVFILE"
grep -q '^GITHUB_BRANCH=' "$ENVFILE" || echo "GITHUB_BRANCH=main" >> "$ENVFILE"

echo "[done] Repo + .env fixed. Now run:"
echo "   $ROOT/run_full_sync.sh"
