#!/usr/bin/env bash
set -euo pipefail

# Automated privacy & hardcoded-path check before commit / release

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERNS=(
  "/Users/peidyang"
  "peidyang"
  "Delonix"
  "德胧"
  "百达屋"
  "feishu-change-bot"
  "delonix_ai_steward"
  "\.hermes/node"
  "ZCode\.app"
  "zcode\.cjs"
)

FOUND=0
SCAN_ERROR=0
for pat in "${PATTERNS[@]}"; do
  # Never write matched content to disk or emit it to CI logs.
  # Do not use grep -q: it may hide read errors after the first match.
  if grep -rnE \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    --exclude-dir=release-artifacts \
    --exclude-dir=__pycache__ \
    --exclude=privacy-check.sh \
    -- "$pat" "$ROOT_DIR" >/dev/null 2>&1; then
    FOUND=1
  else
    status=$?
    if [[ "$status" -ne 1 ]]; then SCAN_ERROR=1; fi
  fi
done
if [[ "$SCAN_ERROR" -ne 0 ]]; then
  echo "[PRIVACY ERROR] Scan incomplete; inspect locally without exposing private content." >&2
  exit 2
fi
if [[ "$FOUND" -ne 0 ]]; then
  echo "[PRIVACY FAIL] Forbidden pattern found; inspect locally without exposing private content." >&2
  exit 1
fi
echo "[PASS] Privacy & hardcoded-path scan passed with 0 hits."
