#!/usr/bin/env bash
set -euo pipefail
cd "${1:-$PWD}"

# Known ApplyPilot DB IDs
known_ids=(
  2779c46ac8fd810aaca3d8fbe1bb59db  # All Jobs
  2779c46ac8fd81748a6ac1f4fd464475  # Last 30 Days
  2779c46ac8fd81f7a02de166acf82edc  # Daily
  2779c46ac8fd81db8b75fe9d792e78b0  # Monthly
  2779c46ac8fd814093f8ecc3f60a2938  # Job Postings A
  2789c46ac8fd81818e6af1917fd81997  # Job Postings B
)

# Build regex set for quick lookup
known_set="^($(printf "%s|" "${known_ids[@]}" | sed 's/|$//'))$"

echo "=== Scanning for Notion database_id usages under: $PWD ==="
echo

# Look for 32-hex IDs (Notion DB/page ids without dashes) in likely code/config files
grep -RInE --exclude-dir='{.git,venv,.venv,__pycache__}' \
  --include='*.{py,ts,js,json,toml,yaml,yml,env,sh,md}' \
  '([a-f0-9]{32})' . | sed -E 's/\x1b\[[0-9;]*m//g' | tee /tmp/notion_id_hits.txt

echo
echo "=== Candidate IDs (unique) ==="
awk -F'([[:space:]:(){}"]+)' '
  {
    for(i=1;i<=NF;i++){
      if (match($i,/^[a-f0-9]{32}$/)) { print substr($i,RSTART,RLENGTH) }
    }
  }' /tmp/notion_id_hits.txt | sort -u | tee /tmp/notion_ids_unique.txt

echo
echo "=== Unknown vs Known ==="
unknown=0
while read -r id; do
  if [[ ! "$id" =~ $known_set ]]; then
    echo "⚠️  Unknown/Non-ApplyPilot ID: $id"
    ((unknown++)) || true
  fi
done < /tmp/notion_ids_unique.txt

if [ "$unknown" -eq 0 ]; then
  echo "✅ All referenced IDs match your ApplyPilot set."
else
  echo "↑ These IDs are where your exporter is likely writing."
fi
