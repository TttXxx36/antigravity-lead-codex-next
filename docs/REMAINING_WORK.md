# 全路线执行总账与剩余步骤

2026-11-27；当前 dev/d05 跨分支快照：D00–D04 DONE，D05 托管 CI PASS 但真实 Windows 11/Antigravity 验收 BLOCKED；D06–D21 已获方案 A 与条件合并许可，依赖未满足不启动；D22 正式发布另需批准。下文历史记录按时间保留，当前状态以表格及最新检查点为准。

## 各卡剩余任务

| 卡 | 阶段 | 前置 | 状态 | 已有产物 / 剩余交付 |
|---|---|---|---|---|
| [D00](decisions/D00.md) 独立仓库与上游基线 | P0 | 无 | DONE | 已合并 PR #1；45 文件 SHA/mode 核验 |
| [D01](decisions/D01.md) 基线测试与可复现基准 | P0 | D00 | DONE | PR #2 已验收合并；原版 Windows FAIL/NOT_RUN 保留 |
| [D02](decisions/D02.md) 开发与验收治理 | P0 | D00 | DONE | PR #3 已验收合并；治理三平台通过；远程保护设置另获授权 |
| [D03](decisions/D03.md) 跨平台路径与运行时发现 | V1.1 | D01,D02 | DONE | PR #5 已合并；三平台实际长路径 I/O 与 MCP smoke PASS；真实客户端/桌面由 D05/D08 验收 |
| [D04](decisions/D04.md) 跨平台锁与状态完整性 | V1.1 | D03 | DONE | PR #6 已合并；39/39 状态回归通过 |
| [D05](decisions/D05.md) 安装器和环境诊断 | V1.1 | D03,D04 | BLOCKED | PR #7；四环境及真实 Windows 11 ARM64 OS 生命周期 PASS；真实 Antigravity 宿主和实际 Codex 版本证据缺失 |
| [D06](decisions/D06.md) 审批门禁与执行边界 | V1.1 | D04,D05 | BLOCKED | PR #8 候选四环境 CI PASS；可信宿主授权/真实 sandbox 未验收；可继续 D07 候选 |
| [D07](decisions/D07.md) 任务结果与进程生命周期正确性 | V1.1 | D04,D06 | BLOCKED | PR #9 四环境 44/44 outcome PASS；真实宿主进程树未验收；可继续 D08 候选 |
| [D08](decisions/D08.md) 历史任务定位与 Windows 发布门禁 | V1.1 | D05,D06,D07 | BLOCKED | PR #10 四环境 CI PASS；实机宿主未验收；D09 候选可继续 |
| [D09](decisions/D09.md) 模型可见的轻量 MCP 接口 | V1.2 | D08 | BLOCKED | PR #11 两轮四环境 PASS；正向 op 与结果边界补测通过；真实宿主与 Token 待验收；可继续 D10 |
| [D10](decisions/D10.md) 结构化通信与短报告协议 | V1.2 | D09 | BLOCKED | PR #12 四环境候选 PASS；真实 structured output/宿主待验收；D11 可继续 |
| [D11](decisions/D11.md) 共享黑板与会话复用 | V1.2 | D10 | BLOCKED | PR #13 四环境 PASS；真实会话与 Token 未验收；D12 可继续 |
| [D12](decisions/D12.md) Token 遥测、预算与动态模型路由 | V1.2 | D01,D10,D11 | BLOCKED | PR #14 四环境 PASS；真实 provider/宿主/基准未验收；D13 可继续 |
| [D13](decisions/D13.md) 幂等派发与循环终止 | V1.2 | D10,D12 | BLOCKED | PR #15 四环境 PASS；真实宿主/恢复未验收；D14 可继续 |
| [D14](decisions/D14.md) 实时流式执行与事件总线 | V1.3 | D07,D13 | BLOCKED | PR #16 四环境 PASS；真实宿主/完整日志轮换未验收；D15 可继续 |
| [D15](decisions/D15.md) SQLite 任务状态迁移 | V1.3 | D04,D14 | PROPOSED | 未实施；插件自有 WAL、迁移/备份/回滚、原生 Codex DB 只读 |
| [D16](decisions/D16.md) MCP 查询缓存与 UI 增量刷新 | V1.3 | D14,D15 | PROPOSED | 未实施；按 ID/TTL/delta、并发请求合并、p95/I/O 对照 |
| [D17](decisions/D17.md) 动态并发与 Worktree 资源治理 | V1.3 | D14,D15,D16 | PROPOSED | 未实施；公平队列、冲突范围、取消释放、保留未提交数据 |
| [D18](decisions/D18.md) 确定性编排状态机 | V2.0 | D13,D15,D17 | PROPOSED | 未实施；显式状态机、lease/revision、审计、恢复防重复 |
| [D19](decisions/D19.md) 风险驱动审查与验收 | V2.0 | D18 | PROPOSED | 未实施；风险分级、确定性检查、安全/并发/迁移必审 |
| [D20](decisions/D20.md) 常驻 Codex App Server 可选适配 | V2.0 | D18,D19 | PROPOSED | 未实施；官方能力协商、CLI 兜底、权限对等、复用/断线测试 |
| [D21](decisions/D21.md) 可观测性与性能/Token 验收 | V2.0 | D12,D16,D19,D20 | PROPOSED | 未实施；配对基准、质量/成功率、真实用量及置信限制 |
| [D22](decisions/D22.md) 发布、兼容性与回滚 | V2.0 | D21 | PROPOSED | 未实施；RC、三平台/真实 Windows、SHA256、回滚演练、人工发布许可 |

各卡完整实施清单和验收门槛以链接原文为准，不能以本表摘要代替。可机读依赖与状态见 [EXECUTION_STATUS.json](EXECUTION_STATUS.json)；更新状态须核验实际证据、PR、人工许可。其他分支的卡文件可能尚未合并，不能仅以 main 的旧 PROPOSED 判定活动状态。

## 现在可以推进的工作

1. D01：保存 Run 45915363640 原始失败基线、Run 45918185018 修复候选及实际环境；验收原始基线是否已完成“记录失败也保留”的目标。PR #2 不得改写上游固定源码。
2. D02：检查 [治理规范](GOVERNANCE.md)、PR 模板和本地治理检查器，核验已通过的 PR #3 三平台工作流；管理员保护规则只提供建议，不擅自设置。待人工验收及合并。
3. PR #4：保留经过 3 平台实测的修复 commit cce185037d451d9f10dd3039e054d5b362a69119。按 D03（PATH/UTF-8）、D04（锁）、D05/D08（原生 MCP 测试）、D06（审批保守回退）分拆集成，不能整包合入 D01 固定基线。已复现 BUG-001/002/003 仍需按卡修复。
4. D03–D22：按依赖拓扑逐卡实施、真实证据、Draft PR、人工验收与合并。前置未完成则保持 BLOCKED/PROPOSED，不以文档或 Mock 冒充生产代码。D05/D08/D22 需要真实 Windows 桌面和 Antigravity/Codex 环境；D12/D20/D21 需要真实接口能力及单独批准的用量预算。D22 另需发布许可。

## 真实验收标准

- P0：固定快照、MIT、可重现原始基线（包括失败）及治理可审计。
- V1.1：三平台回归、真实 Windows 安装/升级/卸载、派发/恢复/取消、审批及数据正确性。
- V1.2：通信协议及模型可见负载、版本化增量、预算/幂等；区分实测/估算/未知。
- V1.3：事件流、状态迁移、缓存、并发资源治理；同口径性能对照。
- V2.0：状态机、风险审查、可选 App Server、配对质量/Token 基准、可回滚 RC 与发布批准。

当前通过 CI 不等于整个项目完成；总 Token 下降 30–60% 仍为目标假设，尚无实际模型用量。测试需记录实际 checkout、平台、命令、退出码、证据、风险，拒绝未测 PASS。

## 最新执行授权

2026-11-27 用户明确验收 D01、D02 并授权合并 PR #2、#3；批准 D03–D22 推荐 A 按依赖实施及 GitHub Actions 测试。后续 PR 的合并、真实模型测试及正式发布仍遵守独立授权门禁。

D03 前置已满足，优先集成路径/运行时部分；D04 再集成锁。
## D03 开发进展

用户已批准 A；dev/d03 平台适配、PR #4 最小锁及原生 Node 测试前置复用。三平台 smoke 已 PASS（Run 45933533805）；D04 状态完整性和 D05 安装、D06 审批仍未实施。

当前最新：D03 代码及三平台 smoke 通过，[PR #5](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/5) 待验收。D04–D22 依赖尚未满足，不重复请求已获的方案授权，但需按治理规则确认合并。
## 最新授权
2026-11-27 用户授权 D03–D21 在满足实际验收门槛后依次合并并更新 DONE，无需再次逐卡确认；未满足则修复或记录 BLOCKED。此授权不涵盖 D22 正式发布、真实模型测试、权限扩张或无条件自动合并。 D03 补足超长路径实际 I/O 验收后再合并，D04 继续状态完整性。
D03 已按条件授权合并，D04 依赖满足。
D04 已实施候选：原子状态写入、损坏副本、全局 ID/目录预留、路径检查、崩溃锁回归。待三平台测试。
D04 已完成；D05 依赖满足。真实 Windows 11 客户端安装/卸载握手为 D05 验收，不可用托管 Windows Server 替代。
D05 候选已实现 PowerShell 安装、备份/恢复/卸载、直接 node.exe stdio、隔离 doctor；托管回归待 CI，真实 Windows 11 与 Antigravity 宿主仍为硬门槛。
## 当前恢复点

D00–D04 正式完成（5/23）；D05 代码及托管 CI 通过，保留 Draft PR #7。必须完成 [真实 Windows 11 验收](evidence/D05-WINDOWS11-acceptance.md)；[CI](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935195557)。D06–D21 不再需要逐卡合并批准，但当前传递依赖未满足；D22 发布另需许可。

## Windows 11 ARM64 真正 OS 补测（2026-11-27）
[Run 45936238126](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45936238126) completed/success，精确测试 head `9813f19c222a858f2a4f7cf217702f62252cc540`，四个 job 均 success。Windows 11 Enterprise / 10.0.26200 / Build 26200 / ProductType 1 / ARM 64-bit Processor；Node 22.23.5 win32 arm64、Python 3.12.10 ARM64；13/13 状态、7/7 Python 平台、4/4 Node 平台、真实本地 MCP 合成客户端和完整 PowerShell 生命周期均 PASS。Windows Server 2025 x64 同样通过新增 SQLite SHA256/内容断言；Linux/macOS 回归 PASS。Windows 两种架构均通过 install/upgrade/restore/uninstall/reinstall、ConsoleOnly、Unicode、missing dependency、injected rollback、持久数据及 SQLite bytes preserved。Job IDs: Win11 140299982943、WinServer 140299983157、Ubuntu 140299983213、macOS 140299983240。原 push/PR 重复取消不计入 PASS。实际 Win11 OS 子门槛已取得 ARM64 证据，真实 x64 桌面及 Antigravity App/IDE 登录宿主仍 NOT_RUN；native mock CLI 仅 --version，0 真实模型调用，不冒充真实宿主。


2026-11-27 用户批准分离候选开发与正式验收/合并。D06–D22 可基于经 CI 验证的前置候选分支依赖顺序开发、独立 stacked Draft PR；实际验收门槛、DONE、main 合并条件不变。前置候选有未解决的 CI FAIL/安全缺陷时先修复；缺真实宿主等环境证据可在不启用受阻能力的前提下继续候选开发。禁止真实模型测试、权限扩张、发布。
D06 基于 D05 精确通过 head 启动，D05 正式验收仍阻塞；后续候选逐卡通过 CI 方可复用。

## 实际四环境 CI（候选开发就绪，不是正式验收）
[Run 45937059171](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45937059171) completed/success，精确 tested commit `b652c5877df2e5a91d5191e1f21fab8c208b3015`；Windows 11 ARM64、Windows Server x64、Ubuntu、macOS 四个 job 均成功。每环境执行5项执行策略、5项 dispatch/hook、18项治理测试（合计112次通过），并运行 D03/D04 平台/状态回归、真实本地 MCP synthetic 及 Windows 原生安装生命周期。真实模型测试未执行。D06 否决未授权操作的候选可作为后续开发基础；可信宿主签发任务/范围/有效期授权、实际 OS sandbox、外部写与真实宿主验证仍 BLOCKED；不得将全部拒绝冒充完整授权功能。PR #8 base dev/d05 保持 Draft，未合并。


D07 候选：BUG-001/002 报告与退出状态校验、原子结果/终态、超时/启动失败、重复 close 及孤儿状态回归；待 CI。

## 实际四环境 CI（候选通过）
[Run 45937506260](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45937506260) completed/success，测试 commit `8e472999c84f1a41dd188a5766d6bd4de7bd02a5`；Windows 11 ARM64、Windows Server x64、Ubuntu、macOS 各7项 Python outcome +4项 Node outcome（共44/44 PASS），真实本地父子进程超时 marker 未出现，缺报告与非零退出反向断言、启动失败、终态重复事件和重启孤儿状态通过。D06 策略、Hook、治理及 D03–D05 累计回归通过。旧 BUG-001/002 为 CANDIDATE_PASS，尚未合入 main；真实 Antigravity/实际 Codex worker 的进程树、逃逸/提前退出根进程及真实掉电未验收，不能据托管结果标 DONE。D07 候选允许后续依赖开发；PR #9 base dev/d06 保持 Draft。

D08 候选：直接查询历史任务、拒绝歧义、Git -z、显式 schema 错误和永久 CI；待实际回归。

## 四环境修复后实测（候选通过）
[Run 45938086882](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45938086882) completed/success，tested commit `5ab0c7db084b87701bb3d5d5f60fc512f833dc7f`；Windows Server x64 (140305829193)、macOS (140305829410)、Ubuntu (140305829450)、Windows 11 ARM64 (140305829483) 四个 job 均 success。Git parser + 原生文件系统 rename 各2项，共8/8 PASS；MCP 集成测试四环境均通过 >250 历史任务（300条 fixture）、歧义、只读哈希及 schema 错误断言；累计回归及两个 Windows 安装生命周期 PASS。首轮失败保留，Git 全局配置改隔离临时空文件后通过。真实 Antigravity/Codex 宿主端到端与 Windows x64 桌面仍 NOT_RUN；候选可用于 D09，不代表正式验收或发布。PR #10 base dev/d07，Draft，未合并。


## D09 补测
初次 [Run 45938576927](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45938576927) 四环境 PASS。补充正向操作状态与当前结果绑定：Python 在原子写入后发布 turn + SHA256，Node 只读取精确状态绑定的 artifact；旧记录无引用时返回不可用，不以扫描旧目录冒充当前结果。校验 ID/session/exit/task status、大小、链接路径；不承诺对恶意本地同权限并发改写的 OS 级隔离。补测含运行中、内容篡改、错误身份、过大、缺失 turn、链接/junction。真实模型/宿主仍未测。复检待执行。

## D09 补测最终候选结果
[Run 45940757723](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45940757723) completed/success，tested commit `99c0e5544bf03c1702fee7b7deb1a196b9fba502`。Ubuntu (140314263163)、Windows Server x64 (140314263322)、macOS (140314263379)、Windows 11 ARM64 (140314263404) 四个 job 全部成功。正向操作状态、当前 artifact SHA256/身份、running/stale/missing/oversized/identity/link 拒绝及实际 Mock run/resume 结果引用验证均通过；累计回归和两种 Windows 安装生命周期通过。真实模型调用 0；真实 Antigravity 可见性/UI、实际 Token、真实宿主及前置正式合并仍 BLOCKED。旧数据无 result_ref 不推断；日志只返回事件元数据；内容哈希不是持久 revision。D09 候选可作为 D10 基础，PR #11 Draft，未合并。


## D10 最终候选实测
[Run 45941283814](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45941283814) completed/success，精确代码 head `5e937fcb4de98d0df60cef144b81e8f619f9e550`；Ubuntu、macOS、Windows Server x64、Windows 11 ARM64 四环境全绿。各环境6项协议测试及1项实际 Mock run/resume revision 回归（28次新增测试），累计 D03–D09 回归通过。首轮 45941194963 因后续修正被取消，不计为通过。真实模型 structured output、真实宿主及实际 Token 未验证；v2 仍显式选择，batch/MCP 默认 v1。D10 候选可复用，正式验收 BLOCKED，PR #12 Draft 未合并。


## 最终候选四环境实测
[Run 45945706823](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45945706823) completed/success，精确测试提交 `09ff29699f4b459281cce41e60a55c9931d7394e`，Ubuntu、macOS、Windows Server x64、Windows 11 ARM64 四环境通过；每环境7项上下文单元测试及实际三轮 Mock run/resume/rebuild 测试，累计回归及 Windows 安装通过。真实宿主网络断线、会话事件兼容性与 Token 未验收。首轮被补充提交替代，不计最终证据。候选可用于 D12，正式验收 BLOCKED，PR #13 未合并。


## 2026-11-27 D12 exact-head verification
[Run 45947305027](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45947305027) attempt 1 completed/success; PR #14 open Draft, dev/d11 -> dev/d12, tested head `f5b1bf017d1f1c259e1c50f0fd89a85100cf082f`. All four job checkout logs explicitly confirm this SHA; each ran `python -m unittest discover -s tests -p test_budget.py -v`, 6/6 OK (24/24 across environments), including malformed stream, conflict, dedup, unknown, limits and cached routing. Each also reports 23-card ledger PASS and successful applicable cumulative steps. Platform-specific steps skipped only as intended.

| Runner | Job | Image version | Python | Node |
|---|---:|---|---|---|
| Windows 11 ARM64 | 140334872489 | windows-11-vs2026-arm64 20261115.219.1 | 3.12.10 | 22.23.5 |
| Windows Server x64 | 140334872785 | windows-2025-vs2026 20261116.315.1 | 3.12.10 | 22.23.5 |
| Ubuntu | 140334872830 | ubuntu-26.04 20261116.88.1 | 3.12.16 | 22.23.5 |
| macOS ARM64 | 140334872749 | macos-26-arm64 20261123.0526.1 | 3.12.10 | 22.23.5 |

Windows 11 Enterprise build 26200 ProductType=1 ARM64 confirmed. No actual provider/model calls or real host verification; Gemini usage and paired benchmark NOT_RUN; prior superseded runs 45947038480/45947156315 retained, not counted as PASS. Boundary-only budget, no system-wide hard cap. D12 candidate ready; formal BLOCKED pending D05–D11 acceptance and real provider/host/benchmark evidence. No merge or release. Main observed `114e0c205f326b4af0935656ef482bba8270b284` (seven checkpoint-only commits since previous recorded main). D13 may inherit under existing candidate approval. Evidence-only commit is distinct from tested code SHA and requires governance recheck.


## 2026-11-27 D13 candidate implementation
Base `5ae7ef0c4af3b748d2cf78ea19e5d9f984f0c472` (D12 exact tested code f5b1bf017d1f1c259e1c50f0fd89a85100cf082f, Run 45947305027; subsequent evidence-only diff). Existing user candidate approval applies. Opt-in `--request-id` with explicit task ID and v2 run/resume; persistent registry in locked dispatcher state, exact argument digest, immutable scope/revision, duplicates return original operation metadata; conflicting keys never dispatch. Keyed tasks reject unkeyed CLI continuation and initial reservation collisions. Reservation persists before invocation, pending/uncertain after crash cannot auto-retry. Explicit new key and retry-of for known failed worker operation; at most two retries and two associated reviews; repeated failure category or two continuations without observed Git progress stop further resume. No automatic retry, merge or verification. D12 budget and D06/D10/D11 policies remain active. The Git metadata fingerprint is conservative (same-size edits may look unchanged, non-Git progress unknown), not an exact diff/content fingerprint. Registry cap 4096; no automatic removal. Direct legacy APIs/old binaries/unmanaged external calls are outside keyed CLI contract. Real host, crash/power loss and formal dependencies not verified; CI pending. Rollback: do not use keyed operations, do not run old binaries on active keyed tasks; preserve registry/state and reconcile pending requests manually.

D13 MCP follow-up: opt-in requestId/retryOf with v2 envelope, durable unique key + console operation inserted in one SQLite BEGIN IMMEDIATE transaction (plugin-owned DB only), same request returns original op, conflicts disclose only original ID/status, no allowDuplicate bypass. Python remains authoritative for actual launch reservation, scope/revision/authorization/budget. Two independent stores are not a distributed transaction; interruptions block retry, not automatic repair. v2 result classification is separate from v1; worker claims not independent verification. Keyed v2 collab binding disabled because short result omits verified session identity. Default legacy UI/MCP behavior unchanged. Test database/restart/real multi-process uniqueness and explicit result handling; final exact head CI pending.

## 2026-11-27 D13 final candidate evidence
[Run 45971644956](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45971644956) completed/success, exact head `b61c1cddb9c1b67b3ebd1bfe7b7b1548b0729081`, PR #15 Draft, base dev/d12. Actual checkout logs verified on all four jobs: macOS ARM64 140413301471, Windows Server x64 140413301959, Windows 11 ARM64 140413301965, Ubuntu 140413302084. Each ran `python -m unittest discover -s tests -p test_request_gate.py -v` 6/6 OK and `node --no-warnings --test tests/test-request-db.mjs` 4/4 PASS (40/40 combined), cumulative steps including governance and native MCP/installation all successful. Windows 11 Enterprise build 26200 ProductType=1 ARM64. Run 45971488857 exposed SQLITE_BUSY on macOS, Ubuntu and Windows Server; fixed by busy handler before WAL and bounded retry, not by weakening tests. Earlier cancelled/superseded runs are not acceptance evidence. D13 candidate ready, formal BLOCKED: actual host, trusted approval, risk review, power loss and cross-store reconciliation remain unverified; conservative Git progress and legacy scope limitations remain. No real model or release; no merge. D14 may proceed under candidate authorization. Evidence-only commit requires recheck.


## 2026-11-27 D14 candidate
Base `f123cb30cf07023e2667126ff6a538890bf68122` (D13 verified code b61c1cddb9c1b67b3ebd1bfe7b7b1548b0729081, Run 45971644956 PASS; evidence-only follow-up). Opt-in v2 --stream-events, MCP streamEvents requires requestId; resume inherits the persisted flag. Legacy default unchanged; D13 default request hashes unchanged. Concurrent binary pipe readers, bounded queue, byte caps stdout 4MiB/stderr 1MiB, JSONL line cap 64KiB, UTF-8 validation on complete lines; incremental raw local artifact writes, fixed metadata snapshots with atomic durable seq and 64-entry rolling replay window, heartbeat and cursor/gap. No raw output in task_events; process_exit is not task acceptance. Output overflow/malformed stream/timeouts stop owned process tree, discard partial usage/session inference and never report success. Raw log cap stops instead of silently rotating/deleting raw evidence; metadata window rotates, full raw-log rotation and cross-turn global sequence are not implemented. If context/session identity or state settlement fails, retain pending/running for manual reconciliation. No new cancel authority or real host test; UI push transport and actual host reconnect remain unverified. Rollback: omit opt-in on new tasks; do not downgrade active streamed tasks or delete artifacts. Four-environment CI pending.

D14 review follow-up: strict duplicate/nonfinite JSON rejection; wait for pending stdin/pipe notifications before accepting EOF; persist stream_integrity, block resume for timeout/overflow/launch failure or unverified stream, retain interrupted task and unknown usage on streaming/session exception. Test actual local mock run/resume, cumulative token settlement, failure and no relaunch. Legacy request digests remain compatible. D13 evidence-only recheck Run 45973332876 four environments PASS. Current exact-head D14 CI pending.

## 2026-11-27 D14 final candidate evidence
[Run 45973849986](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45973849986) completed/success on exact head `b7bc081c680e94f87a3012d5fa1f0f54d93116b5`; PR #16 remains Draft. Checkout logs verified: macOS ARM64 job 140420669725, Windows Server x64 140420670268, Windows 11 ARM64 140420670134, Ubuntu 140420670209. Each ran `python -m unittest discover -s tests -p test_streaming.py -v` 8/8 OK (32/32); native MCP cursor replay/gap/invalid-order checks and all applicable cumulative steps PASS, including governance and Windows lifecycle. Windows 11 Enterprise build 26200 ProductType=1 ARM64. Initial Run 45973642495 superseded/cancelled, not acceptance evidence. Tested local subprocess and synthetic worker only, no real model. Candidate ready; formal BLOCKED by actual host/UI, actual cancellation and reconnect, full raw log rotation and dependency gates. D15 candidate may continue under existing authorization. Evidence-only commit requires recheck.


## Formal acceptance follow-up: D14 process-exit correction (2026-11-27)
Historical D16 Run 45982277920 macOS PermissionError EPERM during D14 rapid process exit remains recorded. Backport only terminate_owned_process_tree and test_owned_process_exit_race_permission_error from verified D16 head ffa9c4e6312d3b034d306ec3a4907cf0f1fdc870 (code tested 6db070f17039338762e03a375c911873302fa32b, Run 45982938825 four environments PASS). No later-card implementation imported. Do not signal group after Popen reaped leader; EPERM wait/owned-child fallback, descendants remain unverified. New D14 exact-head CI NOT_RUN at commit creation; candidate.ready=false until verified. D14 stays BLOCKED: actual cancellation, escaped descendants, real host/UI/reconnect, raw rotation and dependencies remain outstanding. Existing D15–D22 contain this correction in cumulative D16+ or require integration before formal merge; do not force-push or merge main.
