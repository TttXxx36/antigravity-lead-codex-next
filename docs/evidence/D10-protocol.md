# D10 协议候选证据

基线 b057e6da5b1c92477197f696fd1de6fce5a69898，D09 代码四环境 Run 45940757723 success。新增 v2 schema/严格运行时校验/单任务锁内 revision/显式 opt-in，保留 v1；运行/恢复 Mock 实际进程、负向校验、报告状态、机器采集及累计回归待 CI。真实模型/宿主 NOT_RUN，未验证 structured output schema 支持；batch/MCP 仍 v1，D11/D13 后续扩展。不得升级真实模型调用权限或发布。

D10 review follow-up: enforce raw-byte report limit before decoding or stripping whitespace; malformed deeply nested JSON fails closed; document result schema, expose persisted v2 revision in compact managed status, and flag truncated risk lists. Initial CI run 45941194963 superseded by final candidate revision (Ubuntu initial success observed); final head must be independently tested.

## D10 最终候选实测
[Run 45941283814](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45941283814) completed/success，精确代码 head `5e937fcb4de98d0df60cef144b81e8f619f9e550`；Ubuntu、macOS、Windows Server x64、Windows 11 ARM64 四环境全绿。各环境6项协议测试及1项实际 Mock run/resume revision 回归（28次新增测试），累计 D03–D09 回归通过。首轮 45941194963 因后续修正被取消，不计为通过。真实模型 structured output、真实宿主及实际 Token 未验证；v2 仍显式选择，batch/MCP 默认 v1。D10 候选可复用，正式验收 BLOCKED，PR #12 Draft 未合并。
