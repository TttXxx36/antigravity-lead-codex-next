#!/usr/bin/env bash
set -euo pipefail

# Antigravity-Lead-Codex Doctor: environment check & MCP stdio smoke test

GEMINI_CONFIG_DIR="${GEMINI_CONFIG_DIR:-$HOME/.gemini/config}"
CONSOLE_DIR="$GEMINI_CONFIG_DIR/plugins/codex-console"
ROUTER_DIR="$GEMINI_CONFIG_DIR/plugins/codex-auto-router"
DISPATCH_SCRIPT="$GEMINI_CONFIG_DIR/skills/multi-agent-dispatch/scripts/dispatch.py"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

PASS=0
WARN=0
FAIL=0

ok()   { printf '\033[1;32m[PASS]\033[0m %s\n' "$*"; PASS=$((PASS + 1)); }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; WARN=$((WARN + 1)); }
fail() { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*"; FAIL=$((FAIL + 1)); }

echo "=== Antigravity-Lead-Codex Doctor ==="
echo "OS: $(uname -s) $(uname -m)"

# 1. Check Node >= 22.5 + node:sqlite
NODE_BIN=""
for cand in "${CODEX_CONSOLE_NODE_BIN:-}" "$(command -v node || true)" /opt/homebrew/bin/node /usr/local/bin/node "$HOME/.local/bin/node"; do
  [[ -n "$cand" && -x "$cand" ]] || continue
  if "$cand" --no-warnings -e "require('node:sqlite')" >/dev/null 2>&1; then
    NODE_BIN="$cand"
    break
  fi
done
if [[ -n "$NODE_BIN" ]]; then
  ok "Node.js with node:sqlite: $("$NODE_BIN" --version) ($NODE_BIN)"
else
  fail "Node.js >= 22.5 with built-in node:sqlite not found"
fi

# 2. Check Python 3.10+ & Git
if command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    ok "Python: $PY_VER"
  else
    warn "Python $PY_VER < 3.10 (dispatch.py requires 3.10+)"
  fi
else
  warn "python3 not found (optional if using --console-only)"
fi

if command -v git >/dev/null 2>&1; then
  ok "Git: $(git --version)"
else
  warn "git not found (required for Worktree isolation)"
fi

# 3. Check Codex CLI & local SQLite databases
if command -v codex >/dev/null 2>&1; then
  ok "Codex CLI: $(codex --version 2>/dev/null || echo detected) ($(command -v codex))"
elif [[ -x "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" ]]; then
  ok "Codex CLI (ChatGPT bundled): $(/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex --version 2>/dev/null || echo detected)"
else
  warn "Codex CLI binary not found in standard paths"
fi

if [[ -f "$CODEX_HOME/state_5.sqlite" ]]; then
  ok "Codex state DB readable: $CODEX_HOME/state_5.sqlite"
else
  warn "Codex state DB not found at $CODEX_HOME/state_5.sqlite (run Codex at least once)"
fi

# 4. Check installed plugins & artifacts
if [[ -f "$CONSOLE_DIR/plugin.json" && -f "$CONSOLE_DIR/dist/app.html" && -x "$CONSOLE_DIR/bin/run-server.sh" ]]; then
  ok "codex-console plugin files intact ($CONSOLE_DIR)"
else
  fail "codex-console plugin incomplete or not installed at $CONSOLE_DIR"
fi

if [[ -f "$ROUTER_DIR/plugin.json" && -f "$ROUTER_DIR/rules/AGENTS.md" ]]; then
  ok "codex-auto-router plugin installed ($ROUTER_DIR)"
else
  warn "codex-auto-router not installed (OK if installed with --console-only)"
fi

if [[ -f "$DISPATCH_SCRIPT" ]]; then
  ok "multi-agent-dispatch script present ($DISPATCH_SCRIPT)"
else
  warn "multi-agent-dispatch not installed (OK if installed with --console-only)"
fi

# 5. Live MCP stdio handshake smoke test
if [[ -n "$NODE_BIN" && -x "$CONSOLE_DIR/bin/run-server.sh" && -d "$CONSOLE_DIR/node_modules" ]]; then
  TMP_DATA="$(mktemp -d)"
  trap 'rm -rf "$TMP_DATA"' EXIT
  if "$NODE_BIN" --no-warnings -e '
    import { spawn } from "node:child_process";
    const child = spawn("bash", [process.argv[1], "--data-dir", process.argv[2]], { stdio: ["pipe", "pipe", "pipe"] });
    let buf = "";
    const timer = setTimeout(() => { child.kill(); process.exit(1); }, 8000);
    child.stdout.on("data", (d) => {
      buf += d.toString("utf8");
      if (buf.includes("\n")) {
        const msg = JSON.parse(buf.split("\n")[0]);
        clearTimeout(timer);
        child.kill();
        process.exit(msg?.result?.capabilities?.resources && msg?.result?.capabilities?.tools ? 0 : 1);
      }
    });
    child.stdin.write(JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "doctor", version: "1.0.0" } }
    }) + "\n");
  ' "$CONSOLE_DIR/bin/run-server.sh" "$TMP_DATA"; then
    ok "MCP stdio handshake (initialize + tools/resources capabilities) passed"
  else
    fail "MCP stdio handshake failed"
  fi
fi

echo ""
echo "Summary: PASS=$PASS  WARN=$WARN  FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
