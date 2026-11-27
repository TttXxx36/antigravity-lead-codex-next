# D04 状态恢复与安全边界（候选）
原版 BUG-003：损坏 JSON 被静默重置；D03 基本 Windows 锁已合入。D04 增加原子同目录临时文件 fsync/replace、Windows sharing 重试、Unix 非阻塞限时锁、前一有效版本 state.json.bak、损坏原始字节的 SHA256 命名副本。失败时不覆盖现有原件，不自动恢复、不删除工作树。Windows 目录元数据 fsync 未承诺，真实掉电不是本次测试。

新 ID 使用 1–80 ASCII 安全字符、拒绝保留名、点序列、.lock、路径分隔符；大小写不敏感去重；全局锁内独占 mkdir 与 reserved 状态，崩溃留下的预留或目录不会自动重用。恢复/审阅目录也独占；已有任务 resume 使用专用锁，避免同一任务同时 resume。工作树路径验证、清理拒绝非预期路径/分支；无自动删除。状态根由本地用户控制，不是防恶意同 UID 并发改写或 TOCTOU 的 OS 安全边界。

恢复步骤（人工操作，不由测试执行）：停止所有调度进程，保存整个状态目录和工作树；核查 state.json、state.json.bak、state.corrupt-*.json 和已留存的 run/result.json。明确选择经过验证的恢复副本后才在维护窗口替换状态；原损坏文件、孤儿目录及未提交修改均保留。reserved/incomplete 任务禁止自动重派；需要人工核对 worker 是否存活及已有结果，再以新 ID 重新派发（如获许可）。本轮不自动恢复数据，也不承诺断电级全事务。

候选 CI：四进程锁计数/60 条记录、重复 ID 竞争、损坏保留、失败替换、崩溃释放锁、路径边界与原生 MCP/D03 回归。实际结果待 Actions。BUG-001/002 仍属 D07；网络权限及 cleanup 审批属 D06/D17。

## 实际 CI 及合并
[Run 45934605595](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934605595)，精确 head `a3b44b08b58451f41d27def9dcf87ee2428e7900`，Windows/Linux/macOS 13/13 each，39/39 PASS；D03 Python 19 PASS/2 skip、Node 10 PASS/2 skip，MCP 及治理三平台成功。四进程60条记录、多进程唯一 ID、崩溃释放、损坏/备份/替换失败、真实 Mock dispatch/resume 等通过。旧 Run 45934550434 Windows cancelled，未计入。PR #6 merge `1ad712a9ae3ab8d3e11e3616c1e8a995fe4423fb`。