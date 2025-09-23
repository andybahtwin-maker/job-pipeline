#!/usr/bin/env bash
set -euo pipefail

ROOT=~/applypilot
ENVFILE="$ROOT/.env"

echo "[i] Ensuring repo exists..."
if ! gh repo view andybahtwin-maker/job-pipeline >/dev/null 2>&1; then
  gh repo create andybahtwin-maker/job-pipeline --public --confirm
fi

echo "[i] Ensuring .env has GitHub vars..."
grep -q '^GITHUB_REPO=' "$ENVFILE" || cat >> "$ENVFILE" <<'EOF'
# --- GitHub for chart publishing ---
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=andybahtwin-maker/job-pipeline
GITHUB_BRANCH=main
EOF

echo "[i] Patching run_full_sync.sh to skip old Step 2..."
awk '
  /Step 2: publish charts to GitHub/ {skip=1; print "# [skipped old Step 2]"; next}
  /Step 3:/ {skip=0}
  skip==1 {next}
  {print}
' "$ROOT/run_full_sync.sh" > "$ROOT/run_full_sync.sh.new"

mv "$ROOT/run_full_sync.sh.new" "$ROOT/run_full_sync.sh"
chmod +x "$ROOT/run_full_sync.sh"

echo "[done] GitHub publishing fixed. Run again with:"
echo "   $ROOT/run_full_sync.sh"
