# 上游基线与许可

- 来源：https://github.com/Koala973/antigravity-lead-codex
- 审计基线：https://github.com/Koala973/antigravity-lead-codex/commit/b6c36443e5a134ea36aa18dc171f312fdd54b5bc
- 文档版本：v1.0.2；commit 时间：2026-11-25 UTC。
- 上游许可证：MIT，Copyright (c) 2026 Koala973。完整许可证见 [固定上游 LICENSE](https://github.com/Koala973/antigravity-lead-codex/blob/b6c36443e5a134ea36aa18dc171f312fdd54b5bc/LICENSE)。

独立仓库不使用 GitHub Fork，也不向上游写入。D00 获准后才导入固定 commit 的源码快照；在独立提交中保留原 LICENSE、版权和来源。本仓库初始 LICENSE 及版权保持不变，导入时同时保留上游版权。规划文件若与上游 README、AGENTS 或 docs 冲突，应先移入规划目录并审查，不得静默覆盖。导入时校验 Git 对象或文件哈希及文件清单。新项目后续版权归属按实际作者记录，不冒称上游作者。

已识别的源码问题：fcntl 不支持 Windows、Bash 启动、PATH 分隔符、任务 ID 校验、状态损坏保护、网络审批覆盖不全、退出码误判验证、旧任务查找范围、后台进程终态、SQLite 错误静默、重复快照、全量历史进入模型上下文。详见对应决策卡。以上为源码审计风险，尚未完成实机复现/修复验证。
