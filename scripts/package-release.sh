#!/usr/bin/env bash
set -euo pipefail

# Build reproducible release tarball and SHA256SUMS.txt

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-v1.0.0}"
OUT_DIR="${2:-$ROOT_DIR/release-artifacts}"
PKG_NAME="antigravity-lead-codex-${VERSION}"

mkdir -p "$OUT_DIR"
TMP_STAGE="$(mktemp -d)"
trap 'rm -rf "$TMP_STAGE"' EXIT

# Ensure fresh UI bundle
(
  cd "$ROOT_DIR/plugins/codex-console"
  npm ci --no-audit --no-fund
  npm run build:ui
)

STAGE="$TMP_STAGE/$PKG_NAME"
mkdir -p "$STAGE"

cp "$ROOT_DIR/LICENSE" "$ROOT_DIR/README.md" "$ROOT_DIR/README_EN.md" "$ROOT_DIR/CHANGELOG.md" "$STAGE/"
cp -R "$ROOT_DIR/docs" "$ROOT_DIR/img" "$ROOT_DIR/scripts" "$STAGE/"
cp -R "$ROOT_DIR/plugins" "$ROOT_DIR/skills" "$STAGE/"

# Strip dev/transient directories from release bundle
rm -rf "$STAGE/plugins/codex-console/node_modules"
find "$STAGE" -name "__pycache__" -type d -exec rm -rf {} +
find "$STAGE" -name ".DS_Store" -delete

TARBALL="$OUT_DIR/${PKG_NAME}.tar.gz"
tar -czf "$TARBALL" -C "$TMP_STAGE" "$PKG_NAME"

(
  cd "$OUT_DIR"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${PKG_NAME}.tar.gz" > SHA256SUMS.txt
  else
    sha256sum "${PKG_NAME}.tar.gz" > SHA256SUMS.txt
  fi
)

echo "Built release artifact:"
ls -lh "$TARBALL" "$OUT_DIR/SHA256SUMS.txt"
cat "$OUT_DIR/SHA256SUMS.txt"
