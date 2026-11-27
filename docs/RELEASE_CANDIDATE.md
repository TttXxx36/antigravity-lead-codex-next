# V2.0 RC.1 — 未发布候选源代码包

候选编号 v2.0.0-rc.1；它只是归档名称，不是 Git tag 或正式 Release。每个包包含精确源提交的前 12 位，避免把不同源提交混成同一候选。禁止自动发布、自动合并、推送上游或修改保护规则。

## 构建和校验

在可信本地完整 Git checkout，从 HEAD 的已跟踪对象构建（不读工作目录修改或未跟踪文件）：

    python scripts/rc_package.py build --commit FULL_HEAD_SHA --version v2.0.0-rc.1 --out NEW_OUTPUT_DIR

Unix 等价入口：

    bash scripts/package-release.sh v2.0.0-rc.1 FULL_HEAD_SHA NEW_OUTPUT_DIR

使用独立可信渠道取得的 SHA256 校验，明确 commit 和 version；可选仅解包到新目录：

    python scripts/rc_package.py verify --archive PACKAGE.tar.gz --sha256 EXPECTED_SHA256 --commit FULL_HEAD_SHA --version v2.0.0-rc.1
    python scripts/rc_package.py verify --archive PACKAGE.tar.gz --sha256 EXPECTED_SHA256 --commit FULL_HEAD_SHA --version v2.0.0-rc.1 --extract-to NEW_DIR

构建过程不安装依赖，不联网，不访问真实状态，不签名、不打 tag、不创建 Release。固定 Git blobs、排序、USTAR 及 gzip 元数据；存储式 gzip（不压缩以减少平台编码差异）；CI 每个 runner 构建两次检查字节一致性。清单列出每个文件 SHA256、大小、模式、源 SHA；外部 SHA256SUMS.txt 同时记录包和清单。验证器拒绝链接、路径穿越、大小超限、Windows 保留名、大小写冲突、错误清单、非规范包。SHA256 不能证明来源真实性，必须从可信测试证据单独获取。

源包白名单只包含运行时代码、锁文件、已跟踪 UI、必要文档和测试/基准源。保留 LICENSE、LICENSE.upstream；不包含未跟踪文件、node_modules、原生/派发状态、密钥文件、截图、旧工作流发布例子或 .github。历史上游截图不进入 RC；二进制拒绝。对 UTF-8 源码执行有限的常见密钥格式扫描，失败不输出命中值。零命中不等于完整无密钥证明，仍需人工隐私和许可证审查。

## 门禁

- 四环境累计 CI、UI 可复现构建、打包、校验、Mock 回滚演练及安装生命周期只支持候选门禁。
- CI 仅在 dev/d22 Draft PR 完成测试后保留短期 source-rc-* artifact。不会创建 GitHub Release。
- D05–D21 正式 BLOCKED、真实 Windows Antigravity + Codex、实际任务质量/权限/Token、真实 App Server 及实机迁移均未正式通过。
- 所有阻断卡按依赖正式验收合并，并经人工核对源码、隐私、第三方依赖许可、真实宿主和独立发布批准后，才可拟定正式版本。任何不一致/未知状态保持 BLOCKED。
- 回滚见 [MIGRATION.md](MIGRATION.md)，不删除生产数据、不强制重写历史。


## D22 exact-head candidate verification
Run 46000875781 completed/success, exact source 7eb7b43cfe7be57aae2854f94aecf962e7745886. All four actual runners: seven D22 tests each (28/28), each builds twice byte-identically, checks Git blobs/license/source allowlist, strict checksum/identity/manifest/unsafe path/tamper refusal, explicit synthetic-secret negatives, fresh-directory extraction and isolated old-code rollback. On Ubuntu/macOS actual Unix installer with mock Node/npm/curl dependencies completed exit 0 and manual old-component restore; Windows fixture package-tree rehearsal plus actual native PowerShell installer/upgrade/restore/doctor/uninstall/SQLite preservation with native mock executable in cumulative CI. Each rollback recovered 3 components and 2 persistent files byte-identically, SQLite readable. Full cumulative regressions, D21 paired benchmark, governance and Linux UI reproducible rebuild PASS. Four RC artifacts uploaded successfully, all exact inner archive/manifest SHA256 equal across four runners. Initial Run 46000304667 all four blocked on literal synthetic PEM test marker; Run 46000617038 Ubuntu/macOS rollback failed on legacy local installer EXIT trap; both fixes independently tested, failures retained. D21 evidence head 1226e5d Run 46000026000 PASS.

- Version label: v2.0.0-rc.1 (filename only, no Git tag or Release)
- Archive: antigravity-lead-codex-v2.0.0-rc.1-7eb7b43cfe7b.tar.gz, 1812688 bytes, 138 source files
- Archive SHA256: 66835dac37201ffa021a35663ececda4a153d9e7c5a0faa3b8cc3056db51d931
- Manifest SHA256: f31e40e6e8ae4b0693778942ea5b6bd3b42351e2c6aa2fee01026e9dd5b49544
- Artifact run: https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46000875781 (7-day retention; external Artifact ZIP digest differs from inner archive SHA256)

| Runner / job | Rollback mode | Artifact ID |
|---|---|---:|
| install (ubuntu-latest) / 140511976927 | actual_unix_installer_mock_dependencies | 15197329055 |
| install (macos-latest) / 140511977264 | actual_unix_installer_mock_dependencies | 15198081739 |
| install (windows-latest) / 140511977341 | portable_package_tree_rehearsal | 15197134950 |
| install (windows-11-arm) / 140511977363 | portable_package_tree_rehearsal | 15198676005 |

No real provider or native Antigravity/Codex host, no production migration, no complete credential/third-party dependency review, no release/signing/tag/merge/upstream push. Common-pattern scan zero matches is not proof of absence of secrets; source package only, not offline dependency bundle. D05–D21 formal blockers remain. D22 candidate ready; formal BLOCKED, explicit release approval still required. This exact code-head artifact is the verified RC, distinct from the subsequent evidence-only commit; evidence head must be rechecked and would have a different source SHA/archive.