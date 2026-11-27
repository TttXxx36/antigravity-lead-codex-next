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
