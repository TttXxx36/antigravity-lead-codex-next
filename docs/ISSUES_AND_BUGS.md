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

## 最终候选四环境实测
[Run 45945706823](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45945706823) completed/success，精确测试提交 `09ff29699f4b459281cce41e60a55c9931d7394e`，Ubuntu、macOS、Windows Server x64、Windows 11 ARM64 四环境通过；每环境7项上下文单元测试及实际三轮 Mock run/resume/rebuild 测试，累计回归及 Windows 安装通过。真实宿主网络断线、会话事件兼容性与 Token 未验收。首轮被补充提交替代，不计最终证据。候选可用于 D12，正式验收 BLOCKED，PR #13 未合并。


## 候选实施
终态 CLI usage 每进程一次；仅唯一 identified 重复事件去重，歧义/缺失 unknown，输入+输出不额外累加缓存/推理。累计已知和与未知轮次分别保存，实际 model 仅 CLI 明确报告，Gemini unknown。run 可显式 --max-turns/--max-tokens/--max-seconds，持久化预算不可经 resume 修改；每轮之前检查，未知 Token 时禁止继续有限 Token 预算任务，时间限制仅累计受管进程耗时及每轮 timeout，不保证精确硬停止。--budget-route 使用本地 cache 支持的 effort，缺能力不猜测，变更必须记录理由；默认旧 smart。测试用合成 usage，不代表真实模型用量。真实 CLI 字段语义、Gemini、实际模型及对照基准未验收。

审查补测：终态失败/冲突或非法 total_tokens 不作为已知计数，预算状态结构校验，pending 状态不把尚未结算计数冒充总数；恢复重新检查缓存能力；带预算任务的关联 review 默认拒绝（未接入预算结算，不能作为绕过入口）。独立非受管调用仍不属于全局预算。首轮 45947038480 被新提交替代，最终候选单独测试。

D12 final stream-integrity review: nonempty malformed JSONL, non-object events, duplicate keys and nonfinite constants invalidate the sample. A total without both input/output components is unknown until the provider semantics are verified. Finite token budgets stop the next invocation on such incomplete evidence. Blank lines remain harmless. Initial follow-up Run 45947156315 is superseded by this exact-head regression; no claim of final PASS until confirmed.

## 2026-11-27 D12 exact-head verification
[Run 45947305027](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45947305027) attempt 1 completed/success; PR #14 open Draft, dev/d11 -> dev/d12, tested head `f5b1bf017d1f1c259e1c50f0fd89a85100cf082f`. All four job checkout logs explicitly confirm this SHA; each ran `python -m unittest discover -s tests -p test_budget.py -v`, 6/6 OK (24/24 across environments), including malformed stream, conflict, dedup, unknown, limits and cached routing. Each also reports 23-card ledger PASS and successful applicable cumulative steps. Platform-specific steps skipped only as intended.

| Runner | Job | Image version | Python | Node |
|---|---:|---|---|---|
| Windows 11 ARM64 | 140334872489 | windows-11-vs2026-arm64 20261115.219.1 | 3.12.10 | 22.23.5 |
| Windows Server x64 | 140334872785 | windows-2025-vs2026 20261116.315.1 | 3.12.10 | 22.23.5 |
| Ubuntu | 140334872830 | ubuntu-26.04 20261116.88.1 | 3.12.16 | 22.23.5 |
| macOS ARM64 | 140334872749 | macos-26-arm64 20261123.0526.1 | 3.12.10 | 22.23.5 |

Windows 11 Enterprise build 26200 ProductType=1 ARM64 confirmed. No actual provider/model calls or real host verification; Gemini usage and paired benchmark NOT_RUN; prior superseded runs 45947038480/45947156315 retained, not counted as PASS. Boundary-only budget, no system-wide hard cap. D12 candidate ready; formal BLOCKED pending D05–D11 acceptance and real provider/host/benchmark evidence. No merge or release. Main observed `114e0c205f326b4af0935656ef482bba8270b284` (seven checkpoint-only commits since previous recorded main). D13 may inherit under existing candidate approval. Evidence-only commit is distinct from tested code SHA and requires governance recheck.

RISK-08：D12 合成用量与 fail-closed 预算候选通过；真实字段语义及 D13 无进展/幂等仍待验证。BUG-001/002 不改为 FIXED。CI 日志含 actions Node20 deprecation warning，当前未阻止运行；后续兼容升级需独立验证。


## 2026-11-27 D13 candidate implementation
Base `5ae7ef0c4af3b748d2cf78ea19e5d9f984f0c472` (D12 exact tested code f5b1bf017d1f1c259e1c50f0fd89a85100cf082f, Run 45947305027; subsequent evidence-only diff). Existing user candidate approval applies. Opt-in `--request-id` with explicit task ID and v2 run/resume; persistent registry in locked dispatcher state, exact argument digest, immutable scope/revision, duplicates return original operation metadata; conflicting keys never dispatch. Keyed tasks reject unkeyed CLI continuation and initial reservation collisions. Reservation persists before invocation, pending/uncertain after crash cannot auto-retry. Explicit new key and retry-of for known failed worker operation; at most two retries and two associated reviews; repeated failure category or two continuations without observed Git progress stop further resume. No automatic retry, merge or verification. D12 budget and D06/D10/D11 policies remain active. The Git metadata fingerprint is conservative (same-size edits may look unchanged, non-Git progress unknown), not an exact diff/content fingerprint. Registry cap 4096; no automatic removal. Direct legacy APIs/old binaries/unmanaged external calls are outside keyed CLI contract. Real host, crash/power loss and formal dependencies not verified; CI pending. Rollback: do not use keyed operations, do not run old binaries on active keyed tasks; preserve registry/state and reconcile pending requests manually.
RISK-08: key registry and failure/progress guard candidate pending tests; metadata fingerprint and legacy API limitations explicit.

D13 MCP follow-up: opt-in requestId/retryOf with v2 envelope, durable unique key + console operation inserted in one SQLite BEGIN IMMEDIATE transaction (plugin-owned DB only), same request returns original op, conflicts disclose only original ID/status, no allowDuplicate bypass. Python remains authoritative for actual launch reservation, scope/revision/authorization/budget. Two independent stores are not a distributed transaction; interruptions block retry, not automatic repair. v2 result classification is separate from v1; worker claims not independent verification. Keyed v2 collab binding disabled because short result omits verified session identity. Default legacy UI/MCP behavior unchanged. Test database/restart/real multi-process uniqueness and explicit result handling; final exact head CI pending.
- D13 并发审查：MCP 重开 DB 不得将仍存活的 keyed 操作标为中断；新增 owner PID 保守探测及跨进程回归。PID 复用或未知 owner 不自动重派；仍须人工对账。Git 采样失败/截断视为无可用进度证据。候选复检待最新 CI。

- D13 CI regression (Run 45971488857): macOS and Ubuntu concurrent Node DB open failed SQLITE_BUSY (errcode 5) at initialization. Install busy handler before journal mode, avoid redundant WAL switch, bounded busy retry; no test bypass. Latest exact-head cumulative rerun required.


## 2026-11-27 D13 final candidate evidence
[Run 45971644956](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45971644956) completed/success, exact head `b61c1cddb9c1b67b3ebd1bfe7b7b1548b0729081`, PR #15 Draft, base dev/d12. Actual checkout logs verified on all four jobs: macOS ARM64 140413301471, Windows Server x64 140413301959, Windows 11 ARM64 140413301965, Ubuntu 140413302084. Each ran `python -m unittest discover -s tests -p test_request_gate.py -v` 6/6 OK and `node --no-warnings --test tests/test-request-db.mjs` 4/4 PASS (40/40 combined), cumulative steps including governance and native MCP/installation all successful. Windows 11 Enterprise build 26200 ProductType=1 ARM64. Run 45971488857 exposed SQLITE_BUSY on macOS, Ubuntu and Windows Server; fixed by busy handler before WAL and bounded retry, not by weakening tests. Earlier cancelled/superseded runs are not acceptance evidence. D13 candidate ready, formal BLOCKED: actual host, trusted approval, risk review, power loss and cross-store reconciliation remain unverified; conservative Git progress and legacy scope limitations remain. No real model or release; no merge. D14 may proceed under candidate authorization. Evidence-only commit requires recheck.


## 2026-11-27 D14 candidate
Base `f123cb30cf07023e2667126ff6a538890bf68122` (D13 verified code b61c1cddb9c1b67b3ebd1bfe7b7b1548b0729081, Run 45971644956 PASS; evidence-only follow-up). Opt-in v2 --stream-events, MCP streamEvents requires requestId; resume inherits the persisted flag. Legacy default unchanged; D13 default request hashes unchanged. Concurrent binary pipe readers, bounded queue, byte caps stdout 4MiB/stderr 1MiB, JSONL line cap 64KiB, UTF-8 validation on complete lines; incremental raw local artifact writes, fixed metadata snapshots with atomic durable seq and 64-entry rolling replay window, heartbeat and cursor/gap. No raw output in task_events; process_exit is not task acceptance. Output overflow/malformed stream/timeouts stop owned process tree, discard partial usage/session inference and never report success. Raw log cap stops instead of silently rotating/deleting raw evidence; metadata window rotates, full raw-log rotation and cross-turn global sequence are not implemented. If context/session identity or state settlement fails, retain pending/running for manual reconciliation. No new cancel authority or real host test; UI push transport and actual host reconnect remain unverified. Rollback: omit opt-in on new tasks; do not downgrade active streamed tasks or delete artifacts. Four-environment CI pending.
RISK: bounded logs stop on overflow; escaped descendants and actual host cancel/reconnect are not proven. Preserve raw evidence; never automatically relaunch pending operations.

D14 review follow-up: strict duplicate/nonfinite JSON rejection; wait for pending stdin/pipe notifications before accepting EOF; persist stream_integrity, block resume for timeout/overflow/launch failure or unverified stream, retain interrupted task and unknown usage on streaming/session exception. Test actual local mock run/resume, cumulative token settlement, failure and no relaunch. Legacy request digests remain compatible. D13 evidence-only recheck Run 45973332876 four environments PASS. Current exact-head D14 CI pending.

## 2026-11-27 D14 final candidate evidence
[Run 45973849986](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45973849986) completed/success on exact head `b7bc081c680e94f87a3012d5fa1f0f54d93116b5`; PR #16 remains Draft. Checkout logs verified: macOS ARM64 job 140420669725, Windows Server x64 140420670268, Windows 11 ARM64 140420670134, Ubuntu 140420670209. Each ran `python -m unittest discover -s tests -p test_streaming.py -v` 8/8 OK (32/32); native MCP cursor replay/gap/invalid-order checks and all applicable cumulative steps PASS, including governance and Windows lifecycle. Windows 11 Enterprise build 26200 ProductType=1 ARM64. Initial Run 45973642495 superseded/cancelled, not acceptance evidence. Tested local subprocess and synthetic worker only, no real model. Candidate ready; formal BLOCKED by actual host/UI, actual cancellation and reconnect, full raw log rotation and dependency gates. D15 candidate may continue under existing authorization. Evidence-only commit requires recheck.


## 2026-11-27 D15 candidate implementation
Base `12726d05db0b5149ae4c8232e65669958d8d40d9` (D14 tested code b7bc081c680e94f87a3012d5fa1f0f54d93116b5 / Run 45973849986 PASS). Default JSON unchanged. Explicit state-migrate --confirm-quiescent under existing OS lock, backup exact JSON bytes and reject active/uncertain operations, create separate plugin-owned versioned WAL database, verify row counts and SHA256 metadata/task manifest, publish incompatible-to-legacy state.json marker last. SQLite authoritative only after marker; old binaries fail closed instead of writing stale JSON. Single Python transaction path, row-delta writes, FULL sync, previous snapshot backup before commit, no automatic task deletion. State marker or DB corruption never falls back. Read-only Node MCP reconstructs consistent transaction and verifies checksums; native Codex DB untouched. state-rollback --confirm-quiescent exports current DB to JSON atomically and preserves database/backup. state-recover --source initial|previous only exports verified recovery copy, no activation or silent data loss; corrupt DB requires manual reconciliation. Inactive database after interrupted publish retained. Explicitly stop all old CLI/MCP instances, including untracked calls, before migration; process quiescence confirmation not proof. No production data migrated. Full-snapshot reads still present; D16 handles cache/index query optimization. CI pending.
RISK: restore from initial/previous may omit later committed state; recovery export never activates. Old binaries must be stopped before migration. No automatic deletion of inactive DBs.

D15 review/CI follow-up: initial Run 45974526071 migration assertions ran on Windows, but two SQLite fixture connections were not closed by Python connection context manager (WinError 32 during temp cleanup). Explicit contextlib.closing, no skipped assertion or cleanup suppression. Native path guard before any migration directory creation, Node canonical marker and sidecar validation, actual keyed streaming mock run/resume in SQLite with duplicate receipts and D12 usage settlement preserved through inverse migration. Latest exact-head CI pending.

## 2026-11-27 D15 final candidate evidence
[Run 45974689285](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45974689285) completed/success on exact head `de11dc6f48588192c82cfd25172be44cfc5901f1`; PR #17 remains Draft. Checkout logs verified: Windows Server x64 140423383707, Ubuntu 140423384167, macOS ARM64 140423384183, Windows 11 ARM64 140423384199. Each ran test_sqlite_state.py 8/8 OK (32/32); actual Python fixture migration, MCP read, corrupt manifest rejection, inverse migration and unchanged native DB hash PASS; cumulative governance and Windows lifecycle PASS. Initial Run 45974526071 failed on both Windows environments due to fixture connection cleanup (WinError 32); corrected explicitly, no skipped assertions. No production migration or real model calls. Candidate ready; formal BLOCKED by actual host migration/recovery, manual quiescence, dependency gates and unverified power-loss recovery. Recovery exports backup only, not automatic activation. D16 candidate may continue under existing authorization. Evidence-only head requires recheck.


## 2026-11-27 D16 initial candidate
Base 07ce2d89eeee61dcd4eafa8111e88f260d3b39a1 (D15 tested de11dc6f / Run 45974689285 PASS). Explicit ALC_QUERY_CACHE=1 enables app-only revision endpoints; default legacy fresh paths, model-facing task/authorization checks remain unchanged. Bounded 5s display TTL, 32 entries/2MiB, single-flight same source, native/owned DB and WAL metadata invalidation, errors/unknown stamps bypass cache; large legacy JSON bypasses cache. Local quota rollout only, bounded 15s cache, no live app-server or real model calls. UI source selects delta only if advertised, avoids unchanged render, ID detail no automatic Git unless tab selected, slower idle/hidden polling. Changed views still use existing full render; report-specific mtime optimization, measured paired p95/query/I/O, full DOM partial patch and actual host acceptance incomplete. Linux CI builds UI source but tracked dist/app.html is NOT yet rebuilt/committed; do not mark candidate ready or advance D17 until remaining candidate evidence. No merge.

## 2026-11-27 D16 follow-up
Initial ledger head 34046f42ee0393b1bbfa6186ab866f626886d3aa / Run 45975558725 four-environment PASS, 20/20 cache tests, Linux Vite build and MCP delta passed. D15 evidence recheck 45975155258 PASS. Added bounded per-report mtime/digest-aware display cache, large legacy JSON metadata stamping, exact/prefix selector cache only for display, partial panel replacement for silent refresh, stale selection/failure and refresh coalescing safeguards. Added real SQLite query/open and logical content/wire byte benchmark on paired 30-call synthetic fixture; p95 is measured, not estimated; metadata stat syscalls/physical storage I/O not counted. Temporary Linux build transfer emits only generated public-to-repo static bundle chunks and git blob SHA, no token, no write permission; remove transfer step after importing exact verified blob. Dist not updated yet. Formal host, actual browser interaction and physical I/O remain unverified. No D17 start until candidate gate.

D16 verified build transfer: Ubuntu job 140446248179, Run 45981495894, exact source d4c06f7f41ddd17c149661c2f41fd9d679853777 built dist/app.html; 132 ordered base64 chunks reconstructed via Git blob API; runner git hash-object and API blob SHA both 255b42124451a7aac844c0226bd5d419c67119b2. No workflow write permission or real credentials used. Track exact bundle and remove export step; Linux CI now requires byte-identical rebuilt bundle. Initial Ubuntu fixture p95 3.502→1.493ms, queries 270→9, baseline logical content bytes 38670→1096 excluding marker-read overhead; NOT final I/O evidence. Revised marker memo counts its actual content reads/bytes and invalidates on metadata changes; include them in paired benchmark. Report cache includes current state identity in cache stamp, prevents reuse with stale session/exit/status. Final four-environment exact head CI pending; metadata stat syscalls and physical disk bytes remain unmeasured. No production changes.

## 2026-11-27 D16 final candidate evidence
[Run 45981702422](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45981702422) completed/success, exact code head `d70653cacd24c9cc448db4519a3f87deffd7bbfc`, PR #18 Draft. Four environments actual checkout logs verified, 8/8 Node cache tests per job (32/32), native MCP delta and all cumulative tests/governance PASS. Linux rebuilt dist/app.html byte-identically (git blob 255b42124451a7aac844c0226bd5d419c67119b2). Windows used tracked rebuilt bundle. D15 evidence head recheck 45975155258 PASS. Initial D16 Run 45975558725 PASS, 45981495894 superseded; Ubuntu source build was verified before supersession. No real model, deployment, permission expansion or merge.

Paired same-fixture actual 30 calls each, alternating order; p95 ms measured locally, counts actual native SQLite read opens/queries (excludes console preference DB operations), logical file reads/bytes include state marker and report reads; excludes metadata stat syscalls, DB page cache and physical disk bytes. Wire bytes are serialized payload bytes, not measured network transfer.

| Environment / job | p95 ms baseline → candidate | native DB opens | native queries | logical file reads | logical content bytes | JSON payload bytes |
|---|---:|---:|---:|---:|---:|---:|
| Windows Server x64 / 140447071189 | 12.654 → 4.34 | 120 → 4 | 270 → 9 | 60 → 2 | 41130 → 2356 | 4616100 → 156695 |
| Windows 11 ARM64 / 140447071531 | 11.263 → 3.744 | 120 → 4 | 270 → 9 | 60 → 2 | 41130 → 2356 | 4616100 → 156695 |
| macOS ARM64 / 140447071591 | 3.51 → 1.065 | 120 → 4 | 270 → 9 | 60 → 2 | 41310 → 2368 | 4648110 → 157762 |
| Ubuntu / 140447071593 | 4.049 → 1.591 | 120 → 4 | 270 → 9 | 60 → 2 | 38670 → 2192 | 4413150 → 149930 |

Candidate ready under existing authorization; formal BLOCKED: actual Antigravity browser/old-host compatibility, live DOM interaction, physical I/O, real host state changes and dependency acceptance remain unverified. Report-only mutation may lag snapshot TTL (5s); per-report identity/mtime checked when refreshed; local quota 15s TTL. No model/authority checks use display cache. D17 may continue. Evidence-only head requires recheck.


## 2026-11-27 D17 initial candidate
Base c54b32f300259cc4d5178994c42de9a38e2b2d95 (D16 exact source d70653c / Run 45981702422 PASS). Explicit offline local scheduler.json schema {version:1,max_slots:1..4,max_wait_seconds:1..300,min_free_bytes:integer,quota:null|{remaining_percent:0..100,observed_at:epoch_seconds}}. Not a permission or model grant. Persistent FIFO tickets in D04/D15 state transaction, bounded 4096 audit, no automatic deletion, no lease-expiry relaunch. Unknown/stale advisory quota caps at one, <=10% pauses, disk pressure pauses. Canonical Git common directory and overlapping paths serialize, declared file hints are not trusted isolation; unknown scope conflicts all. Run/resume/review/batch use same scheduler; queue cancel only, active interruption/timeout uncertain retains slot until manual reconciliation, no PID auto-reclaim. Direct MCP fork denied when scheduler configured/activated. Batch DAG validates before launches, conservative waves, failed dependency blocks successors, max 4 workers. Cleanup now read-only preview, checks managed path/branch, clean tracked/untracked/ignored state, ancestry and independent acceptance; never removes/prunes/deletes (trusted approval absent). Config absence before activation preserves legacy execution, sticky scheduler.ever prevents accidental bypass after activation; offline operator must stop all clients, reconcile and remove configuration/marker only after review to roll back; older binaries and external Codex calls cannot be governed. Actual host queue/cancellation, quota source and cleanup approval remain unverified. No real model, production config, cleanup, permission expansion or merge. CI pending.

D17 follow-up: initial Run 45982548344 scheduler/cleanup regression failed on macOS and both Windows jobs: legitimate worktree paths included OS-provided aliases (macOS /var vs /private/var, Windows short names). Previous comparison path.resolve()!=path stopped preflight before dirty/unmerged assertions. Fix compares canonical expected configured root plus bounded relative components, retaining link/junction denial; actual no-delete tests unchanged. Added clean merged still approval-required fixture, actual D13 keyed D14 streaming D15 SQLite run/resume with two released slots and duplicate receipts, stale quota and untracked legacy activation failure, native MCP direct-fork denial. Recheck canonical queued scope before launch; casefold conservatively, resource telemetry in MiB buckets. No tests skipped. Latest CI pending.

## Cumulative regression reopened 2026-11-27
D16 evidence-only Run 45982277920 failed on macOS ARM64 job 140448925251 in D14 test_duplicate_and_nonfinite_json_rejected, PermissionError EPERM from killpg racing a rapidly exiting child (other three environments PASS). Original D16 performance/run evidence remains historically valid, but candidate gate reopened pending fix. Do not signal a numeric process group once Popen reaped its leader; on EPERM wait briefly for owned child exit or kill only still-live Popen child, never assert descendants verified. Deterministic real-child regression injects EPERM on POSIX, Windows checks no taskkill after reaping. Existing timeout/malformed result remains failure. Corrected exact-head CI pending. D17 implementation already drafted from prior PASS; pause D18 and synchronize fix after verification. No merge or real model.

## D16 cumulative process-exit correction verification
Run 45982938825 (https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45982938825) completed/success exact head 6db070f17039338762e03a375c911873302fa32b; 4/4 jobs, each 9/9 streaming tests including deterministic EPERM/reaped-child regression, 8/8 D16 cache tests, native MCP and governance PASS. Jobs install (windows-11-arm) 140451182077, install (ubuntu-latest) 140451182488, install (windows-latest) 140451182548, install (macos-latest) 140451182601. Earlier failing evidence Run 45982277920 remains recorded, not erased. D16 UI/cache source unchanged from original four-platform measured run 45981702422. Repeated paired measurements (30 calls each, p95 ms): install (windows-11-arm) 10.107→3.685; install (ubuntu-latest) 5.94→2.406; install (windows-latest) 12.5→3.389; install (macos-latest) 6.47→6.499. Native queries 270→9 each; logical content I/O reductions reproduced. macOS rerun p95 6.470→6.499 ms (slight increase); no claim of universally improved p95 or physical I/O; controlled actual-host repeat required. Candidate gate restored on corrected exact-head CI, formal BLOCKED unchanged. D14 original branch not rewritten; cumulative repair must be accounted for at formal sequential acceptance. D17 pre-integration Run 45982783750 40/40 and all four PASS; synchronize corrected D16 base and test new D17 head before advancing D18.


## D17 corrected-base integration
Pre-integration Run 45982783750 completed/success exact head 09b16b6803e58eb8275c22ad1b9a6b31d1c03fdf; 10/10 D17 tests each (40/40), native MCP direct fork blocked, all four environments cumulative and governance PASS (jobs 140450659395 Ubuntu, 140450659817 Windows 11 ARM64, 140450659900 Windows Server x64, 140450662889 macOS). D16 corrected exact-head Run 45982938825 completed/success, candidate restored; synchronize base ffa9c4e6312d3b034d306ec3a4907cf0f1fdc870 via two-parent candidate integration commit only, not formal merge or main change. Include D16 owned-process exit-race fix/test, latest ledger and evidence; add actual abrupt owner process death test (no automatic slot reclamation, queue cancellation without launch). D17 remains IN_PROGRESS until integrated exact-head recheck. Scope only managed local processes; real host/active cancel reconciliation, actual quota source and trusted cleanup approval unverified; scheduler config is advisory and sticky offline rollback, cleanup preview only. No real models or production mutations.


## D17 integrated candidate verification
Run 45983586382 completed/success, exact source 838787ad94f2cbadb00cb222a21aa1b5a720b9e5, four actual runner logs verified (Windows 11 ARM64 140453373472, Ubuntu 140453373960, macOS ARM64 140453373967, Windows Server x64 140453374144). 11/11 scheduler tests each (44/44), abrupt owner death retains slot, FIFO, low/unknown quota, disk pressure, dependency blocking, canonical same-repo conflicts, clean/dirty worktree no-delete, D13/D14/D15 actual mock run/resume and MCP direct fork denial all PASS. D16 process exit regression and cumulative governance PASS. D16 evidence head ffa9c4e6312d3b034d306ec3a4907cf0f1fdc870 Run 45983418330 all four PASS. Historical D17 alias failure 45982548344 retained. Formal BLOCKED: actual host scheduler, live cancellation and escaped-child reconciliation, advisory quota provenance, trusted cleanup approval and predecessor acceptance unverified. Cleanup preview only; no automatic slot reclamation. Candidate ready for D18 under existing development authorization, no formal merge. Evidence-only head recheck required.



## Formal acceptance follow-up: D14 process-exit correction (2026-11-27)
Historical D16 Run 45982277920 macOS PermissionError EPERM during D14 rapid process exit remains recorded. Backport only terminate_owned_process_tree and test_owned_process_exit_race_permission_error from verified D16 head ffa9c4e6312d3b034d306ec3a4907cf0f1fdc870 (code tested 6db070f17039338762e03a375c911873302fa32b, Run 45982938825 four environments PASS). No later-card implementation imported. Do not signal group after Popen reaped leader; EPERM wait/owned-child fallback, descendants remain unverified. New D14 exact-head CI NOT_RUN at commit creation; candidate.ready=false until verified. D14 stays BLOCKED: actual cancellation, escaped descendants, real host/UI/reconnect, raw rotation and dependencies remain outstanding. Existing D15–D22 contain this correction in cumulative D16+ or require integration before formal merge; do not force-push or merge main.


## D17 candidate ancestry integration (2026-11-27)
D16 0425f17e921ca09571f74c409c4234c35876ca1c / Run 46006220435 4/4 completed/success, actual checkout and cleanup/EPERM logs verified. D17 process-exit function and streaming test blob already identical to D16. Preserve D17 scheduler and read-only cleanup preview; do not copy earlier plain-denial test because it is replaced by D17's preview assertions, which check no removal on both dirty and clean cases. Force/delete branch remain denied. No formal merge; exact integrated head requires CI. Actual host/authorization/dependencies remain BLOCKED.
