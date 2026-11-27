#!/usr/bin/env python3
"""PreToolUse hook for Antigravity Desktop:
- Auto-allows pure, unchained invocations of multi-agent-dispatch's dispatch.py.
- Forces user confirmation (`force_ask`) before merging/cherry-picking agy-worker/* branches.
- Returns `{}` (exit 0) for all other commands and malformed inputs (fail-safe).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sys

DISPATCH_SCRIPT = os.path.realpath(
    os.path.expanduser(
        "~/.gemini/config/skills/multi-agent-dispatch/scripts/dispatch.py"
    )
)
ALLOWED_SUBCOMMANDS = frozenset(
    {"health", "status", "run", "batch", "resume", "review", "cleanup"}
)
ALLOWED_PYTHON_BINS = frozenset(
    filter(
        None,
        {
            "python3",
            "/usr/bin/python3",
            "/opt/homebrew/bin/python3",
            os.path.expanduser("~/.local/bin/python3"),
            shutil.which("python3"),
        },
    )
)
FORBIDDEN_FRAGMENTS = (
    "--dangerously-bypass-approvals-and-sandbox",
    "danger-full-access",
)
NETWORK_FLAGS = frozenset({"--network"})
WORKER_MERGE_RE = re.compile(r"\bgit\b.*\b(?:merge|cherry-pick)\b.*agy-worker/")


def has_unsafe_shell_syntax(cmd: str) -> bool:
    """Return True if cmd contains shell chaining, redirection, subshells, or broken quotes."""
    in_single = False
    in_double = False
    escaped = False
    n = len(cmd)

    for idx, ch in enumerate(cmd):
        if escaped:
            escaped = False
            continue
        if in_single:
            if ch == "'":
                in_single = False
            continue
        if in_double:
            if ch == "\\":
                escaped = True
            elif ch == '"':
                in_double = False
            elif ch == "`":
                return True
            elif ch == "$" and idx + 1 < n and cmd[idx + 1] == "(":
                return True
            continue

        if ch == "\\":
            escaped = True
        elif ch == "'":
            in_single = True
        elif ch == '"':
            in_double = True
        elif ch in (";", "&", "|", "<", ">", "\n", "\r", "`"):
            return True
        elif ch == "$" and idx + 1 < n and cmd[idx + 1] == "(":
            return True

    return in_single or in_double or escaped


def _parse_pure_dispatch_argv(cmd: str) -> list[str] | None:
    # The parser below implements POSIX quoting, not cmd.exe/PowerShell.
    # Fail closed on Windows until shell-specific approval parsing is implemented.
    if os.name == "nt":
        return None
    if not cmd or has_unsafe_shell_syntax(cmd):
        return None
    try:
        argv = shlex.split(cmd, posix=True)
    except ValueError:
        return None

    if any(frag in arg for arg in argv for frag in FORBIDDEN_FRAGMENTS):
        return None

    if len(argv) >= 3 and argv[0] in ALLOWED_PYTHON_BINS:
        script_candidate = os.path.realpath(os.path.expanduser(argv[1]))
        if script_candidate == DISPATCH_SCRIPT and argv[2] in ALLOWED_SUBCOMMANDS:
            return argv

    if len(argv) >= 2:
        script_candidate = os.path.realpath(os.path.expanduser(argv[0]))
        if script_candidate == DISPATCH_SCRIPT and argv[1] in ALLOWED_SUBCOMMANDS:
            return argv

    return None


def _has_network_flag(argv: list[str]) -> bool:
    return any(
        arg in NETWORK_FLAGS or arg.startswith("--network=")
        for arg in argv
    )


def is_pure_dispatch_command(cmd: str) -> bool:
    argv = _parse_pure_dispatch_argv(cmd)
    if argv is None:
        return False
    return not _has_network_flag(argv)


DEFER_TO_STANDARD_APPROVAL = {
    "decision": "ask",
    "reason": "Non-dispatch command; deferring to standard approval.",
}


def evaluate_hook(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return DEFER_TO_STANDARD_APPROVAL
    tool_call = payload.get("toolCall")
    if not isinstance(tool_call, dict):
        return DEFER_TO_STANDARD_APPROVAL
    if tool_call.get("name") != "run_command":
        return DEFER_TO_STANDARD_APPROVAL

    args = tool_call.get("args")
    if not isinstance(args, dict):
        return DEFER_TO_STANDARD_APPROVAL
    cmd = args.get("CommandLine")
    if not isinstance(cmd, str) or not cmd.strip():
        return DEFER_TO_STANDARD_APPROVAL

    dispatch_argv = _parse_pure_dispatch_argv(cmd)
    if dispatch_argv is not None:
        if _has_network_flag(dispatch_argv):
            return {
                "decision": "force_ask",
                "reason": "Human network gate: confirm before granting Codex worker outbound network / authenticated CLI access (--network).",
            }
        return {
            "decision": "allow",
            "reason": "Auto-approved offline sandboxed multi-agent-dispatch CLI call.",
        }

    if WORKER_MERGE_RE.search(cmd):
        return {
            "decision": "force_ask",
            "reason": "Human merge gate: confirm before merging Codex worker branch (agy-worker/*).",
        }

    return DEFER_TO_STANDARD_APPROVAL


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        result = evaluate_hook(payload)
    except Exception:
        result = DEFER_TO_STANDARD_APPROVAL
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
