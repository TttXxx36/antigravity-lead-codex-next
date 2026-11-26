# Codex CLI ("Hand") Capabilities, Extension Guide & Confirmation Gates

`Antigravity-Lead-Codex` treats **Google Antigravity** as the **Brain** (planning, alignment, audits, guardrails) and **OpenAI Codex CLI (`codex exec`)** as the **Hand** (autonomous execution).

A common misconception is that `codex exec` can only edit code files. In practice, modern Codex CLI (`>= 0.170`) is a general-purpose local agent runtime that natively supports **MCP servers, official plugins/connectors, local skills, built-in web search, image generation, and fine-grained sandbox policies**.

---

## 1. Empirical Capability Matrix (`codex exec`)

| Capability Layer | Works in Default `dispatch.py` (`workspace-write`, offline)? | Works with `dispatch.py --network`? | How to Enable / Notes |
| :--- | :--- | :--- | :--- |
| **Multi-file coding, refactoring, tests, local scripts** | Yes (isolated Git worktree) | Yes | Out of the box (`--quality smart`). |
| **Local Office & PDF processing** (`DOCX`, `XLSX`, `PPTX`, `PDF`) | Yes | Yes | Built-in Codex runtime plugins (`documents`, `spreadsheets`, `presentations`, `pdf`) & local `~/.codex/skills/`. |
| **Web search (`web__run`) & image generation (`image_gen`)** | Yes | Yes | Exposed natively inside `codex exec` (requires active ChatGPT/OpenAI account). |
| **Outbound HTTPS, `npm`/`pip`, `gh`, SaaS & Keychain-backed CLIs** | No (blocked by default offline sandbox) | **Yes** (`sandbox_workspace_write.network_access=true`) | Pass `--network`. **Filesystem isolation outside the workdir remains enforced** (writes outside workdir are still denied—never requires `danger-full-access`). |
| **Headless browser automation & E2E testing** | **Yes** (via standard MCP) | **Yes** | Register standard MCP in Codex: `codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --headless --isolated` (or `@playwright/mcp`). Standard MCP servers run outside the shell sandbox. |
| **Cloud SaaS connectors** (GitHub, Figma, Gmail, Linear, Slack, Drive, etc.) | Depends on account OAuth | Yes | Install via `codex plugin list` / `codex plugin add <name>` or mount custom stdio/HTTP MCP servers via `codex mcp add`. |
| **Live already-logged-in Chrome window** | No (conflict / interactive consent) | Only via dedicated CDP port | OpenAI's bundled `cua_repl` requires the Codex Desktop Electron IPC pipe and fails in headless `codex exec` (`The browser access host is unavailable`). Use Antigravity's Chrome MCP, Codex Desktop, or launch Chrome with `--remote-debugging-port=9222` and mount `chrome-devtools-mcp --browserUrl http://127.0.0.1:9222`. |
| **macOS Desktop GUI control (`computer-use` / `cua_repl`)** | No | No | Requires interactive **Codex Desktop** app IPC; do not route through headless `dispatch.py`. |

---

## 2. Making the "Hand" More Versatile (Extension Recipes)

### A. Give Codex CLI Headless Browser Control (Chrome DevTools / Playwright MCP)

```bash
# 1. Headless isolated Chrome (recommended for E2E verification, scraping, DOM audits)
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --headless --isolated

# 2. Optional: Playwright MCP
codex mcp add playwright -- npx -y @playwright/mcp@latest

# 3. Verify registration
codex mcp list
```

> **Tip (Sharing a logged-in Chrome browser)**: Avoid `--autoConnect` simultaneously in both Antigravity and headless `codex exec`—Chrome prompts for interactive approval and single-client conflicts can stall headless workers. If you want Codex to inspect a live Chrome profile, launch a dedicated debug Chrome instance (`--remote-debugging-port=9222`) and mount `--browserUrl http://127.0.0.1:9222`.

### B. Add Official Plugins & SaaS Connectors

```bash
# Browse available local + remote curated plugins
codex plugin list

# Install a plugin (e.g., GitHub, Linear, Slack, Google Drive, Figma, Gmail)
codex plugin add <plugin-name>
```

### C. Add Any Custom CLI or Local Skill

- **CLI tools**: Any local CLI (cloud CLIs, database CLIs, SaaS CLIs) works inside `dispatch.py run --network` while still preventing filesystem writes outside the target workspace.
- **Custom MCP servers**: Mount any stdio or Streamable HTTP MCP server with:
  ```bash
  codex mcp add <name> -- <command> [args...]
  # or remote HTTP MCP:
  codex mcp add <name> --url https://your-mcp-endpoint.example.com/mcp
  ```
- **Reusable Skills**: Place skill folders containing `SKILL.md` in `~/.codex/skills/`.

---

## 3. Scenario Routing & Four Mandatory Confirmation Gates

To prevent Antigravity (Brain) from either **silently taking over work you asked Codex to do** or **blindly dispatching unsupported/risky external mutations**, `plugins/codex-auto-router/rules/AGENTS.md` enforces four hard stop points:

| Gate | Trigger | Required Behavior |
| :--- | :--- | :--- |
| **Gate 1 — Dispatch Plan Confirmation** | Any coding/script task dispatched to Codex | Present a concise 3–6 line plan (`cwd`, `isolation`, offline vs `--network`, `--difficulty`, `--quality`, acceptance criteria) and wait for confirmation (waived **only** for safe offline Tier 1 tasks when the user explicitly writes `"run directly"` / `"直接执行"`). |
| **Gate 2 — Network & External Write Gate** | Passing `--network`, or writing/mutating any live cloud/SaaS system (wikis, remote Git/PRs, email, chat, production APIs/DBs) | **Always require explicit confirmation**—even if direct execution was requested. `allow_dispatch.py` also returns `force_ask` whenever `--network` is present. For bulk external changes, require a read-only dry-run checklist first. |
| **Gate 3 — Explicit Dispatch Blocker Gate** | User explicitly says `"delegate to Codex"` / `"派 Codex"` / `"指派 Codex"` | Antigravity must run **at most 3 quick read-only checks**. Never silently absorb the job for minutes. If blocked (missing MCP/plugin, live Chrome conflict, Desktop GUI), stop immediately and present **Option A (Antigravity handles)** vs **Option B (enable in Codex / use Codex Desktop)**. |
| **Gate 4 — Human Merge & Remote Push Gate** | Merging `agy-worker/*` branches or pushing to remote GitHub | Always require explicit user approval (`allow_dispatch.py` enforces `force_ask` on worker branch merges). |

---

## 4. Short Prompt Cheat Sheet (Inside Antigravity)

- **Standard local coding dispatch (plan first, then execute)**:
  > `写黑板，派 Codex 做 <任务>` / `Write BLACKBOARD and delegate <task> to Codex`
- **Direct local Tier 1 execution (skip Gate 1 plan wait)**:
  > `派 Codex 做 <本地编码任务>，直接执行` / `Delegate <local coding task> to Codex, run directly`
- **Networked CLI / API / MCP task (triggers Gate 2 confirmation)**:
  > `派 Codex 开 --network 做 <外部 CLI / API / 无头浏览器任务>`
- **Maximum frontier quality (`--quality max`)**:
  > `派 Codex 用 max 档做 <复杂重构/架构任务>`
- **Keep in Antigravity (do not dispatch)**:
  > `你自己写，别派 Codex` / `Handle this directly, do not dispatch to Codex`
