# D16 — Display cache and delta evidence


## 2026-11-27 D16 initial candidate
Base 07ce2d89eeee61dcd4eafa8111e88f260d3b39a1 (D15 tested de11dc6f / Run 45974689285 PASS). Explicit ALC_QUERY_CACHE=1 enables app-only revision endpoints; default legacy fresh paths, model-facing task/authorization checks remain unchanged. Bounded 5s display TTL, 32 entries/2MiB, single-flight same source, native/owned DB and WAL metadata invalidation, errors/unknown stamps bypass cache; large legacy JSON bypasses cache. Local quota rollout only, bounded 15s cache, no live app-server or real model calls. UI source selects delta only if advertised, avoids unchanged render, ID detail no automatic Git unless tab selected, slower idle/hidden polling. Changed views still use existing full render; report-specific mtime optimization, measured paired p95/query/I/O, full DOM partial patch and actual host acceptance incomplete. Linux CI builds UI source but tracked dist/app.html is NOT yet rebuilt/committed; do not mark candidate ready or advance D17 until remaining candidate evidence. No merge.

CI evidence NOT_RUN until exact-head verification.


PR #18 Draft; initial code `1f99fb73decf91a088a8cb1098adac69ece1424b`, [initial CI 45975415764](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45975415764). Run observed in progress, no PASS inferred. This ledger-only follow-up records PR number and initial run; current head requires its own recheck. D16 remains IN_PROGRESS, no D17 branch or candidate-ready flag.
