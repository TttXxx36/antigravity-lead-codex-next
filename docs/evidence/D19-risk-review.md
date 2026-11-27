# D19 — Risk-driven review evidence


## 2026-11-27 D19 candidate
Base 7fbc1b0ac2821a6a3a09806b829503ae72361a05; D18 exact-head cumulative Run 45985424111 PASS. Explicit local CLI orchestrator-risk-review --task-id --expected-revision --head --approve-git-checks; no unapproved checks or arbitrary project code. Fixed bounded Git commands compare full immutable recorded base and explicit HEAD commit, ancestry, raw diff modes/paths, patch digest and whitespace; external diff/textconv/hooks/fsmonitor/lazy fetch disabled, no network protocols. Recheck HEAD and orchestration CAS before publishing one bounded digest-linked receipt per task; retain original evidence, duplicate reads do not rerun. Conservative high risk for all non-allowlisted changes, structural changes, sensitive paths/content, unknown/empty/binary/oversize diff; only ordinary modifications to docs/user-guide or docs/tutorials may skip repetitive review when all fixed Git checks PASS. Worktree, project tests and independent review explicitly NOT_RUN; committed pair only, not proof of clean tree, task scope compliance or trusted independent review. D18 verifying never becomes completed or auto-merges; receipt tampering fails closed. No real models, permissions, arbitrary commands or merge. CI pending; formal trusted host/operator and independent review blocked.

CI NOT_RUN pending exact head verification.
