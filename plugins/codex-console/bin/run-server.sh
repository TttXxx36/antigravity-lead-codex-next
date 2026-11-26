#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

find_node22() {
  local candidates=()
  if [[ -n "${CODEX_CONSOLE_NODE_BIN:-}" ]]; then
    candidates+=("$CODEX_CONSOLE_NODE_BIN")
  fi
  if command -v node >/dev/null 2>&1; then
    candidates+=("$(command -v node)")
  fi
  candidates+=(
    "/opt/homebrew/bin/node"
    "/usr/local/bin/node"
    "$HOME/.local/bin/node"
    "$HOME/.volta/bin/node"
    "$HOME/.asdf/shims/node"
  )

  # Check nvm / fnm installed v22+ versions (newest first)
  if [[ -d "$HOME/.nvm/versions/node" ]]; then
    while IFS= read -r p; do
      candidates+=("$p")
    done < <(ls -1d "$HOME"/.nvm/versions/node/v*/bin/node 2>/dev/null | sort -Vr || true)
  fi
  if [[ -d "$HOME/.fnm/node-versions" ]]; then
    while IFS= read -r p; do
      candidates+=("$p")
    done < <(ls -1d "$HOME"/.fnm/node-versions/v*/installation/bin/node 2>/dev/null | sort -Vr || true)
  fi

  local bin
  for bin in "${candidates[@]}"; do
    [[ -n "$bin" && -x "$bin" ]] || continue
    if "$bin" --no-warnings -e "require('node:sqlite')" >/dev/null 2>&1; then
      printf '%s\n' "$bin"
      return 0
    fi
  done
  return 1
}

NODE_BIN="$(find_node22 || true)"
if [[ -z "$NODE_BIN" ]]; then
  echo "[codex-console] Error: Node.js >= 22.5 with built-in node:sqlite is required. Install Node 22+ or set CODEX_CONSOLE_NODE_BIN." >&2
  exit 1
fi

exec "$NODE_BIN" --no-warnings "$PLUGIN_ROOT/server/index.mjs" "$@"
