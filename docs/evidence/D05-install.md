# D05 托管测试证据
测试 head `06a06c144b4c238adc56baeebe7f8d5809dbeba2`，[Run 45935195557](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935195557) completed/success。初版 `373e055c4eab1512d350d5d4bdaadef3cddf8a6f` [Run 45934981525](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934981525) 也 success。最终版本新增 console-only 生命周期、绝对 exe 覆盖检查、清理探测环境及 MCP 子进程等待。

| 平台 | D04 状态 | D03 Python | D03 Node | MCP 集成 | 安装相关 |
|---|---|---|---|---|---|
| Windows Server 2025 | 13 PASS | 7 PASS | 4 PASS | PASS | All/ConsoleOnly 生命周期、缺依赖、回滚、持久 sentinel、Unicode PASS |
| Ubuntu | 13 PASS | 6 PASS / 1 SKIP | 3 PASS / 1 SKIP | PASS | Bash 语法及 isolated MCP initialize/tools/list PASS |
| macOS | 13 PASS | 6 PASS / 1 SKIP | 3 PASS / 1 SKIP | PASS | Bash 语法及 isolated MCP initialize/tools/list PASS |

实际 Windows 日志：`PASS: install, upgrade, restore, uninstall, reinstall, native MCP initialize, missing dependency, injected rollback, persistent data, Unicode paths, console-only lifecycle`。Unix 握手 protocol 2025-03-26、12 tools。治理台账全部 PASS。Job IDs：Windows 140296694490，Linux 140296694534，macOS 140296694218。Windows-only checks 在 Unix 明确跳过。生命周期为一个组合测试脚本，并非独立统计每个用例。Native mock exe 仅支持 --version，其他操作退出 99；合成 MCP 不调用真实模型，不访问真实 Codex 数据；持久目录测试用 sentinel，不声称真实 SQLite 迁移或 Antigravity 宿主通过。未测试真实 Win11 桌面；卡状态 BLOCKED。

## Windows 11 ARM64 真正 OS 补测（2026-11-27）
[Run 45936238126](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45936238126) completed/success，精确测试 head `9813f19c222a858f2a4f7cf217702f62252cc540`，四个 job 均 success。Windows 11 Enterprise / 10.0.26200 / Build 26200 / ProductType 1 / ARM 64-bit Processor；Node 22.23.5 win32 arm64、Python 3.12.10 ARM64；13/13 状态、7/7 Python 平台、4/4 Node 平台、真实本地 MCP 合成客户端和完整 PowerShell 生命周期均 PASS。Windows Server 2025 x64 同样通过新增 SQLite SHA256/内容断言；Linux/macOS 回归 PASS。Windows 两种架构均通过 install/upgrade/restore/uninstall/reinstall、ConsoleOnly、Unicode、missing dependency、injected rollback、持久数据及 SQLite bytes preserved。Job IDs: Win11 140299982943、WinServer 140299983157、Ubuntu 140299983213、macOS 140299983240。原 push/PR 重复取消不计入 PASS。实际 Win11 OS 子门槛已取得 ARM64 证据，真实 x64 桌面及 Antigravity App/IDE 登录宿主仍 NOT_RUN；native mock CLI 仅 --version，0 真实模型调用，不冒充真实宿主。
