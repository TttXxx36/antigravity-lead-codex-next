# D11 候选证据

基线 D10 6a4c3484a30b892d533dae93180ef357bfa072b4（Run 45941283814 success）。

## 候选实施
显式 --protocol-v2 --blackboard 建立任务内稳定目标/范围/验收、sandbox/固定基线 SHA、版本和摘要引用，原子状态锁保存；普通 resume 仅发送短 delta，不再发送稳定字段；阈值 8 轮或累计本地 prompt 16384 UTF-8 字节（不是模型上下文/Token），超限需提供人工审阅 checkpoint 并显式 --rebuild-context，新会话保留稳定目标/约束、决策与未完成项。固定 session 身份、拒绝其他/退役会话、revision 及摘要校验；崩溃未完成状态不自动重试。黑板不采集环境变量、原始日志或模型回复，常见密钥模式拒绝，不能保证识别任意秘密，禁止输入秘密。旧 v1/旧 v2 路径不变。真实宿主、断线后真实 session、实际 Token 和人工 checkpoint 完整性未验收。
测试覆盖实际 Mock 三轮同 session/新 session、阈值、过期 revision、跨任务、摘要篡改、秘密模式、字节预算及累计回归；待实际 CI。

D11 审查补测：黑板约束随 sandbox 收紧保持一致，禁止后续升级；旧协议任务不得占用其他黑板的当前/退役 session；新 Python 进程读取已持久化黑板并校验摘要后继续 Mock 恢复。真实网络断线、外部客户端绕开 dispatcher 或 OS 级同权限篡改未验收。首轮 Run 45945559903 被后续修复替代，最终 head 单独测试。