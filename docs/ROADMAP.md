# 完整开发路线（规划版）

目标：Windows 原生优先，兼容 macOS/Linux，保留 Antigravity MCP UI 和 Git Worktree 隔离；优化 Gemini↔Codex 通信及本地性能，保证审批和正确性。

D00–D02 DONE。2026-11-27 用户明确验收 D01、D02 并授权合并 PR #2、#3；批准 D03–D22 推荐 A 按依赖实施及 GitHub Actions 测试。后续 PR 的合并、真实模型测试及正式发布仍遵守独立授权门禁。 原始 D01 失败/NOT_RUN 保留，D02 治理 CI 通过。

## 阶段顺序

### P0 — 准备与基线（D00–D02）

| 卡片 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| [D00](decisions/D00.md) | 独立仓库与上游基线 | 无 | DONE |
| [D01](decisions/D01.md) | 基线测试与可复现基准 | D00 | DONE |
| [D02](decisions/D02.md) | 开发与验收治理 | D00 | DONE |

### V1.1 — Windows 原生适配与正确性（D03–D08）

| 卡片 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| [D03](decisions/D03.md) | 跨平台路径与运行时发现 | D01,D02 | DONE |
| [D04](decisions/D04.md) | 跨平台锁与状态完整性 | D03 | PROPOSED |
| [D05](decisions/D05.md) | 安装器和环境诊断 | D03,D04 | PROPOSED |
| [D06](decisions/D06.md) | 审批门禁与执行边界 | D04,D05 | PROPOSED |
| [D07](decisions/D07.md) | 任务结果与进程生命周期正确性 | D04,D06 | PROPOSED |
| [D08](decisions/D08.md) | 历史任务定位与 Windows 发布门禁 | D05,D06,D07 | PROPOSED |

### V1.2 — 低 Token 通信（D09–D13）

| 卡片 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| [D09](decisions/D09.md) | 模型可见的轻量 MCP 接口 | D08 | PROPOSED |
| [D10](decisions/D10.md) | 结构化通信与短报告协议 | D09 | PROPOSED |
| [D11](decisions/D11.md) | 共享黑板与会话复用 | D10 | PROPOSED |
| [D12](decisions/D12.md) | Token 遥测、预算与动态模型路由 | D01,D10,D11 | PROPOSED |
| [D13](decisions/D13.md) | 幂等派发与循环终止 | D10,D12 | PROPOSED |

### V1.3 — 高性能执行（D14–D17）

| 卡片 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| [D14](decisions/D14.md) | 实时流式执行与事件总线 | D07,D13 | PROPOSED |
| [D15](decisions/D15.md) | SQLite 任务状态迁移 | D04,D14 | PROPOSED |
| [D16](decisions/D16.md) | MCP 查询缓存与 UI 增量刷新 | D14,D15 | PROPOSED |
| [D17](decisions/D17.md) | 动态并发与 Worktree 资源治理 | D14,D15,D16 | PROPOSED |

### V2.0 — 双模型编排与发布（D18–D22）

| 卡片 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| [D18](decisions/D18.md) | 确定性编排状态机 | D13,D15,D17 | PROPOSED |
| [D19](decisions/D19.md) | 风险驱动审查与验收 | D18 | PROPOSED |
| [D20](decisions/D20.md) | 常驻 Codex App Server 可选适配 | D18,D19 | PROPOSED |
| [D21](decisions/D21.md) | 可观测性与性能/Token 验收 | D12,D16,D19,D20 | PROPOSED |
| [D22](decisions/D22.md) | 发布、兼容性与回滚 | D21 | PROPOSED |

## 批次退出标准

- P0：固定上游快照、保留 MIT、基线与决策治理。
- V1.1：Windows 原生实机及三平台 CI 通过；修复 P0/P1 正确性问题。
- V1.2：紧凑通信、版本化增量、预算与幂等；用量按真实/估算/未知分开。
- V1.3：事件流、状态迁移、查询及 UI 优化完成，并有可比性能证据。
- V2.0：状态机、风险审查、可选 App Server、端到端验收与可回滚发布。

## 工作节奏

每张卡先确认选择与范围 → 创建独立分支 → 最小实现 → 测试与审查 → 提交 Draft PR → 用户验收及合并授权 → 更新卡状态。允许无冲突卡在各自依赖满足后并行，但默认一次只实施一张卡。禁止自动合并或向上游推送。

## 指标

| 指标 | 基线 | 目标（待基准确认） |
|---|---|---|
| 总模型 Token | 待测 | 下降 30–60%，不是承诺 |
| 模型状态/结果响应 | 待测 | 约 200/500 Token（估算预算） |
| 任务成功率 | 待测 | 不低于经批准的基准容差 |
| P0 安全/数据完整性回归 | 待测 | 0 |
| UI 查询、I/O、p95 | 待测 | 同任务可比较下降 |
| Windows 原生验收 | 未测试 | 真实安装、MCP、派发、恢复、取消、回滚通过 |

详见 [基准与验收](BENCHMARK.md)、[上游来源](UPSTREAM.md)、[执行规范](../AGENTS.md)。

D03 已通过实际验收并合并，D04 开始；D03–D21 条件合并授权已记录于治理文档。