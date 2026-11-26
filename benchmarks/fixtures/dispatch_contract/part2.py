def execute_single_task(
    *,
    prompt: str,
    cwd: Path,
    backend: str,
    difficulty: str,
    model: str | None,
    effort: str | None,
    quality: str,
    alternate: bool | None,
    prefer_wide: bool,
    sandbox: str,
    network: bool = False,
    isolation: str,
    timeout: int,
    files_hint: list[str] | None,
    task_id: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    if not cwd.exists() or not cwd.is_dir():
        raise ValueError(f"Target cwd does not exist or is not a directory: {cwd}")
    if network and sandbox != "workspace-write":
        raise ValueError("--network requires --sandbox workspace-write.")

    git_info = inspect_git(cwd)
    eff_isolation, isolation_reason = resolve_isolation(isolation, sandbox, git_info)
    tid = task_id or make_task_id("run")

    if backend == "codex":
        codex_bin = get_codex_bin()
        if not codex_bin:
            raise RuntimeError("codex CLI not found")
        routing = resolve_model_and_effort(
            difficulty=difficulty,
            prompt=prompt,
            files_hint=files_hint,
            explicit_model=model,
            explicit_effort=effort,
            quality=quality,
            alternate=alternate,
            prefer_wide=prefer_wide,
        )
        model_used = routing["model"]
        effort_used = routing["effort"]
    else:
        raise RuntimeError(f"Unsupported backend: {backend}")

    run_dir = RUNS_DIR / tid
    report_path = run_dir / "last_message.json"
    worker_prompt = build_worker_prompt(prompt, sandbox=sandbox, network=network, is_resume=False, files_hint=files_hint)

    if dry_run:
        preview_workdir = (
            WORKTREES_DIR / (Path(git_info["repo_root"]).name if git_info["repo_root"] else "repo") / tid
            if eff_isolation == "worktree"
            else cwd
        )
        preview_cmd = build_codex_exec_cmd(
            codex_bin=get_codex_bin() or "codex",
            workdir=preview_workdir,
            model=model_used,
            effort=effort_used,
            sandbox=sandbox,
            network=network,
            report_path=report_path,
            is_git_repo=git_info["is_git_repo"],
        )
        return {
            "dry_run": True,
            "task_id": tid,
            "backend": backend,
            "routing": routing,
            "isolation": eff_isolation,
            "isolation_reason": isolation_reason,
            "sandbox": sandbox,
            "network": network,
            "git": git_info,
            "preview_workdir": str(preview_workdir),
            "command": preview_cmd,
        }

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(worker_prompt, encoding="utf-8")

    workdir = cwd
    worktree_path: str | None = None
    branch_name: str | None = None
    if eff_isolation == "worktree":
        wt, br = create_worktree(git_info["repo_root"], tid, git_info["head_sha"])
        workdir = wt
        worktree_path = str(wt)
        branch_name = br

    cmd = build_codex_exec_cmd(
        codex_bin=get_codex_bin(),  # type: ignore[arg-type]
        workdir=workdir,
        model=model_used,
        effort=effort_used,
        sandbox=sandbox,
        network=network,
        report_path=report_path,
        is_git_repo=git_info["is_git_repo"],
    )
    rc, stdout_text, stderr_text, timed_out = run_subprocess_with_timeout(
        cmd, cwd=workdir, stdin_text=worker_prompt, timeout=timeout
    )
    (run_dir / "events.jsonl").write_text(stdout_text, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")
    parsed_events = parse_codex_events(stdout_text)
    report = parse_report_file(
        report_path,
        parsed_events["last_agent_text"],
        stderr_text,
        rc,
        event_errors=parsed_events["errors"],
    )
    session_id = parsed_events["session_id"]
    usage = parsed_events["usage"]

    git_truth = collect_git_truth(workdir, git_info["head_sha"])
    now = utc_now()
    final_status = "timed_out" if timed_out else report.get("status", "completed" if rc == 0 else "failed")

    task_record = {
        "task_id": tid,
        "backend": backend,
        "model": model_used,
        "effort": effort_used,
        "difficulty": routing["effective_difficulty"],
        "repo_root": git_info["repo_root"],
        "is_git_repo": git_info["is_git_repo"],
        "base_sha": git_info["head_sha"],
        "original_cwd": str(cwd),
        "workdir": str(workdir),
        "worktree_path": worktree_path,
        "branch": branch_name,
        "isolation": eff_isolation,
        "sandbox": sandbox,
        "network": network,
        "session_id": session_id,
        "status": final_status,
        "exit_code": rc,
        "created_at": now,
        "updated_at": now,
        "run_dir": str(run_dir),
    }

    with locked_state() as state:
        state["tasks"][tid] = task_record

    result = {
        "task_id": tid,
        "backend": backend,
        "model_used": model_used,
        "effort_used": effort_used,
        "routing": routing,
        "isolation": eff_isolation,
        "isolation_reason": isolation_reason,
        "sandbox": sandbox,
        "network": network,
        "workdir": str(workdir),
        "branch": branch_name,
        "session_id": session_id,
        "exit_code": rc,
        "timed_out": timed_out,
        "usage": usage,
        "report": report,
        "git_truth": git_truth,
        "run_dir": str(run_dir),
    }
    (run_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result

def cmd_resume(args: argparse.Namespace) -> int:
    prompt_text = sys.stdin.read() if args.prompt == "-" else args.prompt
    task_record: dict[str, Any] | None = None
    if args.task_id:
        with locked_state() as state:
            task_record = state["tasks"].get(args.task_id)
        if not task_record:
            raise ValueError(f"Unknown task_id: {args.task_id}")

    backend = args.backend or (task_record["backend"] if task_record else "codex")
    session_id = args.session_id or (task_record["session_id"] if task_record else None)
    if not session_id:
        raise ValueError("No session_id available to resume (pass --session-id or valid --task-id).")

    workdir = Path(args.cwd or (task_record["workdir"] if task_record else ".")).resolve()
    if not workdir.exists():
        raise ValueError(f"Workdir does not exist: {workdir}")

    sandbox = args.sandbox or (task_record["sandbox"] if task_record else "workspace-write")
    network = args.network if args.network is not None else bool(task_record.get("network", False) if task_record else False)
    if network and sandbox != "workspace-write":
        raise ValueError("--network requires --sandbox workspace-write.")
    base_sha = task_record.get("base_sha") if task_record else None
    git_info = inspect_git(workdir)

    if backend == "codex":
        codex_bin = get_codex_bin()
        if not codex_bin:
            raise RuntimeError("codex CLI not found")
        if args.model or args.effort or args.difficulty != "auto" or args.prefer_wide or args.quality != "smart":
            routing = resolve_model_and_effort(
                difficulty=args.difficulty,
                prompt=prompt_text,
                explicit_model=args.model,
                explicit_effort=args.effort,
                quality=args.quality,
                alternate=args.alternate,
                prefer_wide=args.prefer_wide,
            )
            model_used = routing["model"]
            effort_used = routing["effort"]
        elif task_record:
            model_used = task_record["model"]
            effort_used = task_record["effort"]
            routing = {
                "effective_difficulty": task_record.get("difficulty", "medium"),
                "quality_mode": args.quality,
                "model": model_used,
                "effort": effort_used,
                "route_note": "inherited model/effort from original task",
            }
        else:
            routing = resolve_model_and_effort(
                difficulty="auto",
                prompt=prompt_text,
                quality=args.quality,
                alternate=args.alternate,
                prefer_wide=args.prefer_wide,
            )
            model_used = routing["model"]
            effort_used = routing["effort"]
    else:
        raise RuntimeError(f"Unsupported backend: {backend}")

    resume_tid = args.task_id or make_task_id("resume")
    turn_id = make_task_id("turn")
    run_dir = RUNS_DIR / resume_tid / turn_id
    report_path = run_dir / "last_message.json"
    worker_prompt = build_worker_prompt(prompt_text, sandbox=sandbox, network=network, is_resume=True)

    if args.dry_run:
        preview_cmd = build_codex_resume_cmd(
            codex_bin=get_codex_bin() or "codex",
            session_id=session_id,
            model=model_used,
            effort=effort_used,
            sandbox=sandbox,
            network=network,
            report_path=report_path,
            is_git_repo=git_info["is_git_repo"],
        )
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "task_id": resume_tid,
                    "backend": backend,
                    "session_id": session_id,
                    "workdir": str(workdir),
                    "network": network,
                    "routing": routing,
                    "command": preview_cmd,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(worker_prompt, encoding="utf-8")

    cmd = build_codex_resume_cmd(
        codex_bin=get_codex_bin(),  # type: ignore[arg-type]
        session_id=session_id,
        model=model_used,
        effort=effort_used,
        sandbox=sandbox,
        network=network,
        report_path=report_path,
        is_git_repo=git_info["is_git_repo"],
    )
    rc, stdout_text, stderr_text, timed_out = run_subprocess_with_timeout(
        cmd, cwd=workdir, stdin_text=worker_prompt, timeout=args.timeout
    )
    (run_dir / "events.jsonl").write_text(stdout_text, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")
    parsed_events = parse_codex_events(stdout_text)
    report = parse_report_file(
        report_path,
        parsed_events["last_agent_text"],
        stderr_text,
        rc,
        event_errors=parsed_events["errors"],
    )
    new_session_id = parsed_events["session_id"] or session_id
    usage = parsed_events["usage"]

    git_truth = collect_git_truth(workdir, base_sha)
    if task_record:
        with locked_state() as state:
            if resume_tid in state["tasks"]:
                state["tasks"][resume_tid]["model"] = model_used
                state["tasks"][resume_tid]["effort"] = effort_used
                state["tasks"][resume_tid]["sandbox"] = sandbox
                state["tasks"][resume_tid]["network"] = network
                state["tasks"][resume_tid]["session_id"] = new_session_id
                state["tasks"][resume_tid]["status"] = (
                    "timed_out" if timed_out else report.get("status", "completed" if rc == 0 else "failed")
                )
                state["tasks"][resume_tid]["updated_at"] = utc_now()

    result = {
        "task_id": resume_tid,
        "turn_id": turn_id,
        "backend": backend,
        "model_used": model_used,
        "effort_used": effort_used,
        "routing": routing,
        "sandbox": sandbox,
        "network": network,
        "workdir": str(workdir),
        "session_id": new_session_id,
        "exit_code": rc,
        "timed_out": timed_out,
        "usage": usage,
        "report": report,
        "git_truth": git_truth,
        "run_dir": str(run_dir),
    }
    (run_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if rc == 0 else 1
