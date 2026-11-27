# 问题、缺陷与风险登记册

更新时间 2026-11-27。来源：固定上游 v1.0.2、D01 原始/候选 Actions、已归档函数级观测及决策卡。已复现与待验证风险分开，优先级为本次整理建议。候选通过不是 main 已修复。

## 已实际复现

| ID | 优先级 | 现象/根因 | 证据 | 归属 | 状态与回归要求 |
|---|---|---|---|---|---|
| BUG-001 | P0 | 缺少结构化报告仍判验证通过 | D07 Run 45937506260 | D07 | CANDIDATE_PASS；缺报告 partial/verification false，未合并 |
| BUG-002 | P0 | 非零退出仍判 completed | D07 Run 45937506260 | D07 | CANDIDATE_PASS；非零退出强制 failed，未合并 |
| BUG-003 | P0 | 损坏 JSON 被静默覆盖 | D04 Run 45934605595 | D04 | FIXED；PR #6 已合并 |
| BUG-004 | P0 | Windows 无 fcntl，dispatcher import 失败 | D04 Run 45934605595 | D04 | FIXED；原生锁与跨进程回归 PASS，PR #6 合并 |
| BUG-005 | P1 | MCP 测试依赖 Bash，原版 Windows NOT_RUN | D03/D05 CI | D05/D08 | 原生测试启动已合入 D03；实际安装候选 D05 托管 PASS，真实宿主待验收 |

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
| ENV-05 | 真实桌面环境证据缺失 | Windows 11 ARM64 OS 已通过；真实 x64 桌面、Antigravity 宿主及真实 Codex 版本仍未验证 |
| ENV-06 | 缺真实模型用量及预算许可 | UNKNOWN；不宣称节省达标 |
| ENV-07 | 历史 D01/D02/PR #4 未获合并许可 | D01/D02 已合并；D03–D21 已获条件许可；PR #4 独立候选保留 |

见 [CI 证据](evidence/CI-RUNS.md)、[剩余路线](REMAINING_WORK.md)。缺陷关闭要求对应修复 commit、反向断言、三平台结果及人工验收；仅有候选不能标 CLOSED。

## D03 当前候选

RISK-01：已实现明确的运行时解析、统一配置路径、PATH 分隔符和 UTF-8；候选测试待 CI。BUG-004：复用 PR #4 基本锁作为 Windows 导入前置，D04 尚需完成数据完整性及竞争回归。BUG-005：原生 Node 测试入口复用，实际安装/宿主未验证。BUG-001/002/003 OPEN。

### D03 实测更新

[Run 45933533805](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45933533805) 三平台平台测试、治理检查和原生 Node MCP 通过。RISK-01 候选 PASS，尚未合入 main，真实 Codex exe/Antigravity 及超长实际 I/O 未验证。BUG-004 的基础锁、BUG-005 的测试启动器已在 D03 候选复用；D04 数据完整性/原子预留、D05 实际安装、D06 shell/权限仍待实施。原始 BUG-001/002/003 仍 OPEN。
D03 最终：RISK-01 路径/原生 exe 解析及长路径 fixture 已通过三平台并合入 main（PR #5）；实际宿主、安装仍待测。BUG-004 基本跨平台锁已合入，D04 完成竞争、损坏和崩溃回归后才关闭。BUG-005 原生 Node MCP smoke 已通过，D05/D08 实际安装及完整回归仍待。
D04 候选 BUG-003/004、RISK-02：损坏状态拒绝覆盖，基础锁增加限时竞争、原子备份写入、任务 ID/路径校验；待 CI，不标关闭。
### D04 最终验收
BUG-003、BUG-004：FIXED（PR #6 已合并）；RISK-02 针对重复 ID、路径穿越、大小写碰撞、原子预留和崩溃锁释放的回归 PASS，当前受信任状态目录模型下已处理。仍不声称恶意同 UID 改写或断电级事务安全。BUG-001/002 OPEN（D07）。[实测](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934605595)。
D05 RISK-03/BUG-005：原生安装及 MCP 配置候选；不删除数据，不自动联网。待托管生命周期与实际桌面验收。
### D05 实测更新
RISK-03：候选安装器完成，Windows Server 2025 的原生安装/升级/恢复/卸载/重装、ConsoleOnly、真实本地 MCP initialize、缺依赖及注入失败回滚均 PASS；Linux/macOS 回归 PASS。[Run 45935195557](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935195557)。ENV-05 仍阻塞真实 Windows 11/Antigravity host 验收；D05 未合并，不声称真实客户端已修复。未发现新的已确认产品 Bug；已加固 ConsoleOnly 缺可选 Python/Git 字段、绝对 exe 覆盖、探测环境和进程清理，均通过最终托管测试。
### D05 Windows 11 补测
RISK-03/BUG-005：四环境 Run 45936238126 success；Win11 ARM64、WinServer x64 SQLite 原始字节保持和生命周期通过。BUG-005 原生启动器已合入 D03；真实宿主缺失，D05 尚未合入。初次四环境 push/PR 同组取消是 CI 配置问题，已改 PR-only，最新四 job 通过；不计为产品 Bug。

D06 RISK-04：候选执行层拒绝无可信授权的联网、危险 sandbox、未受管 resume/queue 和批清单权限绕过，取消自动额度 app-server 连接；可信宿主签发、OS 权限及真实外部写验证待补，未合并。

## 实际四环境 CI（候选开发就绪，不是正式验收）
[Run 45937059171](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45937059171) completed/success，精确 tested commit `b652c5877df2e5a91d5191e1f21fab8c208b3015`；Windows 11 ARM64、Windows Server x64、Ubuntu、macOS 四个 job 均成功。每环境执行5项执行策略、5项 dispatch/hook、18项治理测试（合计112次通过），并运行 D03/D04 平台/状态回归、真实本地 MCP synthetic 及 Windows 原生安装生命周期。真实模型测试未执行。D06 否决未授权操作的候选可作为后续开发基础；可信宿主签发任务/范围/有效期授权、实际 OS sandbox、外部写与真实宿主验证仍 BLOCKED；不得将全部拒绝冒充完整授权功能。PR #8 base dev/d05 保持 Draft，未合并。


D07 BUG-001/002 修复候选已实现，等待 CI；不关闭缺陷或冒充真实客户端验证。RISK-05 受管进程超时、重复终态和崩溃保守恢复候选。

## 实际四环境 CI（候选通过）
[Run 45937506260](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45937506260) completed/success，测试 commit `8e472999c84f1a41dd188a5766d6bd4de7bd02a5`；Windows 11 ARM64、Windows Server x64、Ubuntu、macOS 各7项 Python outcome +4项 Node outcome（共44/44 PASS），真实本地父子进程超时 marker 未出现，缺报告与非零退出反向断言、启动失败、终态重复事件和重启孤儿状态通过。D06 策略、Hook、治理及 D03–D05 累计回归通过。旧 BUG-001/002 为 CANDIDATE_PASS，尚未合入 main；真实 Antigravity/实际 Codex worker 的进程树、逃逸/提前退出根进程及真实掉电未验收，不能据托管结果标 DONE。D07 候选允许后续依赖开发；PR #9 base dev/d06 保持 Draft。

D08 RISK-06 候选实现：>250 历史会话、歧义、只读 SHA、schema 错误、真实 Git Unicode rename 回归；待 CI；不关闭真实宿主风险。

## 首轮 CI 失败及修复
Run 45937983884：Windows x64/ARM64 的真实 Git fixture 初始化失败，Git for Windows 拒绝 Node os.devNull（\\.\nul）作为 GIT_CONFIG_GLOBAL，报 Invalid argument；纯解析测试通过，真实 rename 尚未执行。改用隔离临时空配置文件，禁止读取用户全局配置及 hooks；保留原始失败，重新四环境测试。此为测试环境配置兼容缺陷，不冒充生产 parser 已失败或已修复。

## 四环境修复后实测（候选通过）
[Run 45938086882](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45938086882) completed/success，tested commit `5ab0c7db084b87701bb3d5d5f60fc512f833dc7f`；Windows Server x64 (140305829193)、macOS (140305829410)、Ubuntu (140305829450)、Windows 11 ARM64 (140305829483) 四个 job 均 success。Git parser + 原生文件系统 rename 各2项，共8/8 PASS；MCP 集成测试四环境均通过 >250 历史任务（300条 fixture）、歧义、只读哈希及 schema 错误断言；累计回归及两个 Windows 安装生命周期 PASS。首轮失败保留，Git 全局配置改隔离临时空文件后通过。真实 Antigravity/Codex 宿主端到端与 Windows x64 桌面仍 NOT_RUN；候选可用于 D09，不代表正式验收或发布。PR #10 base dev/d07，Draft，未合并。

D09 RISK-07：候选紧凑 JSON 单 text、状态/结果/增量/操作状态/日志元数据游标，保留原 UI；CI 待测，真实宿主 visibility 和 Token 未验收。


## D09 补测
初次 [Run 45938576927](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45938576927) 四环境 PASS。补充正向操作状态与当前结果绑定：Python 在原子写入后发布 turn + SHA256，Node 只读取精确状态绑定的 artifact；旧记录无引用时返回不可用，不以扫描旧目录冒充当前结果。校验 ID/session/exit/task status、大小、链接路径；不承诺对恶意本地同权限并发改写的 OS 级隔离。补测含运行中、内容篡改、错误身份、过大、缺失 turn、链接/junction。真实模型/宿主仍未测。复检待执行。

## D09 补测最终候选结果
[Run 45940757723](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45940757723) completed/success，tested commit `99c0e5544bf03c1702fee7b7deb1a196b9fba502`。Ubuntu (140314263163)、Windows Server x64 (140314263322)、macOS (140314263379)、Windows 11 ARM64 (140314263404) 四个 job 全部成功。正向操作状态、当前 artifact SHA256/身份、running/stale/missing/oversized/identity/link 拒绝及实际 Mock run/resume 结果引用验证均通过；累计回归和两种 Windows 安装生命周期通过。真实模型调用 0；真实 Antigravity 可见性/UI、实际 Token、真实宿主及前置正式合并仍 BLOCKED。旧数据无 result_ref 不推断；日志只返回事件元数据；内容哈希不是持久 revision。D09 候选可作为 D10 基础，PR #11 Draft，未合并。

D10 RISK-07/08：新增显式 v2 协议、revision 与短报告候选，保留 v1；实际模型 structured output 能力、Token 与宿主仍 NOT_RUN；待 CI。


D10 review follow-up: enforce raw-byte report limit before decoding or stripping whitespace; malformed deeply nested JSON fails closed; document result schema, expose persisted v2 revision in compact managed status, and flag truncated risk lists. Initial CI run 45941194963 superseded by final candidate revision (Ubuntu initial success observed); final head must be independently tested.

## D10 最终候选实测
[Run 45941283814](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45941283814) completed/success，精确代码 head `5e937fcb4de98d0df60cef144b81e8f619f9e550`；Ubuntu、macOS、Windows Server x64、Windows 11 ARM64 四环境全绿。各环境6项协议测试及1项实际 Mock run/resume revision 回归（28次新增测试），累计 D03–D09 回归通过。首轮 45941194963 因后续修正被取消，不计为通过。真实模型 structured output、真实宿主及实际 Token 未验证；v2 仍显式选择，batch/MCP 默认 v1。D10 候选可复用，正式验收 BLOCKED，PR #12 Draft 未合并。


## 候选实施
显式 --protocol-v2 --blackboard 建立任务内稳定目标/范围/验收、sandbox/固定基线 SHA、版本和摘要引用，原子状态锁保存；普通 resume 仅发送短 delta，不再发送稳定字段；阈值 8 轮或累计本地 prompt 16384 UTF-8 字节（不是模型上下文/Token），超限需提供人工审阅 checkpoint 并显式 --rebuild-context，新会话保留稳定目标/约束、决策与未完成项。固定 session 身份、拒绝其他/退役会话、revision 及摘要校验；崩溃未完成状态不自动重试。黑板不采集环境变量、原始日志或模型回复，常见密钥模式拒绝，不能保证识别任意秘密，禁止输入秘密。旧 v1/旧 v2 路径不变。真实宿主、断线后真实 session、实际 Token 和人工 checkpoint 完整性未验收。

D11 审查补测：黑板约束随 sandbox 收紧保持一致，禁止后续升级；旧协议任务不得占用其他黑板的当前/退役 session；新 Python 进程读取已持久化黑板并校验摘要后继续 Mock 恢复。真实网络断线、外部客户端绕开 dispatcher 或 OS 级同权限篡改未验收。首轮 Run 45945559903 被后续修复替代，最终 head 单独测试。