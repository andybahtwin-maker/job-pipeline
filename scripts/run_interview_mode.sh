#!/usr/bin/env bash
set -euo pipefail
. .venv/bin/activate 2>/dev/null || true
export DEMO_MODE=1 DEMO_PRESET="coinbase_btc_binance" AUTO_OPEN_TAB="arbitrage"
echo "[i] Interview Mode"
[ -f run_app.sh ] && bash run_app.sh || python app.py
