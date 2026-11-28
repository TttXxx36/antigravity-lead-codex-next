# Antigravity Lead Codex Next

**让 Antigravity 负责计划和验收，让本地 Codex CLI 负责受控执行，用 Codex Console 查看任务进度。**

[English](README_EN.md) · [安装与实机验收](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/LOCAL_ACCEPTANCE.md) · [问题反馈](https://github.com/TttXxx36/antigravity-lead-codex-next/issues) · [CI](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46082096138)

> **版本提示（2026-11-28）**：V2.0 RC.1 是待实机验证的源码候选，不是稳定版。已验证的完整候选为 `c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56`，四平台 CI 通过；D00–D04 正式 DONE，D05–D22 正式 BLOCKED。main 仍是旧功能基线；不要从 main 或上游安装命令安装 Next 候选。GitHub Release 尚未确认发布；可先按下方精确提交安装。真实桌面、模型用量、权限及生产迁移尚未验收。

## 1. 这个项目能做什么？

| 组件 | 作用 | 你如何使用 |
|---|---|---|
| Antigravity（Brain） | 规划、任务拆分、审核、人工确认 | 在聊天中描述目标和验收条件 |
| Codex Console | 本地 MCP App，查看任务、子代理、协作绑定和事件 | 在 Antigravity 打开侧栏或用 MCP 工具 |
| Multi-Agent Dispatch（Hand） | 调用本地 Codex CLI、隔离 Git Worktree、保存任务状态 | 通过 Antigravity 派发或 PowerShell/Bash 命令 |
| Codex Auto Router | 路由规则与审批门禁 | Full 安装包含；Windows 自动审批保持关闭 |

```text
你 → Antigravity（计划 / 审核） → 人工确认 → Dispatch → Codex CLI
       ↑                                         ↓
       └──── Codex Console（状态 / 结果 / 事件）← 任务状态与独立 Worktree
```

适合多文件开发、重构、测试、任务追踪与审查。不是独立模型、不是 API 代理，也不赠送 Codex 额度；你需要自己的 Antigravity 和 Codex 环境。只查看已有本地任务不要求启动新模型。工作区离线策略不代表 Codex 服务自身无需联网。当前没有可信正向授权或生产 App Server 路由，不能用它绕过宿主权限。

## 2. 先选择安装模式

| | ConsoleOnly | All（完整模式） |
|---|---|---|
| 适用人群 | 只想查看本地任务 | 需要学习派发、Worktree 和审查 |
| Node.js / npm / Codex CLI / Antigravity | 必需 | 必需 |
| Python 3.10+ / Git | 控制台安装可不需要；Git 用于下方克隆 | 必需 |
| Windows PowerShell | 7.2+ | 7.2+ |

建议初学者先 ConsoleOnly，熟悉界面后再 All。Node 22.5+ 且必须支持 `node:sqlite`，推荐 Node 22 LTS 系列。Antigravity 需支持 MCP Apps，Codex 使用官方本地 CLI（需真实模型时请自行完成合法登录）。工具安装与账户设置由用户负责。Ubuntu、macOS、Windows Server x64、Windows 11 ARM64 已有合成/Mock CI；真实 Antigravity 桌面尚未认证。

## 3. 获取正确版本（所有系统）

以下命令下载公开仓库，需要网络。使用独立目录，不要覆盖已有工作树；首次下载后固定到已验证 SHA。

```bash
git clone --branch dev/d22 https://github.com/TttXxx36/antigravity-lead-codex-next.git antigravity-acceptance
cd antigravity-acceptance
git checkout --detach c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56
git rev-parse HEAD
```

输出必须等于上述完整 SHA。固定版本中的 README 是历史版本；请继续使用 [新版教程](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d22/README.md)。Git clone 不是规范 RC 归档；如从 [Releases](https://github.com/TttXxx36/antigravity-lead-codex-next/releases) 获取 RC，须确认实际 tag 已存在，并对照可信 SHA256SUMS、commit、版本及清单验证。[规范源码包校验方法](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/RELEASE_CANDIDATE.md)。不要下载上游 Koala973 的安装脚本来安装本项目。

## 4. Windows 11 原生安装（推荐先在隔离配置测试）

### 4.1 检查环境

打开 PowerShell 7（`pwsh`），进入源码根目录。以下检查不启动模型。

```powershell
$PSVersionTable.PSVersion
node --version
node --no-warnings -e "require('node:sqlite')"
npm --version
python --version
git --version
codex --version
```

如果 `codex` 不在 PATH，可用真实 `codex.exe` 的绝对路径。不要传 `.cmd` 包装器代替 exe。Python、Git 在 ConsoleOnly 安装时可选，但完整模式必须可用。

### 4.2 准备依赖

源码不含 node_modules，UI 已预构建。确认允许网络获取锁定 npm 依赖后执行（不执行包安装脚本）；不允许联网时，须预先准备同一锁文件的可信缓存/依赖，否则停止。安装器本身不会自动下载依赖。

```powershell
Push-Location plugins/codex-console
npm ci --omit=dev --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
Pop-Location
```

### 4.3 配置隔离路径并安装

关闭待测 Antigravity 和受管任务。用全新的测试目录，避免指向日常数据库。以下示例只安装到测试 config；它不会自动让真实 Antigravity 切换配置目录。要验证 UI，须在宿主支持并明确选择相同的隔离 profile 后手动重启。先使用空 CodexHome 或合成状态；没有真实会话时控制台为空是正常结果。

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

若命令找不到 Codex，请把 `$codexBin` 改成经核验的绝对 exe 路径；Node/Python/Git 亦可用 `-NodeBin`、`-PythonBin`、`-GitBin` 显式指定。要在相同隔离配置安装完整组件，关闭宿主后再执行：

```powershell
& ./scripts/install.ps1 -Mode All -CodexBin $codexBin @paths
& ./scripts/doctor.ps1 -GeminiConfigDir $paths.GeminiConfigDir
```

预期：安装输出配置路径和 Backup 事务目录，doctor 输出 Status=PASS（本地合成 MCP 握手），不代表真实宿主 UI 已通过。保留 `$paths` 和 Backup 路径，后续操作必须使用同一配置。安装生成的 MCP 配置在 `config/plugins/codex-console/mcp_config.json`。不要手动改成生产数据库路径来消除空列表。

详见 [Windows 安装](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/WINDOWS_INSTALL.md) 与 [D05 实机检查](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/evidence/D05-WINDOWS11-acceptance.md)。

## 5. macOS / Linux 安装

在独立测试账户或明确隔离的环境中，检查 `node --version`、`node --no-warnings -e "require('node:sqlite')"`、`npm --version`、`codex --version`，完整模式再检查 `python3 --version`、`git --version`。不要从网络 pipe 执行脚本。

> Unix 旧安装脚本会替换组件目录并执行 npm ci，可能运行依赖安装脚本；不是 Windows 那样的事务安装器。仅在确认依赖网络/脚本权限、备份和目录隔离后运行。用 `npm_config_ignore_scripts=true` 保持本次锁定安装禁用生命周期脚本。清除热加载变量。测试账户需隔离原生 Codex 数据和控制台数据（仅修改 GEMINI_CONFIG_DIR 不会自动隔离所有数据）。

```bash
export GEMINI_CONFIG_DIR="$HOME/.gemini/config-alc-rc-test"
export CODEX_HOME="$HOME/.codex-alc-rc-test"
export AGY_DISPATCH_STATE_DIR="$HOME/.local/state/alc-rc-test"
unset ANTIGRAVITY_CSRF_TOKEN ANTIGRAVITY_LS_ADDRESS
npm_config_ignore_scripts=true bash scripts/install.sh --console-only --no-build
bash scripts/doctor.sh
```

完整模式将 `--console-only` 换成 `--all`。只有在隔离账户的默认插件 data 目录也安全时才启动宿主。不要把此命令用于日常配置。真实宿主需自行指向相应 profile；[迁移与回滚](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/MIGRATION.md) 说明旧安装方式及限制。

## 6. 第一次打开 Codex Console

1. 确认 Antigravity 正在使用安装时的测试配置目录；手动重启宿主。
2. 在 MCP Servers / Customizations 检查 `codex-console` 是否加载，尝试右侧辅助面板 `+` → `Codex Console`（实际菜单随宿主版本变化），或请 Antigravity 调用 `open_codex_console`。
3. Tasks 查看本地会话；Subagents 查看派发任务；Collab 查看 Change/Goal 与 Thread 绑定。选择任务可查看状态和审计信息；置顶、隐藏、别名保存在控制台自有数据中，不等于删除 Codex 会话。
4. 若没有测试会话、数据库或可用宿主集成，停止在此处记录 NOT_RUN/空列表，不创建真实模型任务来填补。先不要点击实时额度刷新、只读诊断、发送消息或派发按钮；这些可能启动原生服务或实际模型。

在 Antigravity 聊天中可直接使用下面的话（仅请求本地只读信息）：

> 打开 Codex Console。使用 task_list 列出最多 10 个本地任务，只汇报任务 ID 和状态，不调用模型，不查询实时额度，不发送消息，不修改文件。

> 对指定 taskId 调用 task_status 和 task_result，只给出紧凑结果、验证状态和阻塞原因。worker 的自报结果不是独立验收。

## 7. 从零学习派发任务（完整模式）

以下示例使用另一个**测试项目**，不是 Next 源码仓库，也不是你的生产项目。Worktree 需要 Git 至少一个 commit；未提交修改不会进入新 Worktree。先创建测试 Git 仓库并提交合成文件，或者选择干净的已有测试仓库。用 `--isolation worktree` 明确拒绝非 Git 回退。

### 可选：亲手创建一个不含私有数据的练习仓库

如果你从未使用 Git，在 Windows PowerShell 执行（Git 需已安装）。这里只在新建练习目录使用演示提交身份，不修改全局 Git 配置。

```powershell
$repo = Join-Path $testRoot 'demo-project'
New-Item -ItemType Directory -Path $repo -ErrorAction Stop | Out-Null
git -C $repo init
git -C $repo config user.name 'RC Demo'
git -C $repo config user.email 'demo@example.invalid'
@'
def add(a, b):
    return a + b
'@ | Set-Content -LiteralPath (Join-Path $repo 'calculator.py') -Encoding utf8
git -C $repo add calculator.py
git -C $repo commit -m 'Create disposable example'
git -C $repo status --short
```

最后一条命令在干净仓库应无输出。现在可以用 `$repo` 作为下方目标，不需要改生产项目。可以明确要求 Codex 为 `calculator.add` 生成 `test_calculator.py`，用 `python -m unittest discover -v` 验收；先做 dry-run，实际调用须批准。

### 7.1 在 Windows 查看健康状态和预演

继续使用 4.3 的变量（若新开终端，先还原相同路径）。

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
```

把 `$repo` 改成你的隔离测试项目绝对路径（需有已提交 HEAD）：

```powershell
# 如果上一节已创建练习仓库，保留 $repo；否则改成实际路径。
# $repo = 'C:\path\to\your-test-repo'
& $python $dispatch run --cwd $repo --isolation worktree --difficulty low --quality smart --prompt '为一个简单函数补充单元测试；仅修改测试文件；运行本地测试并汇报。' --dry-run
```

预演不启动 Codex worker；检查输出的 workdir、sandbox、network、routing。health/status 可能读取本地路径与状态，甚至初始化自身状态目录；不要公开原始输出。失败时先修复配置，不删除状态。

### 7.2 经你明确批准后，执行真实测试任务

下面的实际 run/resume 会启动 Codex CLI 并可能消耗模型额度；仅在隔离测试项目、合法账户及明确批准后执行。示例不要求联网执行 shell 命令、不允许远程推送。

```powershell
& $python $dispatch run --cwd $repo --isolation worktree --difficulty low --quality smart --task-id demo-tests --timeout 300 --prompt '为一个简单函数补充单元测试；仅修改测试文件；运行本地测试并汇报变更和失败。'
& $python $dispatch status --task-id demo-tests
```

任务 ID 必须唯一，重复运行示例前换一个新 ID；若任务失败或未知，不要盲目重派。查看返回的 worktree_path/branch（`agy-worker/...`），在该 Worktree 人工检查 `git status --short`、`git diff` 与项目测试。只有已完成且允许续跑的受管任务才可在确认后使用：

```powershell
& $python $dispatch resume --task-id demo-tests --prompt '根据已确认的审查意见修复，并重新运行测试。' --timeout 300
```

退出码 0 或 worker 自报完成并不等于独立验收。不要自动合并、推送或删除 Worktree。Unix 完整模式用 `python3 "$GEMINI_CONFIG_DIR/skills/multi-agent-dispatch/scripts/dispatch.py"` 替换 `& $python $dispatch`，并按自己的目录设置 `--cwd`。

### 7.3 在 Antigravity 中直接协作

> 请先制定派发计划：目标仓库、允许修改的文件范围、独立 Worktree、离线 workspace-write、预期测试、超时。等我确认后再调用 Codex；完成后报告分支、变更、测试、阻塞和下一步，不自动合并或推送。

复杂任务先确认任务划分，再使用 `batch --manifest`（JSON 清单，1–4 并发、最多 128 项；独立写任务使用不同 Worktree），或使用明确的 v2 协议。不要把同一任务反复发送。v2 不是默认，request-id、stream-events、blackboard 有额外协议要求：[协议](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/protocols/README.md)。

## 8. 常用命令与功能边界

| 入口 | 用途 | 备注 |
|---|---|---|
| `health`, `status --task-id ID` | 运行时与本地任务 | 不启动模型 |
| `run ... --dry-run` | 预演派发 | 不启动 worker |
| `run`, `resume`, `review`, `batch` | 执行/续跑/模型审查/批量 | 实际调用需要批准；review 不是纯本地 Git 检查 |
| `task_list`, `task_status`, `task_result`, `task_delta` | MCP 紧凑状态/结果 | result 是 worker 声明 |
| `task_events`, `task_logs` | MCP 分页事件/历史元数据 | 使用返回 cursor，流式 v2 保留 taskSeq，旧 epoch 单独标记 |
| `scheduler-status`, `scheduler-reconcile-preview --ticket ID` | 本地调度元数据/恢复预检 | 不回收不确定槽位，不杀活动 worker |
| `orchestrator-status --task-id ID`, `orchestrator-acceptance-preview --task-id ID --expected-revision N` | 编排状态与独立验收证据 | 仅预览，不能授予 completed |
| `cleanup --task-id ID` | 清理预检 | 删除、force 和 delete-branch 当前拒绝 |
| `app-server-status` | 实验适配计划 | 不启动原生服务或生产执行 |
| `state-migrate`, `state-rollback`, `state-recover` | 插件自有状态迁移/恢复 | 高级操作；先停宿主、核验备份与文档，禁止操作原生库 |

`--network`、危险 sandbox、未受管 queue/resume、自动合并和授权扩张不是可用的绕过选项。签名及 SQLite nonce ledger 仅离线证据验证，未接入生产授权。真实 Token 缺失就是 unknown，不以字节数冒充。历史 [CAPABILITIES](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/CAPABILITIES.md) 与 SKILL 示例包含旧版网络/清理说明；以本 RC 实际 parser、运行时拒绝和 [LOCAL_ACCEPTANCE](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/LOCAL_ACCEPTANCE.md) 为准。

## 9. 更新、卸载和恢复

关闭宿主与任务、确认没有未结算请求，备份原有 config、插件数据和 dispatcher 状态及相应数据库 sidecar。不要复制正在写入的 SQLite 文件作为可靠备份。

Windows（仍使用原 `$paths`，在源码根目录执行）：

```powershell
& ./scripts/install.ps1 -Mode All -CodexBin $codexBin @paths
& ./scripts/doctor.ps1 -GeminiConfigDir $paths.GeminiConfigDir
```

升级会保留已知组件的事务备份。若要撤下三个组件或恢复，分别选择下列命令之一；RestoreFrom 必须是原 config 下已 committed 的备份事务路径。

```powershell
& ./scripts/install.ps1 -Mode Uninstall @paths
# 或：
& ./scripts/install.ps1 -Mode Restore -RestoreFrom 'C:\path\to\config\.alc-backups\transaction' @paths
```

数据保留不代表可以不备份。ConsoleOnly 卸载也会处理三个已知组件，请检查是否存在先前安装的 Router/Dispatch；首次无旧组件可恢复时使用卸载。rollback_incomplete 或未知 journal 停止操作并保存现场。Unix 旧卸载会删除三个组件目录，不是事务备份；只在隔离配置且备份完成后按 [迁移指南](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/MIGRATION.md) 操作。

## 10. 常见问题

| 问题 | 处理方式 |
|---|---|
| 找不到 node:sqlite | 用符合要求的 Node，执行 4.1 的检查；指定正确 NodeBin |
| Source dependency/file missing | 在源码 plugins/codex-console 中准备锁定依赖；不要忽略错误 |
| doctor PASS 但没有面板 | 检查测试 profile、插件 MCP config、MCP Apps 支持及实际宿主加载；手动重启 |
| 控制台空白或没有 Codex DB | 测试 CodexHome 可能为空；不自动创建真实任务或读取日常数据库 |
| worktree requires HEAD | 使用有至少一个 commit 的干净测试 Git 项目 |
| network denied / authorization unavailable | 正常安全门禁，不关闭或绕过 |
| 状态不确定 / 重复 request / stream incomplete | 停止重试，检查 status、证据和预检；保留文件 |
| 模型缓存不存在或 Token unknown | 不猜模型或用量；检查本地账户/缓存，先做 dry-run |
| UI 旧版或升级失败 | 核对安装目录和 SHA；保留备份，按迁移指南回退 |

问题反馈请附 OS/架构、Node/Python/Git/Codex/Antigravity 版本、完整 commit、操作命令、退出码、脱敏报错和复现步骤。不要上传凭据、原生数据库、完整聊天、私人路径或未脱敏日志。

## 11. 文档与贡献

| 想了解 | 文档 |
|---|---|
| 安装和实机验收 | [Windows](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/WINDOWS_INSTALL.md) · [集中实机矩阵](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/LOCAL_ACCEPTANCE.md) |
| 回滚和归档验证 | [迁移](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/MIGRATION.md) · [RC](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/RELEASE_CANDIDATE.md) |
| 设计及测试 | [架构](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/ARCHITECTURE.md) · [协议](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/protocols/README.md) · [基准](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/BENCHMARK.md) · [结果](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/RESULTS.md) |
| 当前进度 | [路线图](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/ROADMAP.md) · [剩余工作](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/REMAINING_WORK.md) · [Bug](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/ISSUES_AND_BUGS.md) · [台账](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/EXECUTION_STATUS.json) · [PR #24](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/24) |

固定版本证据：[Run 46082096138](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46082096138) 四环境通过；18 个候选的 72 个环境任务通过不等于 72 项真实功能认证。RC 仍须实际 Windows 11 x64 + Antigravity + Codex、可信权限、独立验收、真实任务和用量验证。欢迎按 [AGENTS](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/AGENTS.md) 提交最小范围、可复现的修复 PR，勿提交真实数据。

## 12. 许可证

本项目独立维护，非 fork。上游 [Koala973/antigravity-lead-codex](https://github.com/Koala973/antigravity-lead-codex)；保留 [来源说明](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/docs/UPSTREAM.md)、[MIT](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/LICENSE)、[上游 MIT](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/LICENSE.upstream)、[历史 README](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/README_UPSTREAM.md) 和 [UI 第三方原始声明](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/c1f2ed2ab1e6ec065b054af94d9430f3d68d9a56/plugins/codex-console/UI-THIRD-PARTY-NOTICES.md)。源码归档不含 node_modules 或原生构建二进制，不提供后者单独再分发授权。
