---
name: codex-console
description: >-
  Use the Codex Console MCP server and side-pane UI to visualize, inspect,
  diagnose, queue/resume, and track cross-session Change-to-Codex-Thread
  bindings across local Codex CLI exec sessions, Desktop threads, and
  multi-agent-dispatch Worktrees.
---

# Codex Console（Antigravity 侧栏可视化控制台）

`codex-console` 插件提供：
1. **Antigravity 侧栏 / 左侧全局页面 UI**（MCP App `open_codex_console`），实时聚合 `~/.codex/{state_5,goals_1,queue_1,thread_history_1}.sqlite` 与 `~/.local/state/multi-agent-dispatch/state.json`，解决 Codex 桌面端看不到 `codex exec` / Worktree 派发任务的盲区。
2. **主控编排与 SQLite 跨会话协作工具**（Antigravity Brain 可直接调用）：
   - `open_codex_console`: 打开或刷新侧栏 `Codex Console` 面板（可传 `tab`、`threadId`、`query`）。
   - `list_codex_tasks`: 按项目、状态（`running`/`blocked`/`exec_done`）、`onlyExec` 检索本地 Codex 任务。
   - `get_codex_task_detail`: 读取指定 Codex 会话的最近对话、Goal 状态、Git Worktree 变更与控制台历史诊断。
   - `ask_codex_readonly`: 基于 `codex exec fork --ephemeral -c sandbox_mode="read-only"` 执行非侵入式只读提问或一键诊断卡点，不修改工作区文件、不污染原会话上下文。
   - `send_codex_message`: 通过 `codex queue --resume`（排队唤醒）或 `codex exec resume` / `dispatch.py resume` 向目标会话投递指令，内置 60 秒防重投保护。
   - `spawn_codex_worker`: 调用 `multi-agent-dispatch` 在隔离 Git Worktree（或非 Git 目录 `inplace`）中新建受管子代理，支持按需开启 `network: true`（`--network`，需先过人工确认门禁）并可选写入跨会话绑定。
   - `manage_collab_binding`: 读写 `${PLUGIN_DATA}/console.sqlite` 中的 `Change / BLACKBOARD 任务 ↔ Codex Thread ID` 绑定表与交接日志，供多个 Antigravity 会话共享上下文。

## 推荐使用姿势（Brain ↔ Hand 协同）
- 派发新的多文件编码任务后，调用 `manage_collab_binding(action="upsert", ...)` 记录 `changeKey`、`goalTitle`、`ownerRole`（明确哪些由 `codex` 负责、哪些由 `antigravity` 负责）与 `threadId`。
- 任务疑似卡住或 Goal 阻塞时，优先在控制台点击「一键诊断卡点」或调用 `ask_codex_readonly`，再把诊断结论点「发回当前对话」由 Antigravity 拍板决策。
