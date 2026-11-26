# D01 基线与当前验收范围

固定源码基线：`77f9f9b95674ada26c8833b5057cebfb4ff70643`，对应上游 v1.0.2 `b6c36443e5a134ea36aa18dc171f312fdd54b5bc`。仅 Mock/本地授权；本次不修改业务源码。

## 可复现工具

- [任务集](../benchmarks/task_suite.json)：B01–B08。
- [运行器](../benchmarks/run_benchmark.py)：独立临时目录、合成数据、Mock CLI；默认执行实际上游本地探针。
- [结果 schema](../benchmarks/metrics_schema.json)：用量 unknown/null，保留失败及 NOT_RUN。
- [使用说明](../benchmarks/README.md)：区分工具自检与真正的上游 Mock 基准。
- [本次证据](evidence/D01-baseline.md)。

## 环境及状态

| 项目 | 观测/状态 |
|---|---|
| Linux 容器 | Python 3.13.5、Node v22.16.0、Git 2.47.3（版本命令实际查询） |
| Mock 工具 | 16/16 PASS；8场景各2次，仅自检 |
| Linux 上游 dispatcher / MCP | NOT_RUN（本地 GitHub DNS 不可用，源码与依赖未能完整落地） |
| Windows / macOS | NOT_RUN（无对应环境） |
| Codex / Antigravity 真实版本、可用模型 | UNKNOWN，未探测用户宿主 |
| 实际模型调用次数 | 0（本次自检及缺源码检查） |
| Gemini/GPT Token | UNKNOWN；不产生虚构用量 |
| 真实代码质量及性能节省率 | UNKNOWN |

完整 D01 验收缺口：在完整本地 checkout 和已安装依赖环境执行默认 runner，三平台保留成功、失败及 NOT_RUN，记录准确 checkout SHA 与版本。Windows 上游 fcntl 等原有问题按实际结果记录，不提前修复。两次工具自检的 p95 只是近邻秩描述，不能作为有效性能基准。模型调用需要另行授权；不在本卡范围内。完整基准未满足前不能标 DONE 或进入 D02。

## 本地执行

    git rev-parse HEAD
    python benchmarks/run_benchmark.py --harness-only --repeat 5 --output benchmarks/results/local-harness.json
    python benchmarks/run_benchmark.py --repeat 5 --output benchmarks/results/local-baseline.json

若 Node 依赖未安装，MCP 探针会记录 NOT_RUN；本次不擅自安装依赖、不启用远程 CI。不把工具自检的耗时作为上游性能。
