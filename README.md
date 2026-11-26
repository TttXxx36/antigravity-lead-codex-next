# Antigravity Lead Codex Next

独立维护规划：Windows 原生、低 Token、事件驱动的 Gemini × Codex（目标 GPT-6 系列，以实际可用模型为准）协同开发框架。

> D00 已导入并校验上游 v1.0.2 原始快照，经用户验收后通过 PR #1 合并至 main；尚未实施 Windows 适配、Token 优化或功能修复，也未运行真实模型基准。不是已验证的 Windows 产品。

## 项目入口

- [完整开发路线](docs/ROADMAP.md)：5 个批次，23 张可单独验收的决策卡。
- [决策卡索引](docs/decisions/README.md)：所有技术选择、范围、验收与回滚。
- [上游来源与许可证](docs/UPSTREAM.md)：独立仓库，不 fork。
- [基准与验收方法](docs/BENCHMARK.md)：真实/估算/未知用量区分。
- [开发代理规则](AGENTS.md)：按卡执行、人工确认、不得自动合并。

## 当前状态

P0 / D00 DONE（用户已验收并授权合并）。当前仓库为公开独立仓库，D00 基线已在 main。已由 GitHub API 确认 fork=false。上游是 [Koala973/antigravity-lead-codex](https://github.com/Koala973/antigravity-lead-codex)。已保留双方 MIT 版权声明；原始上游文档见 [README_UPSTREAM.md](README_UPSTREAM.md)，原始许可证见 [LICENSE.upstream](LICENSE.upstream)，完整性证据见 [D00 清单](docs/evidence/D00-import.md)。

## 启动下一步

D00 方案 A 已验收并通过 [PR #1](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/1) 合并。D01 方案 A 已获批准，dev/d01 已建立 Mock 基准工具及本地自检证据，状态 REVIEW（完整源码及三平台基准仍待运行）。详见 [BASELINE.md](docs/BASELINE.md)。D02 未启动，必须另行批准。不会 fork，不会向上游推送，不会在规划初始化时执行代码开发。
