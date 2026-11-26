# Changelog

All notable changes to **antigravity-lead-codex** will be documented in this file.

## [1.0.2] - 2026-11-25

### Added / 新增
- **Explicit Dispatch Gates & 4 Confirmation Checkpoints / 显式派发硬门禁与四大确认点**：更新 `codex-auto-router/rules/AGENTS.md`，在用户显式指派 Codex 时强制限制 Antigravity 最多执行 ≤3 步轻量只读预检，禁止静默越俎代庖；补齐派发计划、联网/外部写操作、阻塞上报、分支合并与远端推送四道确认门禁。
- **Opt-In `--network` Sandbox Flag / 受控 `--network` 联网沙箱开关**：`dispatch.py`（`run` / `batch` / `resume`）与 `codex-console` `spawn_codex_worker` 支持按需启用 `sandbox_workspace_write.network_access=true`，解锁外网请求与本机鉴权 CLI，同时继续锁死工作目录外文件写入隔离（绝不降级至 `danger-full-access`）；`allow_dispatch.py` Hook 对 `--network` 强制返回 `force_ask`。
- **Capability Matrix & Hand Extension Guide / 适配场景与扩展手册**：新增 [docs/CAPABILITIES.md](docs/CAPABILITIES.md)，给出三层适配场景矩阵及 `codex mcp add`（如无头 `chrome-devtools-mcp` / Playwright MCP）、`codex plugin add`、`~/.codex/skills/` 实测扩展配方，并补齐单元测试（5/5 通过）。

## [1.0.1] - 2026-11-25

### Improved / 优化
- **Pixel Purple Cat In-Place Meow / 像素紫猫原地停步喵叫**：点击右上角像素紫猫时改为捕获当前实时跑道坐标与朝向原地停步跳跃并冒出 `喵~`，消除回到默认位置的生硬瞬移。
- **Unified Dual-Pane Showcase / 双图实机展示升级**：README 升级为双 2× Retina 零马赛克展示图（`任务` 全景视图 + `子代理` 统一双栏审计视图）。

## [1.0.0] - 2026-11-24

### Added
- **Codex Console (`plugins/codex-console`)**: Native Antigravity MCP App rendering in both the right auxiliary side pane (`aux_pane`) and left sidebar full-page view (`global`).
  - Dual-DB architecture: strictly read-only short-lived queries against `~/.codex/{state_5,goals_1,queue_1,thread_history_1}.sqlite` plus `~/.local/state/multi-agent-dispatch/state.json`, with local persistence (pins, aliases, diagnostic logs, cross-session bindings) isolated in `${PLUGIN_DATA}/console.sqlite`.
  - Apple Notes × Linear minimalist light/dark UI with full-frame violet gradient glow, unified dual-pane layout across all 3 tabs, soft-hide drawer (`已隐藏`), instant hover tooltips, and an original MIT-licensed pixel purple cat status pet (`working` / `strolling` / `sleeping zZz` / `blocked` / click `喵~`).
  - Live Codex Quota Ring in the top bar displaying the tightest bottleneck (`min(5h remaining, weekly remaining)`), with hover popover (per-window progress bars, exact reset countdown, plan tier, reset credits) powered by official `codex app-server` live RPC + instant local rollout fallback.
  - Antigravity-first task prioritization (`零重力拉起 / CLI 派发` pinned above collapsible Codex Desktop sessions).
  - Live auto-refreshing conversation feed (4s when running / 12s when idle), newest-first ordering by default, scroll-position preservation, and clean Markdown rendering.
  - Non-destructive read-only diagnosis (`一键诊断卡点` / `只读提问`) via `codex exec fork --ephemeral -c sandbox_mode="read-only"`.
  - Message dispatch bar supporting `codex queue --resume`, `codex exec resume`, `dispatch.py resume`, and 60s duplicate-send protection.
  - One-click **`发回当前对话`** (`app.sendMessage`) and workspace file open (`com.google.antigravity/toggle-aux-pane`).
  - Cross-session Change ↔ Codex Thread SQLite binding ledger (`跨会话协作` tab + `manage_collab_binding` MCP tool).
- **Codex Auto Router (`plugins/codex-auto-router`)**: Brain ↔ Hand collaboration rules (`rules/AGENTS.md`) and fail-safe PreToolUse merge-gate hook (`hooks/allow_dispatch.py`).
- **Multi-Agent Dispatch (`skills/multi-agent-dispatch`)**: Zero-dependency Python 3.10+ isolated Git Worktree dispatcher with dynamic frontier model discovery and `--quality smart|max|balanced` routing.
- **Tooling & CI**: Portable `bin/run-server.sh` Node 22+ resolver, `scripts/install.sh`, `scripts/doctor.sh`, `scripts/package-release.sh`, `scripts/privacy-check.sh`, and macOS/Ubuntu GitHub Actions CI + Release workflows.
