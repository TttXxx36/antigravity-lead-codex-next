#!/usr/bin/env bash
set -euo pipefail

# Antigravity-Lead-Codex installer (macOS & Linux / WSL2)
# Supports both local clone execution and remote `curl -fsSL ... | bash` execution.

REPO_OWNER="${ALC_REPO_OWNER:-Koala973}"
REPO_NAME="${ALC_REPO_NAME:-antigravity-lead-codex}"
REPO_REF="${ALC_REF:-main}"

GEMINI_CONFIG_DIR="${GEMINI_CONFIG_DIR:-$HOME/.gemini/config}"
PLUGINS_DIR="$GEMINI_CONFIG_DIR/plugins"
SKILLS_DIR="$GEMINI_CONFIG_DIR/skills"

MODE="all"       # all | console-only | uninstall
AUTO_YES=0
SKIP_UI_BUILD=0
SOURCE_DIR=""

usage() {
  cat <<'EOF'
Usage: install.sh [OPTIONS]

Options:
  --all             Install full suite: codex-console + codex-auto-router + multi-agent-dispatch (default)
  --console-only    Install only the Codex Console side-pane MCP App plugin
  --uninstall       Remove installed Antigravity-Lead-Codex plugins and skill (keeps SQLite data)
  --ref <branch>    Git branch or tag to download when running remotely (default: main)
  --no-build        Use pre-bundled dist/app.html without rebuilding UI via Vite
  -y, --yes         Non-interactive mode
  -h, --help        Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) MODE="all"; shift ;;
    --console-only) MODE="console-only"; shift ;;
    --uninstall) MODE="uninstall"; shift ;;
    --ref) REPO_REF="${2:-main}"; shift 2 ;;
    --no-build) SKIP_UI_BUILD=1; shift ;;
    -y|--yes) AUTO_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

log() { printf '\033[1;34m[antigravity-lead-codex]\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[ERR]\033[0m %s\n' "$*" >&2; }

if [[ "$MODE" == "uninstall" ]]; then
  log "Removing installed plugins and skill from $GEMINI_CONFIG_DIR ..."
  rm -rf "$PLUGINS_DIR/codex-console" "$PLUGINS_DIR/codex-auto-router" "$SKILLS_DIR/multi-agent-dispatch"
  ok "Uninstalled plugins & skill. Persistent SQLite data under ~/.gemini/antigravity/plugin_data/codex-console was preserved."
  exit 0
fi

# Detect Node >= 22.5 (with node:sqlite)
find_node22() {
  local candidates=()
  [[ -n "${CODEX_CONSOLE_NODE_BIN:-}" ]] && candidates+=("$CODEX_CONSOLE_NODE_BIN")
  command -v node >/dev/null 2>&1 && candidates+=("$(command -v node)")
  candidates+=(
    "/opt/homebrew/bin/node"
    "/usr/local/bin/node"
    "$HOME/.local/bin/node"
    "$HOME/.volta/bin/node"
    "$HOME/.asdf/shims/node"
  )
  if [[ -d "$HOME/.nvm/versions/node" ]]; then
    while IFS= read -r p; do candidates+=("$p"); done < <(ls -1d "$HOME"/.nvm/versions/node/v*/bin/node 2>/dev/null | sort -Vr || true)
  fi
  local b
  for b in "${candidates[@]}"; do
    [[ -n "$b" && -x "$b" ]] || continue
    if "$b" --no-warnings -e "require('node:sqlite')" >/dev/null 2>&1; then
      printf '%s\n' "$b"
      return 0
    fi
  done
  return 1
}

NODE_BIN="$(find_node22 || true)"
if [[ -z "$NODE_BIN" ]]; then
  err "Node.js >= 22.5 (with built-in node:sqlite) is required but was not found."
  err "Please install Node 22+ (e.g. brew install node@22 or nvm install 22) and re-run."
  exit 1
fi
NPM_BIN="$(dirname "$NODE_BIN")/npm"
[[ -x "$NPM_BIN" ]] || NPM_BIN="$(command -v npm || true)"
if [[ -z "$NPM_BIN" ]]; then
  err "npm not found alongside $NODE_BIN."
  exit 1
fi
ok "Node.js verified: $("$NODE_BIN" --version) ($NODE_BIN)"

if [[ "$MODE" == "all" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    err "python3 (>= 3.10) is required for --all mode. Re-run with --console-only or install Python 3.10+."
    exit 1
  fi
  if ! command -v git >/dev/null 2>&1; then
    err "git is required for isolated Worktree dispatch."
    exit 1
  fi
  ok "Python verified: $(python3 --version)"
fi

if command -v codex >/dev/null 2>&1 || [[ -x "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" ]]; then
  ok "Codex CLI detected."
else
  warn "Codex CLI binary not detected in PATH yet. Install @openai/codex or ChatGPT Desktop before dispatching tasks."
fi

# Resolve source directory: local repo or remote GitHub tarball
TMP_DIR=""
cleanup_tmp() {
  # Local installs have no download directory. An EXIT trap must not turn
  # successful installation into status 1 under set -e.
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf -- "$TMP_DIR"
  fi
}
trap cleanup_tmp EXIT

SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [[ -n "$SCRIPT_PATH" && -f "$SCRIPT_PATH" ]]; then
  CANDIDATE_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
  if [[ -d "$CANDIDATE_ROOT/plugins/codex-console" ]]; then
    SOURCE_DIR="$CANDIDATE_ROOT"
  fi
fi

if [[ -z "$SOURCE_DIR" ]]; then
  TMP_DIR="$(mktemp -d)"
  TAR_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/${REPO_REF}.tar.gz"
  if [[ "$REPO_REF" == v* ]]; then
    TAR_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/tags/${REPO_REF}.tar.gz"
  fi
  log "Downloading $TAR_URL ..."
  curl -fsSL "$TAR_URL" | tar -xz -C "$TMP_DIR"
  SOURCE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  if [[ ! -d "$SOURCE_DIR/plugins/codex-console" ]]; then
    err "Downloaded archive did not contain plugins/codex-console."
    exit 1
  fi
fi

mkdir -p "$PLUGINS_DIR" "$SKILLS_DIR"

# 1. Install codex-console plugin
log "Installing plugin: codex-console -> $PLUGINS_DIR/codex-console"
mkdir -p "$PLUGINS_DIR/codex-console"
rm -rf "$PLUGINS_DIR/codex-console"/{assets,bin,dist,server,ui,skills}
cp -R "$SOURCE_DIR/plugins/codex-console"/* "$PLUGINS_DIR/codex-console/"
chmod +x "$PLUGINS_DIR/codex-console/bin/run-server.sh"

log "Installing Node.js dependencies for codex-console..."
if [[ "$SKIP_UI_BUILD" -eq 1 && -f "$PLUGINS_DIR/codex-console/dist/app.html" ]]; then
  (cd "$PLUGINS_DIR/codex-console" && PATH="$(dirname "$NODE_BIN"):$PATH" "$NPM_BIN" ci --omit=dev --no-audit --no-fund)
else
  (cd "$PLUGINS_DIR/codex-console" && PATH="$(dirname "$NODE_BIN"):$PATH" "$NPM_BIN" ci --no-audit --no-fund && "$NPM_BIN" run build:ui)
fi
ok "codex-console installed."

# 2. Install codex-auto-router & multi-agent-dispatch (full mode)
if [[ "$MODE" == "all" ]]; then
  log "Installing plugin: codex-auto-router -> $PLUGINS_DIR/codex-auto-router"
  rm -rf "$PLUGINS_DIR/codex-auto-router"
  cp -R "$SOURCE_DIR/plugins/codex-auto-router" "$PLUGINS_DIR/codex-auto-router"
  chmod +x "$PLUGINS_DIR/codex-auto-router/hooks/allow_dispatch.py"
  ok "codex-auto-router installed."

  log "Installing skill: multi-agent-dispatch -> $SKILLS_DIR/multi-agent-dispatch"
  rm -rf "$SKILLS_DIR/multi-agent-dispatch"
  cp -R "$SOURCE_DIR/skills/multi-agent-dispatch" "$SKILLS_DIR/multi-agent-dispatch"
  chmod +x "$SKILLS_DIR/multi-agent-dispatch/scripts/dispatch.py"
  ok "multi-agent-dispatch installed."
fi

# 3. Hot-reload Antigravity MCP server if running inside an Antigravity shell
if [[ -n "${ANTIGRAVITY_CSRF_TOKEN:-}" ]]; then
  LS_ADDR="${ANTIGRAVITY_LS_ADDRESS:-localhost:5387}"
  if curl -sf -H "Content-Type: application/json" \
      -H "x-codeium-csrf-token: ${ANTIGRAVITY_CSRF_TOKEN}" \
      -d '{"serverName":"codex-console_codex_console"}' \
      "http://${LS_ADDR}/exa.language_server_pb.LanguageServerService/RefreshMcpServers" >/dev/null 2>&1; then
    ok "Triggered live Antigravity MCP hot-reload."
  fi
fi

echo ""
ok "Installation complete! Open Antigravity -> click '+' in the right side pane -> select 'Codex Console'."
echo "Run diagnostics anytime with: bash $SOURCE_DIR/scripts/doctor.sh"
