# 开发代理执行规则

1. 阅读 [路线](docs/ROADMAP.md)、[剩余任务](docs/REMAINING_WORK.md)、[缺陷登记](docs/ISSUES_AND_BUGS.md)、[治理规范](docs/GOVERNANCE.md) 及对应决策卡；核验实际分支、PR head 与 main，不将台账快照视为实时状态。
2. 每卡明确用户批准、范围和预算；推荐不等于授权。依赖卡已验收、合并才进入依赖任务。PROPOSED → ACCEPTED → IN_PROGRESS → REVIEW → DONE；BLOCKED/DEFERRED 记录原因。用户验收且合并后才 DONE；原始基线的失败结果照实保留。
3. 独立 dev/dXX，最小变更，每卡 Draft PR；修复候选单独注明范围/基线。禁止自动合并、强推、发布、fork、向上游推送；不得覆盖用户未提交修改。原版与候选基线分离。
4. 默认离线 workspace-write；Codex 原生 DB 严格只读。真实模型基准、网络、外部写、删除用户数据、远程保护、合并及发布另需明确许可。已批准 GitHub Actions 可在临时 runner 获取锁定依赖（ignore-scripts），不能调用真实模型或给生产 worker 联网权限。
5. 机器可获取的信息由程序采集；模型只传目标、范围、验收、变更、阻塞、证据引用。状态查询不调用模型；完整日志默认留在 UI/本地，公开证据脱敏。
6. 区分退出码、任务及验证状态；未测 NOT_RUN/UNKNOWN，失败不伪造 PASS。真实 Token 缺失 unknown，禁止无实测宣称节省或 Windows 桌面支持。
7. 锁定输入 SHA、实际 checkout、测试命令/预算/环境、退出码、风险及回滚。提供卡 ID、PR/head、证据、剩余项与下一步。人类验收前不自动进入依赖卡；全路线推进不取消门禁。
8. 台账由本地检查器校验，但真实权限与审批由可信宿主/GitHub 执行，不依赖文本检查。详见 docs/GOVERNANCE.md。

## 已批准的条件合并例外
2026-11-27 用户授权 D03–D21 在满足实际验收门槛后依次合并并更新 DONE，无需再次逐卡确认；未满足则修复或记录 BLOCKED。此授权不涵盖 D22 正式发布、真实模型测试、权限扩张或无条件自动合并。 每卡固定 head、实际必需检查成功、依赖 DONE、风险可控、证据齐备才可执行受控合并；不设置自动合并功能，不绕过保护规则。