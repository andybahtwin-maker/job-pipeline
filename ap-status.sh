#!/usr/bin/env bash
set -euo pipefail
echo "== service =="
systemctl --user status applypilot-daily.service --no-pager || true
echo
echo "== timer =="
systemctl --user list-timers applypilot-daily.timer --all --no-pager || true
