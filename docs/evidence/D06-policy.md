# D06 候选执行边界

2026-11-27 用户批准分离候选开发与正式验收/合并。D06–D22 可基于经 CI 验证的前置候选分支依赖顺序开发、独立 stacked Draft PR；实际验收门槛、DONE、main 合并条件不变。前置候选有未解决的 CI FAIL/安全缺陷时先修复；缺真实宿主等环境证据可在不启用受阻能力的前提下继续候选开发。禁止真实模型测试、权限扩张、发布。

基线 D05 7b29c0b40fcfa61305c587dbc5992270e5018d27 / Run 45936571412 success。风险取舍：保留模型派发的本地受管入口及只读询问，禁止未受管 queue/resume（不会隐式 fallback），明确 network_access=false，禁止批任务混合联网、危险 sandbox 和破坏性 cleanup。没有可信宿主签发方，当前任何网络请求均拒绝；不会以本地文件/环境变量/布尔值冒充用户授权。Hook 仅标准人工审批、危险操作提示，不作为执行边界。仅使用本地额度证据，实时 app-server 待授权。实际 Codex 服务模型传输不由 worker sandbox 控制；真实 OS 沙箱、外部写及 Git 合并约束、可信授权签发/过期仍未验证，必须保留 BLOCKED，不可发布。测试仅 mock、本地及 Actions。

## 实际四环境 CI（候选开发就绪，不是正式验收）
[Run 45937059171](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45937059171) completed/success，精确 tested commit `b652c5877df2e5a91d5191e1f21fab8c208b3015`；Windows 11 ARM64、Windows Server x64、Ubuntu、macOS 四个 job 均成功。每环境执行5项执行策略、5项 dispatch/hook、18项治理测试（合计112次通过），并运行 D03/D04 平台/状态回归、真实本地 MCP synthetic 及 Windows 原生安装生命周期。真实模型测试未执行。D06 否决未授权操作的候选可作为后续开发基础；可信宿主签发任务/范围/有效期授权、实际 OS sandbox、外部写与真实宿主验证仍 BLOCKED；不得将全部拒绝冒充完整授权功能。PR #8 base dev/d05 保持 Draft，未合并。


## 2026-11-27 formal acceptance security review
Static review of exact D06 head 39cc294bba80c5d563df21b4b329a2646293e017 found a plain cleanup path calling remove_worktree and setting cleaned without trusted authorization (only force/delete-branch and reserved state rejected). BUG-007 proposed P1; potential worktree removal during active/unaccepted task, not a reproduced data loss. Correction rejects all D06 cleanup before state access or Git mutation, and regression checks plain/force/delete-branch denial. D17+ cumulative cleanup already preview-only; intermediate D07–D16 need safe integration before formal acceptance. MCP descriptions now accurately describe denied unmanaged queue/resume and local quota only; tool identifiers/schema preserved. No actual deletion, model calls, permission expansion or host grants. New exact-head tests NOT_RUN until CI; candidate.ready=false, formal BLOCKED. D05 real environment still missing. Trusted scoped grants and actual OS sandbox remain unimplemented/unverified respectively.
