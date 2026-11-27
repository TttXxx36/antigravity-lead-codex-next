#!/usr/bin/env bash
set -euo pipefail
# D22 offline source RC only; no npm, tag, release, network or publishing.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -ne 3 ]]; then
  echo "Usage: package-release.sh v2.0.0-rc.N FULL_HEAD_SHA NEW_OUTPUT_DIR" >&2
  exit 2
fi
exec python3 "$ROOT_DIR/scripts/rc_package.py" build --root "$ROOT_DIR" --version "$1" --commit "$2" --out "$3"
