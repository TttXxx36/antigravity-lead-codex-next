# Antigravity Lead Codex Next

独立维护的 Antigravity × Codex 协同开发框架；当前为 V2.0 **未发布候选分支**。main 仍为既有已验收基础版本。D00–D04 正式 DONE，D05 起各卡候选开发与正式验收分离；以 [执行台账](docs/EXECUTION_STATUS.json) 和原始 CI 为准。真实宿主、实际模型质量/Token 及正式发布尚未批准或验收。

## 候选能力

- CLI 默认、只读原生 Codex 数据查询、严格任务身份及状态恢复；JSON 默认、SQLite 显式离线迁移。
- 紧凑 MCP、事件元数据、预算和幂等门禁、持久化调度、确定性编排、风险审查、只读 App Server 实验探测；所有 opt-in 能力仍受安全和正式验收约束。
- 真实四环境 CI（Ubuntu、macOS ARM64、Windows Server x64、Windows 11 ARM64）；Mock/合成任务不是实机产品认证。真实 Windows Antigravity + Codex UI、真实模型与权限、生产迁移/回滚仍未验收。

## 入口

- [路线图](docs/ROADMAP.md) · [决策卡](docs/decisions/README.md) · [剩余任务](docs/REMAINING_WORK.md) · [Bug](docs/ISSUES_AND_BUGS.md)
- [测量方法](docs/BENCHMARK.md) · [D21 配对结果](docs/RESULTS.md)
- [RC 构建和校验](docs/RELEASE_CANDIDATE.md) · [迁移与回滚](docs/MIGRATION.md) · [Windows 安装说明](docs/WINDOWS_INSTALL.md)

当前 RC 仅为源代码包准备，不得作为正式发布安装；不自动联网、下载依赖、扩大权限或调用模型。明确批准后方可进行实际宿主测试。不要使用上游安装命令作为 Next 安装命令。

上游为 [Koala973/antigravity-lead-codex](https://github.com/Koala973/antigravity-lead-codex)，独立仓库非 fork，保留 [上游来源](docs/UPSTREAM.md)、[原始文档](README_UPSTREAM.md)、[MIT 许可证](LICENSE) 和 [原始许可证](LICENSE.upstream)。原始上游文档仅作历史参考，不表示 Next 功能已验收。


## 集中本地验收（未发布候选）
完整候选请以 dev/d22 的经 CI 验证精确提交为准，不是 main 正式版本。见 [集中实机验收矩阵](docs/LOCAL_ACCEPTANCE.md)。
