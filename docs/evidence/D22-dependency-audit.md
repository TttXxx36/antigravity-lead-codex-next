# Installed dependency notice inventory (offline)


## 2026-11-27 formal acceptance round 3
All three historical runs completed success: D06 46004369900 (20/20 execution policy, exact b9c3fe4df5636aa32bac3ee673e9a0ca5839ddeb); D14 46004229789 (36/36 streaming, exact ba9a3b5e4f1625cd1b19fefb6ba469a37aff8346); D22 46004434638 (exact c1066765390cd60d479c6170ab9b875d05cd2442, all four checkout/RC logs confirmed). New archive c1066765390c 1843408 bytes / 138 files; archive sha256 8938c35fa137e1af180acb9af4c3db1d5030746c6c05080f7ea920861484d797; manifest sha256 0e667746330f45fafdf24089f3d26c03d26bad2066edd3ebeb1a773c16efa806. CI-reported digests only for this archive. Independently downloaded earlier 6f2d23b RC artifact 15200575184: outer/inner/manifest digests and 138/138 file metadata plus embedded manifest and canonical verify_bytes PASS; keep separate.
D07-D16 per-branch minimal safety patch synchronization (no formal merge, no rewritten history):
- D07 8736befbf2d54503ae3e951f74175a3a75ea15d1
- D08 b155c5f2b3d2e0bb08c1bf5cb5d2f341a43db4b6
- D09 2e00dc70211988554e654d9c10fc448c5d884a77
- D10 529b55538e0aa51a2b5db4d65167ada2eeb0ca11
- D11 2849bbd82952f7f0c33914e47df92ad4e6f87c81
- D12 46994031fde3203ee64713721d3d655231a4750d
- D13 75fba01e9b6f5d1e1a6ddc51392db195aea3524d
- D14 e493d582bf05facc9f9f29c71bf20c92b694f24f
- D15 9be1c0e8ea43551b36ba12fb2fb7c7079b222f9f
- D16 77a9060b0df4bccbdd2e65a6006273c1ba42aab1
D15 includes D14 EPERM test and function; D16+ already contain EPERM, D17+ cleanup preview-only verified in source. Standalone new-head CI must be verified, historical cumulative results preserved. Actual base refs diverged; reconcile ancestry before formal merge. D05 actual host evidence NOT_RUN.
New offline dependency inventory in CI uses existing locked installs, no added network or dependency scripts; examines installed manifest/version, hidden npm lock, notice SHA256 and heuristic family, reports missing/ambiguous text for review. No legal compliance assertion or vulnerability audit. Full dependency notice and provenance review still BLOCKED. All 18 formal statuses remain BLOCKED; no model, permission expansion, production DB writes, data deletion or release.

Run status NOT_RUN at creation. Actual package license text family matching is heuristic; complete notice obligations and vulnerability/provenance reviews remain separate. No advisory queries or credential collection.


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
