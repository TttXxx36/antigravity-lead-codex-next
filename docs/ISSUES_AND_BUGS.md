# 问题、缺陷与风险登记册

更新时间 2026-11-27。来源：固定上游 v1.0.2、D01 原始/候选 Actions、已归档函数级观测及决策卡。已复现与待验证风险分开，优先级为本次整理建议。候选通过不是 main 已修复。

## 已实际复现

| ID | 优先级 | 现象/根因 | 证据 | 归属 | 状态与回归要求 |
|---|---|---|---|---|---|
| BUG-001 | P0 | parse_report_file 缺报告且 exit=0 仍给 completed/verification_passed=true | 原版 Linux/macOS 与候选三平台 dispatch-contract.json | D07 | OPEN；必须缺报告不通过 |
| BUG-002 | P0 | exit=7，fallback 报告 completed，仍返回 completed | 同上 | D07 | OPEN；退出/任务/验证三状态分离 |
| BUG-003 | P0 | locked_state 读取损坏 JSON 后写入任务会覆盖原损坏数据 | 同上 | D04 | OPEN；拒绝写入、保留原件和备份 |
| BUG-004 | P0 | Windows 无 fcntl，完整调度器模块 import 失败；原 Python 单测未运行 | Run 45915363640：每个调度器套件 30 NOT_RUN、Python exit 5 | D04 | CANDIDATE_PASS；PR #4 原生 msvcrt + 进程竞争测试，待集成 |
| BUG-005 | P1 | 原 MCP 集成使用 Bash，Windows native 测试 NOT_RUN | 原 Run Windows summary | D05/D08 | CANDIDATE_PASS；PR #4 改 Node 直启，真实安装仍未测 |

## 代码审计线索与后续验收（未声明全部复现）

| ID | 优先级 | 问题/验证目标 | 归属 | 验收要求 |
|---|---|---|---|---|
| RISK-01 | P1 | runner.mjs 使用冒号拼 PATH；子进程文本编码、exe/自定义 HOME 发现 | D03 | PR #4 部分候选，跨平台长路径/保留名称/exe 缺失 |
| RISK-02 | P0 | task_id 路径穿越、重复 ID 或目录预留竞争 | D04 | 校验边界、并发原子预留、重复拒绝 |
| RISK-03 | P1 | Bash install/doctor/MCP config 非 Windows 原生 | D05 | PowerShell 原生真实安装、卸载保留数据 |
| RISK-04 | P0 | POSIX hook 不能安全解释 Windows Shell；batch/resume/MCP 授权边界需审计 | D06 | PR #4 hook 保守 ask；可信宿主、权限回归、无自动联网 |
| RISK-05 | P0 | spawn/error/close/timeout/取消、非零退出、无报告路径可能误终态 | D07 | 进程树清理、重复事件/崩溃恢复、失败不可假通过 |
| RISK-06 | P1 | 历史任务查询快照上限、短 ID 歧义、Git 特殊文件名/rename、DB 异常 | D08 | 201/250+ 历史任务、唯一前缀、porcelain -z、异常可见 |
| RISK-07 | P1 | MCP 全量详情及 text/structuredContent 重复传输；操作状态可见性 | D09/D10 | 实际宿主协议、模型可见负载及 UI 回归 |
| RISK-08 | P1 | 多轮重复上下文、用量重复累加/缺失、无进展重试 | D11–D13 | revision、unknown、预算、幂等及停止策略 |
| RISK-09 | P1 | 执行结束才记录、日志内存开销、状态竞争、全量轮询/重复查询 | D14–D17 | 实时事件、有界日志、插件自有 DB、缓存与资源回归 |
| RISK-10 | P1 | 模型自由编排、真实能力未协商、Token 目标未验证 | D18–D22 | 确定性状态机、风险审查、权限等价、配对基准与发布门禁 |

## 已遭遇的工程阻塞与处理

| 编号 | 事实 | 当前处置 |
|---|---|---|
| ENV-01 | 初始源码导入连接中断 | D00 已恢复、45/45 SHA/mode 完整 |
| ENV-02 | 本地 github.com DNS 失败、依赖不可用 | 改 GitHub 托管三平台 CI；本地网络问题不等于项目缺陷 |
| ENV-03 | 原 5 次本地自检超时 | 保留 2 次实测，后续 Actions 各条件 5 次 |
| ENV-04 | Actions Artifact 14 天留存 | 归档六份 ZIP 摘要、SHA256、链接；保留可下载原件 |
| ENV-05 | 缺真实 Windows 11/Antigravity/Codex 宿主 | 仍 NOT_RUN；GitHub Windows Server 2025 不代替用户桌面 |
| ENV-06 | 缺真实模型用量及预算许可 | UNKNOWN；不宣称节省达标 |
| ENV-07 | D01/D02/PR #4 未获合并许可 | 保持 Draft；按依赖验收，不强推 |

见 [CI 证据](evidence/CI-RUNS.md)、[剩余路线](REMAINING_WORK.md)。缺陷关闭要求对应修复 commit、反向断言、三平台结果及人工验收；仅有候选不能标 CLOSED。

## D03 当前候选

RISK-01：已实现明确的运行时解析、统一配置路径、PATH 分隔符和 UTF-8；候选测试待 CI。BUG-004：复用 PR #4 基本锁作为 Windows 导入前置，D04 尚需完成数据完整性及竞争回归。BUG-005：原生 Node 测试入口复用，实际安装/宿主未验证。BUG-001/002/003 OPEN。

### D03 实测更新

[Run 45933533805](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45933533805) 三平台平台测试、治理检查和原生 Node MCP 通过。RISK-01 候选 PASS，尚未合入 main，真实 Codex exe/Antigravity 及超长实际 I/O 未验证。BUG-004 的基础锁、BUG-005 的测试启动器已在 D03 候选复用；D04 数据完整性/原子预留、D05 实际安装、D06 shell/权限仍待实施。原始 BUG-001/002/003 仍 OPEN。
D03 最终：RISK-01 路径/原生 exe 解析及长路径 fixture 已通过三平台并合入 main（PR #5）；实际宿主、安装仍待测。BUG-004 基本跨平台锁已合入，D04 完成竞争、损坏和崩溃回归后才关闭。BUG-005 原生 Node MCP smoke 已通过，D05/D08 实际安装及完整回归仍待。