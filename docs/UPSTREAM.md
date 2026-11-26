# 上游基线与许可

- 来源：https://github.com/Koala973/antigravity-lead-codex
- 审计基线：https://github.com/Koala973/antigravity-lead-codex/commit/b6c36443e5a134ea36aa18dc171f312fdd54b5bc
- 文档版本：v1.0.2；commit 时间：2026-11-25 UTC。
- 上游许可证：MIT，Copyright (c) 2026 Koala973。完整许可证见 [固定上游 LICENSE](https://github.com/Koala973/antigravity-lead-codex/blob/b6c36443e5a134ea36aa18dc171f312fdd54b5bc/LICENSE)。

独立仓库不使用 GitHub Fork，也不向上游写入。D00 获准后才导入固定 commit 的源码快照；在独立提交中保留原 LICENSE、版权和来源。本仓库初始 LICENSE 及版权保持不变，导入时同时保留上游版权。规划文件若与上游 README、AGENTS 或 docs 冲突，应先移入规划目录并审查，不得静默覆盖。导入时校验 Git 对象或文件哈希及文件清单。新项目后续版权归属按实际作者记录，不冒称上游作者。

已识别的源码问题：fcntl 不支持 Windows、Bash 启动、PATH 分隔符、任务 ID 校验、状态损坏保护、网络审批覆盖不全、退出码误判验证、旧任务查找范围、后台进程终态、SQLite 错误静默、重复快照、全量历史进入模型上下文。详见对应决策卡。以上为源码审计风险，尚未完成实机复现/修复验证。

## D00 导入记录

方案 A 已批准，导入提交：`7f6bebddc5a895a1da707d66b187f2221a7cca3e`。原始 README 移至根目录 README_UPSTREAM.md，以保留相对图片/文档链接；原始 LICENSE 保存为 LICENSE.upstream；根 LICENSE 保留本仓库原版权并加入上游版权。除此之外 43 个上游文件保留原路径。45/45 上游 Blob SHA 和 Git 文件 mode 与基线一致，见 [完整性证据](evidence/D00-import.md)。原有规划文档保留，仅状态与来源说明在独立文档提交更新。工作流仍保存在上游原位置 docs/workflows/，未激活 GitHub Actions。未进行功能/实机测试或依赖安装。

2026-11-27：用户明确批准 D00 验收并合并 [PR #1](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/1)，合并提交 `b7358f748c58cb183c8926a93afd9660c71de872`，固定源码成为 main 正式基线。D00 DONE；D01 未开始。
