# D07 候选验收说明

D06 通过 CI 的代码加证据提交 39cc294bba80c5d563df21b4b329a2646293e017；逐卡候选开发已授权。报告严格匹配现有 worker schema；保留 worker_claimed_verification_passed，但不冒充可信验证，verification_status unknown/not_run，verification_passed false。完成任务不等于验收通过；缺报告或无效报告 partial、非零退出/error event failed，CLI 非完成退出 1。result 原子写先于状态终态；resume 标记 running，异常/崩溃保持非成功，不自动重派。SQLite finishOp 使用 running 条件更新，重复事件不能覆盖终态。Python/Node 受管进程超时终止请求：Unix 进程组，Windows 对仍在运行的自有根进程 taskkill /T /F；CI 真实本地父子进程 marker 回归；不保证逃逸/提前退出的树或恶意进程，真实宿主进程树与真实断电恢复仍未验收。所有测试为本地合成/Mock，0真实模型。D05/D06 未合并；D07 仅 Draft。

## 实际四环境 CI（候选通过）
[Run 45937506260](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45937506260) completed/success，测试 commit `8e472999c84f1a41dd188a5766d6bd4de7bd02a5`；Windows 11 ARM64、Windows Server x64、Ubuntu、macOS 各7项 Python outcome +4项 Node outcome（共44/44 PASS），真实本地父子进程超时 marker 未出现，缺报告与非零退出反向断言、启动失败、终态重复事件和重启孤儿状态通过。D06 策略、Hook、治理及 D03–D05 累计回归通过。旧 BUG-001/002 为 CANDIDATE_PASS，尚未合入 main；真实 Antigravity/实际 Codex worker 的进程树、逃逸/提前退出根进程及真实掉电未验收，不能据托管结果标 DONE。D07 候选允许后续依赖开发；PR #9 base dev/d06 保持 Draft。
