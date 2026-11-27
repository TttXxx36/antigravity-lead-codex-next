# D08 历史查询与 CI 候选

基线 ebc685892a863e8b96975ed20985188cdb0cd06a，D07 已验证代码 8e47299 / Run 45937506260。新增直接参数化查询，精确 ID 优先，前缀最多两个结果，歧义拒绝。SQLite readOnly:true、错误显式可见，测试临时四个 Codex DB SHA256 读前读后不变；真实 Git porcelain -z rename 与路径 fixture。保留最近任务列表功能；直接详情仍聚合其他数据，D16 再优化。长期累计 CI 对同仓库 PR 和 main push 执行四环境，不使用 secrets/真实模型；实际 Antigravity/Codex 端到端及 Windows 支持发布门槛仍 NOT_RUN。

## 首轮 CI 失败及修复
Run 45937983884：Windows x64/ARM64 的真实 Git fixture 初始化失败，Git for Windows 拒绝 Node os.devNull（\\.\nul）作为 GIT_CONFIG_GLOBAL，报 Invalid argument；纯解析测试通过，真实 rename 尚未执行。改用隔离临时空配置文件，禁止读取用户全局配置及 hooks；保留原始失败，重新四环境测试。此为测试环境配置兼容缺陷，不冒充生产 parser 已失败或已修复。