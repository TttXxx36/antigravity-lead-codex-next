# D05 替代验收路径：真实 Windows 11 CI 与宿主验证分离
2026-11-27。用户要求继续完成验收，使用 GitHub Actions 或其他方式。保留原 D05 必需门槛、D03–D21 条件合并、无真实模型/权限扩张/发布的边界。

## 已取得与新增
- 上一证据提交 ab820b490a92cf0147f3d5afc1edb540f2f49248 的 [Run 45935441825](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935441825) success。
- GitHub 官方 [托管 runner 说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) 列出公开仓库免费的 windows-11-arm。新增此 runner，并强制读取 Win32_OperatingSystem 的 Caption、ProductType、BuildNumber、OSArchitecture，确认真实 Windows 11 工作站而非 Server。记录 Python/Node 进程架构及 checkout SHA。
- 两种 Windows 均增加真实合成 SQLite 文件，验证生命周期后内容和 SHA256 保持不变。仍使用 native mock Codex，未访问真实用户库。
- 首个四环境提交 bd61d684e995d2e5b6f6f18f869ac2d4ab12c583 同时触发 [push run 45935965161](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935965161) 和 [PR run 45935970796](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935970796)，两者同一 concurrency group，push 的三个 job 被取消，PR 排队。为避免重复取消，改为仅 PR trigger，独立 concurrency group。取消不是通过也不是产品缺陷。

## 实际宿主仍须验证
Google 官方 [MCP Apps](https://antigravity.google/docs/mcp-apps)、[插件构建](https://antigravity.google/docs/build-plugins)、[MCP](https://antigravity.google/docs/mcp) 文档表明本地插件可用 agy plugin validate 做格式验证，但不能据此证明 Antigravity App/IDE 实际 initialize；实际 App/IDE 的 MCP 管理器及工具 schema cache 可提供握手佐证。官方下载脚本目前未能在本执行环境获取并核验，因此不执行未经核验的远程脚本；不将账户/凭据注入公开 Actions；不注册公共仓库 self-hosted runner 到用户日常电脑（避免任意工作流访问实际机器）。

安全的剩余路径是用户控制的独立 Win11 测试机/VM，安装官方 Antigravity、实际 Codex exe 与锁定依赖；本地执行真实宿主清单，查看宿主 MCP 连接状态并记录实际 initialize 和 tools/resources 的证据，脱敏后提交 PR #7。无需真实模型请求。官方 CLI validate 可作为额外证据（不是 desktop host PASS）。不上传 token、数据库、完整私有日志。Windows 11 ARM64 OS 测试如成功，只解除 OS 子门槛，不自动解除 host 验收。x64 桌面另如实标未测试。

D06–D22 按现行依赖门禁尚未正式启动，D05 仍 BLOCKED 直到全部必需证据具备；不需要重复获取已授权的条件合并许可。
