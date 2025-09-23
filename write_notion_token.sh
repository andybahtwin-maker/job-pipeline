#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)/applypilot"
ENVFILE="$ROOT/.env"
mkdir -p "$ROOT"

echo "This will securely store your NOTION_TOKEN into: $ENVFILE"
read -rsp "Paste your NOTION_TOKEN now (input hidden) and press Enter: " TOKEN
echo
if [[ -z "$TOKEN" ]]; then
  echo "[!] No token entered. Aborting." >&2
  exit 1
fi

# Ensure .env exists
touch "$ENVFILE"

# Replace existing NOTION_TOKEN or append
if grep -q '^NOTION_TOKEN=' "$ENVFILE" 2>/dev/null; then
  awk -v tok="NOTION_TOKEN=$TOKEN" 'BEGIN{found=0} 
    /^NOTION_TOKEN=/{print tok; found=1; next} 
    {print} 
    END{if(!found) print tok}' "$ENVFILE" > "$ENVFILE.tmp" && mv "$ENVFILE.tmp" "$ENVFILE"
else
  echo "NOTION_TOKEN=$TOKEN" >> "$ENVFILE"
fi

chmod 600 "$ENVFILE"
echo "[i] Token written to $ENVFILE (owner-only permissions)."

# Run the creds checker if available
CHECK_SCRIPT="$ROOT/scripts/check_notion_creds.py"
if [[ -x "$CHECK_SCRIPT" ]]; then
  echo "[i] Running credential check..."
  if [[ -f "$ROOT/.venv-applypilot/bin/activate" ]]; then
    # shellcheck disable=SC1090
    . "$ROOT/.venv-applypilot/bin/activate"
  fi
  python3 "$CHECK_SCRIPT" || {
    echo "[warn] Credential check failed. Double-check token + that the integration has page access."
    exit 1
  }
else
  echo "[i] No check script found at $CHECK_SCRIPT. Run fix_env_and_check.sh if needed."
fi

echo "[ok] Done. You can now run notion_sync.py."
