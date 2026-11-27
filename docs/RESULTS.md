# D21 测量结果

正式真实模型验收：NOT_RUN。四环境候选配对基准已通过，真实任务及 Token 未验收。


## D21 candidate implementation 2026-11-27
A paired benchmark; exact predecessor 505f5bf955f47b66c935b3371e3991085221e083 (D20 evidence recheck 45990579786 all four PASS). Same checked-out implementation, legacy full snapshot vs opt-in delta, NOT historical main-vs-candidate benchmark. Actual native MCP over stdio and synthetic SQLite fixture: six independent pairs, five polls per arm, alternating order, force first candidate refresh/new revision, then reuse; OS caches not controlled. Validate equal displayed task IDs/status/title, managed IDs/status, stats, connected health on every successful poll. Capture actual serialized request+response JSON-RPC envelope bytes excluding newline (not network or model tokens), per-batch wall clock median and nearest-rank p95, explicit attempted/success/failure/unknown/not-run counts, no retries. Failures retained; no savings if incomplete. 30–60% communication hypothesis explicitly report BELOW/WITHIN/ABOVE, no guarantee. Fixture-only quality and regression, real quality/Token NOT_RUN, Gemini UNKNOWN, no byte-to-token conversion or billing claim. Numeric whitelist output with no prompts/path/raw payloads; checkout and fixture shape digest, Node/OS/arch. Full history read-only checkout for pinned ancestry, no permission expansion. Six summary/negative unit tests and actual paired native MCP regression on four runners pending. Formal acceptance blocked real tasks, model/effort/cache and independent evidence.


## D21 exact-head candidate verification
Run 45999409240 completed/success; source c1bff452b8718c759820ae919aa05c1c6246811b. Four actual environments; six summary/validation tests each (24/24); native MCP and cumulative CI/governance PASS. Six paired repetitions per arm with five polls per repetition (30+30 per platform, 240 total); 48/48 batches and 240/240 polls PASS, 0 retries; compared displayed IDs/status/title, managed IDs/status and stats. Same checkout legacy full vs revision delta; fixture shape digest 1343cc3bb9f735d31622a771ee10c07d900f37ebc324e04eae1e96265d5c3f39; not historical baseline execution. Both arms run in actual MCP fixture, no model/effort; force first refresh then reuse, OS cache not controlled. Latency per 5-poll batch, p95 nearest rank over 6 samples, not production tail estimate. Bytes serialized JSON-RPC request+response excluding newline; denominator baseline bytes, no network or token conversion.

| Runner / job | Baseline bytes | Candidate bytes | Reduction | Median ms | p95 ms | Hypothesis |
|---|---:|---:|---:|---|---|---|
| install (windows-11-arm) / 140506913225 | 1397170 | 289522 | 79.278% | 34.935 → 18.55 | 39.621 → 23.288 | ABOVE |
| install (windows-latest) / 140506913630 | 1397050 | 289498 | 79.278% | 21.277 → 11.703 | 24.326 → 13.048 | ABOVE |
| install (macos-latest) / 140506913695 | 1405210 | 291130 | 79.282% | 9.78 → 4.86 | 11.008 → 5.796 | ABOVE |
| install (ubuntu-latest) / 140506913703 | 1339600 | 278008 | 79.247% | 11.6 → 6.377 | 13.886 → 7.111 | ABOVE |

Measured communication exceeds 30–60% hypothesis for this narrow stable synthetic polling workload; not actual total communication, cost, real task quality/success or token savings. Fixture checks zero failures and zero observed P0 fixture regressions; all actual real tasks/model quality, actual Codex usage, Gemini usage, mixed-workload baselines, confidence and production P0 acceptance NOT_RUN/UNKNOWN. No real model invocation or merge. Candidate ready for D22 offline package/rollback preparation; formal BLOCKED. Evidence-only head recheck required.
