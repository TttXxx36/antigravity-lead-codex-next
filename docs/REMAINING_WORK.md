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
| [D08](decisions/D08.md) 历史任务定位与 Windows 发布门禁 | V1.1 | D05,D06,D07 | PROPOSED | 未实施；按 ID 查询、歧义拒绝、Git -z、DB 错误、三平台与 Windows 实机 |
| [D09](decisions/D09.md) 模型可见的轻量 MCP 接口 | V1.2 | D08 | PROPOSED | 未实施；状态/结果/增量/日志拆分，宿主兼容，保留 UI |
| [D10](decisions/D10.md) 结构化通信与短报告协议 | V1.2 | D09 | PROPOSED | 未实施；版本化 task/result/delta、字段预算、程序证据、拒绝乱序 |
| [D11](decisions/D11.md) 共享黑板与会话复用 | V1.2 | D10 | PROPOSED | 未实施；rev、增量 resume、受控压缩重建、跨任务隔离 |
| [D12](decisions/D12.md) Token 遥测、预算与动态模型路由 | V1.2 | D01,D10,D11 | PROPOSED | 未实施；真实/估算/unknown 区分、预算、路由、避免重复累加 |
| [D13](decisions/D13.md) 幂等派发与循环终止 | V1.2 | D10,D12 | PROPOSED | 未实施；持久 request_id、进度指纹、重复错误停止、授权重试 |
| [D14](decisions/D14.md) 实时流式执行与事件总线 | V1.3 | D07,D13 | PROPOSED | 未实施；流式 JSONL、心跳/seq、内存有界、断线恢复 |
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


## 2026-11-27 formal acceptance security review
Static review of exact D06 head 39cc294bba80c5d563df21b4b329a2646293e017 found a plain cleanup path calling remove_worktree and setting cleaned without trusted authorization (only force/delete-branch and reserved state rejected). BUG-007 proposed P1; potential worktree removal during active/unaccepted task, not a reproduced data loss. Correction rejects all D06 cleanup before state access or Git mutation, and regression checks plain/force/delete-branch denial. D17+ cumulative cleanup already preview-only; intermediate D07–D16 need safe integration before formal acceptance. MCP descriptions now accurately describe denied unmanaged queue/resume and local quota only; tool identifiers/schema preserved. No actual deletion, model calls, permission expansion or host grants. New exact-head tests NOT_RUN until CI; candidate.ready=false, formal BLOCKED. D05 real environment still missing. Trusted scoped grants and actual OS sandbox remain unimplemented/unverified respectively.


## Formal acceptance round 3: BUG-007 candidate evidence
[Run 46004369900](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46004369900) four environments success, exact checkout b9c3fe4df5636aa32bac3ee673e9a0ca5839ddeb directly checked in all logs. Jobs ARM64 140523698666, Windows x64 140523698892, macOS 140523699016, Ubuntu 140523699106. Five execution-policy tests per job PASS (20/20), including plain/force/delete-branch cleanup denial before state/Git access; five dispatch/hook and 18 governance tests per job PASS. BUG-007 candidate fix verified, not formally closed. No real host or model or data deletion. D07–D16 must integrate; D17+ preview-only implementation remains. Formal D06 BLOCKED. Evidence-only head requires recheck.
