# Windows CI repair candidate — independent from original baseline

User requested investigation and repair of failing Windows Actions tests. Original D01 head 4aa954211c4cc9c44da4c7cc67d7562e6fb94b52, [Run 45915363640](https://github.com/TttXxx36/antigravity-lead-codex-next/actions/runs/45915363640), remains unchanged. Linux and macOS all six checks passed; Windows source hashes and harness passed, full dispatcher and upstream-mock returned exit 1, original Python tests exit 5, original Bash MCP test NOT_RUN. Downloaded Windows artifact confirms 40/40 harness, 20/20 native Node MCP samples, 30/30 dispatcher samples NOT_RUN (ModuleNotFoundError) in each dispatcher suite. Upstream dispatch imports fcntl unconditionally; Windows does not provide it. Original unit-test setUpClass imports that module, so no tests can run. Windows Bash launcher was deliberately skipped in baseline. These are genuine baseline results, not infrastructure errors.

Candidate only:
- OS-backed Windows byte-range lock (msvcrt) and POSIX flock, bounded Windows contention retry, release on exceptions, no replacement of lock file. UTF-8 subprocess text for Git/Codex.
- POSIX-only shell approval parser fails closed on Windows; standard human approval remains required. No new Windows auto-approval. Full shell-specific hook design belongs to D06.
- Node PATH uses path.delimiter. Native Node MCP integration test runs without Bash and targets a non-Codex executable; shutdown precedes temp cleanup.
- Four-process lock contention test (60 updates) and release-on-exception regression.
- Candidate-only source hashes, result label, full-module regression workflow and actual per-platform artifact; original D01 baseline hashes/results not overwritten. Do not merge candidate into D01 if retaining the original source baseline; separately review how to integrate into D03/D04/D05/D06. No real model calls, no automatic merge.

This addresses observed CI failure paths; Windows install/actual Codex and Antigravity host integration, unrelated state corruption and report correctness defects remain outside this targeted repair. Actions validation pending at commit time.
