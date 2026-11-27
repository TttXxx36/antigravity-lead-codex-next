# D05 托管测试证据
测试 head `06a06c144b4c238adc56baeebe7f8d5809dbeba2`，[Run 45935195557](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935195557) completed/success。初版 `373e055c4eab1512d350d5d4bdaadef3cddf8a6f` [Run 45934981525](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934981525) 也 success。最终版本新增 console-only 生命周期、绝对 exe 覆盖检查、清理探测环境及 MCP 子进程等待。

| 平台 | D04 状态 | D03 Python | D03 Node | MCP 集成 | 安装相关 |
|---|---|---|---|---|---|
| Windows Server 2025 | 13 PASS | 7 PASS | 4 PASS | PASS | All/ConsoleOnly 生命周期、缺依赖、回滚、持久 sentinel、Unicode PASS |
| Ubuntu | 13 PASS | 6 PASS / 1 SKIP | 3 PASS / 1 SKIP | PASS | Bash 语法及 isolated MCP initialize/tools/list PASS |
| macOS | 13 PASS | 6 PASS / 1 SKIP | 3 PASS / 1 SKIP | PASS | Bash 语法及 isolated MCP initialize/tools/list PASS |

实际 Windows 日志：`PASS: install, upgrade, restore, uninstall, reinstall, native MCP initialize, missing dependency, injected rollback, persistent data, Unicode paths, console-only lifecycle`。Unix 握手 protocol 2025-03-26、12 tools。治理台账全部 PASS。Job IDs：Windows 140296694490，Linux 140296694534，macOS 140296694218。Windows-only checks 在 Unix 明确跳过。生命周期为一个组合测试脚本，并非独立统计每个用例。Native mock exe 仅支持 --version，其他操作退出 99；合成 MCP 不调用真实模型，不访问真实 Codex 数据；持久目录测试用 sentinel，不声称真实 SQLite 迁移或 Antigravity 宿主通过。未测试真实 Win11 桌面；卡状态 BLOCKED。