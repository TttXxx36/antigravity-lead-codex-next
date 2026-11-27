# Windows 原生安装（D05 候选）

目标：Windows 11、PowerShell 7.2+、Python 3.10+（完整模式）、Node 22.5+ 且支持 node:sqlite、Git、真实 Codex 原生 exe。无需 Git Bash/WSL；不使用 shell:true，不自动安装依赖或访问网络，不热重载 Antigravity。Codex 的 --version 是本地探测，不是模型测试。

从可信的独立仓库 checkout 执行，先核对 SHA。锁定 npm 运行依赖需要用户自行准备或已授权的 GitHub Actions（npm ci --omit=dev --ignore-scripts --no-audit --no-fund，在 plugins/codex-console 中）。未获网络许可时不要执行安装依赖命令。预构建 UI 已在 dist/app.html。Windows npm 的 cmd wrapper 不作为 Codex/Python/Node/Git 可执行文件。

```powershell
pwsh -NoProfile -File scripts/install.ps1 -Mode All -CodexBin "C:\path\codex.exe"
pwsh -NoProfile -File scripts/doctor.ps1
```

路径可用 -GeminiConfigDir、-CodexHome、-DispatchStateDir、-PluginDataDir、-NodeBin、-PythonBin、-GitBin、-CodexBin 指定。已存在的用户数据库请先确定其目录并显式传入 -PluginDataDir；默认沿用 ~/.gemini/antigravity/plugin_data/codex-console。数据路径必须与被管理组件目录分离。安装后 MCP config 使用绝对 node.exe、server/index.mjs、独立数据目录及 env；手动重启 Antigravity。真实宿主是否接受配置字段仍需 Windows 11 实机验收，不能以本地 stdio smoke 代替。

升级：再次执行 install。旧组件完整移动至 config/.alc-backups/<transaction>/original，失败回滚，保留 journal.json 和失败候选。关闭宿主及 worker 后执行。卸载仅移动三个已知组件，数据不动；不清除备份。恢复选取已 committed 的备份：
```powershell
pwsh -NoProfile -File scripts/install.ps1 -Mode Uninstall
pwsh -NoProfile -File scripts/install.ps1 -Mode Restore -RestoreFrom "C:\path\config\.alc-backups\transaction"
```
自定义 config 时所有操作传同一参数。Restore 恢复备份存在的组件，不删除其他新组件；首次安装无旧件时使用卸载。进程崩溃/rollback_incomplete 时停止使用，保留目录及 journal，人工检查备份和现场；不自动清空。安装器不是对恶意同 UID 文件改写的安全隔离。

Windows 技能调用（先按审批流程取得授权）：
```powershell
$cfg = if ($env:GEMINI_CONFIG_DIR) { $env:GEMINI_CONFIG_DIR } else { Join-Path $HOME '.gemini\config' }
$dispatch = Join-Path $cfg 'skills\multi-agent-dispatch\scripts\dispatch.py'
$python = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { (Get-Command python.exe -CommandType Application).Source }
& $python $dispatch health
& $python $dispatch status
```
使用安装时的 CODEX_HOME/AGY_DISPATCH_STATE_DIR/GEMINI_CONFIG_DIR 和 exe 配置，PowerShell 参数数组，不使用 Invoke-Expression。Windows 自动审批 Hook 继续关闭，D06 单独验收。Unix install.sh/doctor.sh 保留原状。

D05 必需真实 Windows 11 安装/升级/卸载/重装和 Antigravity 实际 MCP initialize 握手。当前托管 Windows Server CI 只能验证本地原生安装生命周期及 synthetic MCP；真实桌面、真实 Codex 版本及宿主加载需用户环境，不调用模型。

## 已验证和待验证
[Run 45935195557](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935195557) 三平台 success，包含 Windows Server 2025 合成安装全生命周期与 ConsoleOnly。真实 Windows 11/Antigravity 宿主仍 BLOCKED；使用 [实机验收清单](evidence/D05-WINDOWS11-acceptance.md) 提交脱敏证据。不要将本地 doctor 的合成 handshake 当作真实 host 加载。