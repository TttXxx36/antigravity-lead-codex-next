# D12 用量与预算候选

基线 D11 cbfbb93fcf6dc00a42cc061993190519fe9bb8b1（Run 45945706823 success）。

## 候选实施
终态 CLI usage 每进程一次；仅唯一 identified 重复事件去重，歧义/缺失 unknown，输入+输出不额外累加缓存/推理。累计已知和与未知轮次分别保存，实际 model 仅 CLI 明确报告，Gemini unknown。run 可显式 --max-turns/--max-tokens/--max-seconds，持久化预算不可经 resume 修改；每轮之前检查，未知 Token 时禁止继续有限 Token 预算任务，时间限制仅累计受管进程耗时及每轮 timeout，不保证精确硬停止。--budget-route 使用本地 cache 支持的 effort，缺能力不猜测，变更必须记录理由；默认旧 smart。测试用合成 usage，不代表真实模型用量。真实 CLI 字段语义、Gemini、实际模型及对照基准未验收。
测试覆盖已知/未知、重复/冲突、缓存与推理子项、预算耗尽、mock 执行与恢复及能力缓存路由。无真实模型请求。预算不适用于未受管外部会话、只读诊断或单独 review；不宣称全系统硬预算。旧任务缺历史用量保持 prior_unknown。