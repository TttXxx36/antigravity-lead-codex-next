# D12 使用说明（候选）

显式 run 参数 `--max-turns N --max-tokens N --max-seconds N --budget-route` 可组合。预算持久化在任务状态，恢复不能增加限额。Token 限额仅比较已结算的 CLI usage；一轮可超预算，下一轮阻断。缺失/歧义 usage 不按0计，有限 Token 预算下一轮停止。累计时间仅进程时间，timeout 包含终止宽限、非硬实时。旧任务无完整用量历史时总数 unknown。实际模型身份必须由终态 CLI 事件明确报告，请求 model 与实际 model 不混淆。Gemini 未接入，不估算。缓存/推理属于子计数，不重复加总。`--budget-route` 读取本地模型能力，按复杂度选择已列 effort，未知能力时不推测；恢复显式改变选择需 `--route-reason`。旧默认 smart 保留。CLI status 可读摘要；完整本地 result 含逐轮 usage_telemetry。未受管的外部调用和单独 review 不在该预算覆盖范围。所有合成数据仅测试，实际模型、真实 Token 降幅和跨模型费用待另授权验证。
