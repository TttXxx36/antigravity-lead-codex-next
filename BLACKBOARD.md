# D11 任务级黑板（候选）

黑板不是仓库全局共享可写文件。每个受管任务在 dispatch state.json 的 context_board 字段保存其独立版本、稳定目标/范围/验收、sandbox/网络约束/基线 SHA、generation、turns、prompt_bytes、人工审阅 checkpoint（summary/decisions/pending）和最近结果引用。摘要 SHA256 与状态记录共同原子保存；摘要不是签名或权限证明。工作树沿用原任务固定基线；不复制其他任务上下文。状态命令仅输出计数，不直接输出黑板正文。

新任务显式 `run --protocol-v2 --blackboard --prompt -` 使用 D10 完整 v2 请求。后续 `resume --protocol-v2 --task-id ID --prompt -` 只接受 {"version":2,"task_id":"ID","rev":2,"base_rev":1,"delta":"next"}。稳定字段不可借 delta envelope 改写；delta 文本不是权限。累计本地 prompt 16384 UTF-8 字节或8轮触发停止普通 resume。需经人类核对、补全历史决策和未完成项，显式 `--rebuild-context` 并加入 checkpoint: {"summary":"reviewed","decisions":["..."],"pending":["..."]}，才从同一 workdir 发起新 session；没有 checkpoint 不自动压缩或丢弃约束。最多32代。历史原始结果留在本地 artifact，不能把用户提供 checkpoint 当成独立证明。实际模型上下文、服务端 compaction、Token 计量不在此候选中。

不采集环境/密钥、原始日志、模型回复到黑板；常见 credential pattern 拒绝，任何自定义/编码密钥无法穷尽识别，调用者禁止输入秘密。状态目录由用户权限保护，不声称加密。仅信任 CLI thread.started 的单一身份，正常 resume 必须同 session，重建必须新 session；缺失/冲突/其他任务或退役身份 fail closed，保持未完成状态供检查，不自动重试。真实宿主的 session 事件兼容性仍 NOT_RUN。旧 v1 和未 opt-in 的 v2 不变；已有黑板任务不得隐式降级。回退应用版本前保留状态备份，禁止用旧代码续跑黑板任务。
