# D05 真实 Windows 11 验收清单（尚未执行）
本清单供用户的 Windows 11 环境或本地 Codex 执行。**当前全部真实宿主项 NOT_RUN**；不能把 GitHub Windows Server 2025 或 isolated doctor 替代实际宿主测试。无需真实模型调用，不要执行派发、quota 或联网操作；不扩权限。先停止 Antigravity 与 worker，备份数据；优先在可恢复的测试配置/测试机执行，未经授权不要修改生产配置。

## 1. 获取并核对版本
使用可信 checkout 的 dev/d05（PR #7）最新 head，`git status --short`、`git rev-parse HEAD`，记录准确 SHA。核对已安装 PowerShell 7.2+、Node >=22.5 node:sqlite、Python >=3.10、Git、真实本地 Codex exe 的 --version。运行 `Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,ProductType`，确认 Windows 11 桌面（ProductType 1，实际版本及架构）。不要上传私有路径、密钥、数据库、完整日志。锁定 npm 依赖需已准备；缺失即 BLOCKED，未经授权不联网安装。

## 2. 本地原生生命周期
参考 [Windows 安装说明](../WINDOWS_INSTALL.md)，明确实际测试 config、PluginDataDir、DispatchStateDir、CodexHome；备份原件并确认目录分离。先在临时目录运行 `pwsh -NoProfile -File tests/test-install-windows.ps1`（本地 native mock，不用真实模型；依赖已准备，需 .NET Framework csc）。再以真实安装环境（用户明确允许的测试配置）执行 install All、doctor、升级、备份恢复、卸载、重装。确认原用户数据库/数据不被删除；用测试 sentinel 或在宿主关闭时比对已备份数据，绝不上传原数据库。记录每步命令、退出码、journal 状态和脱敏证据。发生错误停止、保留备份、记录 FAIL，不手动覆盖失败证据。

## 3. Antigravity 实际宿主握手
在真实 Windows 11 Antigravity 中使用上述安装的测试配置，重启/加载 MCP 插件，核对实际启动命令为 native node.exe，server/index.mjs，正确独立数据路径；从宿主诊断/日志核验 MCP initialize 成功、tools/resources 可列出。不要触发模型、quota、worker 或真实用户数据查询。记录 Antigravity 版本、成功/失败的 initialize/能力协商证据（脱敏），不把 doctor 的合成进程日志冒充宿主日志。恢复原配置并保持备份。

## 4. 回传结果（填实际值；未执行保持 NOT_RUN）

| 门槛 | 状态 | 证据/退出码 |
|---|---|---|
| Windows 11 OS/架构/checkout SHA | NOT_RUN | |
| Native install / upgrade / restore | NOT_RUN | |
| Uninstall / reinstall / data preserved | NOT_RUN | |
| Unicode / missing dependency / rollback | NOT_RUN | |
| Real Antigravity MCP initialize and tools/resources | NOT_RUN | |
| No actual model test / permissions unchanged | NOT_RUN | |

记录真实版本、SHA、实际结果、已知限制、备份/回滚路径（可脱敏）。可将报告提交 PR #7 评论或提供给开发代理；只有必需证据完整且精确 head 的 Actions 通过才按既有条件授权合并。D06 之后依赖 D05 DONE，不重复请求已获合并许可。