# Codex 统一交接清单（P0 / D01 + D02）

交接日期：2026-11-27。用户要求启动 D02，将未完成工作统一收集并交由 Codex 继续完成。本文件是交接入口，不是验收通过证明，也不是对后续所有决策卡的开发授权。

## 1. 当前权威状态

| 决策卡 | 状态 | 工作分支 | 审核入口 |
|---|---|---|---|
| D00 | DONE | main | [PR #1（已合并）](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/1) |
| D01 | REVIEW，验收未完成 | dev/d01 | [PR #2（Draft）](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/2) |
| D02 | IN_PROGRESS，交接已启动 | dev/d02 | 本分支 Draft PR |
| D03–D22 | PROPOSED，未授权实施 | 尚未创建 | [完整路线](ROADMAP.md) |

- main 基线：`77f9f9b95674ada26c8833b5057cebfb4ff70643`，上游快照 `b6c36443e5a134ea36aa18dc171f312fdd54b5bc`。
- D01 已交接的固定 head：`00dc677a38cc8508b15e0a4e0847edffb2cae178`。D01 的实际状态以 dev/d01 的决策卡及 PR #2 为准；main 尚不包含未合并的 D01 变更。
- D02 的正式前置依赖为 D00，已满足。D01 尚未 DONE 不阻止 D02 独立治理工作，但 D03 必须等待 D01 与 D02 均验收并合并、另获授权。
- D01 与 D02 保持独立分支、独立 PR；本次 D02 从 main 创建，不从 dev/d01 创建。不要把两个 PR squash 成一个。若后续合并发生文档冲突，按真实状态解决并保持各自证据，不覆盖未完成记录。

## 2. D01：接续 PR #2，补齐本地 Mock 基准

现有证据：
- [D01 决策卡](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d01/docs/decisions/D01.md)
- [基准说明](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d01/docs/BASELINE.md)
- [第一轮自检](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d01/docs/evidence/D01-baseline.md)
- [第二轮真实函数片段集成](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d01/docs/evidence/D01-dispatch-contract.md)
- [第二轮原始记录](https://github.com/TttXxx36/antigravity-lead-codex-next/blob/dev/d01/benchmarks/results/d01-dispatch-contract-linux.json)

已报告：第一轮工具自检 16/16，第二轮改后工具自检 8/8，固定源码片段集成 12/12（6 场景 × 2 次，18 个 Mock 子进程）。这些是不同测试套件、不是完整模块或三平台通过证明；原始证据保留，不重写历史。真实模型测试调用 0；实际模型用量未知。

| ID | 未完成任务 | 优先级 | 完成证据 |
|---|---|---|---|
| H01 | 在完整 checkout 核对 D01 head、固定源 Blob、实际 Git HEAD；检查所用 Mock 的来源和调用边界 | P0 | 版本、哈希、工具版本、隔离路径及命令记录 |
| H02 | 审查现有 runner/Mock/schema 是否匹配上游接口，修正测试工具本身；验证缺源码、缺依赖、断言关闭、超时、错误退出、失败记录及结果 schema | P0 | 工具测试和 JSON 校验结果；不得改业务源码来使基线通过 |
| H03 | 跑完整 dispatcher 模块和原有 Python 测试：B01/B02/B03/B04/B07/B08 | P0 | 原始退出码、每个用例的状态、耗时、Mock 次数、实际 checkout；若平台不支持保留失败 |
| H04 | 跑真实 MCP stdio + 合成 SQLite 的 B05/B06，分别冷/热进程内查询 | P0 | 实际 RPC 结果、响应字节、延迟、冷/热定义；依赖缺失明确 NOT_RUN |
| H05 | 跑原有 MCP 集成测试之前审查启动脚本，确保所有 Codex CLI 调用均指向本地 Mock，禁止自动安装/真实模型回退 | P0 | 已核验 Mock 边界、依赖来源、测试日志；无法保证隔离则 BLOCKED |
| H06 | 在 Windows、Linux、macOS 分别执行可用的完整基准；记录 fcntl 等原版兼容性失败，不提前修复 | P0 | 每平台独立环境和结果；不可用平台 NOT_RUN，不以 Linux 路径测试冒充 Windows |
| H07 | 补足重复样本（默认建议每场景每条件 5 次）、实际 Node/Python/Git 版本、失败/重试、缓存状态、缺失用量字段 | P1 | JSON + 汇总、统计口径、模型用量 unknown/null；真实模型版本未知可标 UNKNOWN |
| H08 | 更新 D01 的 BASELINE、证据文档、决策卡、PR #2；核实 diff 仅测试/文档 | P0 | Draft PR 新 head 与验收缺口；待用户验收，不擅自 DONE |

建议命令（从 dev/d01 的完整 checkout 执行；先阅读 benchmarks/README.md，并确认 runner 安全、依赖已存在；Python 不用 -O）：

    git status --short
    git rev-parse HEAD
    python --version
    node --version
    git --version
    python benchmarks/run_benchmark.py --harness-only --repeat 5 --output benchmarks/results/local-harness.json
    python benchmarks/dispatch_contract.py --repeat 5 --output benchmarks/results/local-contract-full.json
    python benchmarks/run_benchmark.py --repeat 5 --output benchmarks/results/local-baseline.json
    python -m unittest discover -s tests -p test_dispatch.py

MCP 测试命令必须在审查真实启动路径和依赖后才执行。特别注意 console_snapshot 可能触发 quota app-server 探测，必须显式设置并验证可执行的本地 Mock，不能依赖 PATH 找到的真实 Codex；不要直接执行会自动安装依赖的 launcher。若要安装依赖、联网或启用远程 CI，先获得用户单独授权。现有本地环境 DNS 限制不等同于 Codex 的环境限制，重新核实。测试在隔离临时目录操作合成数据，不接触真实用户 Codex/Gemini 数据。不能用 B04 的两次故障注入宣称已验证自动重试，也不能用固定 Mock 会话 ID 证明真实会话唯一性。

## 3. D02：独立治理分支待 Codex 完成

用户已授权启动 D02 和本次交接。沿用既定的“决策卡 + 小 PR + 人工审批”原则（方案 A 为默认实施建议，非对自动化权限扩张的授权）。本次仅创建交接材料，治理实现待 Codex；本卡不是 DONE。

| ID | 待办 | 优先级 | 验收标准 |
|---|---|---|---|
| H09 | 完善 AGENTS.md 的授权、依赖门禁、状态迁移、分支/PR、测试与回滚规则 | P0 | 不允许未授权任务、真实模型测试、联网、发布或自动合并；Codex 原生数据库只读 |
| H10 | 完善 PR 模板及决策状态的可追溯规范 | P0 | 卡 ID、审批记录、base/head SHA、测试预算、证据、未完成项、风险、回滚、人工验收齐全 |
| H11 | 建立离线测试执行规范与 CI 计划，分离 Mock、本地集成、需另行授权的联网/真实模型测试 | P0 | Windows/Linux/macOS 计划、依赖准备、超时、退出码、NOT_RUN/FAIL 处理；不得擅自激活付费或联网 CI |
| H12 | 实现或准备可在本地验证的治理检查（按卡片范围/权限） | P1 | 模拟未批准卡、缺失证据、失败假通过及越权变更被识别；不把文本检查冒充技术强制安全门禁 |
| H13 | 形成 main 保护规则的建议与人工配置说明 | P1 | 禁止强推/删除、必需审查与检查的建议；无管理员授权不得修改远程规则 |
| H14 | 更新 D02 卡与本交接清单，提交独立 Draft PR，提供验收材料 | P0 | 不改 D01 分支、不改业务源码、不自动合并；状态 REVIEW 或 BLOCKED，等待用户 |

建议顺序：先 H09/H10，再 H11/H12/H13，最后 H14。D01 可独立并行补齐；两张卡分别审查与验收。D02 文档若引用 D01，须链接 PR #2 或其固定 commit，避免将未合并文件当成 main 上的文件。当前仅交接文件与 D02 状态变更；其余治理工作尚未实现或测试。

## 4. 已发现缺陷：保留证据，延后到获批的修复卡

| ID | 已复现现象 | 归属 | 未来验收建议 |
|---|---|---|---|
| BUG-001 | 缺少结构化报告且 exit=0 时，parse_report_file 返回 completed、verification_passed=true | D07 | 缺证据不得标验证成功 |
| BUG-002 | exit=7 但 fallback 报告声称 completed 时，parse_report_file 仍返回 completed | D07 | 独立校验退出与任务/验证状态 |
| BUG-003 | locked_state 读取损坏 JSON 后写入任务，原状态可被覆盖 | D04 | 保留损坏文件、显式错误、无静默覆盖 |

这三项为第二轮源码函数片段直接观察，不代表所有应用路径都已复现。另有 fcntl/Bash/PATH、网络审批、任务 ID、历史查找等原审计风险，尚需验证；见各卡，不当作已确认的新测试结论。D01/D02 不修复生产缺陷。

## 5. 后续开发积压（仅供索引，未授权执行）

D03–D08 Windows 与正确性；D09–D13 低 Token 通信；D14–D17 性能执行；D18–D22 编排和发布。详细依赖和验收门槛见 [ROADMAP](ROADMAP.md) 与 [决策卡索引](decisions/README.md)。禁止以本交接为由提前开发。

## 6. 统一返回格式

每项 Hxx 返回 PASS / FAIL / NOT_RUN / BLOCKED，记录实际证据路径、命令、退出码、平台、源码 SHA、未完成原因、风险、下一步。PASS 只能用于实际执行并满足判定条件的测试。D01 用量数据未知时保持 unknown/null；基准运行禁止真实模型调用（这不限制用户使用 Codex 作为开发代理本身）。不得声称已在 Windows/macOS 实测、已节省 Token 或全部验收，除非有对应证据。每个 PR 单独提供变更及证据、等待用户审核；不要合并或进入 D03。
