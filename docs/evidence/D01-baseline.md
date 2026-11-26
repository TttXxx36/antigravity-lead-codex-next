# D01 工具自检与未执行项

日期：2026-11-27（对话日期）。环境 Linux 容器。代码来源：本地编写的 3 个文件，随后 GitHub Blob SHA 与本地 git hash-object 完全相同：

| 文件 | Blob SHA |
|---|---|
| benchmarks/run_benchmark.py | 99001b464a91ce7ef01595b4dd62b30501d7331f |
| tests/mock_codex.py | 8d3d00da742af884056851c164401eb54c4b61fb |
| benchmarks/task_suite.json | a85fe924f9d805ba10bb73f371707609bbf42481 |

执行命令：`python benchmarks/run_benchmark.py --harness-only --repeat 2 --output harness.json`。退出码 0，16/16 PASS，0 FAIL，0 NOT_RUN。此前尝试 5 次重复的命令超出工具时限，没有完整结果；未计入统计。另执行 `python -m py_compile benchmarks/run_benchmark.py tests/mock_codex.py` 成功。

| 场景 | PASS | FAIL | 中位数 ms | p95 ms |
|---|---:|---:|---:|---:|
| B01 | 2 | 0 | 1452.549 | 1466.347 |
| B02 | 2 | 0 | 1152.609 | 1190.286 |
| B03 | 2 | 0 | 2041.862 | 2299.962 |
| B04 | 2 | 0 | 1965.072 | 2054.912 |
| B05 | 2 | 0 | 29.349 | 32.913 |
| B06 | 2 | 0 | 25.793 | 26.837 |
| B07 | 2 | 0 | 1008.653 | 1023.776 |
| B08 | 2 | 0 | 1026.914 | 1038.26 |

这些耗时只描述工具自检（包含临时目录与子进程开销），不是上游性能。B05/B06 仅生成/读取合成 SQLite；B07 仅单个 Mock smoke，不是 Worktree 并发基准；B03 检查 Mock resume 成功；B04 是两次人为注入失败，工具成功识别，不代表自动重试。样本量 2，p95 为最大值，不具统计稳定性。

另在无源码本地目录运行默认模式一次：10 个分组（B05/B06 各 cold/warm），全部 NOT_RUN，0 PASS/FAIL，输出 JSON 并返回非零状态。未在完整源码树实际运行 dispatcher/MCP。Git clone/ls-remote 失败原因：DNS 无法解析 github.com。本地无法使用 GitHub 连接器直接挂载完整仓库。Windows/macOS 无运行环境；未执行原有 Python 单测/MCP 集成测试。0 真实模型调用，模型 Token unknown/null。没有安装依赖、修改上游源码或开启 CI。没有发布任何真实用户数据库或提示词。

下一步需在真实 checkout 中用本地已安装依赖重复运行默认 runner，并保存三平台结果。不得以自检替代完整基准验收。回滚：关闭 Draft PR，main 不受影响。
