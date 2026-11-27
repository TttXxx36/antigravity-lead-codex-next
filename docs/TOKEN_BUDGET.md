# D12 使用说明（候选）

显式 run 参数 `--max-turns N --max-tokens N --max-seconds N --budget-route` 可组合。预算持久化在任务状态，恢复不能增加限额。Token 限额仅比较已结算的 CLI usage；一轮可超预算，下一轮阻断。缺失/歧义 usage 不按0计，有限 Token 预算下一轮停止。累计时间仅进程时间，timeout 包含终止宽限、非硬实时。旧任务无完整用量历史时总数 unknown。实际模型身份必须由终态 CLI 事件明确报告，请求 model 与实际 model 不混淆。Gemini 未接入，不估算。缓存/推理属于子计数，不重复加总。`--budget-route` 读取本地模型能力，按复杂度选择已列 effort，未知能力时不推测；恢复显式改变选择需 `--route-reason`。旧默认 smart 保留。CLI status 可读摘要；完整本地 result 含逐轮 usage_telemetry。未受管的外部调用和单独 review 不在该预算覆盖范围。所有合成数据仅测试，实际模型、真实 Token 降幅和跨模型费用待另授权验证。


审查补测：终态失败/冲突或非法 total_tokens 不作为已知计数，预算状态结构校验，pending 状态不把尚未结算计数冒充总数；恢复重新检查缓存能力；带预算任务的关联 review 默认拒绝（未接入预算结算，不能作为绕过入口）。独立非受管调用仍不属于全局预算。首轮 45947038480 被新提交替代，最终候选单独测试。

D12 final stream-integrity review: nonempty malformed JSONL, non-object events, duplicate keys and nonfinite constants invalidate the sample. A total without both input/output components is unknown until the provider semantics are verified. Finite token budgets stop the next invocation on such incomplete evidence. Blank lines remain harmless. Initial follow-up Run 45947156315 is superseded by this exact-head regression; no claim of final PASS until confirmed.