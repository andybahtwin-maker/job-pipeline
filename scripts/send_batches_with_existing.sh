#!/usr/bin/env bash
set -euo pipefail
OUTROOT="${1:-outbox}"
RUN_DIR="$(ls -dt "${OUTROOT}"/2* 2>/dev/null | head -n1 || true)"
[[ -z "$RUN_DIR" ]] && { echo "[!] No batches found in $OUTROOT. Run the batcher first."; exit 1; }
echo "[i] Using run dir: $RUN_DIR"
for B in "$RUN_DIR"/batch_*; do
  SUBJECT="$(cat "$B/subject.txt")"
  HTML="$B/body.html"
  echo "[dry-run] would send: '$SUBJECT' with $HTML"
done
