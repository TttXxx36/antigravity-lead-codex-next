# D16 — Display cache and delta evidence


## 2026-11-27 D16 initial candidate
Base 07ce2d89eeee61dcd4eafa8111e88f260d3b39a1 (D15 tested de11dc6f / Run 45974689285 PASS). Explicit ALC_QUERY_CACHE=1 enables app-only revision endpoints; default legacy fresh paths, model-facing task/authorization checks remain unchanged. Bounded 5s display TTL, 32 entries/2MiB, single-flight same source, native/owned DB and WAL metadata invalidation, errors/unknown stamps bypass cache; large legacy JSON bypasses cache. Local quota rollout only, bounded 15s cache, no live app-server or real model calls. UI source selects delta only if advertised, avoids unchanged render, ID detail no automatic Git unless tab selected, slower idle/hidden polling. Changed views still use existing full render; report-specific mtime optimization, measured paired p95/query/I/O, full DOM partial patch and actual host acceptance incomplete. Linux CI builds UI source but tracked dist/app.html is NOT yet rebuilt/committed; do not mark candidate ready or advance D17 until remaining candidate evidence. No merge.

CI evidence NOT_RUN until exact-head verification.


PR #18 Draft; initial code `1f99fb73decf91a088a8cb1098adac69ece1424b`, [initial CI 45975415764](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45975415764). Run observed in progress, no PASS inferred. This ledger-only follow-up records PR number and initial run; current head requires its own recheck. D16 remains IN_PROGRESS, no D17 branch or candidate-ready flag.


## 2026-11-27 D16 follow-up
Initial ledger head 34046f42ee0393b1bbfa6186ab866f626886d3aa / Run 45975558725 four-environment PASS, 20/20 cache tests, Linux Vite build and MCP delta passed. D15 evidence recheck 45975155258 PASS. Added bounded per-report mtime/digest-aware display cache, large legacy JSON metadata stamping, exact/prefix selector cache only for display, partial panel replacement for silent refresh, stale selection/failure and refresh coalescing safeguards. Added real SQLite query/open and logical content/wire byte benchmark on paired 30-call synthetic fixture; p95 is measured, not estimated; metadata stat syscalls/physical storage I/O not counted. Temporary Linux build transfer emits only generated public-to-repo static bundle chunks and git blob SHA, no token, no write permission; remove transfer step after importing exact verified blob. Dist not updated yet. Formal host, actual browser interaction and physical I/O remain unverified. No D17 start until candidate gate.

D16 verified build transfer: Ubuntu job 140446248179, Run 45981495894, exact source d4c06f7f41ddd17c149661c2f41fd9d679853777 built dist/app.html; 132 ordered base64 chunks reconstructed via Git blob API; runner git hash-object and API blob SHA both 255b42124451a7aac844c0226bd5d419c67119b2. No workflow write permission or real credentials used. Track exact bundle and remove export step; Linux CI now requires byte-identical rebuilt bundle. Initial Ubuntu fixture p95 3.502→1.493ms, queries 270→9, baseline logical content bytes 38670→1096 excluding marker-read overhead; NOT final I/O evidence. Revised marker memo counts its actual content reads/bytes and invalidates on metadata changes; include them in paired benchmark. Report cache includes current state identity in cache stamp, prevents reuse with stale session/exit/status. Final four-environment exact head CI pending; metadata stat syscalls and physical disk bytes remain unmeasured. No production changes.

## 2026-11-27 D16 final candidate evidence
[Run 45981702422](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45981702422) completed/success, exact code head `d70653cacd24c9cc448db4519a3f87deffd7bbfc`, PR #18 Draft. Four environments actual checkout logs verified, 8/8 Node cache tests per job (32/32), native MCP delta and all cumulative tests/governance PASS. Linux rebuilt dist/app.html byte-identically (git blob 255b42124451a7aac844c0226bd5d419c67119b2). Windows used tracked rebuilt bundle. D15 evidence head recheck 45975155258 PASS. Initial D16 Run 45975558725 PASS, 45981495894 superseded; Ubuntu source build was verified before supersession. No real model, deployment, permission expansion or merge.

Paired same-fixture actual 30 calls each, alternating order; p95 ms measured locally, counts actual native SQLite read opens/queries (excludes console preference DB operations), logical file reads/bytes include state marker and report reads; excludes metadata stat syscalls, DB page cache and physical disk bytes. Wire bytes are serialized payload bytes, not measured network transfer.

| Environment / job | p95 ms baseline → candidate | native DB opens | native queries | logical file reads | logical content bytes | JSON payload bytes |
|---|---:|---:|---:|---:|---:|---:|
| Windows Server x64 / 140447071189 | 12.654 → 4.34 | 120 → 4 | 270 → 9 | 60 → 2 | 41130 → 2356 | 4616100 → 156695 |
| Windows 11 ARM64 / 140447071531 | 11.263 → 3.744 | 120 → 4 | 270 → 9 | 60 → 2 | 41130 → 2356 | 4616100 → 156695 |
| macOS ARM64 / 140447071591 | 3.51 → 1.065 | 120 → 4 | 270 → 9 | 60 → 2 | 41310 → 2368 | 4648110 → 157762 |
| Ubuntu / 140447071593 | 4.049 → 1.591 | 120 → 4 | 270 → 9 | 60 → 2 | 38670 → 2192 | 4413150 → 149930 |

Candidate ready under existing authorization; formal BLOCKED: actual Antigravity browser/old-host compatibility, live DOM interaction, physical I/O, real host state changes and dependency acceptance remain unverified. Report-only mutation may lag snapshot TTL (5s); per-report identity/mtime checked when refreshed; local quota 15s TTL. No model/authority checks use display cache. D17 may continue. Evidence-only head requires recheck.
