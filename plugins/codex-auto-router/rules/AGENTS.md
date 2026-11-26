# Brain ↔ Hand Collaboration Policy (Antigravity ↔ Codex CLI)

1. **All User Communication Stays in Antigravity**:
   - Conduct requirement alignment, `/grill-me` clarifications, progress audits, and merge decisions directly with the user inside Antigravity.

2. **Explicit Dispatch Pre-Flight Gate (Hard Stop on Silent Self-Execution)**:
   - Whenever the user explicitly asks to delegate to Codex (`"delegate to Codex"` / `"dispatch to Codex"` / `"派 Codex"` / `"指派 Codex"`):
     - **STOP before doing the work yourself.** Antigravity MUST NOT silently take over execution or run multi-step investigation/scraping (> 3 quick read-only checks) before reporting back.
     - Run at most **3 quick read-only checks** to: (a) classify the task into Tier 1 / Tier 2 / Tier 3 below, and (b) verify workspace Git status and required Codex CLI / MCP / plugin readiness.
     - **If Tier 1 or Tier 2 (feasible via `dispatch.py`)**: Immediately present a concise **3–6 line Dispatch Plan** (target `cwd`, `isolation`, capability tier: offline vs `--network` vs Codex MCP/plugin, `--difficulty` & `--quality`, acceptance criteria) and wait for confirmation (skip waiting ONLY for safe local Tier 1 tasks when the user explicitly authorized direct execution, e.g. `"run directly"` / `"直接执行"`).
     - **If Tier 3 or missing prerequisite** (e.g., Codex lacks a required MCP/plugin, or the task requires Antigravity's live logged-in Chrome window / macOS Desktop GUI `cua_repl`): **STOP immediately**, state the exact technical blocker, and present **Option A (Antigravity handles directly)** vs **Option B (unlock in Codex via `--network`, `codex mcp add`, `codex plugin add`, or interactive Codex Desktop)**.

3. **Capability & Scenario Routing Matrix**:
   - **Tier 1 — Default Offline `dispatch.py` (`workspace-write`, no network, isolated Git worktree)**:
     - Multi-file coding, refactoring, debugging, test suites, local scripts, repo-wide review, local Office/PDF generation (`documents` / `spreadsheets` / `presentations` / `pdf` Codex plugins & `~/.codex/skills/`). Built-in web search (`web__run`) and image generation (`image_gen`) also work natively inside `codex exec`.
   - **Tier 2 — Networked & MCP-Extended `dispatch.py` (`workspace-write` + `--network` and/or Codex MCP/Plugins)**:
     - Outbound API / authenticated CLI tasks (`gh`, cloud/SaaS CLIs, package installs, Keychain-backed CLIs): pass `--network` (`sandbox_workspace_write.network_access=true`), unlocking outbound network while **preserving filesystem sandboxing outside the workdir** (never use `danger-full-access`).
     - Headless browser automation / E2E / scraping: register standard MCP in Codex (`codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --headless --isolated` or `playwright-mcp`).
     - Cloud SaaS workflows (GitHub, Figma, Gmail, Linear, Slack, Google Drive, etc.): install Codex plugins/connectors (`codex plugin add <name>`) or custom stdio/HTTP MCP servers (`codex mcp add`).
   - **Tier 3 — Handle Directly in Antigravity ("Brain") or Interactive Codex Desktop**:
     - Q&A, architecture planning, `/grill-me`, tiny localized edits (<= 20 lines in 1 file), `docs/BLACKBOARD.md` management, final diff/test audit, or whenever the user explicitly asks Antigravity to edit directly.
     - Operating the user's **already-logged-in Chrome window** via Antigravity's `chrome-devtools` MCP (unless a dedicated CDP `--browserUrl` is configured for Codex), or Desktop GUI automation (`cua_repl` relies on Codex Desktop Electron IPC and fails in headless `codex exec`).

4. **Four Mandatory Confirmation Gates (Hard Stop Points)**:
   - **Gate 1 — Dispatch Plan Confirmation**: Present the 3–6 line plan before calling `dispatch.py run/batch` (waived only for safe local Tier 1 tasks with explicit direct-execution approval).
   - **Gate 2 — Network & External Write Gate**: ALWAYS ask explicit confirmation before passing `--network` OR mutating any external live system (cloud docs/wikis, remote Git/PRs, email/chat, production APIs/databases) — even if direct execution was requested. For bulk external mutations, require a read-only dry-run/checklist confirmation first.
   - **Gate 3 — Blocker Escalation Gate**: On explicit Codex dispatch requests, if a required capability/MCP/CLI is missing or blocked, stop within <= 3 read-only checks and present Option A vs Option B instead of silently taking over.
   - **Gate 4 — Human Merge & Remote Push Gate**: Never auto-merge `agy-worker/*` branches, auto-create remote GitHub repos, or push without explicit user confirmation.

5. **Shared Blackboard (`docs/BLACKBOARD.md`) & Workspace Isolation**:
   - For Git repo coding tasks: create/update `docs/BLACKBOARD.md` (goals, architecture decisions, checklist with acceptance criteria, status) and ensure at least one local Git commit exists so Worktrees have `HEAD`.
   - For non-Git operational/document workspaces: do NOT silently `git init`; declare `--isolation inplace` in the Dispatch Plan.

6. **Brain → Hand → Brain → Hand Loop (`multi-agent-dispatch`)**:
   - Load `multi-agent-dispatch` (`~/.gemini/config/skills/multi-agent-dispatch/SKILL.md`) and run `python3 ~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py` (`run`, `batch`, `resume`, `review`). Default `--quality smart` balances model quality and quota across newest official Codex models; instruct Codex to self-verify inside its turn.
   - After Codex returns its compact JSON report, independently verify `git diff --stat` and tests, update `docs/BLACKBOARD.md` (and optional `codex-console` cross-session bindings), report back in Antigravity, and either iterate (`resume`) or—only after Gate 4 confirmation—merge `agy-worker/*` and run `dispatch.py cleanup --task-id <id> --delete-branch`.
