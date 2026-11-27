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
