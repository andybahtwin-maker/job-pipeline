#!/usr/bin/env bash
set -euo pipefail

ROOT=~/applypilot
ENVFILE="$ROOT/.env"
CHARTDIR="$ROOT/outputs/charts"

ARCHIVE="$ROOT/scripts/archive_jobs.py"
MAKECHARTS="$ROOT/scripts/make_job_charts.py"
PUBLISH_RAW="$ROOT/scripts/publish_charts_to_github.py"
PUBLISH_ARCHIVE="$ROOT/scripts/publish_folder_to_github.py"
ENSURE_URLS="$ROOT/scripts/ensure_charts_public_and_urls.py"
EXPORT_AI="$ROOT/scripts/export_for_ai.py"
PUBLISH_AI="$ROOT/scripts/publish_ai_to_github.py"
NOTION="$ROOT/scripts/update_notion_summary.py"

mkdir -p "$CHARTDIR"

echo "[i] Step 0: load env"
[ -f "$ENVFILE" ] || { echo "[!] $ENVFILE missing"; exit 1; }
set -a; . "$ENVFILE"; set +a
: "${GITHUB_REPO:=andybahtwin-maker/job-pipeline}"
: "${GITHUB_BRANCH:=main}"
export GITHUB_REPO GITHUB_BRANCH

echo "[i] Step 1: archive today's new jobs"
python3 "$ARCHIVE" || true

echo "[i] Step 2: (re)generate whole-archive charts"
python3 "$MAKECHARTS"

echo "[i] Step 3: publish charts to repo"
[ -f "$PUBLISH_RAW" ] && python3 "$PUBLISH_RAW" || echo "[warn] $PUBLISH_RAW missing; skipping"

echo "[i] Step 4: publish archive (master + daily CSVs)"
python3 "$PUBLISH_ARCHIVE"

echo "[i] Step 5: export AI JSON + publish"
python3 "$EXPORT_AI"
python3 "$PUBLISH_AI"

echo "[i] Step 6: write resilient public URLs and update Notion"
python3 "$ENSURE_URLS"
python3 "$NOTION"

echo "[done] Daily sync complete."
