#!/usr/bin/env bash
set -euo pipefail

echo "=== Env/Config Notion ID audit ==="
files=$(ls -1 .env* 2>/dev/null || true)
files="$files $(git ls-files | grep -E '\.(ya?ml|toml|json|cfg|ini|py|sh)$' || true)"

echo "Files scanned:"
echo "$files" | tr ' ' '\n' | sed '/^$/d' | nl

echo
echo "— Keys that look like Notion config —"
grep -RInE 'NOTION|DATABASE_ID|DB_ID|NOTION_.*ID' $files 2>/dev/null || echo "(none)"

echo
echo "— Any 32-hex Notion-style IDs —"
grep -RInE '[a-f0-9]{32}' $files 2>/dev/null | sed -E 's/\x1b\[[0-9;]*m//g' || echo "(none)"
