#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv || true
. .venv/bin/activate
pip install --upgrade pip
[ -f requirements.txt ] && pip install -r requirements.txt
bash scripts/enable_demo_mode.sh
[ -f run_app.sh ] && bash run_app.sh || python app.py
