---
name: multi-agent-dispatch
description: >-
  Delegate coding, refactoring, debugging, review, local document/media
  workflows, or opt-in networked CLI/MCP tasks from Google Antigravity (Brain)
  to local OpenAI Codex CLI (Hand), dynamically routing newest official frontier
  models with default --quality smart via isolated Git worktrees, Blackboard
  sync, confirmation gates, and compact JSON reports.
---

# Multi-Agent Dispatch (`Antigravity Brain ↔ Codex CLI Hand`)

Use [dispatch.py](./scripts/dispatch.py) for the **Brain → Gate → Blackboard → Hand → Audit** loop.

## Capability Tiers & Scenario Routing

| Tier | Mode / Flag | Supported Scenarios | Confirmation Gate |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Default Offline)** | `dispatch.py run` (`workspace-write`, offline, Git worktree) | Multi-file coding, refactoring, debugging, tests, scripts, repo review, local Office/PDF generation (`documents` / `spreadsheets` / `presentations` / `pdf` plugins & `~/.codex/skills/`). Built-in web search (`web__run`) and image gen (`image_gen`) also work in `codex exec`. | Present 3–6 line plan (waived only if user explicitly authorized direct execution). |
| **Tier 2 (Networked & MCP-Extended)** | `dispatch.py run --network` and/or Codex MCP/Plugins | Outbound HTTPS / authenticated CLIs (`gh`, SaaS/cloud CLIs, `npm`/`pip`, Keychain-backed CLIs); headless browser automation via `codex mcp add chrome-devtools` / `playwright-mcp`; cloud SaaS connectors via `codex plugin add` (GitHub, Figma, Gmail, Linear, Slack, etc.). `--network` sets `sandbox_workspace_write.network_access=true` while **keeping filesystem isolation outside workdir** (never `danger-full-access`). | **Mandatory confirmation** before `--network` or any external write/mutation (even when direct execution was requested). |
| **Tier 3 (Brain or Codex Desktop)** | Do NOT force via `dispatch.py` | `/grill-me`, architecture design, tiny 1-file edits (<= 20 lines), `docs/BLACKBOARD.md`, final diff/test audit, operating the user's already-logged-in Chrome window (without dedicated CDP `--browserUrl`), or Desktop GUI (`cua_repl` requires Codex Desktop Electron IPC pipe and fails in headless `codex exec`). | On explicit Codex dispatch requests, stop within <= 3 read-only checks and present Option A (Antigravity) vs Option B (Codex setup/Desktop). |

## Extending Codex CLI ("Hand") Capabilities

Headless `codex exec` inherits MCP servers, plugins, and skills from `~/.codex/`:
1. **Standard MCP Servers** (run outside the shell sandbox):
   - Headless Chrome automation: `codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --headless --isolated`
   - Connect to an explicitly started debug Chrome: `codex mcp add chrome-cdp -- npx -y chrome-devtools-mcp@latest --browserUrl http://127.0.0.1:9222`
   - Playwright / DB / SaaS MCPs: `codex mcp add <name> -- <command...>` or `codex mcp add <name> --url <https://...>`
2. **Official Plugins & Connectors**: `codex plugin list` and `codex plugin add <plugin-name>` (Office/PDF runtime plugins, GitHub, Figma, Gmail, Linear, Slack, Google Drive, etc.).
3. **Local Skills**: drop `SKILL.md` bundles into `~/.codex/skills/`.
4. **Networked CLI Sandbox**: pass `--network` to `dispatch.py run|batch|resume` to allow outbound HTTPS and Keychain-backed CLIs while blocking writes outside the workdir.

## Blackboard Sync & Quota-Saving Rules

1. **Shared Blackboard (`docs/BLACKBOARD.md`)**: For Git repos, write confirmed goals, constraints, and task acceptance criteria to `docs/BLACKBOARD.md` and commit locally so Worktrees inherit complete context from `HEAD`. For non-Git operational folders, declare `--isolation inplace` in the plan rather than silently running `git init`.
2. **Coarse-grained single-turn tasks**: Instruct Codex inside its prompt to read `docs/BLACKBOARD.md`, implement changes, **and run tests/linters/typechecks itself** before returning.
3. **Structured short reports**: `dispatch.py` passes [report_schema.json](./resources/report_schema.json) and collects `git status --short` / `git diff --stat`, keeping Antigravity context clean and compact.
4. **Worktree isolation & human gates**:
   - Git write tasks default to `--isolation worktree` (`agy-worker/<task_id>`).
   - **NEVER auto-merge** worker branches, **NEVER pass `--network`** without confirmation, and **NEVER push to GitHub** without explicit user approval.
5. **Brain-driven iteration**: Review each report in Antigravity, decide the next prompt, and use `resume --task-id <id>` (reusing the Worktree, session, and `network` setting) or launch the next `run`.

## Dynamic Frontier Discovery & Smart Quality-Quota Routing (`--quality smart` Default)

`dispatch.py` dynamically reads `~/.codex/models_cache.json`, identifies the newest official generation's **flagship** and **wide_fast** siblings, and calibrates reasoning effort against `supported_reasoning_levels`:

| `--difficulty` | `--quality smart` (**Default**) | `--quality max` | `--quality balanced` |
| :--- | :--- | :--- | :--- |
| `low` | `wide_fast` + `medium` | `flagship` + `high` | `wide_fast` + `medium` |
| `medium` | Alternates `wide_fast` ↔ `flagship` at `high` | `flagship` + `xhigh` | Alternates `wide_fast (high)` ↔ `flagship (medium)` |
| `hard` | `flagship` + `xhigh` | `flagship` + `max` | `flagship` + `high` |
| `extreme` | `flagship` + `max` | `flagship` + `ultra` | `flagship` + `xhigh` |
| `auto` (default) | Heuristic classifier -> tier above | Heuristic classifier -> tier above | Heuristic classifier |

- Pass `--prefer-wide` (or `>=10` `--files` under `auto`) to route large-context sweeps to `wide_fast`.
- Pass `--model` / `--effort` anytime to override explicitly.

## Command Reference

Run via `python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py <subcommand>`:

1. **Preflight health & frontier model discovery check**:
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py health
   ```
2. **Single task dispatch** (offline by default; add `--network` only after Gate 2 confirmation):
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py run \
     --cwd /path/to/repo \
     --difficulty auto \
     --prompt "Read docs/BLACKBOARD.md, implement task X with unit tests, and run tests to verify."
   ```
   Networked CLI / API example (preserves filesystem sandbox outside workdir):
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py run \
     --cwd /path/to/workspace \
     --isolation inplace \
     --network \
     --prompt "Run read-only API audit and output structured summary."
   ```
3. **Parallel batch dispatch** (supports `--network` default or per-item `"network": true`):
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py batch \
     --cwd /path/to/repo \
     --max-concurrency 3 \
     --manifest /path/to/tasks.json
   ```
4. **Resume an existing worker session** (inherits original `network` setting; override with `--network` / `--no-network`):
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py resume \
     --task-id <task_id> \
     --prompt "Fix edge case noted in audit and re-run tests."
   ```
5. **Read-only code review**:
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py review \
     --task-id <task_id>
   ```
6. **Inspect state & clean up worktree after user approves/merges**:
   ```bash
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py status
   python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py cleanup --task-id <task_id> --delete-branch
   ```
