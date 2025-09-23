#!/usr/bin/env bash
set -euo pipefail
systemctl --user start applypilot-daily.service
sleep 1
journalctl --user -u applypilot-daily.service -n 200 --no-pager || true
echo
echo "[i] Also see files under: ~/applypilot/logs/"
