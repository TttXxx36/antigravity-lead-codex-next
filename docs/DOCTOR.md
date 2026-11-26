# Doctor & Troubleshooting Guide

Run the built-in diagnostic script anytime:

```bash
bash scripts/doctor.sh
```

## Common Issues & Fixes

### 1. `Node.js >= 22.5 with built-in node:sqlite not found`
`codex-console` uses Node's built-in `node:sqlite` module so no C++ native addons need to be compiled.
- Install Node 22+ via Homebrew (`brew install node@22`), `nvm install 22`, or `fnm install 22`.
- If Node lives in a non-standard path, export `CODEX_CONSOLE_NODE_BIN=/path/to/node` before launching Antigravity or edit `plugins/codex-console/bin/run-server.sh`.

### 2. `Codex Console` does not appear in Antigravity's `+` side-pane menu
- Verify `~/.gemini/config/plugins/codex-console/plugin.json` and `mcp_config.json` exist.
- Check Antigravity **Customizations / MCP Servers** settings and confirm `codex-console` is enabled and `codex-console_codex_console` is running.
- Run `bash scripts/doctor.sh` to verify the MCP stdio handshake passes cleanly.

### 3. After updating the UI, the side pane still shows the old interface
Antigravity caches the loaded iframe while the tab remains open. Close the **`Codex Console`** side-pane tab and reopen it via **`+` → `Codex Console`** (no full app restart required).

### 4. `codex queue` succeeds but an exited CLI thread does not immediately wake up
`codex queue --resume` relies on Codex's local daemon to consume queued turns. For exited headless `codex exec` threads, switch the bottom composer dropdown to **`同步续跑 (codex exec resume)`** or **`Dispatch 续跑 (dispatch.py)`**.

### 5. `Codex state DB not found at ~/.codex/state_5.sqlite`
Start Codex Desktop or run `codex exec` at least once so Codex initializes `~/.codex/state_5.sqlite`. If you store Codex state in a custom directory, set `CODEX_HOME`.
