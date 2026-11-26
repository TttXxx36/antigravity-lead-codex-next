# Fixed upstream dispatcher excerpts (baseline only)

Copyright (c) 2026 Koala973. Original MIT license: [LICENSE.upstream](../../../LICENSE.upstream). Source: https://github.com/Koala973/antigravity-lead-codex/blob/b6c36443e5a134ea36aa18dc171f312fdd54b5bc/skills/multi-agent-dispatch/scripts/dispatch.py (full Blob 2057553f544c0ef605eb2c9ad8ae0f8fb59df84a).

These three fixtures contain 20 original function definitions, not a complete module. They were copied from the fixed source in function groups, with original function bodies preserved, joining functions by one blank line and retaining the contextmanager decorator. They are intentionally executable only through the explicit excerpt-mode test loader, which injects imports, paths, and mock routing/CLI. Never use these fixtures as production or as proof that the full module was tested.

| Fixture | Git Blob SHA | Functions |
|---|---|---|
| part0.py | 71ceae90ea5a4b5df6079813533ae123eba7f7d3 | utc_now, ensure_state_dirs, locked_state, find_binary, get_git_bin, make_task_id, inspect_git, resolve_isolation, create_worktree, cap_lines, collect_git_truth, build_worker_prompt |
| part1.py | 954c03bf4c26766cd5fde98df0985b5e70b4778c | build_codex_exec_cmd, build_codex_resume_cmd, extract_session_id_from_obj, run_subprocess_with_timeout, parse_codex_events, parse_report_file |
| part2.py | d3cd17225d860441aa1b8ac10b021b699e9d1808 | execute_single_task, cmd_resume |

Do not modify or format these files. Preserve LF line endings to reproduce strict Git Blob hashes. No real model invocation, user data, or private credentials are included.
