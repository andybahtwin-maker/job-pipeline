#!/usr/bin/env bash
set -euo pipefail

ROOT=~/applypilot
ENVFILE="$ROOT/.env"
PUBLISH="$ROOT/scripts/publish_charts_to_github.py"
UPDATE="$ROOT/scripts/update_notion_summary.py"
CHARTS="$ROOT/outputs/charts"
REPO="${GITHUB_REPO:-andybahtwin-maker/job-pipeline}"
BRANCH="${GITHUB_BRANCH:-main}"

mkdir -p "$CHARTS"

# 0) Sanity: token + env
if ! grep -q '^GITHUB_REPO=' "$ENVFILE" 2>/dev/null; then echo "GITHUB_REPO=$REPO" >> "$ENVFILE"; fi
if ! grep -q '^GITHUB_BRANCH=' "$ENVFILE" 2>/dev/null; then echo "GITHUB_BRANCH=$BRANCH" >> "$ENVFILE"; fi

# ensure GITHUB_TOKEN present
if ! grep -q '^GITHUB_TOKEN=' "$ENVFILE" 2>/dev/null; then
  echo "[!] GITHUB_TOKEN missing in $ENVFILE"
  echo "    Add: GITHUB_TOKEN=<your fine-grained PAT with repo Contents: Read/Write>"
  exit 1
fi
set -a; . "$ENVFILE"; set +a

# 1) Make sure repo exists and is initialized (has a default branch)
echo "[i] Ensuring repo $REPO exists and has a first commit..."
if ! gh repo view "$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" --public --confirm --add-readme
else
  # if repo exists but is empty (no default branch), add README
  if ! gh api "repos/$REPO/branches/$BRANCH" >/dev/null 2>&1; then
    gh repo edit "$REPO" --default-branch "$BRANCH" || true
    gh api -X PUT \
      -H "Authorization: token $GITHUB_TOKEN" \
      -F message='init README' \
      -F content="$(printf '# job-pipeline\n\nCharts for ApplyPilot.\n' | base64 -w0)" \
      "repos/$REPO/contents/README.md" >/dev/null || true
  fi
fi

# 2) Regenerate charts (local)
if [ -x "$ROOT/scripts/make_job_charts.py" ]; then
  python3 "$ROOT/scripts/make_job_charts.py" || true
fi

# 3) Publish charts to GitHub (Contents API with PAT)
if [ -x "$PUBLISH" ]; then
  python3 "$PUBLISH" || true
else
  echo "[warn] Missing $PUBLISH"
fi

# 4) Update Notion summary (will embed images iff chart_urls.json has urls)
python3 "$UPDATE"

echo "[done] GitHub fixed, charts published (if any), Notion updated."
