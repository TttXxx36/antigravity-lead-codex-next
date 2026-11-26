# Antigravity Lead Codex Next

独立维护规划：Windows 原生、低 Token、事件驱动的 Gemini × Codex（目标 GPT-6 系列，以实际可用模型为准）协同开发框架。

> 当前仅包含开发规划。没有导入上游源码，没有实施任何功能，没有执行真实模型基准，不是可安装产品。

## 项目入口

- [完整开发路线](docs/ROADMAP.md)：5 个批次，23 张可单独验收的决策卡。
- [决策卡索引](docs/decisions/README.md)：所有技术选择、范围、验收与回滚。
- [上游来源与许可证](docs/UPSTREAM.md)：独立仓库，不 fork。
- [基准与验收方法](docs/BENCHMARK.md)：真实/估算/未知用量区分。
- [开发代理规则](AGENTS.md)：按卡执行、人工确认、不得自动合并。

## 当前状态

P0 / D00 待确认。当前仓库为公开独立仓库，main 分支。已由 GitHub API 确认 fork=false。上游是 [Koala973/antigravity-lead-codex](https://github.com/Koala973/antigravity-lead-codex)。后续导入源码必须保留上游 MIT 版权声明，同时保留本仓库已有版权。

## 启动下一步

用户明确批准 D00 后，执行独立源码基线导入；此后按决策卡依赖顺序逐批次推进。不会 fork，不会向上游推送，不会在规划初始化时执行代码开发。
