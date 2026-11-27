# 2026-11-27 — D00–D22 candidate development checkpoint

## Current position
- Main remains 114e0c205f326b4af0935656ef482bba8270b284. D00–D04 DONE (5/23); D05–D22 BLOCKED with candidate.ready=true (18/23). No PROPOSED or IN_PROGRESS cards. All candidate implementation work reached the authorized offline gate, not formal project completion.
- D21 PR #23 exact source c1bff452b8718c759820ae919aa05c1c6246811b Run 45999409240 4/4; evidence head 1226e5d27db5737cc843145a956c980790b6aac5 Run 46000026000 4/4. 24/24 unit tests, 48/48 paired batches, 240/240 synthetic polls, communication 79.247–79.282% less for stable fixture, actual model token use unknown.
- D22 PR #24 exact source 7eb7b43cfe7be57aae2854f94aecf962e7745886 Run 46000875781 4/4; antigravity-lead-codex-v2.0.0-rc.1-7eb7b43cfe7b.tar.gz, archive SHA256 66835dac37201ffa021a35663ececda4a153d9e7c5a0faa3b8cc3056db51d931, 4 artifacts. See [D22 evidence](evidence/D22-source-rc.md), [D21 results](RESULTS.md), [ledger](EXECUTION_STATUS.json). Evidence-only commit recheck pending at creation; confirm exact PR head CI before further work.

## Formal blockers by card
- D05 安装器和环境诊断 / PR #7: Real Antigravity host and actual Codex version pending; no production merge.
- D06 审批门禁与执行边界 / PR #8: No positive trusted grant issuance or real OS sandbox proof; network, unmanaged queue/resume, live quota disabled; no production merge.
- D07 任务结果与进程生命周期正确性 / PR #9: Real Codex/Antigravity worker tree, escaped descendants and real power-loss not verified; no formal merge.
- D08 历史任务定位与 Windows 发布门禁 / PR #10: Actual Antigravity/Codex end-to-end and Windows x64 desktop unverified; no formal merge.
- D09 模型可见的轻量 MCP 接口 / PR #11: Actual host and token tests NOT_RUN; old records without result_ref unavailable; metadata-only log cursor and nonpersistent hash; not merged.
- D10 结构化通信与短报告协议 / PR #12: Actual model and host unverified; v2 opt-in; batch/MCP v1; no formal merge.
- D11 共享黑板与会话复用 / PR #13: Real host/session continuity, token measurements and formal dependencies pending; opt-in only.
- D12 Token 遥测、预算与动态模型路由 / PR #14: Synthetic usage only; actual provider semantics, Gemini usage, real host/model capabilities, benchmark and formal dependency merges pending; no hard system-wide budget.
- D13 幂等派发与循环终止 / PR #15: Opt-in keyed CLI/MCP only; legacy callers excluded; conservative Git metadata; real host and power loss, cross-store reconciliation and trusted retry approval not independently accepted; no merge.
- D14 实时流式执行与事件总线 / PR #16: Opt-in v2; bounded raw log cap stops rather than rotates; metadata rolling window and per-turn cursors only; real host push/cancel/reconnect and escaped descendants remain unverified; no merge.
- D15 SQLite 任务状态迁移 / PR #17: Disposable fixtures only; actual host migration, manual process quiescence, power-loss and recovery activation not verified; no production migration or native DB writes.
- D16 MCP 查询缓存与 UI 增量刷新 / PR #18: Synthetic fixtures; original paired p95 improvement in four environments but macOS rerun slight increase; actual host and physical I/O unverified; EPERM fallback only owned child, escaped descendants not confirmed; no merge.
- D17 动态并发与 Worktree 资源治理 / PR #19: Real subprocess/Git/SQLite mock fixtures; actual Antigravity host, live cancellation/escaped descendant reconciliation, trusted quota/cleanup approval and dependencies unverified; cleanup preview only.
- D18 确定性编排状态机 / PR #20: Mock subprocesses, real local Git/SQLite and MCP; trusted host acceptance/completed, actual host crash recovery and active cancellation unverified. No automatic merge.
- D19 风险驱动审查与验收 / PR #21: Actual Git pinned committed pair plus D18 mock worker fixtures; worktree, arbitrary project checks, trusted independent approval and scope compliance not verified. No automatic acceptance/merge.
- D20 常驻 Codex App Server 可选适配 / PR #22: Actual mock subprocess transport/reconnect, strict metadata parser, fixture timings only; no native App Server startup, production task routing, actual task/permission/usage parity or native performance verified. CLI stays default; real model and release need separate authorization.
- D21 可观测性与性能/Token 验收 / PR #23: Same-checkout native MCP synthetic polling comparison only; no historical model workload, actual Codex/Gemini usage, real task quality or production P0 verification. No model calls or release.
- D22 发布、兼容性与回滚 / PR #24: Four identical source-only RC artifacts, actual mock installer/portable rollback/SQLite fixtures; no actual Windows Antigravity+Codex host, production rollback, complete privacy/dependency licensing audit, real model parity or release grant. No tag, release, formal merge or upstream push.

## Next work (formal acceptance, not another candidate card)
1. Preserve candidate refs, RC and evidence. Check exact-head final evidence recheck and unresolved errors. Do not merge draft PRs just because synthetic CI passed.
2. Obtain authorized real Windows Antigravity + Codex host, actual version/session/UI and trusted grant evidence. D05–D21 formal acceptance in dependency order; rebase/integrate each accepted exact tested candidate as needed, rerun cumulative tests; D14 process-exit correction exists on later candidate and must be accounted for. Never mark DONE before all actual gates and approved merge are satisfied.
3. Separately approve any actual provider/model experiment, scope/budget and permission. Record real paired baseline quality, actual Codex usage, Gemini usage as measured/estimated/unknown; no simulated bytes-to-token claims. Verify production backup/restore in authorized isolated environment, not native DB mutation.
4. D22 release only after all blockers closed, final exact source/manifest checked, privacy/dependency license review and explicit release approval. No automatic merge, release, upstream push, remote protection change or real-model benchmark; permissions all false. No formal Release or Tag has been created.

This checkpoint is on dev/d22, not main; main's older checkpoint is intentionally not rewritten by candidate development. See [migration](MIGRATION.md) and [RC guide](RELEASE_CANDIDATE.md).
