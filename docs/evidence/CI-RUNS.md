# D01 原始基线与 Windows 修复候选：持久摘要

核对了两个 GitHub Actions Run、六份原始 ZIP 的 SHA256 及内部 JSON；每个平台每组 5 次。保留原版和候选版本区分。

- 原版 head `4aa954211c4cc9c44da4c7cc67d7562e6fb94b52`，[Run 45915363640](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45915363640)，整体 failure。
- 候选 head `cce185037d451d9f10dd3039e054d5b362a69119`，[Run 45918185018](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45918185018)，整体 success。

| 版本/平台 | 自检 | 完整调度器 | 综合 Mock | CI checks |
|---|---:|---:|---:|---|
| 原 Windows | 40 PASS | 30 NOT_RUN | 20 PASS / 30 NOT_RUN | 2 PASS / 3 FAIL / 1 NOT_RUN |
| 原 Linux | 40 PASS | 30 PASS | 50 PASS | 6 PASS |
| 原 macOS | 40 PASS | 30 PASS | 50 PASS | 6 PASS |
| 候选 Windows | 40 PASS | 30 PASS | 50 PASS | 6 PASS |
| 候选 Linux | 40 PASS | 30 PASS | 50 PASS | 6 PASS |
| 候选 macOS | 40 PASS | 30 PASS | 50 PASS | 6 PASS |

原 Windows 调度器未运行原因 ModuleNotFoundError；源码无条件导入 fcntl。原 Python exit 5，原 Bash MCP NOT_RUN；MCP B05/B06 冷热全部 20 PASS。候选完整调度器及 MCP 通过，新增锁回归通过。两轮均为 Mock、合成数据，0 真实模型调用，模型用量 unknown。三项负面观测在原 Linux/macOS、候选三平台均为 true/completed，未修复。

## 原始产物校验

| run / os | artifact | ZIP SHA256 |
|---|---|---|
| 原 Windows | [15161703518](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45915363640/artifacts/15161703518) | `187dc40a616f059185a55aa0bd4066de9d27b7112f8acda8a9aedbde8603d482` |
| 原 Linux | [15162071983](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45915363640/artifacts/15162071983) | `2ac9bf15517f3f48932b2b4c0f4e7f59d8cc35e1146707da1cad4960d8ce2f5e` |
| 原 macOS | [15162126149](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45915363640/artifacts/15162126149) | `96463a599f67ee058dd50e1d8dbc1a0beb57a14d58f855c3d0058c425eedb80b` |
| 候选 Windows | [15163565219](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45918185018/artifacts/15163565219) | `bea150b8c290729900f715b326bc575bb0ab6082333fbc16deb89ac1761856f6` |
| 候选 Linux | [15162779084](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45918185018/artifacts/15162779084) | `b11c04d84c3d814f38a3c3e98fbc2b56b824e7e02f875b31e29792970c73cf6a` |
| 候选 macOS | [15163635215](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45918185018/artifacts/15163635215) | `05f63540af458e404304c39143f8cd476b7ca09b2f3f047141e3060dac2b9bcf` |

六份 ZIP 均包含 baseline.json、dispatch-contract.json、harness.json、summary.json；下载后核验 digest 与 GitHub 一致。原始 ZIP 留存 14 天；本摘要不依赖 artifact 存活。实际版本：Node v22.23.5；Windows Python 3.12.10/Git 2.56.1.windows.1/2025Server；Linux Python 3.12.16/Git 2.56.1；Darwin Python 3.12.10/Git 2.56.1。托管运行器并非用户桌面，不能宣称实际模型或完整安装通过。样本重复/重叠，不是独立用例数；性能比较受主机差异影响。

## Windows 综合基准原版/候选（中位数 / p95，ms，原版缺失不填 0）

| 组 | 原版 | 候选 |
|---|---:|---:|
| B01 fresh | NOT_RUN | 643.117 / 647.418 |
| B02 fresh | NOT_RUN | 638.705 / 640.574 |
| B03 fresh | NOT_RUN | 948.885 / 1180.340 |
| B04 fresh | NOT_RUN | 1054.407 / 1057.158 |
| B05 cold | 13.888 / 15.429 | 13.141 / 13.384 |
| B05 warm | 4.158 / 5.171 | 4.307 / 7.318 |
| B06 cold | 75.366 / 77.836 | 72.723 / 74.422 |
| B06 warm | 60.341 / 68.606 | 59.438 / 62.100 |
| B07 fresh | NOT_RUN | 801.286 / 831.509 |
| B08 fresh | NOT_RUN | 633.911 / 638.115 |

不是性能节省验收：原版 dispatcher 缺失可比分母，n=5，托管环境不完全同机，不推导真实 Token 节省。


## 2026-11-27 D12 exact-head verification
[Run 45947305027](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45947305027) attempt 1 completed/success; PR #14 open Draft, dev/d11 -> dev/d12, tested head `f5b1bf017d1f1c259e1c50f0fd89a85100cf082f`. All four job checkout logs explicitly confirm this SHA; each ran `python -m unittest discover -s tests -p test_budget.py -v`, 6/6 OK (24/24 across environments), including malformed stream, conflict, dedup, unknown, limits and cached routing. Each also reports 23-card ledger PASS and successful applicable cumulative steps. Platform-specific steps skipped only as intended.

| Runner | Job | Image version | Python | Node |
|---|---:|---|---|---|
| Windows 11 ARM64 | 140334872489 | windows-11-vs2026-arm64 20261115.219.1 | 3.12.10 | 22.23.5 |
| Windows Server x64 | 140334872785 | windows-2025-vs2026 20261116.315.1 | 3.12.10 | 22.23.5 |
| Ubuntu | 140334872830 | ubuntu-26.04 20261116.88.1 | 3.12.16 | 22.23.5 |
| macOS ARM64 | 140334872749 | macos-26-arm64 20261123.0526.1 | 3.12.10 | 22.23.5 |

Windows 11 Enterprise build 26200 ProductType=1 ARM64 confirmed. No actual provider/model calls or real host verification; Gemini usage and paired benchmark NOT_RUN; prior superseded runs 45947038480/45947156315 retained, not counted as PASS. Boundary-only budget, no system-wide hard cap. D12 candidate ready; formal BLOCKED pending D05–D11 acceptance and real provider/host/benchmark evidence. No merge or release. Main observed `114e0c205f326b4af0935656ef482bba8270b284` (seven checkpoint-only commits since previous recorded main). D13 may inherit under existing candidate approval. Evidence-only commit is distinct from tested code SHA and requires governance recheck.
