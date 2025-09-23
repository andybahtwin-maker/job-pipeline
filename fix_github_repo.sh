#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in ~/projects
mkdir -p ~/projects
cd ~/projects

# Check if repo exists locally
if [ ! -d job-pipeline ]; then
  echo "[i] Cloning job-pipeline..."
  gh repo clone andybahtwin-maker/job-pipeline
fi

cd job-pipeline

# Ensure branch "main" exists
if ! git show-ref --verify --quiet refs/heads/main; then
  echo "[i] Creating main branch"
  git checkout -b main || git checkout master
  git branch -M main
  git push -u origin main
fi

echo "[ok] Repo is ready at ~/projects/job-pipeline on branch main"
