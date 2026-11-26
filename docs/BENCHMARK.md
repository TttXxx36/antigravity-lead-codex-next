# 基准与验收规范

## 测试集与环境
固定上游 SHA、优化 SHA、操作系统、Node/Python/Git/Codex/Antigravity 版本、实际模型 ID、推理强度、缓存状态、任务提示和验收条件。真实模型调用须另获批准，优先使用合成 fixture/mock。

| 场景 | 检查重点 |
|---|---|
| 简单单文件修复 | 低 effort、无重复审查 |
| 多文件重构 | Worktree 隔离、正确 diff、测试 |
| 多轮追加需求 | resume、revision、上下文增量 |
| 阻塞/重复错误 | 自动停止、保留阻塞信息 |
| 联网及权限 | 默认离线、可信审批、外部写门禁 |
| 并发及取消 | 幂等、资源回收、状态一致 |
| Windows 中文及空格路径 | 安装、MCP 握手、Git 解析 |
| 历史任务及数据库异常 | 精确查询、错误可观测 |

## 测量方法
相同任务配对比较基线/优化版；预算允许时每组至少5次，分开冷/热缓存；记录成功、失败、重试和耗时，不只统计成功任务。分别报告 Codex input/output/cached/reasoning（仅按实际事件语义）；Gemini 无真实接口时标 estimate 或 unknown。缓存 Token 不重复加总；不可控的推理量不承诺硬限制。用量缺失不能当零。用量与订阅剩余额度不是同一指标。总量节省率=(基线-优化)/基线，仅对同口径且可测的值计算。

## 记录字段
run_id、task_id、baseline_sha、candidate_sha、os、model、effort、cache_state、success、verification_status、input_tokens、cached_input_tokens、output_tokens、reasoning_tokens、usage_source、latency_ms、mcp_payload_bytes、poll_count、retry_count、review_count、risk、artifact_ref。

目标：总 Token 下降30–60%（研发假设，非实测）；任务成功率不低于用户批准的容差；P0 回归为零；统计中位数、p95 和失败率。样本不足时明确限制，不宣称达标。脱敏并避免保存 API 密钥、用户源码和完整提示词到公开日志。
