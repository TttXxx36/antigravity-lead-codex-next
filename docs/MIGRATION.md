# V2.0 候选迁移、备份与回滚（未授权发布）

本指南只适用于经人工核验、隔离环境演练的候选包。不要在生产宿主直接执行；正式发布、实际迁移、真实模型调用须分别批准。

## 迁移前

1. 核对来源提交、CI 原始证据、独立可信 SHA256SUMS.txt、双 MIT 许可证及 RC-MANIFEST.json。SHA256 是完整性校验，不是签名。
2. 停止 Antigravity、Codex Console 及所有受管任务，确认没有排队/运行/未结算请求或租约；不能用 PID 消失代替确认。保留当前版本的完整安装目录、配置和依赖锁文件。
3. 在宿主关闭且数据库已安全静止时分别备份 GEMINI_CONFIG_DIR、插件自有 data、AGY_DISPATCH_STATE_DIR（包含 marker、实际数据库及必要 WAL/SHM、runs）、原生 Codex 数据；不复制正在写入的 SQLite 主文件作为可靠备份。保护备份权限，不上传原生历史或凭据。
4. 保留旧安装包、运行时版本及恢复说明；先在隔离目录测试，不覆盖真实路径。

## 兼容与启用

- Node 22.5+（CI 22）、Python 3.10+（CI 3.12）、Git；Windows 原生 PowerShell 7.2+。CI 仅真实 runner 上的合成/Mock 任务，实际 Windows Antigravity + Codex 未验收。
- 默认 CLI、JSON 状态、旧执行路径；网络与危险 sandbox 不得无授权开启。D13/D14/D16/D17/D18/D19 等 opt-in 特性分别验证，不同时启用未知组合。
- ALC_APP_SERVER_EXPERIMENTAL=1 只表示实验诊断意向；不启用真实 App Server 执行。
- D15 state-migrate/state-rollback 须显式 --confirm-quiescent，先读 D15 决策与实际 CLI --help；保留原备份，禁止未结算任务时迁移。不得手工改 marker 或删除 SQLite WAL/SHM 来强制回退。
- RC 为源代码包，包含已跟踪 UI bundle 和锁文件，不包含 node_modules；依赖准备另行授权，使用锁定依赖和可信缓存；禁止用未验证网络安装替代。
- Windows 参考 docs/WINDOWS_INSTALL.md：install.ps1 -Mode All 或 ConsoleOnly；用已准备依赖和显式路径。诊断通过不代表宿主真实 MCP UI 兼容。
- Unix 旧 install.sh 不是跨平台事务安装器；它会安装依赖，若有宿主热加载变量可能联系本机宿主。先备份、清除环境中的热加载/凭据变量，仅在隔离环境使用；不要从上游 curl|bash 安装 Next 候选。

## 失败及恢复

1. 停止任务与宿主；不能确认静止、存在未知请求/租约时停止恢复，人工核对，不自动重派。
2. Windows 使用已提交的 .alc-backups 事务目录：install.ps1 -Mode Restore -RestoreFrom <具体备份目录>，同时传入原来显式配置/数据路径。仅支持 committed 备份；不完整 journal 必须人工处理。
3. Unix 使用预先保存的三个代码组件目录（plugins/codex-console、plugins/codex-auto-router、skills/multi-agent-dispatch）：先把失败版本移至隔离保留目录，再将旧代码及配置恢复到原路径；不覆盖持久数据目录。不得把演练当作自动原子安装保证。
4. 状态回退仅使用相应 D15 官方 CLI 和人工核验过的静止备份；不直接删除、改名或覆盖 Codex 原生数据库。对确需恢复的数据使用匹配版本和完整备份，验证 SHA256、SQLite integrity_check 与记录数量；先复制到临时目录验证。
5. 核验旧版本依赖、启动诊断、原生数据库与插件/派发数据一致性，再经人工批准重启。失败版本和审计记录保留，不重写 Git 历史。

实机恢复、断电原子性、所有平台真实宿主迁移仍 NOT_RUN。本轮只在临时目录做旧组件恢复、实际 SQLite/JSON 保全及既有 Windows 模拟原生安装生命周期测试。
