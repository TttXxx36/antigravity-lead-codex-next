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
| [D15](decisions/D15.md) SQLite 任务状态迁移 | V1.3 | D04,D14 | BLOCKED | PR #17 四环境 PASS；真实宿主迁移/恢复及依赖验收阻塞；D16 可继续 |
| [D16](decisions/D16.md) MCP 查询缓存与 UI 增量刷新 | V1.3 | D14,D15 | BLOCKED | PR #18 四环境 PASS；UI 构建/性能证据已补齐；真实宿主及物理 I/O 未验收；D17 可继续 |
| [D17](decisions/D17.md) 动态并发与 Worktree 资源治理 | V1.3 | D14,D15,D16 | BLOCKED | PR #19 集成四环境 PASS；真实宿主、取消及可信清理未验收；D18 可继续 |
| [D18](decisions/D18.md) 确定性编排状态机 | V2.0 | D13,D15,D17 | BLOCKED | PR #20 四环境累计 PASS；可信验收/实际恢复未验证；D19 可继续 |
| [D19](decisions/D19.md) 风险驱动审查与验收 | V2.0 | D18 | BLOCKED | PR #21 四环境累计 PASS；可信独立审查及项目检查未验证；D20 可继续 |
| [D20](decisions/D20.md) 常驻 Codex App Server 可选适配 | V2.0 | D18,D19 | BLOCKED | PR #22 四环境离线候选 PASS；真实协议、任务/权限/用量/性能对等未验证；D21 可继续 |
| [D21](decisions/D21.md) 可观测性与性能/Token 验收 | V2.0 | D12,D16,D19,D20 | BLOCKED | PR #23 四环境配对候选 PASS；真实质量/Token 未验证；D22 可继续 |
| [D22](decisions/D22.md) 发布、兼容性与回滚 | V2.0 | D21 | BLOCKED | PR #24 四环境候选 PASS；正式依赖/实机/独立发布授权未满足 |

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


## 2026-11-27 D15 candidate implementation
Base `12726d05db0b5149ae4c8232e65669958d8d40d9` (D14 tested code b7bc081c680e94f87a3012d5fa1f0f54d93116b5 / Run 45973849986 PASS). Default JSON unchanged. Explicit state-migrate --confirm-quiescent under existing OS lock, backup exact JSON bytes and reject active/uncertain operations, create separate plugin-owned versioned WAL database, verify row counts and SHA256 metadata/task manifest, publish incompatible-to-legacy state.json marker last. SQLite authoritative only after marker; old binaries fail closed instead of writing stale JSON. Single Python transaction path, row-delta writes, FULL sync, previous snapshot backup before commit, no automatic task deletion. State marker or DB corruption never falls back. Read-only Node MCP reconstructs consistent transaction and verifies checksums; native Codex DB untouched. state-rollback --confirm-quiescent exports current DB to JSON atomically and preserves database/backup. state-recover --source initial|previous only exports verified recovery copy, no activation or silent data loss; corrupt DB requires manual reconciliation. Inactive database after interrupted publish retained. Explicitly stop all old CLI/MCP instances, including untracked calls, before migration; process quiescence confirmation not proof. No production data migrated. Full-snapshot reads still present; D16 handles cache/index query optimization. CI pending.

D15 review/CI follow-up: initial Run 45974526071 migration assertions ran on Windows, but two SQLite fixture connections were not closed by Python connection context manager (WinError 32 during temp cleanup). Explicit contextlib.closing, no skipped assertion or cleanup suppression. Native path guard before any migration directory creation, Node canonical marker and sidecar validation, actual keyed streaming mock run/resume in SQLite with duplicate receipts and D12 usage settlement preserved through inverse migration. Latest exact-head CI pending.

## 2026-11-27 D15 final candidate evidence
[Run 45974689285](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45974689285) completed/success on exact head `de11dc6f48588192c82cfd25172be44cfc5901f1`; PR #17 remains Draft. Checkout logs verified: Windows Server x64 140423383707, Ubuntu 140423384167, macOS ARM64 140423384183, Windows 11 ARM64 140423384199. Each ran test_sqlite_state.py 8/8 OK (32/32); actual Python fixture migration, MCP read, corrupt manifest rejection, inverse migration and unchanged native DB hash PASS; cumulative governance and Windows lifecycle PASS. Initial Run 45974526071 failed on both Windows environments due to fixture connection cleanup (WinError 32); corrected explicitly, no skipped assertions. No production migration or real model calls. Candidate ready; formal BLOCKED by actual host migration/recovery, manual quiescence, dependency gates and unverified power-loss recovery. Recovery exports backup only, not automatic activation. D16 candidate may continue under existing authorization. Evidence-only head requires recheck.


## 2026-11-27 D16 initial candidate
Base 07ce2d89eeee61dcd4eafa8111e88f260d3b39a1 (D15 tested de11dc6f / Run 45974689285 PASS). Explicit ALC_QUERY_CACHE=1 enables app-only revision endpoints; default legacy fresh paths, model-facing task/authorization checks remain unchanged. Bounded 5s display TTL, 32 entries/2MiB, single-flight same source, native/owned DB and WAL metadata invalidation, errors/unknown stamps bypass cache; large legacy JSON bypasses cache. Local quota rollout only, bounded 15s cache, no live app-server or real model calls. UI source selects delta only if advertised, avoids unchanged render, ID detail no automatic Git unless tab selected, slower idle/hidden polling. Changed views still use existing full render; report-specific mtime optimization, measured paired p95/query/I/O, full DOM partial patch and actual host acceptance incomplete. Linux CI builds UI source but tracked dist/app.html is NOT yet rebuilt/committed; do not mark candidate ready or advance D17 until remaining candidate evidence. No merge.

## 2026-11-27 D16 follow-up
Initial ledger head 34046f42ee0393b1bbfa6186ab866f626886d3aa / Run 45975558725 four-environment PASS, 20/20 cache tests, Linux Vite build and MCP delta passed. D15 evidence recheck 45975155258 PASS. Added bounded per-report mtime/digest-aware display cache, large legacy JSON metadata stamping, exact/prefix selector cache only for display, partial panel replacement for silent refresh, stale selection/failure and refresh coalescing safeguards. Added real SQLite query/open and logical content/wire byte benchmark on paired 30-call synthetic fixture; p95 is measured, not estimated; metadata stat syscalls/physical storage I/O not counted. Temporary Linux build transfer emits only generated public-to-repo static bundle chunks and git blob SHA, no token, no write permission; remove transfer step after importing exact verified blob. Dist not updated yet. Formal host, actual browser interaction and physical I/O remain unverified. No D17 start until candidate gate.

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


## 2026-11-27 D18 initial candidate
Base adefa4881d3c7ffa1480ab77139cd0fbd6d3a417, D17 verified 838787a Run 45983586382 all four PASS. A: explicit opt-in local CLI orchestration state machine persisted in existing locked JSON/SQLite state. Queue pins exact task/request ID, envelope SHA, immutable scope and canonical cwd; D13 request reservation creates lease atomically, D17 ticket and admission change queued→running in same transaction, D13 terminal receipt and orchestration settlement commit together. Explicit revision CAS for cancel/retry/verify, bounded two known-failure retries retain D13 progress/retry guards; no automatic retry/replay or PID lease expiry. Abrupt owner death leaves durable pending lease, read-only recover reports manual reconciliation, no new worker; queued cancellation only before reservation. Hash-linked bounded audit (128 tasks, 24 events/task, cursor limit 10); hashes detect accidental corruption, not authentication. Worker success → verifying only; artifact digest/identity check cannot substitute for independent trusted acceptance, verify always BLOCKED, completed transition explicitly unavailable until trusted host approval bridge. Timeout/uncertainty retain lease, migration blocked while unresolved. Existing non-orchestrated behavior remains default; managed registered task cannot bypass keyed/scheduler gates. MCP adds exact bounded read-only orchestration_status; no model-facing mutation, acceptance, cleanup or merge. No real model/production writes, permissions or formal merge. Actual host/trusted acceptance and active cancellation/reconciliation remain unverified. Candidate CI pending.

D18 follow-up: initial Run 45985228514 orchestration regression step PASS on each platform (full initial run may be superseded). Added real installed Python dispatcher fixture to native MCP integration, exact queued/cancelled receipts, no task goal/path leakage, no model-facing mutations, unchanged state JSON/native DB hashes. Reject repeated failure/no-progress when queueing retry, before creating a doomed revision; D13 launch gate remains authoritative. D17 evidence-head recheck Run 45984857562 four environments PASS. Latest exact-head cumulative CI pending.

## D18 exact-head candidate verification
Run 45985424111 completed/success on all four actual runners; exact source fbd1dbc29cedf1c2d1900151dba11b8827f41788. Ubuntu 140459741740, macOS ARM64 140459741767, Windows Server x64 140459741267, Windows 11 ARM64 140459741896. 9/9 state-machine tests per environment (36/36), real local mock subprocess crash, timeout, duplicate/reservation, SQLite restart, explicit retry/CAS, tampered artifact/audit, scheduler gating and native MCP read-only receipt PASS; cumulative CI/governance PASS. Earlier run 45985228514 all four orchestration steps PASS; two jobs superseded, not a full four-platform PASS. Candidate ready; formal BLOCKED: actual host reconciliation, independent trusted acceptance/completed bridge, cancellation and upstream formal acceptance unverified. No automatic merge. Evidence-only head recheck required.


## 2026-11-27 D19 candidate
Base 7fbc1b0ac2821a6a3a09806b829503ae72361a05; D18 exact-head cumulative Run 45985424111 PASS. Explicit local CLI orchestrator-risk-review --task-id --expected-revision --head --approve-git-checks; no unapproved checks or arbitrary project code. Fixed bounded Git commands compare full immutable recorded base and explicit HEAD commit, ancestry, raw diff modes/paths, patch digest and whitespace; external diff/textconv/hooks/fsmonitor/lazy fetch disabled, no network protocols. Recheck HEAD and orchestration CAS before publishing one bounded digest-linked receipt per task; retain original evidence, duplicate reads do not rerun. Conservative high risk for all non-allowlisted changes, structural changes, sensitive paths/content, unknown/empty/binary/oversize diff; only ordinary modifications to docs/user-guide or docs/tutorials may skip repetitive review when all fixed Git checks PASS. Worktree, project tests and independent review explicitly NOT_RUN; committed pair only, not proof of clean tree, task scope compliance or trusted independent review. D18 verifying never becomes completed or auto-merges; receipt tampering fails closed. No real models, permissions, arbitrary commands or merge. CI pending; formal trusted host/operator and independent review blocked.

Initial Run 45989026894 D19 step Ubuntu/macOS PASS; both Windows runners FAIL (normal CRLF fixture reported whitespace FAIL; candidate not accepted). Set explicit Git core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol, fixture baseline LF and explicit CRLF positive/actual trailing-space negative tests. Original failure preserved; new exact-head CI pending. D18 evidence head 7fbc1b0 Run 45988615991 all four PASS.

## D19 exact-head candidate verification
Run 45989218603 completed/success, exact source cb785a16c940ab8cc18dea4441cf3936b8da35df. Four actual runners: Ubuntu 140472497754, macOS ARM64 140472497378, Windows Server x64 140472497959, Windows 11 ARM64 140472497825. All 10 risk tests per platform (40/40), explicit CRLF positive/real trailing whitespace negative, actual Git pinned evidence/ancestry, sensitive and unknown mandatory audit, no external diff/textconv, explicit approval, stale/tampered receipt rejection, real D18 mock worker integration, no completion/merge, cumulative CI and 23-card governance PASS. Initial Windows CRLF failure 45989026894 preserved. Candidate ready; formal BLOCKED: trusted independent human/host review, uncommitted worktree and project tests NOT_RUN by local Git-only evidence policy; full task scope/compliance and upstream formal acceptance unverified. Evidence-only head recheck required.

## 2026-11-27 D20 candidate
Base 552c27d79133a287a2a3c4424d410d09f26e8886, D19 exact source cb785a1 Run 45989218603 four environments PASS. A: CLI remains default; ALC_APP_SERVER_EXPERIMENTAL=1 only requests experimental capability diagnostics, cannot route a production task. Separate codex_app_server.py stdio probe transport accepts an explicitly supplied owned process from trusted code; dispatcher never constructs one. Strict bounded UTF-8 JSONL, exact initialize response version, initialized and metadata-only thread/read, request identity, no arbitrary RPC or server approval replies, explicit reconnect, no mutation or automatic replay. D13 pending/uncertain, D17 live ticket or D18 outstanding lease blocks even advisory fallback. Compare effective readOnly/workspaceWrite metadata, approval never, network false, exact roots/cwd/model/effort; unknown/new permission profiles refuse. Observe only thread/tokenUsage/updated.tokenUsage.total cumulative snapshot (not spend or additive last); duplicate/rollback/gap conservative, terminal notification is a worker claim only. Actual offline mock subprocess tests, reuse/reconnect/negative protocol fixtures and cold-vs-reused timing (not native performance). Native executable discovery only, NOT_RUN for actual native protocol, result/permission/usage parity and performance; actual real server/turn launch, credential/network/host integration and trusted review require separate approval/evidence. No actual app-server startup or real model call, no formal merge. Source contracts reviewed 2026-11-27: https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md ; https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/json/v2/ThreadReadParams.json ; https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/typescript/v2/SandboxPolicy.ts ; https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/json/v2/ThreadTokenUsageUpdatedNotification.json . CI pending.

## D20 exact-head candidate verification
Run 45990023472 completed/success, exact source 78043c43833f10fafc48eddf0b6a3398e3e6e520, four actual runners. 10/10 D20 tests each (40/40): strict handshake/version, reused owned local mock process, explicit reconnect with no mutation or replay, unsupported/timeout/disconnect/oversize/invalid/approval refusal, pending D18 request fallback blocked, strict policy receipt comparison, usage snapshot deduplication/gap, CLI default and cumulative CI/governance PASS. D19 evidence head 552c27d Run 45989845681 four environments PASS. Fixture-only benchmark, six reads per pair, six cold processes versus one reused: install (windows-11-arm) job 140475191922: cold 328 ms, reuse 47 ms, cold median 54.5 ms; install (macos-latest) job 140475192216: cold 173.822 ms, reuse 29.072 ms, cold median 29.14 ms; install (windows-latest) job 140475192244: cold 188 ms, reuse 31 ms, cold median 31 ms; install (ubuntu-latest) job 140475192325: cold 135.046 ms, reuse 24.117 ms, cold median 22.398 ms. These are actual mock process/transport timings, not real model speed, quality, billing or native App Server performance. Native execution remains structurally disabled. Native protocol startup, actual same-task result and permission enforcement equivalence, native usage/latency and host recovery are NOT_RUN. No actual model or native App Server startup, no credential/network changes, no formal acceptance or merge. Candidate ready for D21 offline measurement work only; formal BLOCKED. Evidence-only head recheck required.

## D21 candidate implementation 2026-11-27
A paired benchmark; exact predecessor 505f5bf955f47b66c935b3371e3991085221e083 (D20 evidence recheck 45990579786 all four PASS). Same checked-out implementation, legacy full snapshot vs opt-in delta, NOT historical main-vs-candidate benchmark. Actual native MCP over stdio and synthetic SQLite fixture: six independent pairs, five polls per arm, alternating order, force first candidate refresh/new revision, then reuse; OS caches not controlled. Validate equal displayed task IDs/status/title, managed IDs/status, stats, connected health on every successful poll. Capture actual serialized request+response JSON-RPC envelope bytes excluding newline (not network or model tokens), per-batch wall clock median and nearest-rank p95, explicit attempted/success/failure/unknown/not-run counts, no retries. Failures retained; no savings if incomplete. 30–60% communication hypothesis explicitly report BELOW/WITHIN/ABOVE, no guarantee. Fixture-only quality and regression, real quality/Token NOT_RUN, Gemini UNKNOWN, no byte-to-token conversion or billing claim. Numeric whitelist output with no prompts/path/raw payloads; checkout and fixture shape digest, Node/OS/arch. Full history read-only checkout for pinned ancestry, no permission expansion. Six summary/negative unit tests and actual paired native MCP regression on four runners pending. Formal acceptance blocked real tasks, model/effort/cache and independent evidence.

## D21 exact-head candidate verification
Run 45999409240 completed/success; source c1bff452b8718c759820ae919aa05c1c6246811b. Four actual environments; six summary/validation tests each (24/24); native MCP and cumulative CI/governance PASS. Six paired repetitions per arm with five polls per repetition (30+30 per platform, 240 total); 48/48 batches and 240/240 polls PASS, 0 retries; compared displayed IDs/status/title, managed IDs/status and stats. Same checkout legacy full vs revision delta; fixture shape digest 1343cc3bb9f735d31622a771ee10c07d900f37ebc324e04eae1e96265d5c3f39; not historical baseline execution. Both arms run in actual MCP fixture, no model/effort; force first refresh then reuse, OS cache not controlled. Latency per 5-poll batch, p95 nearest rank over 6 samples, not production tail estimate. Bytes serialized JSON-RPC request+response excluding newline; denominator baseline bytes, no network or token conversion.

| Runner / job | Baseline bytes | Candidate bytes | Reduction | Median ms | p95 ms | Hypothesis |
|---|---:|---:|---:|---|---|---|
| install (windows-11-arm) / 140506913225 | 1397170 | 289522 | 79.278% | 34.935 → 18.55 | 39.621 → 23.288 | ABOVE |
| install (windows-latest) / 140506913630 | 1397050 | 289498 | 79.278% | 21.277 → 11.703 | 24.326 → 13.048 | ABOVE |
| install (macos-latest) / 140506913695 | 1405210 | 291130 | 79.282% | 9.78 → 4.86 | 11.008 → 5.796 | ABOVE |
| install (ubuntu-latest) / 140506913703 | 1339600 | 278008 | 79.247% | 11.6 → 6.377 | 13.886 → 7.111 | ABOVE |

Measured communication exceeds 30–60% hypothesis for this narrow stable synthetic polling workload; not actual total communication, cost, real task quality/success or token savings. Fixture checks zero failures and zero observed P0 fixture regressions; all actual real tasks/model quality, actual Codex usage, Gemini usage, mixed-workload baselines, confidence and production P0 acceptance NOT_RUN/UNKNOWN. No real model invocation or merge. Candidate ready for D22 offline package/rollback preparation; formal BLOCKED. Evidence-only head recheck required.


## D22 candidate implementation 2026-11-27
Base 1226e5d27db5737cc843145a956c980790b6aac5; D21 exact source c1bff45 Run 45999409240 completed/success all four. A staged unpublished source RC. Exact committed Git objects only, fixed USTAR/gzip metadata and sorted members, SHA256 archive + per-file canonical manifest, both MIT notices preserved unchanged. Strict source allowlist, no node_modules/real state/screenshot/.github workflow/credential files; reject non-text, common secret patterns, invalid/reserved paths, links, case collisions and size limits; scan is limited, not a guarantee. Verify digest/manifest/identity/canonical archive before fresh-directory extraction. No dependency install, network, model, tag, release or upstream push by packaging tool. CI tests two byte-identical builds per runner, Git blob match, tamper/traversal/identity, secret-pattern negatives, disposable old code tree restore with real SQLite/JSON untouched; actual Unix installer uses explicit mock Node/npm/curl, existing native Windows lifecycle tests actual installation/restore/doctor using native mock executable. Source package only; actual Antigravity/Codex host and production migration/rollback NOT_RUN. Read-only CI retains short-lived RC artifacts only after applicable cumulative checks on dev/d22 PR; no formal publication. README/English/CHANGELOG/guide updated, license originals preserved; historical source retained. Formal release blocked all upstream formal acceptance, actual host and explicit authorization. CI pending.

Initial Run 46000304667 all four FAIL at package preflight: existing D11 tests/test_context.py includes literal PEM header only as a synthetic rejection test (no actual key body); scanner correctly refused it. Construct identical runtime negative-test string by concatenation instead of embedding contiguous marker in source. No scan exemption, pattern removal or credential disclosure; add immutable blob SHA to diagnostic (never matched contents/filename). Original failure preserved. Reverify all four.

Run 46000617038: archive identity/reproducibility/secret/tamper tests passed; Windows D22 steps passed, Ubuntu/macOS rollback test failed because local install returned nonzero. Independently reproduced legacy cleanup_tmp short-circuit returning 1 from EXIT trap under set -e when TMP_DIR empty. Fix only cleanup guard to if block, no deletion of any additional path; test requires actual completion marker and exit 0, without raw captured paths. Prior failure retained. D21 evidence head 1226e5d Run 46000026000 all four PASS. New exact-head CI pending.

## D22 exact-head candidate verification
Run 46000875781 completed/success, exact source 7eb7b43cfe7be57aae2854f94aecf962e7745886. All four actual runners: seven D22 tests each (28/28), each builds twice byte-identically, checks Git blobs/license/source allowlist, strict checksum/identity/manifest/unsafe path/tamper refusal, explicit synthetic-secret negatives, fresh-directory extraction and isolated old-code rollback. On Ubuntu/macOS actual Unix installer with mock Node/npm/curl dependencies completed exit 0 and manual old-component restore; Windows fixture package-tree rehearsal plus actual native PowerShell installer/upgrade/restore/doctor/uninstall/SQLite preservation with native mock executable in cumulative CI. Each rollback recovered 3 components and 2 persistent files byte-identically, SQLite readable. Full cumulative regressions, D21 paired benchmark, governance and Linux UI reproducible rebuild PASS. Four RC artifacts uploaded successfully, all exact inner archive/manifest SHA256 equal across four runners. Initial Run 46000304667 all four blocked on literal synthetic PEM test marker; Run 46000617038 Ubuntu/macOS rollback failed on legacy local installer EXIT trap; both fixes independently tested, failures retained. D21 evidence head 1226e5d Run 46000026000 PASS.

- Version label: v2.0.0-rc.1 (filename only, no Git tag or Release)
- Archive: antigravity-lead-codex-v2.0.0-rc.1-7eb7b43cfe7b.tar.gz, 1812688 bytes, 138 source files
- Archive SHA256: 66835dac37201ffa021a35663ececda4a153d9e7c5a0faa3b8cc3056db51d931
- Manifest SHA256: f31e40e6e8ae4b0693778942ea5b6bd3b42351e2c6aa2fee01026e9dd5b49544
- Artifact run: https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46000875781 (7-day retention; external Artifact ZIP digest differs from inner archive SHA256)

| Runner / job | Rollback mode | Artifact ID |
|---|---|---:|
| install (ubuntu-latest) / 140511976927 | actual_unix_installer_mock_dependencies | 15197329055 |
| install (macos-latest) / 140511977264 | actual_unix_installer_mock_dependencies | 15198081739 |
| install (windows-latest) / 140511977341 | portable_package_tree_rehearsal | 15197134950 |
| install (windows-11-arm) / 140511977363 | portable_package_tree_rehearsal | 15198676005 |

No real provider or native Antigravity/Codex host, no production migration, no complete credential/third-party dependency review, no release/signing/tag/merge/upstream push. Common-pattern scan zero matches is not proof of absence of secrets; source package only, not offline dependency bundle. D05–D21 formal blockers remain. D22 candidate ready; formal BLOCKED, explicit release approval still required. This exact code-head artifact is the verified RC, distinct from the subsequent evidence-only commit; evidence head must be rechecked and would have a different source SHA/archive.

## 2026-11-27 正式验收启动：RC 保全及隐私扫描修复
- 实际 main 114e0c205f326b4af0935656ef482bba8270b284；D05 #7 仍 Draft、head 7b29c0b40fcfa61305c587dbc5992270e5018d27，main 比较 diverged ahead 6 / behind 11；四 job Run 45936571412 success。D05 实际 Windows x64 / Antigravity / Codex NOT_RUN，不合并。#7–#24 均 Draft/open/unmerged。
- 两套 Ubuntu artifact 15197329055 / 15198117897 已下载；ZIP、内层 archive、manifest SHA256 分别与元数据/既有记录一致；每套 138 文件 size/mode/digest 和 rc_package.verify_bytes canonical 校验 PASS。保留原包与 Run 46000875781 / 46001598488，不混用。未发布。
- BUG-006（建议 P1，D22）：原 Bash 隐私扫描用固定 /tmp 文件并输出匹配原文；合成 fixture 实测退出 1 且泄露原文。另静态确认 grep 错误会被当作无命中。修复取消临时文件和原文输出，区分 0/1/2，扫描异常 fail closed。Linux Python 3.13.5 本地 PrivacyScannerTests 3/3 PASS；修复后源码扫描 PASS。无真实私密数据。新 head 累计 CI 尚未完成；不标 CLOSED/DONE，历史 RC 不等于新候选。
- 锁文件初审：162 dependency entries（95 non-dev），MIT 150/BSD-3-Clause 3/ISC 8/BSD-2-Clause 1；162 integrity 字段存在，resolved 均 registry.npmmirror.com，两个 hasInstallScript（esbuild/fsevents）；仅锁文件元数据，不代表实际依赖许可证文本、CVE、供应链已审完。保持 ignore-scripts；不改 registry 或扩大网络许可。
- 原始 RC 治理检查与 18/18 治理测试本地 PASS。真实宿主、模型、完整 license/privacy、实际回滚与发布授权仍 BLOCKED；D14 EPERM 修复需回移。
