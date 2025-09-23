#!/usr/bin/env bash
set -euo pipefail
. applypilot/.venv-applypilot/bin/activate
python -m pip install --quiet --upgrade requests
echo "[ok] Installed requests into .venv-applypilot"
