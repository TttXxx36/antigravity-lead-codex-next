# 集中实机验收（最终累计候选，非正式发布）

用户要求先完成可离线开发、修复、自动化测试，将必须实机的项目集中标注，在完整候选就绪后由用户拉取本地验收。原 D03–D21 条件合并授权、D22 另行批准、真实模型/权限扩张单独批准、Codex 原生数据库只读等边界不变。D00–D04 DONE；D05–D22 正式 BLOCKED。代码候选不是生产版本。

## 版本与安全准备

- 集成试用版本为 dev/d22 / PR #24 的最终经 CI 验证精确 head。在独立 clone/测试环境阅读 README、WINDOWS_INSTALL、MIGRATION、RELEASE_CANDIDATE、各决策卡；不要覆盖已有工作树。main 仍是旧正式基线；不得直接把累计候选合入 main。
- D05 专项基线为 dev/d05 / PR #7：f5e508c27fec644a5eefed0db3a54bd6656bed48，Run 46031037560 四环境 PASS；main 114e0c205f326b4af0935656ef482bba8270b284，ahead 7 / behind 0。待合并 head 若变动必须重核。累计 D22 宿主证据不自动证明每个独立 PR。
- Windows 11 x64（ProductType=1，BuildNumber>=22000，OSArchitecture X64），PowerShell 7.2+、Node >=22.5 且支持 node:sqlite、Python >=3.10、Git、实际本地 Antigravity/Codex。缺锁定依赖或测试 profile 记录 BLOCKED；依赖准备按已有授权，不在生产机擅自联网或更改配置。
- 仅在用户认可的独立临时 profile 及合成数据执行写操作；停止对应宿主/worker、备份并核验，明确分离 GeminiConfigDir、CodexHome、DispatchStateDir、PluginDataDir。不上传原生用户库、账号、完整日志、真实任务；原生 DB 永远只读。不要把日常电脑暴露为公共 self-hosted runner。只做版本/握手无需模型调用。
- 证据填写实际 SHA、OS/arch、应用/工具版本、命令/退出码、脱敏结果、回滚状态、PASS/FAIL/NOT_RUN/UNKNOWN。不得用未授权功能补齐。

## 实机与独立验收矩阵（全部待实际证据）

W=真实 Windows x64/桌面；H=实际宿主/系统边界；A=另行授权（真实模型、可信授权、生产操作或发布）；E=现有候选能力限制，不能用实机 PASS 掩盖缺功能；F=正式依赖和合并。

| 卡 | 类型 | 待验收/限制（详见原卡） |
|---|---|---|
| D05 | W/H | 安装/升级/恢复/卸载/重装；实际 Antigravity MCP initialize/tools/resources，真实 Codex --version，隔离数据不变 |
| D06 | H/A/E | OS sandbox、外部写和联网拒绝；可信宿主签发、范围/时效/重放约束尚无可信来源，全部拒绝不是正向授权功能 |
| D07 | W/H | 实际 Codex 进程树、提前退出、逃逸后代、真实掉电恢复、结果语义；仅 owned process 范围 |
| D08 | W/H | Antigravity/Codex 端到端、Windows x64 发布门禁、实际 DB schema 只读兼容 |
| D09 | H/A | 真实 MCP 宿主 UI/旧客户端兼容、真实 Token 独立测量；不把字节当 Token |
| D10 | H/A | 真模型 structured output、宿主协议与独立验收；v1 默认、v2 opt-in |
| D11 | H/A | 真实会话连续性、断线重连、checkpoint 完整性及实际 Token |
| D12 | H/A | provider usage 字段语义、模型/effort/cache、预算与真实基准；未知用量不得伪造 |
| D13 | H/A | 跨 store reconciliation、实际掉电、可信新请求授权、Git 指纹限制 |
| D14 | W/H/E | UI push/reconnect、活动取消、逃逸后代；新增 append-only 256 KiB 原始日志分段及 taskSeq 跨轮序号候选待 CI；旧版升级 epoch 单独标识，仍有总字节上限，真实 UI/重连须实测 |
| D15 | W/H | 仅插件自有 SQLite，宿主停止后的迁移/恢复激活、掉电、旧版兼容；禁止生产库试验 |
| D16 | W/H | 真实浏览器及旧宿主 UI、物理 I/O、可比较 p95 |
| D17 | W/H/A/E | 实际调度/活动取消/逃逸后代和可信 quota；不自动回收不确定 slot；scheduler-reconcile-preview 导出绑定票据证据，cleanup 使用有界离线 Git 检查，可信回收/删除仍待宿主授权 |
| D18 | H/A/E | 可信独立验收 completed bridge、真实恢复/取消审批；orchestrator-acceptance-preview 导出绑定 revision/结果/risk 的独立验收包，不授予 completed；可信验收仍待宿主授权 |
| D19 | H/A | 独立人/可信宿主审查、真实任务 scope 和 worktree 测试 |
| D20 | W/H/A/E | 实际 App Server 启动/协议与真实任务/权限/usage parity；仅实验探测，CLI 默认，真实生产路由未启用 |
| D21 | H/A | 历史基线与候选真实工作负载、质量、成功率、P0、真实 usage 和模型/effort/cache；合成轮询不是生产 Token |
| D22 | W/H/A/F | 生产等价隔离宿主回滚、前置 D05–D21 正式门禁、完整隐私/分发审查、最终精确源 RC、另行发布授权 |

## 建议本地顺序

1. 只读确认 checkout SHA/clean 状态、Windows OS/架构及工具版本、Antigravity/Codex 版本；按 docs/WINDOWS_INSTALL.md 准备独立测试配置。记录对象 SHA。
2. 运行 pwsh -NoProfile -File tests/test-install-windows.ps1（已准备依赖，native mock，合成状态）。按 D05 清单在隔离 profile 做真实 install All、doctor、upgrade/restore、uninstall/reinstall、Unicode/缺依赖/故障回滚，验证合成 sentinel 及恢复。实际 MCP 握手只 initialize/list/read-only smoke，不调用真实 worker、quota 或用户数据。
3. 在累计候选运行只读 UI、状态、缓存、协议及插件自有 SQLite 隔离 fixture 场景。故障、取消、掉电仅隔离测试任务；未取得真实模型/可信权限许可的项目保持 NOT_RUN/BLOCKED。不执行实际 worktree cleanup。
4. 汇总证据：卡 ID / 精确 commit / 环境 / 命令和退出码 / 测试数据类型 / 脱敏结果 / 备份恢复 / 观察限制。不上传数据库、私人路径或凭据。
5. 正式合并依赖顺序不变。每个实际待合并 head 重核前置 DONE、必要 checks、真实证据、权限和回滚，D05→D21 受控合并后才 DONE。D22 保持 Draft，正式合并及发布需明确批准。最新 D05 文档祖先变更须在正式依赖阶段按非重写方式协调，不重复整栈开发。

| 卡/门槛 | 精确 SHA / 环境 | 状态 | 命令 / 退出码 / 脱敏证据 | 恢复结果 |
|---|---|---|---|---|
| D05 Windows 11 x64 / host | | NOT_RUN | | |
| D06–D22 依上表逐项增行 | | NOT_RUN | | |

没有实机或授权的项明确留下 NOT_RUN；现有工程限制 E 必须单独解决，不能因为 Windows 测试成功自动关闭。
