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
for pat in "${PATTERNS[@]}"; do
  if grep -rnE \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    --exclude-dir=release-artifacts \
    --exclude-dir=__pycache__ \
    --exclude=privacy-check.sh \
    "$pat" "$ROOT_DIR" >/tmp/alc_privacy_hit.txt 2>/dev/null; then
    echo "[PRIVACY FAIL] Matched forbidden pattern: $pat"
    cat /tmp/alc_privacy_hit.txt
    FOUND=1
  fi
done
rm -f /tmp/alc_privacy_hit.txt

if [[ "$FOUND" -ne 0 ]]; then
  echo "Privacy scan FAILED. Clean matched references before committing or publishing." >&2
  exit 1
fi

echo "[PASS] Privacy & hardcoded-path scan passed with 0 hits."
