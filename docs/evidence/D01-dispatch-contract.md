# D01 第二轮：固定源码函数集成证据

日期：2026-11-27（对话日期）。本地 Linux、Python 3.13.5、Node v22.16.0、Git 2.47.3。未安装依赖，未运行真实模型。

## 来源及完整性
固定基线 `77f9f9b95674ada26c8833b5057cebfb4ff70643`；上游 dispatch.py Blob 2057553f544c0ef605eb2c9ad8ae0f8fb59df84a。GitHub DNS 及直接下载仍失败；从连接器取得 20 个原始函数，分三组转移到本地，Git hash-object 返回三个与远程生成的 Blob SHA 完全相同的值。详见 [源码片段清单](../../benchmarks/fixtures/dispatch_contract/README.md)。函数体未修改。
- 实际运行的 dispatch_contract.py Git Blob：2d5a49a40b2095ef11c13222b02969207b297dd0。
- 改进后的 run_benchmark.py Git Blob：ed9edba8a804bbfb7e20086a621a6da3957a58be。
- 原 Mock：8d3d00da742af884056851c164401eb54c4b61fb；任务集：a85fe924f9d805ba10bb73f371707609bbf42481。
- 本地运行命令：`python benchmarks/dispatch_contract.py --excerpt-dir /tmp/d01-contract --repeat 2 --output /tmp/d01/contract.json`，退出码 0。GitHub 仓库中的片段目录可直接复现。

## 结果
| 场景 | 通过 | 中位数 ms | p95 ms | 每次 JSONL bytes |
|---|---:|---:|---:|---:|
| B01 | 2/2 | 1137.946 | 1320.623 | 404 |
| B02 | 2/2 | 1196.235 | 1223.457 | 420 |
| B03 | 2/2 | 2074.116 | 2138.597 | 808 |
| B04 | 2/2 | 2085.057 | 2136.476 | 862 |
| B07 | 2/2 | 1123.007 | 1167.92 | 808 |
| B08 | 2/2 | 945.989 | 965.38 | 404 |

12 PASS、0 FAIL、0 NOT_RUN（仅此片段套件，非全部基准）。18 个 Mock CLI 子进程、0 真实模型调用。实际运行原始 execute_single_task、cmd_resume、Git Worktree、flock/state、命令构造、报告及 JSONL 解析；注入临时路径、固定路由、CLI double；没有执行全模块导入、模型发现或 MCP。B04 是两次故意失败派发，非自动重试；B07 检查不同分支及路径、状态记录未丢、父工作区未污染，模拟会话 ID 固定，不测真实会话唯一性；B08 是 Linux 中文/空格路径，不代表 Windows。两样本 p95 为最大值，仅描述测量；payload bytes 不是 Token。完整样本见 [JSON](../../benchmarks/results/d01-dispatch-contract-linux.json)。

## 已复现的上游缺陷（未修改）
| 观察 | 实际值 | 后续卡 |
|---|---|---|
| BUG-001：parse_report_file，无报告/无 fallback，exit=0 | status=completed, verification_passed=true | D07 |
| BUG-002：parse_report_file，fallback 报告 completed，exit=7 | status=completed | D07 |
| BUG-003：locked_state 读取损坏 JSON 后再写入合成任务 | 原损坏数据被覆盖 | D04 |

这是函数级直接观察；未断言完整应用路径均触发。后续修复应添加反向安全断言，并保留本轮基线证据。

## 运行器加固
默认 runner 校验 dispatch.py、报告 schema、5 个 MCP server 文件及 package.json/lock（9 文件），并记录实际 checkout SHA。缺失依赖或源码时 NOT_RUN，固定源码不匹配 FAIL；增强 B02 文件内容、B07 分支、状态持久化与父工作区隔离断言；拒绝危险沙箱与联网选项；Python -O 不允许。已执行 Python 语法检查；修改后 `--harness-only --repeat 1` 8/8 PASS；无完整源码的默认 `--repeat 1` 10 NOT_RUN，退出码 1。完整模块模式、MCP cold/warm、Windows/macOS 均尚未运行。模型用量 unknown/null。

保持 D01 REVIEW，不自动合并、不进入 D02。只保留脱敏结果，未修改原业务源码或启用 CI。
