#!/usr/bin/env bash
set -euo pipefail
export DEMO_MODE=1
mkdir -p demo_data
cat > demo_data/sample_ticks.csv <<'CSV'
timestamp,exchange,product,price,fee_bps
2025-08-01T12:00:00Z,coinbase,BTC-USD,64000,10
2025-08-01T12:00:01Z,binance,BTC-USDT,63920,8
CSV
cat > demo_data/fees_config.json <<'JSON'
{"coinbase": {"taker_bps": 10}, "binance": {"taker_bps": 8}}
JSON
echo "[✓] Demo mode enabled"
