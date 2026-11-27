# D03 跨平台路径和运行时 smoke 证据

- 已授权方案 A；基线 main `185961beefe84ebbf9a66d4b74407e7449d3f473`，测试 head `b37f1dd0d3d1fb2e0c10d2729def979b1d0660fb`。
- [PR #5](https://github.com/TttXxx36/antigravity-lead-codex-next/pull/5)；[Actions Run 45933533805](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45933533805) completed/success；从逐 Job 日志核验。

| 平台 | Python test_platform.py | Node test-platform.mjs | 台账 | Native MCP |
|---|---|---|---|---|
| Windows | 7/7 OK | 4/4 PASS | PASS | PASS |
| Linux | 7/7 OK | 3 PASS / 1 SKIP | PASS | PASS |
| macOS | 7/7 OK | 3 PASS / 1 SKIP | PASS | PASS |

Windows-only Python wrapper check 在 Linux/macOS 直接返回，非执行 Windows 断言；Node wrapper check 明确 SKIP。三个 job 共 31 次标记通过的测试调用（其中两次 Python 提前返回），2 次显式跳过，0 FAIL。另三平台 native Node MCP integration 成功，非模型调用。实际路径 fixture 创建中文、空格、较长目录，超过260字符路径仅词法测试，不能据此声称实际超长 I/O 或真实 Windows 桌面支持。使用系统 Python/Node 作为可执行路径/Mock，真实 Codex CLI 和 Antigravity 宿主未测。原 D01 baseline 仍固定历史版本，D01/D02 专属 workflow 在 D03 被条件跳过，不计入结果。

## 改动与取舍

- Python dispatcher 与 Node platform adapter 使用共同环境变量、路径规范化及显式覆盖/PATH 优先规则（旧默认路径保留）。无效显式覆盖不回退；Windows 只选 .exe，不执行 cmd/bat；禁用设备命名空间/保留名、尾随点/空格、ADS 等；不引入 shell:true。Python 的实际 Codex 选择从每次版本探测排序变为显式/PATH 优先；health 保留版本诊断。真实候选版本选择策略仍须 D12 验收。
- 为让 Windows 能加载模块及运行 MCP 测试，复用 PR #4 已通过的基本 msvcrt/flock、UTF-8 与 Node 测试启动/清理。没有提前实施状态损坏保护、任务 ID 原子预留或审批机制；D04/D05/D06/D07 独立验收。完整上游 Python suite 的 Windows hook、原始基准工具（固定原版 SHA）不作为本卡 PASS，后续回归完善。
- 真实模型调用 0（测试范围仅 Mock/synthetic；usage UNKNOWN）。未发布、未合并、未改变用户权限或原生 Codex DB。

Job IDs: Windows 140291421928、Linux 140291422172、macOS 140291422081。回滚：未合并时关闭 PR；合并后 revert D03 commit，保留基线与证据。后续文档提交只记录证据，最新 head 复检须以实际 CI 为准。

## 最终补测及合并

[Run 45934273615](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45934273615) success，精确 head `4e10446f189599eb0ebb4c075b8cc9d043d1c48b`，Windows/Linux/macOS 三个 job 均 success。Python/Node 测试新增实际 >260 字符目录及文件创建、UTF-8 读写、删除；Unix Python wrapper 专属测试改为显式 skip。依据用户条件授权合并 PR #5，merge `c6c6188b078dcf51b3729c2834782ca5033cf3f9`；D03 DONE。