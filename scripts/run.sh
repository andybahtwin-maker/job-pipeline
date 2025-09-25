#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# activate venv if you have one
if [ -f "$HOME/.venvs/jobpipe/bin/activate" ]; then
  source "$HOME/.venvs/jobpipe/bin/activate"
fi
export PYTHONPATH="$(pwd)"
exec python run_pipeline.py
