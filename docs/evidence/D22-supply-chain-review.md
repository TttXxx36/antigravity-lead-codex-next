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
