# Antigravity Lead Codex Next

**Plan and audit in Antigravity, execute controlled tasks with local Codex CLI, and inspect progress in Codex Console.**

[中文指南](README.md) · [Local acceptance](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/LOCAL_ACCEPTANCE.md) · [Issues](https://github.com/TttXxx36/antigravity-lead-codex-next/issues) · [CI](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46082096138)

> **Status (2026-11-28):** V2.0 RC.1 is a source candidate for local testing, not a stable or host-certified release. The tested commit is `c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56`. Four-platform CI passed. D00–D04 formally DONE; D05–D22 formally BLOCKED. main is the older accepted baseline, not the RC. No GitHub Release publication has been confirmed. Use the pinned checkout below, not upstream install commands.

## 1. What is this project?

| Component | Role | How you use it |
|---|---|---|
| Antigravity (Brain) | Plan, split work, review, ask for approval | Describe your goal and acceptance criteria in chat |
| Codex Console | Local MCP App: tasks, workers, events and collaboration | Open the side pane or call MCP tools |
| Multi-Agent Dispatch (Hand) | Local Codex CLI execution, Git worktrees, durable task state | Dispatch from chat or the terminal |
| Codex Auto Router | Routing rules and confirmation gates | Full installation; Windows automatic approval remains disabled |

```text
You → Antigravity → Human approval → Dispatch → Codex CLI
       ↑                                      ↓
       └──── Codex Console ← task state / isolated worktree
```

Use it for multi-file coding, refactoring, tests and task tracking. It is not a model, API proxy, or source of free quota. You bring your own Antigravity and Codex installation. Local metadata queries need no new model request. An offline workspace sandbox does not mean Codex service transport is offline. Production positive authorization and native App Server routing are not enabled.

## 2. Requirements and install modes

| Requirement | ConsoleOnly | All (full) |
|---|---|---|
| Antigravity with MCP Apps, local Codex CLI | Required | Required |
| Node >=22.5 with node:sqlite, npm | Required | Required |
| Python >=3.10 and Git | Optional for installer; Git needed to clone below | Required |
| Windows PowerShell >=7.2 | Required on Windows | Required on Windows |

Start with ConsoleOnly. Use All when you need worktree dispatch. Install the prerequisites yourself and use your legitimate Codex account for any later authorized model execution. Ubuntu, macOS, Windows Server x64 and Windows 11 ARM64 passed synthetic/mock CI; actual Antigravity desktop integration remains unverified.

## 3. Get the pinned candidate

The following public repository download requires network access. Use a new checkout, not an existing worktree.

```bash
git clone --branch dev/d22 https://github.com/TttXxx36/antigravity-lead-codex-next.git antigravity-acceptance
cd antigravity-acceptance
git checkout --detach c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56
git rev-parse HEAD
```

Check the full SHA. A Git checkout is not the canonical source archive. For a future [Release](https://github.com/TttXxx36/antigravity-lead-codex-next/releases) asset, verify its trusted SHA256SUMS, manifest, source commit and version using the [RC guide](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/RELEASE_CANDIDATE.md). Do not run upstream Koala973 installers for Next.

## 4. Windows native installation

### 4.1 Preflight

Open PowerShell 7 in the source root. These checks do not start a model.

```powershell
$PSVersionTable.PSVersion
node --version
node --no-warnings -e "require('node:sqlite')"
npm --version
python --version
git --version
codex --version
```

Use the actual native codex.exe, not a .cmd wrapper. Python/Git are optional for ConsoleOnly installation, required for All. Prepare the locked runtime dependencies only after approving registry access (no install scripts); otherwise use a previously verified offline cache or stop.

```powershell
Push-Location plugins/codex-console
npm ci --omit=dev --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
Pop-Location
```

### 4.2 Isolated installation

Stop the test host and workers. Do not use daily data paths. This creates a test configuration; it does not automatically change the profile used by Antigravity. Use a host-supported isolated profile for actual UI testing, then manually restart. An empty test CodexHome may produce an empty task list.

```powershell
$testRoot = Join-Path $HOME ('alc-rc-test-' + [guid]::NewGuid().ToString('N'))
$paths = @{
  GeminiConfigDir  = Join-Path $testRoot 'config'
  CodexHome        = Join-Path $testRoot 'codex'
  DispatchStateDir = Join-Path $testRoot 'dispatch'
  PluginDataDir    = Join-Path $testRoot 'console-data'
}
$codexBin = (Get-Command codex.exe -CommandType Application -ErrorAction Stop).Source
& ./scripts/install.ps1 -Mode ConsoleOnly -CodexBin $codexBin @paths
& ./scripts/doctor.ps1 -GeminiConfigDir $paths.GeminiConfigDir
```

If Codex is not on PATH, set `$codexBin` to its verified absolute exe path. `-NodeBin`, `-PythonBin`, `-GitBin` also accept explicit executable paths. For the full suite in the same profile, stop the host, then:

```powershell
& ./scripts/install.ps1 -Mode All -CodexBin $codexBin @paths
& ./scripts/doctor.ps1 -GeminiConfigDir $paths.GeminiConfigDir
```

Keep the original `$paths` and printed Backup transaction directory. Status=PASS is a synthetic local MCP handshake, not desktop certification. Installed configuration: `config/plugins/codex-console/mcp_config.json`. See [Windows notes](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/WINDOWS_INSTALL.md) and [D05 acceptance](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/evidence/D05-WINDOWS11-acceptance.md).

## 5. macOS / Linux

Check Node, npm, node:sqlite, Codex, and (full mode) Python/Git as above. Use a dedicated test account/profile, not production. The legacy Unix installer replaces component directories and runs npm ci; it is not transactional, and may run install scripts. Obtain permission for dependency preparation, back up first, disable lifecycle scripts and unset hot-reload variables. Changing GEMINI_CONFIG_DIR alone does not isolate all data; the test account must isolate its default plugin data too.

```bash
export GEMINI_CONFIG_DIR="$HOME/.gemini/config-alc-rc-test"
export CODEX_HOME="$HOME/.codex-alc-rc-test"
export AGY_DISPATCH_STATE_DIR="$HOME/.local/state/alc-rc-test"
unset ANTIGRAVITY_CSRF_TOKEN ANTIGRAVITY_LS_ADDRESS
npm_config_ignore_scripts=true bash scripts/install.sh --console-only --no-build
bash scripts/doctor.sh
```

For the full suite replace --console-only with --all. Use only a host-supported matching isolated profile. Do not pipe an upstream script from the network. See [migration and rollback](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/MIGRATION.md).

## 6. First use: open the console

1. Verify the host uses your test profile, then restart manually.
2. Check MCP Servers / Customizations and enable the installed Codex Console. Try the right auxiliary pane `+` → `Codex Console`, or ask Antigravity to call `open_codex_console`. Menus vary by host version.
3. Tasks shows local sessions, Subagents shows managed workers, Collab shows Change/Goal-to-thread bindings. Pin/hide/rename is stored in the console's own data; it does not delete native threads.
4. No test sessions or missing database may mean an empty view. Record NOT_RUN if host integration is unavailable. Do not click live quota refresh, AI diagnosis, send or spawn as a first read-only check: they can invoke services or models.

Example prompts for Antigravity:

> Open Codex Console. Use task_list to show at most ten local task IDs and statuses. Do not call a model, refresh live quota, send messages, or change files.

> For the selected taskId, use task_status and task_result. Report compact result, verification status and blockers. Treat worker claims as unverified.

## 7. Learn task dispatch (All mode)

Use a separate disposable test Git repository with a committed HEAD, never the Next checkout or production project. Uncommitted changes are not inherited into a worktree. Explicit --isolation worktree prevents non-Git inplace fallback.

```powershell
$env:GEMINI_CONFIG_DIR = $paths.GeminiConfigDir
$env:CODEX_HOME = $paths.CodexHome
$env:AGY_DISPATCH_STATE_DIR = $paths.DispatchStateDir
$env:CODEX_BIN = $codexBin
$python = (Get-Command python.exe -CommandType Application -ErrorAction Stop).Source
$dispatch = Join-Path $paths.GeminiConfigDir 'skills/multi-agent-dispatch/scripts/dispatch.py'
& $python $dispatch health
& $python $dispatch status
& $python $dispatch --help
$repo = 'C:\path\to\your-test-repo'
& $python $dispatch run --cwd $repo --isolation worktree --difficulty low --quality smart --prompt 'Add unit tests for a simple function; change tests only; run local tests and report.' --dry-run
```

Reuse the same paths when reopening the shell. Replace the placeholder repo with an actual test project. Dry-run does not launch a worker. Health/status may read paths or initialize managed local state; do not publish raw output. Review routing, workspace, sandbox and network before proceeding.

**Actual model execution below is optional and requires explicit approval.** It may use your quota. No workspace network access, remote push or production data.

```powershell
& $python $dispatch run --cwd $repo --isolation worktree --difficulty low --quality smart --task-id demo-tests --timeout 300 --prompt 'Add unit tests for a simple function; change tests only; run local tests and report.'
& $python $dispatch status --task-id demo-tests
```

Use unique task IDs. Inspect the returned worktree_path and agy-worker branch with git status, git diff and project tests. A worker exit or claim is not independent acceptance. Only resume a known eligible managed task with approval:

```powershell
& $python $dispatch resume --task-id demo-tests --prompt 'Fix the reviewed issue and rerun tests.' --timeout 300
```

On Unix use `python3 "$GEMINI_CONFIG_DIR/skills/multi-agent-dispatch/scripts/dispatch.py"` instead of `& $python $dispatch`, and your actual repo path. In chat ask Antigravity to propose a plan (cwd, scope, worktree, offline workspace-write, tests, timeout), wait for confirmation, delegate, then report branch, evidence and blockers. Never auto-merge or push.

Batch manifests support 1–4 concurrent slots and up to 128 tasks. Use independent worktrees for parallel writes. Protocol v1 is default; v2, request IDs, task-local context and streaming require explicit protocol setup. See [protocol guide](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/protocols/README.md).

## 8. Command and tool reference

| Entry | Purpose / boundary |
|---|---|
| health, status --task-id ID | Local runtime and task metadata; no model |
| run ... --dry-run | Preview; no worker |
| run, resume, review, batch | Model execution or review; approval required |
| task_list, task_status, task_result, task_delta | Bounded MCP metadata; results are worker claims |
| task_events, task_logs | Cursor-based event/history metadata; use returned cursor; v2 taskSeq and legacy epoch |
| scheduler-status, scheduler-reconcile-preview --ticket ID | Preview only; no uncertain slot release or worker kill |
| orchestrator-status --task-id ID, orchestrator-acceptance-preview --task-id ID --expected-revision N | Revision-bound evidence; no completed transition |
| cleanup --task-id ID | Preview only; destructive flags denied |
| app-server-status | Experimental plan, no native launch or production route |
| state-migrate, state-rollback, state-recover | Advanced own-state operations; quiescence, backups and explicit consent; never native DB |

Network grants, dangerous sandboxes, unmanaged queue/resume and automatic merges are unavailable. The signed receipt/SQLite replay ledger is offline validation, not production authority. Unknown Token counts stay unknown. Older [CAPABILITIES](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/CAPABILITIES.md) and SKILL examples contain legacy network and cleanup descriptions; the actual RC parser, fail-closed policy and [local acceptance](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/LOCAL_ACCEPTANCE.md) take precedence.

## 9. Upgrade, uninstall and rollback

Stop the host/workers and confirm no unsettled requests. Back up config and separate managed data, including database sidecars when quiescent. Never assume a live SQLite main-file copy is a reliable backup. On Windows reuse the original `$paths`:

```powershell
& ./scripts/install.ps1 -Mode All -CodexBin $codexBin @paths
& ./scripts/doctor.ps1 -GeminiConfigDir $paths.GeminiConfigDir
```

Choose one of these only when required. Restore must use the original committed backup transaction under the same config:

```powershell
& ./scripts/install.ps1 -Mode Uninstall @paths
# OR
& ./scripts/install.ps1 -Mode Restore -RestoreFrom 'C:\path\to\config\.alc-backups\transaction' @paths
```

Uninstall handles all three known components, even after ConsoleOnly; check previous components. Data is preserved, not a substitute for backups. If rollback is incomplete or journal unknown, stop and retain evidence. Unix uninstall removes component directories; see [migration](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/MIGRATION.md) for manual backup/restore. No production rollback certification.

## 10. Troubleshooting

| Symptom | Action |
|---|---|
| node:sqlite missing | Select the correct Node executable, check preflight |
| Source dependency/file missing | Prepare locked runtime dependencies in source plugin directory |
| Doctor PASS but no pane | Verify matching test profile, MCP configuration, host MCP Apps support and restart |
| Empty console / native DB absent | Test home may be empty; do not access daily data or launch models to fill it |
| Worktree requires HEAD | Use a clean committed test repo |
| Network denied / authority unavailable | Expected gate; do not bypass it |
| Uncertain state / duplicate request / incomplete stream | Stop retries and inspect status/evidence |
| Missing model cache / usage unknown | Check local setup, dry-run, do not invent model or Token data |
| Upgrade failure / stale UI | Check path and SHA, preserve backup, follow rollback guide |

Report OS/arch, tool and app versions, exact source SHA, command, exit code, sanitized error and reproduction. Never upload keys, native databases, raw chat/history or private paths.

## 11. Further reading and contributions

- [Windows installation](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/WINDOWS_INSTALL.md), [local acceptance matrix](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/LOCAL_ACCEPTANCE.md), [migration](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/MIGRATION.md), [RC verification](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/RELEASE_CANDIDATE.md).
- [Architecture](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/ARCHITECTURE.md), [protocols](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/protocols/README.md), [benchmark](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/BENCHMARK.md), [results](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/RESULTS.md).
- [Roadmap](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/ROADMAP.md), [remaining work](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/REMAINING_WORK.md), [issues](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/ISSUES_AND_BUGS.md), [ledger](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/EXECUTION_STATUS.json), [PR #24](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/24).

[Run 46082096138](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46082096138) passed all four environments for the pinned source. The 72 passed candidate environment jobs do not certify real host functionality. Actual Windows x64 desktop, trusted permissions, independent completion, real task/usage benchmark and production route are still gated. Follow [AGENTS](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/AGENTS.md) for scoped reproducible PRs.

## 12. License and provenance

Independently maintained, not a fork of [Koala973/antigravity-lead-codex](https://github.com/Koala973/antigravity-lead-codex). [Provenance](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/UPSTREAM.md), [MIT](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/LICENSE), [upstream MIT](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/LICENSE.upstream), [historical README](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/README_UPSTREAM.md), [UI third-party notices](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/plugins/codex-console/UI-THIRD-PARTY-NOTICES.md). The source archive excludes node_modules and native build binaries; it does not clear standalone native binary redistribution.
