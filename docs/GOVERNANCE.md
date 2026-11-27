# D02 开发与验收治理

## 运行边界与权限

用户选择决策卡方案、明确范围和预算后才允许 ACCEPTED。原路线要求独立小 PR 和人工合并。用户的总体继续开发指令不等于对真实模型基准、扩大网络/沙箱、远程规则、发布、删除数据及自动合并的授权。GitHub Actions 已授权用于 Mock/本地测试；临时 runner 只安装锁定依赖、ignore-scripts，禁止真实模型及 secrets。CI 自身需要获取 checkout/action/依赖，不等于应用或工作者联网许可。所有生产 Codex DB 保持只读。未经授权的操作标 BLOCKED。

## 状态协议

PROPOSED → ACCEPTED → IN_PROGRESS → REVIEW → DONE。BLOCKED/DEFERRED 须记录原因、恢复条件及证据，恢复至已批准范围；REVIEW 可退回 IN_PROGRESS。DONE 只有用户实际验收、合并且必需门槛具备才成立。原始基线的“记录失败”是合法测量成果，但失败的产品验收不能标 PASS；如用户明确批准基线本身，保留 FAIL/NOT_RUN 原始结果并记录其验收语义，绝不伪造全绿。

每卡锁定输入 SHA，输出 PR/head、批准、范围、依赖、测试预算、实际命令/退出码、环境、风险/回滚。证据使用稳定的 commit/run/artifact 引用；NOT_RUN、FAIL、UNKNOWN、BLOCKED 不等同于 PASS。真实 Token 缺失保持 unknown；不能用字符数或订阅额度冒充 Token。

## 分支与审查

每卡独立 dev/dXX 从已验收基线建立，默认 Draft。异常修复候选单独分支并注明卡归属、基线和不改变既有验收范围。先通过确定性检查；审批、并发、锁、迁移、安全和安装要审查失败路径及回滚。PR #4 只作为候选，D01 原始基线不混入修复。分支冲突时保留每卡证据，不强推。每个依赖均 DONE 并已合并后才开始下一卡。人类验收前停止自动合并。

## CI 分层

- T0：Python 标准库治理校验、语法和 schema；三平台、无额外依赖。
- T1：合成 fixture、Mock CLI、真实本地程序/MCP；已授权的 CI 可 npm ci --ignore-scripts，禁 secrets/真实模型。
- T2：真实 Windows 11 桌面安装、MCP 宿主与 Codex CLI 验证；须提供实际宿主环境。
- T3：真实 Gemini/Codex 用量及 App Server 官方接口能力，须另获用户预算/网络许可。
- 每个运行固定 SHA、Python/Node/Git、平台、超时，保留失败及 NOT_RUN。原版基线与候选 CI 分开，全部回归不可通过 continue-on-error 隐藏。
- 读取 [CI 证据](evidence/CI-RUNS.md)；D02 工作流只测治理脚本，不声称测试了生产程序。

## 本地治理检查（非安全强制器）

运行 `python scripts/check_governance.py docs/EXECUTION_STATUS.json` 和 `python -m unittest discover -s tests -p test_governance.py -v`。检查结构、23 卡 ID、依赖、状态、审批/PR/证据、禁止自动权限及 DONE 合并条件；单测覆盖非法状态、未批准、未满足依赖、失败假通过、越权权限、缺失卡。它只能检查台账文本，不能证明审批真实性、GitHub 规则已设置或 OS 沙箱实际生效。真实 GitHub 合并、保护、权限必须人工/可信宿主控制。

## main 保护建议（尚未设置）

由管理员在 Settings → Rules / Rulesets 针对 main 配置：禁止 force push 和删除，必须 PR，审查至少 1 人（单人仓库先核对是否可满足），通过必要 CI，审查新提交后重新确认；禁止绕过规则或将失败检查标成功。先确认规则和 checks 名称及账号可用性，再由用户授权设置，避免锁死单人维护者。原版 Windows 基线失败不是修复版分支的成功门槛；未来主分支使用 D08 的正式三平台回归。规则修改、合并、发布都未在本卡自动执行。

## 退出及回滚

提交 Draft PR 与证据，等待人工验收；关闭未合并 PR 即可回到原状。已合并后使用 revert，保留历史和证据。若证据缺失、测试失败、审批缺失，维持 REVIEW/BLOCKED，不能启动依赖卡。

## 已执行治理 CI
[Run 45922285638](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45922285638)，测试 head `02d2e14f676e5f8e9b1a365c8d65553120d915cd`，三平台均成功；详见 [D02-governance.md](evidence/D02-governance.md)。
