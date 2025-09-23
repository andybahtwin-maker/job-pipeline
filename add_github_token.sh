#!/usr/bin/env bash
set -e
# Load secrets from .env
export $(grep -v '^#' .env | xargs)

# Example usage in your pipeline
echo "NOTION_TOKEN loaded: ${NOTION_TOKEN:0:4}***"
echo "GITHUB_TOKEN loaded: ${GITHUB_TOKEN:0:4}***"

# Call your real runner below
# python3 scripts/update_notion_summary.py
