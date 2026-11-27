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

## 2026-11-27 formal acceptance round 2: verified privacy fix and early-card remediation
- BUG-006 CANDIDATE_PASS (not formally closed): exact code head 6f2d23bfb8b7bf56cdaed20239e049af1571de11, [Run 46003742874](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46003742874) completed/success; all 4 checkout logs and D22_REPRO/D22_RC agree. Jobs macOS 140521599289, Windows Server x64 140521599556, Ubuntu 140521599618, Windows 11 ARM64 140521599708. D22 module: 10/10 each Unix, 7 PASS + 3 Bash-only skips each Windows (34 PASS / 6 SKIP total), cumulative CI, governance and Linux UI build PASS. No model tests. New source-only archive 1833168 bytes, 138 files; archive SHA256 675ec1ff72f08adab33cf45ba2b68458dfbfff3b6a54507e166c60298cdcd442; manifest SHA256 4d62623471ebfc4244236d5b03ab64118b220d66d9de55428deb0481979791d8; all four twoBuildsIdentical=true, sourceOnly=true, releaseAuthorized=false. Artifacts Ubuntu 15200575184, macOS 15199527087, Windows x64 15198934223, Windows ARM64 15199776435; expire 2026-12-04 UTC. Hashes from verified CI logs, not independent local download for this new archive. Preserve the two prior immutable RCs separately. Evidence-only follow-up head requires own recheck; no recursive RC evidence rebuild loop.
- D14 #16 standalone backport ba9a3b5e4f1625cd1b19fefb6ba469a37aff8346; [Run 46004229789](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46004229789) in progress at last query. Only the D16-tested process-exit correction and test moved back. D15 needs integration; D16+ cumulative code already has fix. Standalone D14 candidate.ready=false pending CI, historical cumulative PASS unchanged.
- D06 #8 standalone static review found ordinary cleanup may remove worktree without trusted grant (BUG-007 proposed P1, not reproduced data loss). Correction b9c3fe4df5636aa32bac3ee673e9a0ca5839ddeb denies all cleanup before state access/Git and aligns MCP descriptions. Standalone candidate.ready=false pending CI. D07–D16 require safe integration before formal acceptance; D17+ current cleanup is read-only preview, verified by source inspection. No actual deletion or expanded permission. Trusted positive grants unimplemented, actual OS sandbox NOT_RUN. Cumulative ledger retains historical tested snapshots, not a claim that all current standalone branch heads are ready.
- D05 real Windows x64/Antigravity/Codex evidence still absent; no formal merge, no native Codex DB writes, no tag/release. main remains 114e0c205f326b4af0935656ef482bba8270b284. All formal gates unchanged.


## Formal acceptance round 3 final evidence checkpoint (2026-11-27)
- D06 evidence-only head 234c8388b093b5dedf1d7c0cc65e42e7d1d1a710 Run 46004837384 completed/success (run metadata); code head b9c3fe4 logs verified previously. BUG-007 candidate pass, not formally closed.
- Initial per-branch safety patches caused mergeable=false/no PR CI for D07/08/09/15/16. Non-rewriting two-parent candidate integration recovered all five PRs mergeable=true; not a formal PR merge. Current standalone exact head and CI:
- D07 943f1c0606ad47b9602d49d5ea38765c24ea7639 https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46006007007 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D08 c4d75a778c0c70f80a2b3ea2afdb1bd04cfb4e87 https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46006085006 in progress at last query (do not mark PASS)
- D09 61ed00c712fc0d5bf9a7f24eb5e4aed7f98fbb78 https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46006153189 in progress at last query (do not mark PASS)
- D10 529b55538e0aa51a2b5db4d65167ada2eeb0ca11 https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46005016728 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D11 2849bbd82952f7f0c33914e47df92ad4e6f87c81 https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46005067101 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D12 46994031fde3203ee64713721d3d655231a4750d https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46005073293 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D13 75fba01e9b6f5d1e1a6ddc51392db195aea3524d https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46005120129 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D14 e493d582bf05facc9f9f29c71bf20c92b694f24f https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46005125939 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D15 1a6d3d640954128114defeb57d0ebed989ef9117 https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46005934753 4/4 PASS (actual checkout and cleanup tests checked in all four logs)
- D16 0425f17e921ca09571f74c409c4234c35876ca1c https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46006220435 in progress at last query (do not mark PASS)
- D15 actual parent D14 e493d582bf05facc9f9f29c71bf20c92b694f24f integrated; new D15 1a6d3d640954128114defeb57d0ebed989ef9117 Run 46005934753 all four actual checkout/cleanup/EPERM tests PASS. D16 integrated D15 but CI pending. D17-D22 source retains preview-only cleanup + EPERM; actual D16->D17 diverged ahead 4/behind 6 and D09->D10 diverged ahead 4/behind 8 after integrations; D17->D22 successive ancestors before this checkpoint. Other intermediate ancestry reconciliation remains required before formal merge. Historical exact-head PASS does not establish latest merge-candidate PASS.
- D22 installed dependency audit plus cumulative Run 46005586701 4/4 success, exact fc6fdc51923c7605072fb97062b21b7c0628f478 checkout logs verified. Runtime each 95 installed/95 with notice/identity PASS, one heuristic notice review; Linux build 112 installed/109 with notice/identity PASS, four review items. Ubuntu artifact 15200857136 downloaded and inspected: fast-uri 3.1.9 BSD-3-Clause with notice hash b010b0dfdfdb23d7396e03b82cd4621fc9bb8f95d6b0aea70b9c24e12074c786 (heuristic family mismatch), @esbuild/linux-x64 0.25.12, @rollup/rollup-linux-x64-gnu and -musl 4.68.8 have no standalone notice in package root; verify parent package notices and binary distribution obligations, not a legal violation conclusion. Other runtime reports show one notice review each; not individually downloaded. Audit metadata artifacts Ubuntu 15200857136, macOS 15201536188, Win x64 15201456279, Win ARM64 15202540417. Lock LF SHA256 17d1b90be6a04f5d5d7d63e10f12c0890a571924fba02453b775917510ada881; independent CRLF conversion exactly equals Windows c63363e51b0aee30429cbdbee42cd4748dc20dafe637e526f7d0c5ae3277f9b5. No extra audit network; vulnerability/provenance and full legal notice review NOT_RUN/BLOCKED.
- D22 new source RC fc6fdc51923c: 139 files, 1863893 bytes, archive SHA256 89f1accabff7de04b67c29696fbf6e56baf5f83f8269394690156c91426b493f, manifest SHA256 2647ccc4b8a1ec3cb7ec5af670ba5a87a73cbedd299a9b4654dc51d89df73b16 (four CI logs match, no local byte verification of this version). Artifact IDs Ubuntu 15200827028, macOS 15202265863, x64 15202031188, ARM64 15201611600. Prior 6f2d23b RC verified independently and preserved; no tag or release.
- Main 114e0c205f326b4af0935656ef482bba8270b284, D05 actual host evidence still NOT_RUN; 5 DONE / 18 BLOCKED. No formal merge, model calls, permission expansion, native database write, data deletion or publish. Evidence-only next head needs recheck; avoid recursive documentation-only RC rebuild loop.


## 2026-11-28 formal acceptance continuation — exact Zod remediation and independent artifact review
- Tested source d40e45320ed028581d2246fe560c909256b2644e; [Run 46025354306](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46025354306), four actual checkout logs and jobs completed/success: Ubuntu 140595233589, macOS 140595234048, Windows Server x64 140595233907, Windows 11 ARM64 140595233921. All D22_REPRO and D22_RC hashes match; Linux tracked UI reproducibility PASS. D21 base 44b0fbe98dd2470f7095576757d1cbc96f89f947, compare ahead 12 / behind 0. D22 remains Draft/BLOCKED.
- Ubuntu RC artifact 15211252800 downloaded independently; ZIP SHA256 41846e6ea3b0c427da729a235b2afa83eba2b7ae758d5a097e57e13d60733c61, inner archive 2058468 bytes SHA256 ce7dec978a48317e31124bb6aa18a92fc7f439a5bdaf4d210780af8b0e42f3e8, manifest SHA256 69becc3020a30c43a4e5bc2dfc244fd722a4617d5125ac2429a02bbbbdd3453b; 140/140 source files size/mode/digest, embedded manifest, canonical verify_bytes PASS. Source-only v2.0.0-rc.1, no release authorization. Other RC artifacts macOS 15210474516, Win x64 15211612970, ARM64 15211928159: metadata/logs checked, not independently downloaded. Original ZIP retained in this session and provided for user preservation; no cross-session storage guarantee; artifacts expire 2026-12-04 UTC.
- Ubuntu audit 15210524457 independently downloaded, ZIP SHA256 038db8483cea4e453a3492c5e597b6305e7c57f050b1077da3349f29327898b5. Both audit JSON reports zero vulnerabilities at every severity, all/runtime/signatures/SBOM exit 0; 112 signatures and 26 attestations verified by npm, not independently re-signed. Zod 4.6.7 in both inventories, lock and SBOM; RC lock LF SHA256 f0cce3d06a58e27b25111a14d7ca69741d1e38319d3516f376cc7640bf1aa573 matches both inventory reports. Git blobs manifest a35d9a0f4b690f4a57861f209861cd3f93892f81, lock 196e8559e331f9689f117f034d690830a4d43b11, bundle 61ac6557921403aa3564d5f54328f8987e06e198 independently reproduced. Old HIGH FAIL (46015133159) and trial Linux UI FAIL (46017099856) retained, remediation candidate PASS, no general security clearance.
- NEW BUG-009 (proposed P2, SBOM evidence integrity): actual CycloneDX 1.5 JSON has 112 component records but 109 unique component bom-refs, 113 dependency records but 110 unique refs including root. Four nested content-type@2.1.0 instances (body-parser, express, negotiator, type-is) share one bom-ref and duplicate dependency entries; same package hash, no missing reference targets observed, no actual tampering observed. SBOM command PASS does not imply structural PASS. Independent uniqueness check FAIL. Preserve original evidence; investigate generator or path-qualified graph with lock-backed resolution, validate uniqueness and edge mapping, add regression. Do not silently deduplicate or mark ready before resolution.
- Offline inventory identity PASS runtime 95 installed/95 notices; build 112/109. fast-uri 3.1.9 notice SHA256 b010b0dfdfdb23d7396e03b82cd4621fc9bb8f95d6b0aea70b9c24e12074c786 matches prior manual review; three binary notice questions OPEN (esbuild 0.25.12 linux-x64, Rollup 4.68.8 linux-x64-gnu/musl). Parent esbuild and Rollup notices exist in inventory; actual license text/distribution obligations not independently closed. No full legal approval. Local governance checker PASS and 18/18 governance tests, 5/5 dependency notice tests PASS on extracted exact-source snapshot.
- D05 still NOT_RUN actual Windows 11 x64 / Antigravity / real Codex host (current execution environment Linux x64). main 114e0c205f326b4af0935656ef482bba8270b284 vs dev/d05 ahead 6 / behind 11, diverged; reconcile final candidate without force push and recheck exact head before host acceptance/merge. D00-D04 DONE, D05-D22 BLOCKED. No real model, production data access, native DB write, permission expansion, release or formal merge. D22 candidate.ready remains false due to SBOM structural defect, not Zod HIGH. Evidence-only commit is distinct from tested source and requires own CI; do not recursively rebuild preserved RC for each evidence update.
