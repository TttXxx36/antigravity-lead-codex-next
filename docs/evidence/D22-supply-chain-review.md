# D22 supply-chain review — 2026-11-27

## Scope and evidence boundary

- Exact candidate before this review: `17519126ef8f5ef6ce64ee2cc53b3b921cac3068`.
- BUG-008 four-platform CI: [Run 46007057302](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/46007057302), all four Jobs PASS and actual checkout SHA verified.
- Audit artifact ZIPs from that run: Ubuntu build/runtime, macOS runtime, Windows x64 runtime, Windows ARM64 runtime. Runtime package count 95 per platform; build package count 112 on Linux. All identity metadata checks PASS.
- Audit JSON explicitly records `vulnerabilityAudit=NOT_RUN`; therefore this run supplies no CVE clearance.

## Four license findings

See [D22 dependency audit evidence](D22-dependency-audit.md) for the per-package decision. fast-uri 3.1.9's exact upstream BSD-3-Clause text hash matches the installed notice and resolves the heuristic mismatch. esbuild and both Rollup platform packages declare MIT and are covered by tagged upstream project license files, but no separate license file exists in the platform-package source directories; published tarball notice inclusion remains OPEN. No blanket compliance PASS is issued.

## Vulnerability and provenance collection

The D22 workflow now collects full/runtime npm advisory JSON, npm registry signatures, and CycloneDX SBOM from a Linux runner against `registry.npmjs.org`. It retains raw outputs, stderr and exit codes without changing dependencies. This is evidence collection, not an automatic remediation or release gate. Review advisory severity, affected paths, fixed versions, signatures and attestations; a failed/unsupported registry-signature check is INCONCLUSIVE. npm lockfile integrity and hidden-lock consistency do not by themselves prove publisher provenance.

## Outstanding release blockers

1. Inspect new npm audit JSON and triage every advisory, especially high/critical and reachable production paths.
2. Confirm registry signature/provenance coverage for the locked package set; identify unsigned packages or unsupported endpoints.
3. Inspect published tarballs or upstream release process for the three MIT platform packages to verify license notice distribution.
4. Complete legal notice aggregation and provenance review before D22 acceptance. No D22 formal merge or release authorized by this record.


## HIGH vulnerability triage

- Exact installed version: `zod@3.25.76`; direct dependency `^3.25.0`.
- npm advisory: [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5), CVSS 7.5 HIGH, CWE-770; both full and production-only audits report one HIGH and no other severities.
- npm recommends `zod@4.6.7`, marked SemVer-major. Current application uses only `z.string`, `z.number`, `z.boolean`, `z.enum`, and common validators. MCP SDK/ext-apps and zod-to-json-schema peer ranges allow Zod 4. This does not replace full tests.
- Registry signatures: 112/112 verified; 26 attestations verified. CycloneDX SBOM: 112 components and 113 dependency nodes.
- D22 workflow now generates a temporary Zod 4.6.7 lock candidate with `--ignore-scripts`, captures the manifests, installs it on each matrix platform, checks `npm ls zod`, then runs the full regression and repeats npm audit. Repository package files remain unchanged until the generated lock is reviewed.

**Release blocker:** do not merge D22 while the HIGH Zod advisory remains. Require 0 high/critical in both all-dependency and production-only audits, all four CI jobs PASS on the committed Zod 4 lock, signatures/provenance reviewed, and the three platform package notice distributions closed.


## 2026-11-27 — final stack reconciliation and Zod candidate repair
- D18 exact b2eabc3a24c1cb8fae06b249c1c8ed8961f44c7b Run 46013467970 all four jobs success. D19 db7720dbded79acabaf26703e5b92d4eaa1c36a1 Run 46013882116, D20 cbbed8ac862546470d0cacc78a282a9ae760141d Run 46014172198, D21 44b0fbe98dd2470f7095576757d1cbc96f89f947 Run 46014451284 completed/success (run metadata). D18–D22 compare behind_by=0; PR #20–24 draft, unmerged, mergeable=true at verification. No duplicate ancestry rewrite. Earlier exact integrated D06–D10 candidate evidence restored in ledger; D11–D21 existing PASS retained.
- BUG-008 CANDIDATE_PASS, exact 17519126ef8f5ef6ce64ee2cc53b3b921cac3068 Run 46007057302, all 4 actual checkout logs checked: 18 tests PASS, 2 Unix symlink fixture skips on Windows, zero failures; runtime identity 95 packages per runner, Linux build 112. No formal defect closure.
- Zod temporary upgrade trial 0245d5404e19c1d486d3c8015f5f3fb620d324c3 Run 46017099856: Windows x64 140566909928, macOS 140566910375, Windows ARM64 140566910422 success; Ubuntu 140566910503 FAIL at tracked UI reproducibility. Ubuntu artifact 15205774969 ZIP SHA256 015f043e1b7fa3b37d2a0e98476201410769636b4c69b5e7c97ac4a52e4125d0 independently verified. Full/runtime audit JSON all severities zero, exit 0; signatures 112 verified, attestations 26, SBOM exit 0. Trial results NOT an exact committed RC acceptance.
- Commit reviewed candidate manifest blob a35d9a0f4b690f4a57861f209861cd3f93892f81 and lock blob 196e8559e331f9689f117f034d690830a4d43b11; both exactly match artifact Git hashes. Lock LF SHA256 f0cce3d06a58e27b25111a14d7ca69741d1e38319d3516f376cc7640bf1aa573. Only root version normalization to 1.0.2 and Zod dependency/version/resolved/integrity changed. UI bundle reconstructed losslessly from complete Linux git diff, matching every old/context line and hunk count; new blob 61ac6557921403aa3564d5f54328f8987e06e198 equals actual CI git hash-object output. Remove temporary npm install mutation; strict npm ci and exact Zod version assertion, preserve tracked bundle check and audits. New exact-head CI required, no bypass.
- Prior fast-uri notice hash match is recorded in supply-chain review; three esbuild/Rollup platform binary tarball notice-distribution questions remain OPEN. No complete legal clearance or guarantee of no vulnerabilities. All formal statuses unchanged, 5 DONE /18 BLOCKED; D05 actual host unavailable. No real model, permissions expansion, production DB write, data deletion, formal merge or release.
