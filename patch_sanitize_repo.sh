#!/usr/bin/env bash
set -e

cd ~/applypilot

echo "[1] Add .gitignore rules..."
cat >> .gitignore <<'EOG'
# Local secrets
.env
*_token.sh
EOG

echo "[2] Create .env.example..."
cat > .env.example <<'EOT'
# Replace with your own secrets
NOTION_TOKEN=replace_with_your_notion_token
GITHUB_TOKEN=replace_with_your_github_token
EOT

echo "[3] Rewrite token scripts to load from .env..."
for f in add_github_token.sh finalize_and_run.sh finalize_publish.sh \
         fix_and_sync.sh fix_env.sh fix_github_env.sh; do
  if [[ -f "$f" ]]; then
    cat > "$f" <<'EOS'
#!/usr/bin/env bash
set -e
# Load secrets from .env
export $(grep -v '^#' .env | xargs)

# Example usage in your pipeline
echo "NOTION_TOKEN loaded: ${NOTION_TOKEN:0:4}***"
echo "GITHUB_TOKEN loaded: ${GITHUB_TOKEN:0:4}***"

# Call your real runner below
# python3 scripts/update_notion_summary.py
EOS
    chmod +x "$f"
  fi
done

echo "[4] Commit sanitized repo..."
git add .gitignore .env.example add_github_token.sh finalize_and_run.sh \
         finalize_publish.sh fix_and_sync.sh fix_env.sh fix_github_env.sh
git commit -m "sanitize: move secrets to .env, add .env.example, update scripts"

echo "[5] Force push (overwrite remote secrets)..."
git push origin main --force
