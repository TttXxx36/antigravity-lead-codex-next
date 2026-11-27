# 当前开发检查点（2026-11-27）

此文件是跨分支实时检查点的持久快照，优先于较早的 README/台账历史文字。已获用户 D03–D21 条件合并许可：实际满足各卡验收门槛后才合并；缺证据/失败/安全阻塞不得越过；不自动发布、真实模型测试或扩权限。

| 卡 | 结果 | 证据 |
|---|---|---|
| D00–D02 | DONE | PR #1–#3 已验收合并；原 Windows 失败基线保留 |
| D03 | DONE | [PR #5](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/5)、[三平台实际长路径](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934273615) |
| D04 | DONE | [PR #6](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/6)、[39/39 三平台](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934605595) |
| D05 | BLOCKED（候选未合并） | [PR #7](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/7)、[首轮托管三平台 PASS](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934981525)、[新增 ConsoleOnly 复检 PASS](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45935195557)；D05 分支最新状态为准 |
| D06–D21 | 待依赖完成（已授权） | 不越过 D05；[剩余路线](REMAINING_WORK.md) |
| D22 | 正式发布待单独授权 | 不发布 |

## 当前阻塞：实际 Windows 11 桌面和 Antigravity MCP 宿主

托管 Windows Server 2025 的安装、升级、恢复、卸载、重装、中文路径、缺依赖及回滚，首轮均通过；仍不是 Windows 11 桌面或真实 Antigravity host 的验收。D05 明确要求实际 Windows 11 生命周期和宿主 MCP initialize。当前没有用户机器访问或可信证据；保持 PR #7 Draft、D05 BLOCKED。无需重复申请已授权的合并，但必须补真实证据。

请在实际 Windows 11 环境使用 dev/d05 的 [安装说明](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d05/docs/WINDOWS_INSTALL.md) 和 [D05 证据目录](https://github.com/TttXxx36/antigravity-lead-codex-next/tree/dev/d05/docs/evidence)。只测试安装与握手，不执行模型派发、quota 探测或权限扩张。保留数据和备份，公开报告脱敏。取得证据后核验精确 head、按条件合并 D05，再依次 D06–D21。

已修复：BUG-003（损坏 JSON 被覆盖）、BUG-004（Windows fcntl）；BUG-001/002 仍待 D07；BUG-005 测试启动器已原生化，实际安装候选仍待真实宿主。详见 [缺陷登记册](ISSUES_AND_BUGS.md) 和 D05 分支更新。原 D01 基准、PR #4 候选及所有版权/历史保留。

## 最终托管结果

D05 新版 Run 45935195557 已 completed/success，三个平台成功，Windows 日志明确包含 console-only lifecycle。测试 head `06a06c144b4c238adc56baeebe7f8d5809dbeba2`；[证据](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d05/docs/evidence/D05-install.md)，[实际 Win11 验收清单](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d05/docs/evidence/D05-WINDOWS11-acceptance.md)。D05 分支台账和决策卡已标 BLOCKED，证据提交 `ab820b490a92cf0147f3d5afc1edb540f2f49248`。D05 未合并，main 仍以 D04 为生产代码基线。已正式完成 5/23，D05 阻塞，D06–D22 未实施。

## 2026-11-27 Windows 11 替代验收推进

PR #7 新 head 9813f19c222a858f2a4f7cf217702f62252cc540。新增公开免费 windows-11-arm（实际 Windows 11 工作站 OS 检查）、两种 Windows 的 SQLite 内容及 SHA256 保留回归；修复 push/PR 并发重复取消，采用 PR-only。四环境 [Run 45936238126](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45936238126)：Windows Server x64、Linux、macOS 已通过，Windows 11 ARM64 尚待最终结论。前次文档复检 Run 45935441825 success。详见 [替代验收记录](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d05/docs/evidence/D05-alternative-validation.md)。

无法查询仓库 self-hosted runner 列表（连接器接口不支持）；当前无可访问的已登录 Antigravity 桌面宿主。禁止在公共 CI 注入个人登录凭据或把日常电脑挂为公共 self-hosted runner。实际宿主 initialize 仍为独立门槛，D05 继续 BLOCKED，不将 OS 测试冒充 host 通过。D06–D22 未启动；条件合并权限不变。
