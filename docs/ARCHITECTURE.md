# Architecture — Antigravity-Lead-Codex

## 1. Design Philosophy: Brain ↔ Hand Separation

| Layer | Owner | Responsibilities |
| :--- | :--- | :--- |
| **Brain** | Google Antigravity | Requirement alignment (`/grill-me`), architecture design, maintaining `docs/BLACKBOARD.md`, auditing diffs & tests, enforcing 4 confirmation gates, resolving blockers, human merge decisions |
| **Hand** | Local Codex CLI (`dispatch.py`) | Multi-file implementation, refactoring, local Office/PDF/skill tasks in offline `workspace-write` worktrees; opt-in networked CLI/API tasks via `--network` (`sandbox_workspace_write.network_access=true` with filesystem isolation intact); extensible via `codex mcp add` (e.g., headless `chrome-devtools-mcp`) and `codex plugin add` |
| **Control Plane** | `codex-console` MCP App | Real-time side-pane visibility into all Codex CLI / Worktree / Desktop threads, non-destructive read-only diagnosis, queue/resume dispatch, and cross-session Change ↔ Thread SQLite bindings |

For the full capability matrix, MCP/plugin extension recipes, and confirmation gates, see [docs/CAPABILITIES.md](./CAPABILITIES.md).

---

## 2. Dual-Database Isolation (Zero Lock Contention)

Codex Desktop and Codex CLI keep `~/.codex/*.sqlite` open in SQLite WAL mode. Writing directly into Codex's internal databases risks lock contention and schema corruption.

`codex-console` enforces strict database isolation:
1. **Codex SQLite DBs (Strictly Read-Only, Short-Lived Connections)**
   - `state_5.sqlite`: `threads`, `projects`, `project_roots`, `thread_spawn_edges`
   - `goals_1.sqlite`: `thread_goals` (`active`, `paused`, `blocked`, `usage_limited`, `budget_limited`, `complete`)
   - `queue_1.sqlite`: `queued_items`
   - `thread_history_1.sqlite`: `thread_turns`, `thread_items`
   - Every query opens `{ readOnly: true }`, sets `PRAGMA busy_timeout = 2000`, executes indexed lookups, and immediately closes in `finally` so WAL checkpointing is never blocked.
2. **Console SQLite DB (Plugin-Owned WAL DB)**
   - Path: `${PLUGIN_DATA}/console.sqlite` (typically `~/.gemini/antigravity/plugin_data/codex-console/console.sqlite`).
   - Tables:
     - `thread_prefs`: local pins & custom task aliases.
     - `console_ops`: audit log of read-only diagnostics, `codex queue`, `exec resume`, and worker spawns + 60s deduplication hashes.
     - `collab_bindings` & `collab_messages`: cross-session `Change / Goal ↔ Codex Thread ID` collaboration middleware readable by any Antigravity window via MCP.

---

## 3. Antigravity MCP App Protocol (`SEP-1865` + Extensions)

- **UI Resource**: `ui://codex-console/app.html` (`mimeType: "text/html;profile=mcp-app"`), bundled via Vite + `vite-plugin-singlefile` into a single self-contained HTML file (~385 KB) with zero external script/style/network dependencies to satisfy Antigravity's strict default CSP (`default-src 'none'`).
- **Entrypoints**: `open_codex_console` advertises `com.google.antigravity/ui.entrypoints` for both `aux_pane` (side-pane tab & `+` menu) and `global` (left sidebar full-page view).
- **Visibility Separation**:
  - Model + App tools (`open_codex_console`, `list_codex_tasks`, `get_codex_task_detail`, `ask_codex_readonly`, `send_codex_message`, `spawn_codex_worker`, `manage_collab_binding`) allow Antigravity itself to orchestrate Codex and read cross-session bindings.
  - App-only tools (`console_snapshot`, `console_toggle_pin`, `console_get_op`, `console_git_inspect`) declare `visibility: ["app"]` so high-frequency UI polling never pollutes the LLM tool list.
- **Host Bridge Capabilities**:
  - `app.sendMessage()` powers one-click **`发回当前对话`** (gated on `hostCapabilities.message` so it cleanly hides in global views).
  - `com.google.antigravity/toggle-aux-pane` opens `docs/BLACKBOARD.md` and changed worktree files in adjacent Antigravity editor tabs.

---

## 4. Non-Destructive Read-Only Diagnosis

Clicking **「一键诊断卡点」** or **「只读提问」** spawns:

```bash
codex exec fork --ephemeral --skip-git-repo-check \
  -c sandbox_mode="read-only" \
  -c approval_policy="never" \
  -o <tmp_output_file> \
  <thread_id> "<diagnostic_prompt>"
```

Because `--ephemeral` forks the session in memory without writing back to the original thread history and `sandbox_mode="read-only"` forbids file mutations, diagnostics can safely inspect even an actively running or blocked worker.
