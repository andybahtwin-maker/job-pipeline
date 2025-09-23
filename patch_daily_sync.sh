#!/usr/bin/env bash
set -euo pipefail

FILE="applypilot/daily_sync.sh"
[ -f "$FILE" ] || { echo "[!] $FILE not found"; exit 1; }

tmp="$(mktemp)"
added_lock=0
added_prep=0

awk -v added_lock="$added_lock" -v added_prep="$added_prep" '
  BEGIN {
    have_lock=0; have_prep=0
  }
  {
    line=$0
    if (line ~ /python3 "\$ROOT\/scripts\/lock_db_id.py"/) have_lock=1
    if (line ~ /python3 "\$ROOT\/scripts\/prep_new_jobs.py"/) have_prep=1
    lines[NR]=line
  }
  END {
    # Emit, injecting just before notion_sync.py
    for (i=1; i<=NR; i++) {
      print lines[i]
      if (lines[i] ~ /python3 "\$ROOT\/scripts\/notion_sync.py"/) {
        if (!have_lock) {
          print "python3 \"$ROOT/scripts/lock_db_id.py\""
        }
        if (!have_prep) {
          print "python3 \"$ROOT/scripts/prep_new_jobs.py\""
        }
      }
    }
  }
' "$FILE" > "$tmp"

# Only replace if content changed
if ! cmp -s "$FILE" "$tmp"; then
  cp "$FILE" "$FILE.bak.$(date +%s)"
  mv "$tmp" "$FILE"
  chmod +x "$FILE"
  echo "[ok] Patched $FILE (added missing steps)."
else
  rm -f "$tmp"
  echo "[ok] $FILE already had the steps; no change."
fi
