# D01 GitHub Actions 三平台基准

2026-11-27 用户明确要求使用 GitHub Actions 测试。仅授权本次测试工作流及临时 runner 上的锁定 npm 运行依赖安装（不运行 lifecycle scripts）；不调用真实模型、不修改业务源码、不合并、不发布。

工作流：`.github/workflows/d01-mock-baseline.yml`，PR #2 同仓 dev/d01 → main 触发，checkout 精确 PR head，不保存凭据，contents:read，三平台矩阵 fail-fast=false，20 分钟 job 限制，5 次重复。仅合成 SQLite 和隔离 Mock；不读取用户真实账户或数据库。Node 运行依赖通过 npm ci --omit=dev --ignore-scripts 安装；无真实模型令牌注入。CI 原始 Bash MCP 集成在 Windows 明确 NOT_RUN，独立原生 Node MCP 探针仍尝试。原始 fcntl 限制保留实际失败/NOT_RUN。不把失败标通过。

每个 runner 上传 ci-evidence 中的 JSON（14 天），包含版本、实际 checkout、基准原始样本、退出状态及摘要。未运行/失败保留，job 非零。当前工作流尚待远程触发及实测确认；以 GitHub Actions 的实际 run/job/ artifact 为准。托管 runner 不是用户 Windows 实机，也不是 Antigravity 实机验证。D01 仍 REVIEW。
