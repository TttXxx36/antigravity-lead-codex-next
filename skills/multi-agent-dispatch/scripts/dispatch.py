#!/usr/bin/env python3
"""Local multi-agent dispatcher for Antigravity (Brain) -> Codex CLI (Hand).

Dynamically discovers the newest official Codex frontier models from models_cache.json,
defaults to smart quality+quota (--quality smart) routing across flagship and wide_fast
models (with --quality max and --quality balanced overrides), manages isolated Git
worktrees, enforces safe headless sandbox overrides, and returns compact structured
JSON summaries to preserve Antigravity context quota.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import hashlib
import json
import os
import ntpath
import re
import shutil
import subprocess
import sys
import signal
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_DIR / "resources" / "report_schema.json"

# Shared platform rules: mirrored by server/platform.mjs.
_WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$", re.I)


def validate_windows_path(value: str) -> None:
    """Reject device namespaces, ADS, reserved names and ambiguous trailing dots/spaces."""
    raw = value.replace("/", "\\")
    if raw.startswith(("\\\\?\\", "\\\\.\\")):
        raise ValueError("Windows device namespace paths are not supported")
    _, rest = ntpath.splitdrive(raw)
    for part in rest.split("\\"):
        if not part or part in (".", ".."):
            continue
        if part.endswith((" ", ".")) or any(c in '<>:"|?*' or ord(c) < 32 for c in part):
            raise ValueError("Invalid Windows path component")
        if _WINDOWS_RESERVED.fullmatch(part.split(".", 1)[0].rstrip(" ")):
            raise ValueError("Reserved Windows path component")


def configured_path(value: str | Path, *, windows: bool | None = None) -> Path:
    raw = os.path.expanduser(str(value))
    if not raw or "\x00" in raw:
        raise ValueError("Invalid empty/NUL path")
    if windows if windows is not None else os.name == "nt":
        validate_windows_path(raw)
    return Path(os.path.abspath(raw))


def environment_path(name: str, default: Path) -> Path:
    return configured_path(os.environ.get(name) or default)


CODEX_HOME = environment_path("CODEX_HOME", Path.home() / ".codex")
GEMINI_CONFIG_DIR = environment_path("GEMINI_CONFIG_DIR", Path.home() / ".gemini" / "config")
STATE_DIR = environment_path("AGY_DISPATCH_STATE_DIR", Path.home() / ".local" / "state" / "multi-agent-dispatch")
STATE_FILE = STATE_DIR / "state.json"
LOCK_FILE = STATE_DIR / "state.lock"
RUNS_DIR = STATE_DIR / "runs"
WORKTREES_DIR = STATE_DIR / "worktrees"

BUNDLED_CODEX_BIN = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
MODELS_CACHE_PATHS = (
    CODEX_HOME / "models_cache.json",
    CODEX_HOME / "models_cache.codex_work_desktop.json",
)

VALID_DIFFICULTIES = ("auto", "low", "medium", "hard", "extreme")
VALID_QUALITIES = ("smart", "max", "balanced")
VALID_BACKENDS = ("codex",)
VALID_SANDBOXES = ("read-only", "workspace-write")
VALID_ISOLATIONS = ("auto", "worktree", "inplace")

EXTREME_KEYWORDS = (
    "architecture redesign",
    "system redesign",
    "distributed",
    "zero-downtime",
    "security audit",
    "race condition",
    "deadlock",
    "full rewrite",
    "end-to-end architecture",
    "架构重设计",
    "架构重构",
    "全链路",
    "安全审计",
    "死锁",
    "分布式",
)
HARD_KEYWORDS = (
    "refactor",
    "debug",
    "diagnose",
    "optimize",
    "algorithm",
    "concurrency",
    "async",
    "state machine",
    "compiler",
    "parser",
    "migration",
    "database",
    "schema",
    "multi-module",
    "cross-module",
    "performance",
    "root cause",
    "重构",
    "排查",
    "根因",
    "并发",
    "异步",
    "状态机",
    "复杂",
    "算法",
    "性能优化",
    "跨模块",
    "迁移",
)
LOW_KEYWORDS = (
    "typo",
    "readme",
    "comment",
    "docstring",
    "rename",
    "format",
    "lint",
    "unit test",
    "single file",
    "boilerplate",
    "scaffold",
    "summarize",
    "summary",
    "文档",
    "注释",
    "改名",
    "重命名",
    "单文件",
    "简单",
    "小修",
    "单元测试",
    "格式化",
    "总结",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_state_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (RUNS_DIR, WORKTREES_DIR):
        reject_link(folder)
        folder.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def exclusive_state_lock(lock_path: Path, timeout: float = 30.0) -> Iterator[None]:
    """Hold an OS-backed interprocess lock on a persistent lock file.

    Windows locks byte zero (a range may extend beyond EOF). Never truncate or
    replace the lock file, and release only a lock that was acquired.
    """
    with lock_path.open("a+b") as lock_fh:
        if os.name == "nt":
            deadline = time.monotonic() + timeout
            while True:
                lock_fh.seek(0)
                try:
                    msvcrt.locking(lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK) and getattr(exc, "winerror", None) not in (33, 36):
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Timed out acquiring dispatcher state lock") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                lock_fh.seek(0)
                msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Timed out acquiring dispatcher state lock") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


class StateIntegrityError(RuntimeError):
    """State is unreadable or inconsistent; never replace it implicitly."""


def reject_link(p: Path) -> None:
    if p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()):
        raise StateIntegrityError(f"Refusing linked state path: {p}")


def atomic_write_bytes(target: Path, payload: bytes) -> None:
    """Same-directory fsynced temporary file; bounded retry for Windows sharing."""
    reject_link(target)
    fd, name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(10):
            try:
                os.replace(temp, target)
                break
            except PermissionError:
                if os.name != "nt" or attempt == 9:
                    raise
                time.sleep(0.05)
        if os.name != "nt":
            dirfd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
    finally:
        temp.unlink(missing_ok=True)


def decode_state(raw: bytes) -> dict[str, Any]:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate state JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("Non-finite state JSON number")

    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys, parse_constant=reject_constant)
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), dict):
        raise ValueError("state must contain a tasks object")
    rr = data.get("rr_counter", 0)
    if type(rr) is not int or rr < 0:
        raise ValueError("invalid rr_counter")
    if any(not isinstance(record, dict) for record in data["tasks"].values()):
        raise ValueError("invalid task record")
    data.setdefault("rr_counter", 0)
    return data


def preserve_corrupt_state(raw: bytes) -> Path:
    target = STATE_FILE.with_name("state.corrupt-" + hashlib.sha256(raw).hexdigest() + ".json")
    reject_link(target)
    if target.exists():
        if target.read_bytes() != raw:
            raise StateIntegrityError("Corrupt backup checksum collision; original untouched")
    else:
        atomic_write_bytes(target, raw)
    return target


@contextlib.contextmanager
def locked_state() -> Iterator[dict[str, Any]]:
    """Serialize read/modify/write; never reset malformed existing state."""
    ensure_state_dirs()
    reject_link(LOCK_FILE)
    with exclusive_state_lock(LOCK_FILE):
        reject_link(STATE_FILE)
        raw = STATE_FILE.read_bytes() if STATE_FILE.exists() else None
        if raw is None:
            data = {"rr_counter": 0, "tasks": {}}
        else:
            try:
                data = decode_state(raw)
            except (ValueError, UnicodeError) as exc:
                backup = preserve_corrupt_state(raw)
                raise StateIntegrityError(f"Invalid dispatcher state; original untouched; copy: {backup}") from exc
        snapshot = json.dumps(data, sort_keys=True)
        yield data
        if json.dumps(data, sort_keys=True) != snapshot or raw is None:
            payload = (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
            decode_state(payload)
            if raw is not None:
                atomic_write_bytes(STATE_FILE.with_suffix(".json.bak"), raw)
            atomic_write_bytes(STATE_FILE, payload)


def validate_task_id(value: str) -> str:
    """Portable path and Git ref component; forbid case-ambiguous and reserved forms."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value):
        raise ValueError("Invalid task_id: expected 1–80 ASCII letters/digits/dot/underscore/hyphen")
    if ".." in value or value.endswith(".") or value.lower().endswith(".lock"):
        raise ValueError("Invalid task_id component")
    validate_windows_path(value)
    return value


def bounded_child(root: Path, *parts: str) -> Path:
    """Check all components under a trusted configured root, including symlinks/junctions."""
    reject_link(root)
    candidate = root.joinpath(*parts)
    if not candidate.resolve().is_relative_to(root.resolve()) or candidate == root:
        raise ValueError("Path escapes configured state root")
    current = root
    for part in parts:
        validate_task_id(part)
        current = current / part
        reject_link(current)
    return candidate


def reserve_run_dir(task_id: str, record: dict[str, Any] | None = None) -> Path:
    """Atomically reserve ID under lock; orphaned directories are never reused."""
    tid = validate_task_id(task_id)
    with locked_state() as state:
        run_dir = bounded_child(RUNS_DIR, tid)
        if any(key.casefold() == tid.casefold() for key in state["tasks"]):
            raise ValueError("Duplicate task_id")
        if any(p.name.casefold() == tid.casefold() for p in RUNS_DIR.iterdir()):
            raise ValueError("Duplicate or orphaned run directory")
        run_dir.mkdir(exist_ok=False)
        if record is not None:
            state["tasks"][tid] = {**record, "task_id": tid, "run_dir": str(run_dir), "status": "reserved"}
    return run_dir


def native_executable(value: str | Path) -> str | None:
    """Resolve an existing executable; Windows accepts .exe, never .cmd/.bat."""
    try:
        p = configured_path(value)
        if os.name == "nt" and p.suffix.lower() != ".exe":
            return None
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    except (OSError, ValueError):
        pass
    return None


def binary_candidates(name: str, fallbacks: tuple[str, ...] = (), override: str | None = None) -> list[str]:
    if override and os.environ.get(override):
        explicit = native_executable(os.environ[override])
        return [explicit] if explicit else []
    leaf = name + ".exe" if os.name == "nt" else name
    # Do not implicitly search cwd or relative PATH entries.
    raw = [str(Path(p.strip('"')) / leaf) for p in os.environ.get("PATH", "").split(os.pathsep)
           if p and Path(p.strip('"')).is_absolute()]
    if os.name != "nt":
        raw.extend(fallbacks)
    results = []
    seen = set()
    for candidate in raw:
        resolved = native_executable(candidate)
        if resolved:
            key = os.path.normcase(os.path.realpath(resolved))
            if key not in seen:
                seen.add(key)
                results.append(resolved)
    return results


def find_binary(name: str, fallbacks: tuple[str, ...] = (), override: str | None = None) -> str | None:
    values = binary_candidates(name, fallbacks, override)
    return values[0] if values else None


CODEX_FALLBACKS = (BUNDLED_CODEX_BIN, "~/.local/bin/codex", "~/.npm-global/bin/codex",
                   "~/.volta/bin/codex", "/opt/homebrew/bin/codex", "/usr/local/bin/codex")


def parse_codex_semver(version_text: str | None) -> tuple[int, int, int, int, int]:
    """Parse 'codex-cli 0.171.0-alpha.13' into a sortable tuple where stable > prerelease."""
    if not version_text:
        return (-1, 0, 0, 0, 0)
    match = re.search(r"(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z0-9.]+))?", version_text)
    if not match:
        return (-1, 0, 0, 0, 0)
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    pre = match.group(4)
    if not pre:
        return (major, minor, patch, 1, 0)
    pre_nums = re.findall(r"\d+", pre)
    pre_patch = int(pre_nums[-1]) if pre_nums else 0
    return (major, minor, patch, 0, pre_patch)


def list_codex_candidates() -> list[dict[str, Any]]:
    """Health diagnostics only; actual selection follows explicit/PATH priority."""
    return [{"bin": candidate, "version": probe_version([candidate, "--version"])}
            for candidate in binary_candidates("codex", CODEX_FALLBACKS, "CODEX_BIN")]


def get_codex_bin() -> str | None:
    return find_binary("codex", CODEX_FALLBACKS, "CODEX_BIN")


def get_node_bin() -> str | None:
    return find_binary("node", ("~/.local/bin/node", "/opt/homebrew/bin/node", "/usr/local/bin/node"), "NODE_BIN")


def get_git_bin() -> str | None:
    return find_binary("git", ("/usr/bin/git", "/opt/homebrew/bin/git", "/usr/local/bin/git"), "GIT_BIN")


def probe_version(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (proc.stdout or proc.stderr or "").strip()
    return output.splitlines()[0] if output else None


def extract_model_generation(slug: str) -> tuple[int, int]:
    """Extract numeric generation tuple (major, minor) from model slug."""
    match = re.search(r"(\d+)(?:\.(\d+))?", slug)
    if not match:
        return (-1, -1)
    return (int(match.group(1)), int(match.group(2)) if match.group(2) else 0)


def normalize_cached_model(entry: dict[str, Any]) -> dict[str, Any] | None:
    slug = entry.get("slug") or entry.get("id")
    if not isinstance(slug, str) or not slug.strip():
        return None
    if entry.get("visibility") != "list" or entry.get("supported_in_api") is False:
        return None
    raw_levels = entry.get("supported_reasoning_levels")
    efforts: list[str] = []
    if isinstance(raw_levels, list):
        for lvl in raw_levels:
            if isinstance(lvl, dict) and isinstance(lvl.get("effort"), str) and lvl["effort"].strip():
                efforts.append(lvl["effort"].strip())
    priority = entry.get("priority")
    context_window = entry.get("context_window")
    return {
        "slug": slug.strip(),
        "gen": extract_model_generation(slug),
        "priority": priority if isinstance(priority, int) else 9999,
        "context_window": context_window if isinstance(context_window, int) else 0,
        "description": str(entry.get("description") or ""),
        "default_reasoning_level": entry.get("default_reasoning_level"),
        "supported_efforts": efforts,
    }


def pick_frontier_roles(listed_models: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Pick newest-generation flagship (highest capability) and wide_fast (largest context) siblings."""
    if not listed_models:
        return None, None
    ranked = sorted(
        listed_models,
        key=lambda m: (-m["gen"][0], -m["gen"][1], m["priority"], m["slug"]),
    )
    top_gen = ranked[0]["gen"]
    top_candidates = ranked[:3] if top_gen == (-1, -1) else [m for m in ranked if m["gen"] == top_gen]

    def _flagship_rank(m: dict[str, Any]) -> tuple[int, int, int, int]:
        desc = m["description"].lower()
        slug_l = m["slug"].lower()
        if "most capable" in desc or "complex" in desc:
            tier = 0
        elif any(tok in slug_l for tok in ("astra", "pro", "max")):
            tier = 1
        else:
            tier = 2
        return (tier, m["priority"], -m["context_window"], 0)

    flagship = min(top_candidates, key=_flagship_rank)
    siblings = [m for m in top_candidates if m["slug"] != flagship["slug"]]
    if not siblings:
        return flagship, flagship

    def _wide_rank(m: dict[str, Any]) -> tuple[int, int, int]:
        combined = f"{m['slug']} {m['description']}".lower()
        fast_hint = 0 if any(tok in combined for tok in ("go-to", "fast", "sol", "mini", "flash")) else 1
        return (-m["context_window"], fast_hint, m["priority"])

    wide_fast = min(siblings, key=_wide_rank)
    return flagship, wide_fast


def discover_frontier_models() -> dict[str, Any]:
    """Read live Codex models cache and dynamically resolve flagship & wide_fast models."""
    override = os.environ.get("AGY_MODELS_CACHE_FILE")
    candidate_paths = (Path(os.path.expanduser(override)),) if override else MODELS_CACHE_PATHS

    best: dict[str, Any] | None = None
    best_score = (-1, (-2, 0, 0, 0, 0))
    for cache_path in candidate_paths:
        if not cache_path.exists():
            continue
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        client_ver = raw.get("client_version") if isinstance(raw, dict) else None
        raw_models = raw.get("models", raw) if isinstance(raw, dict) else raw
        listed: list[dict[str, Any]] = []
        if isinstance(raw_models, list):
            for entry in raw_models:
                if isinstance(entry, dict):
                    norm = normalize_cached_model(entry)
                    if norm:
                        listed.append(norm)
        score = (len(listed), parse_codex_semver(client_ver))
        if best is None or score > best_score:
            best_score = score
            flagship, wide_fast = pick_frontier_roles(listed)
            best = {
                "exists": True,
                "source_file": str(cache_path),
                "client_version": client_ver,
                "flagship": flagship,
                "wide_fast": wide_fast,
                "listed_models": listed,
                "listed_slugs": [m["slug"] for m in sorted(listed, key=lambda x: (-x["gen"][0], -x["gen"][1], x["priority"]))],
            }

    if best is None:
        return {
            "exists": False,
            "source_file": None,
            "client_version": None,
            "flagship": None,
            "wide_fast": None,
            "listed_models": [],
            "listed_slugs": [],
        }
    return best


def pick_supported_effort(preferred_chain: tuple[str, ...], supported_efforts: list[str]) -> str:
    if not supported_efforts:
        return preferred_chain[0]
    for eff in preferred_chain:
        if eff in supported_efforts:
            return eff
    return supported_efforts[-1]


def classify_difficulty(prompt: str, files_hint: list[str] | None = None) -> tuple[str, str]:
    """Deterministically classify task difficulty from prompt text and file hints."""
    text = prompt.lower()
    files_count = len(files_hint or [])

    if any(kw in text for kw in EXTREME_KEYWORDS):
        return "extreme", "matched extreme-tier architectural/concurrency/audit keyword"
    if any(kw in text for kw in HARD_KEYWORDS) or files_count >= 5:
        reason = (
            "matched hard-tier complexity keyword"
            if any(kw in text for kw in HARD_KEYWORDS)
            else f"broad scope ({files_count} target files)"
        )
        return "hard", reason
    if (any(kw in text for kw in LOW_KEYWORDS) or len(prompt.strip()) <= 140) and files_count <= 2:
        if any(kw in text for kw in LOW_KEYWORDS):
            return "low", "matched low-tier routine/doc/test keyword"
        if len(prompt.strip()) <= 140:
            return "low", "short localized prompt (<=140 chars)"
    return "medium", "default medium-tier implementation scope"


def resolve_model_and_effort(
    *,
    difficulty: str,
    prompt: str,
    files_hint: list[str] | None = None,
    explicit_model: str | None = None,
    explicit_effort: str | None = None,
    quality: str = "smart",
    alternate: bool | None = None,
    prefer_wide: bool = False,
) -> dict[str, Any]:
    """Dynamically route across newest official Codex models by quality mode & difficulty."""
    if difficulty == "auto":
        effective_difficulty, difficulty_reason = classify_difficulty(prompt, files_hint)
    else:
        effective_difficulty = difficulty
        difficulty_reason = f"explicit difficulty={difficulty}"

    use_alternate = (quality in ("smart", "balanced")) if alternate is None else alternate
    frontier = discover_frontier_models()
    flagship = frontier["flagship"]
    wide_fast = frontier["wide_fast"]
    flagship_slug = flagship["slug"] if flagship else None
    wide_slug = wide_fast["slug"] if wide_fast else None

    flagship_ctx = flagship["context_window"] if flagship else 0
    wide_ctx = wide_fast["context_window"] if wide_fast else 0
    wide_auto = (
        difficulty == "auto"
        and len(files_hint or []) >= 10
        and wide_fast is not None
        and wide_ctx > flagship_ctx
    )
    use_wide = prefer_wide or wide_auto

    rr_slot: int | None = None
    target_meta: dict[str, Any] | None
    if quality == "smart":
        if effective_difficulty == "low":
            target_meta = wide_fast or flagship
            effort_chain = ("medium", "high", "low")
            role_label = "wide_fast"
        elif effective_difficulty == "medium":
            if use_wide and wide_fast:
                target_meta = wide_fast
                effort_chain = ("high", "xhigh", "medium")
                role_label = "wide_fast (prefer-wide)"
            elif use_alternate and not explicit_model and flagship and wide_fast and flagship_slug != wide_slug:
                with locked_state() as state:
                    rr_slot = int(state.get("rr_counter", 0))
                    state["rr_counter"] = rr_slot + 1
                if rr_slot % 2 == 0:
                    target_meta = wide_fast
                    effort_chain = ("high", "xhigh", "medium")
                    role_label = f"wide_fast (smart slot {rr_slot})"
                else:
                    target_meta = flagship
                    effort_chain = ("high", "xhigh", "medium")
                    role_label = f"flagship (smart slot {rr_slot})"
            else:
                target_meta = flagship or wide_fast
                effort_chain = ("high", "xhigh", "medium")
                role_label = "flagship"
        elif effective_difficulty == "hard":
            target_meta = wide_fast if (use_wide and wide_fast) else flagship
            effort_chain = ("xhigh", "max", "high")
            role_label = "wide_fast" if (use_wide and wide_fast) else "flagship"
        else:
            target_meta = wide_fast if (use_wide and wide_fast) else flagship
            effort_chain = ("max", "ultra", "xhigh", "high")
            role_label = "wide_fast" if (use_wide and wide_fast) else "flagship"
    elif quality == "max":
        if effective_difficulty == "low":
            target_meta = wide_fast if (use_wide and wide_fast) else flagship
            effort_chain = ("high", "xhigh", "medium")
            role_label = "wide_fast" if (use_wide and wide_fast) else "flagship"
        elif effective_difficulty == "medium":
            if use_wide and wide_fast:
                target_meta = wide_fast
                effort_chain = ("max", "xhigh", "high")
                role_label = "wide_fast (prefer-wide)"
            elif use_alternate and not explicit_model and flagship and wide_fast and flagship_slug != wide_slug:
                with locked_state() as state:
                    rr_slot = int(state.get("rr_counter", 0))
                    state["rr_counter"] = rr_slot + 1
                if rr_slot % 2 == 0:
                    target_meta = flagship
                    effort_chain = ("xhigh", "max", "high")
                    role_label = f"flagship (max-alt slot {rr_slot})"
                else:
                    target_meta = wide_fast
                    effort_chain = ("max", "xhigh", "high")
                    role_label = f"wide_fast (max-alt slot {rr_slot})"
            else:
                target_meta = flagship
                effort_chain = ("xhigh", "max", "high")
                role_label = "flagship"
        elif effective_difficulty == "hard":
            target_meta = wide_fast if (use_wide and wide_fast) else flagship
            effort_chain = ("max", "xhigh", "high")
            role_label = "wide_fast" if (use_wide and wide_fast) else "flagship"
        else:
            target_meta = wide_fast if (use_wide and wide_fast) else flagship
            effort_chain = ("ultra", "max", "xhigh", "high")
            role_label = "wide_fast" if (use_wide and wide_fast) else "flagship"
    else:
        if effective_difficulty == "low":
            target_meta = wide_fast or flagship
            effort_chain = ("medium", "high", "low")
            role_label = "wide_fast"
        elif effective_difficulty == "medium":
            if use_alternate and not explicit_model and flagship and wide_fast and flagship_slug != wide_slug:
                with locked_state() as state:
                    rr_slot = int(state.get("rr_counter", 0))
                    state["rr_counter"] = rr_slot + 1
                if rr_slot % 2 == 0:
                    target_meta = wide_fast
                    effort_chain = ("high", "medium")
                    role_label = f"wide_fast (balanced slot {rr_slot})"
                else:
                    target_meta = flagship
                    effort_chain = ("medium", "high")
                    role_label = f"flagship (balanced slot {rr_slot})"
            else:
                target_meta = wide_fast or flagship
                effort_chain = ("high", "medium")
                role_label = "wide_fast"
        elif effective_difficulty == "hard":
            target_meta = flagship
            effort_chain = ("high", "xhigh", "medium")
            role_label = "flagship"
        else:
            target_meta = flagship
            effort_chain = ("xhigh", "max", "high")
            role_label = "flagship"

    routed_model = target_meta["slug"] if target_meta else None
    final_model = explicit_model or routed_model

    if explicit_effort:
        final_effort = explicit_effort
    else:
        matched_meta = next(
            (m for m in frontier["listed_models"] if m["slug"] == final_model),
            target_meta,
        )
        supported_effs = matched_meta["supported_efforts"] if matched_meta else []
        final_effort = pick_supported_effort(effort_chain, supported_effs)

    model_label = final_model or "codex-cli-default"
    route_note = (
        f"quality={quality}, difficulty={effective_difficulty} -> "
        f"{'explicit override' if explicit_model else role_label}: {model_label} (effort={final_effort})"
    )
    return {
        "requested_difficulty": difficulty,
        "effective_difficulty": effective_difficulty,
        "difficulty_reason": difficulty_reason,
        "quality_mode": quality,
        "prefer_wide": use_wide,
        "model": final_model,
        "effort": final_effort,
        "rr_slot": rr_slot,
        "cache_client_version": frontier["client_version"],
        "discovered_flagship": flagship_slug,
        "discovered_wide_fast": wide_slug,
        "route_note": route_note,
    }


def inspect_git(workdir: Path) -> dict[str, Any]:
    git_bin = get_git_bin()
    if not git_bin:
        return {"is_git_repo": False, "repo_root": None, "head_sha": None, "branch": None}

    top = subprocess.run(
        [git_bin, "-C", str(workdir), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    if top.returncode != 0:
        return {"is_git_repo": False, "repo_root": None, "head_sha": None, "branch": None}

    repo_root = Path(top.stdout.strip()).resolve()
    head = subprocess.run(
        [git_bin, "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    head_sha = head.stdout.strip() if head.returncode == 0 else None

    branch_proc = subprocess.run(
        [git_bin, "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else None
    return {
        "is_git_repo": True,
        "repo_root": str(repo_root),
        "head_sha": head_sha,
        "branch": branch,
    }


def resolve_isolation(
    requested_isolation: str,
    sandbox: str,
    git_info: dict[str, Any],
) -> tuple[str, str]:
    """Determine effective isolation ('worktree' vs 'inplace') with safe fallbacks."""
    is_git = git_info["is_git_repo"]
    has_head = bool(git_info["head_sha"])

    if requested_isolation == "inplace":
        return "inplace", "explicitly requested inplace execution"

    if requested_isolation == "worktree":
        if not is_git or not has_head:
            raise ValueError(
                "worktree isolation requires a Git repository with at least one commit (HEAD)."
            )
        return "worktree", "explicitly requested isolated Git worktree"

    if sandbox == "read-only":
        return "inplace", "auto isolation uses inplace for read-only sandbox"
    if not is_git or not has_head:
        return "inplace", "auto isolation fell back to inplace (non-Git or repo without HEAD commit)"
    return "worktree", "auto isolation selected isolated Git worktree for workspace-write"


def create_worktree(repo_root: str, task_id: str, base_sha: str) -> tuple[Path, str]:
    git_bin = get_git_bin()
    if not git_bin:
        raise RuntimeError("git executable not found")
    repo_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(repo_root).name).strip("-") or "repo"
    try:
        validate_task_id(repo_slug)
    except ValueError:
        repo_slug = "repo-" + hashlib.sha256(repo_root.encode("utf-8")).hexdigest()[:12]
    wt_path = bounded_child(WORKTREES_DIR, repo_slug, validate_task_id(task_id))
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    if wt_path.exists():
        raise ValueError("Worktree directory already exists")
    branch_name = f"agy-worker/{task_id}"
    proc = subprocess.run(
        [git_bin, "-C", repo_root, "worktree", "add", "-b", branch_name, str(wt_path), base_sha],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git worktree add failed: {(proc.stderr or proc.stdout).strip()}"
        )
    return wt_path, branch_name


def remove_worktree(
    repo_root: str,
    worktree_path: str | None,
    branch_name: str | None,
    *,
    delete_branch: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    git_bin = get_git_bin()
    if not git_bin:
        raise RuntimeError("git executable not found")
    details: dict[str, Any] = {"worktree_removed": False, "branch_deleted": False, "messages": []}

    if worktree_path and Path(worktree_path).exists():
        cmd = [git_bin, "-C", repo_root, "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(worktree_path)
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(
                f"git worktree remove failed: {(proc.stderr or proc.stdout).strip()}"
            )
        details["worktree_removed"] = True
        details["messages"].append(f"Removed worktree {worktree_path}")
    else:
        subprocess.run([git_bin, "-C", repo_root, "worktree", "prune"], capture_output=True, text=True, encoding="utf-8")
        details["messages"].append("Worktree directory already absent; ran git worktree prune")

    if delete_branch and branch_name:
        flag = "-D" if force else "-d"
        proc = subprocess.run(
            [git_bin, "-C", repo_root, "branch", flag, branch_name],
            capture_output=True,
            text=True, encoding="utf-8",
        )
        if proc.returncode != 0:
            details["messages"].append(
                f"Branch {branch_name} not deleted: {(proc.stderr or proc.stdout).strip()}"
            )
        else:
            details["branch_deleted"] = True
            details["messages"].append(f"Deleted branch {branch_name}")

    return details


def cap_lines(text: str, max_lines: int = 40) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    kept = lines[:max_lines]
    kept.append(f"... ({len(lines) - max_lines} more lines truncated)")
    return "\n".join(kept)


def collect_git_truth(workdir: Path, base_sha: str | None) -> dict[str, Any]:
    git_bin = get_git_bin()
    if not git_bin or not workdir.exists():
        return {"is_git": False}

    check = subprocess.run(
        [git_bin, "-C", str(workdir), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    if check.returncode != 0:
        return {"is_git": False}

    status_proc = subprocess.run(
        [git_bin, "-C", str(workdir), "status", "--short"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    head_proc = subprocess.run(
        [git_bin, "-C", str(workdir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    current_sha = head_proc.stdout.strip() if head_proc.returncode == 0 else None

    diff_cmd = [git_bin, "-C", str(workdir), "diff", "--stat"]
    if base_sha:
        diff_cmd.append(base_sha)
    diff_proc = subprocess.run(diff_cmd, capture_output=True, text=True, encoding="utf-8")

    return {
        "is_git": True,
        "head_sha": current_sha,
        "base_sha": base_sha,
        "has_new_commits": bool(base_sha and current_sha and current_sha != base_sha),
        "status_short": cap_lines(status_proc.stdout, 40),
        "diff_stat": cap_lines(diff_proc.stdout, 40),
    }


def build_worker_prompt(
    user_prompt: str,
    *,
    sandbox: str,
    network: bool = False,
    is_resume: bool = False,
    files_hint: list[str] | None = None,
) -> str:
    scope_line = f"- Priority files/paths: {', '.join(files_hint)}\n" if files_hint else ""
    net_note = " (network_access=true; keep external actions strictly scoped)" if network else ""
    if is_resume:
        return (
            f"{user_prompt.strip()}\n\n"
            "[Execution Contract]\n"
            f"- Sandbox: {sandbox}{net_note}. Do not merge or switch outside this worktree.\n"
            f"{scope_line}"
            "- Run the relevant verification checks/tests before finishing and report exact outcomes concisely.\n"
        )
    return (
        f"{user_prompt.strip()}\n\n"
        "[Execution Contract]\n"
        f"- Sandbox: {sandbox}{net_note}. Keep changes scoped to this task and never auto-merge.\n"
        f"{scope_line}"
        "- Before finishing, run appropriate verification (tests/lint/build/typecheck) and summarize facts concisely.\n"
    )


def extract_session_id_from_obj(obj: Any) -> str | None:
    """Recursively locate a thread_id / session_id / sessionId field in parsed JSON."""
    if isinstance(obj, dict):
        for key in ("thread_id", "session_id", "sessionId", "conversation_id"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        for val in obj.values():
            found = extract_session_id_from_obj(val)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = extract_session_id_from_obj(item)
            if found:
                return found
    return None


def parse_codex_events(events_text: str) -> dict[str, Any]:
    session_id: str | None = None
    usage: dict[str, Any] | None = None
    last_agent_text: str | None = None
    errors: list[str] = []

    for raw_line in events_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue

        if session_id is None:
            session_id = extract_session_id_from_obj(ev)

        ev_type = str(ev.get("type", ""))
        if ev_type == "turn.completed" and isinstance(ev.get("usage"), dict):
            usage = ev["usage"]
        elif isinstance(ev.get("usage"), dict) and usage is None:
            usage = ev["usage"]

        if ev_type in ("error", "turn.failed"):
            msg = ev.get("message") or (ev.get("error") or {}).get("message")
            if isinstance(msg, str) and msg.strip():
                errors.append(msg.strip())

        item = ev.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                last_agent_text = text.strip()

    return {
        "session_id": session_id,
        "usage": usage,
        "last_agent_text": last_agent_text,
        "errors": errors[-5:],
    }


def parse_report_file(
    report_path: Path,
    fallback_text: str | None,
    stderr_text: str,
    exit_code: int,
    event_errors: list[str] | None = None,
) -> dict[str, Any]:
    """Report is a worker claim, not independent proof of verification."""
    candidate_text = ""
    if report_path.is_file():
        try:
            candidate_text = report_path.read_text(encoding="utf-8", errors="strict").strip()
        except (OSError, UnicodeError):
            pass
    parsed = None
    if candidate_text:
        try:
            value = json.loads(candidate_text)
            if (isinstance(value, dict)
                and set(value) == {"status", "summary", "files_modified", "commands_run",
                                   "verification_passed", "risks_or_followups", "notes_for_orchestrator"}
                and value["status"] in ("completed", "partial", "blocked", "failed")
                and isinstance(value["summary"], str) and value["summary"].strip()
                and isinstance(value["notes_for_orchestrator"], str)
                and type(value["verification_passed"]) is bool
                and all(isinstance(value[k], list) and all(isinstance(x, str) for x in value[k])
                        for k in ("files_modified", "commands_run", "risks_or_followups"))):
                parsed = value
        except (ValueError, TypeError):
            pass
    if parsed is None:
        tail = "\n".join((candidate_text or fallback_text or stderr_text).splitlines()[-20:])[:1500]
        parsed = {"status": "partial", "summary": tail or "No valid structured worker report",
                  "files_modified": [], "commands_run": [], "verification_passed": False,
                  "risks_or_followups": ["Structured report missing or invalid; inspect logs."],
                  "notes_for_orchestrator": ""}
        source = "missing_or_invalid"
    else:
        source = "structured_file"
    claimed = parsed["verification_passed"] if source == "structured_file" else None
    if exit_code != 0 or event_errors:
        parsed["status"] = "failed"
        parsed["risks_or_followups"].append("Process failed or emitted an error; inspect logs.")
        if event_errors:
            parsed["summary"] = "\n".join(event_errors)[:1500]
    parsed["worker_claimed_verification_passed"] = claimed
    parsed["verification_passed"] = False
    parsed["verification_status"] = "unknown" if source == "structured_file" else "not_run"
    parsed["report_source"] = source
    return parsed


def outcome_fields(report: dict[str, Any], rc: int, timed_out: bool, stderr: str) -> dict[str, Any]:
    process_status = ("timed_out" if timed_out else "launch_failed" if
                      stderr.startswith("[dispatcher] Launch failed:") else
                      "exited" if rc == 0 else "failed")
    return {"process_status": process_status, "task_status": report["status"],
            "verification_status": report["verification_status"],
            "verification_passed": False}


def task_exit_code(result: dict[str, Any]) -> int:
    return 0 if result.get("dry_run") or (
        result.get("exit_code") == 0 and result.get("task_status") == "completed"
        and not result.get("timed_out")) else 1

def make_task_id(prefix: str = "task") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}"


def enforce_execution_policy(sandbox: str, network: bool = False, effort: str | None = None) -> None:
    """Fail closed until a trusted host can issue scoped, expiring grants.

    A request boolean, manifest or saved state is never a grant. This controls
    worker sandbox configuration, not the Codex service's own transport.
    """
    if sandbox not in ("read-only", "workspace-write"):
        raise ValueError("D06: unsupported or dangerous sandbox")
    if network is not False:
        raise ValueError("D06: network access denied; trusted host authorization unavailable")
    if effort is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", effort):
        raise ValueError("D06: invalid reasoning effort")


def validate_resume_binding(record: dict[str, Any], args: argparse.Namespace) -> None:
    if args.session_id is not None and args.session_id != record.get("session_id"):
        raise ValueError("D06: resume session differs from managed task")
    if args.cwd is not None and configured_path(args.cwd) != configured_path(record["workdir"]):
        raise ValueError("D06: resume cwd differs from managed task")
    if args.sandbox is not None and args.sandbox != record.get("sandbox") and args.sandbox != "read-only":
        raise ValueError("D06: resume sandbox escalation denied")
    if record.get("status") in ("reserved", "running", "interrupted"):
        raise ValueError("D06: incomplete task cannot be resumed")


def build_codex_exec_cmd(
    *,
    codex_bin: str,
    workdir: Path,
    model: str | None,
    effort: str | None,
    sandbox: str,
    network: bool = False,
    report_path: Path,
    is_git_repo: bool,
) -> list[str]:
    enforce_execution_policy(sandbox, network, effort)
    cmd = [
        codex_bin,
        "exec",
        "-C",
        str(workdir),
    ]
    if model:
        cmd.extend(["-m", model])
    if effort:
        cmd.extend(["-c", f'model_reasoning_effort="{effort}"'])
    cmd.extend([
        "-s",
        sandbox,
    ])
    cmd.extend(["-c", "sandbox_workspace_write.network_access=false"])
    cmd.extend([
        "-c",
        'approval_policy="never"',
        "--json",
        "--output-schema",
        str(SCHEMA_PATH),
        "-o",
        str(report_path),
    ])
    if not is_git_repo:
        cmd.append("--skip-git-repo-check")
    cmd.append("-")
    return cmd


def build_codex_resume_cmd(
    *,
    codex_bin: str,
    session_id: str,
    model: str | None,
    effort: str | None,
    sandbox: str,
    network: bool = False,
    report_path: Path,
    is_git_repo: bool,
) -> list[str]:
    enforce_execution_policy(sandbox, network, effort)
    # codex exec resume does NOT accept -s/--sandbox or -C/--cd; use -c sandbox_mode and subprocess cwd.
    cmd = [
        codex_bin,
        "exec",
        "resume",
    ]
    if model:
        cmd.extend(["-m", model])
    if effort:
        cmd.extend(["-c", f'model_reasoning_effort="{effort}"'])
    cmd.extend([
        "-c",
        f'sandbox_mode="{sandbox}"',
    ])
    cmd.extend(["-c", "sandbox_workspace_write.network_access=false"])
    cmd.extend([
        "-c",
        'approval_policy="never"',
        "--json",
        "--output-schema",
        str(SCHEMA_PATH),
        "-o",
        str(report_path),
    ])
    if not is_git_repo:
        cmd.append("--skip-git-repo-check")
    cmd.extend([session_id, "-"])
    return cmd


def terminate_owned_process_tree(proc: subprocess.Popen) -> None:
    """Terminate the owned worker tree; never target an arbitrary user PID."""
    if os.name == "nt":
        # taskkill uses the native process tree of this still-live child.
        if proc.poll() is None:
            system = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
            try:
                subprocess.run([str(system), "/PID", str(proc.pid), "/T", "/F"],
                               capture_output=True, timeout=10, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
            if proc.poll() is None:
                proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_subprocess_with_timeout(
    cmd: list[str],
    *,
    cwd: Path,
    stdin_text: str | None,
    timeout: int,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str, bool]:
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            start_new_session=(os.name != "nt"),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
    except OSError as exc:
        return 127, "", f"[dispatcher] Launch failed: {type(exc).__name__}: {exc}", False
    try:
        out, err = proc.communicate(input=stdin_text, timeout=timeout)
        return proc.returncode, out, err, False
    except subprocess.TimeoutExpired as exc:
        terminate_owned_process_tree(proc)
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            # Descendant may have escaped/inherited pipes; never hang or report success.
            out = exc.stdout or ""
            err = exc.stderr or ""
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    stream.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
        out = out.decode("utf-8", "replace") if isinstance(out, bytes) else out
        err = err.decode("utf-8", "replace") if isinstance(err, bytes) else err
        return 124, out, f"{err}\n[dispatcher] Timed out after {timeout}s; process tree termination requested".strip(), True
    except BaseException:
        terminate_owned_process_tree(proc)
        raise

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
    enforce_execution_policy(sandbox, network, effort)
    cwd = configured_path(cwd)
    if not cwd.exists() or not cwd.is_dir():
        raise ValueError(f"Target cwd does not exist or is not a directory: {cwd}")

    git_info = inspect_git(cwd)
    eff_isolation, isolation_reason = resolve_isolation(isolation, sandbox, git_info)
    tid = validate_task_id(task_id if task_id is not None else make_task_id("run"))

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

    run_dir = bounded_child(RUNS_DIR, tid)
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

    run_dir = reserve_run_dir(tid, {"backend": backend, "model": model_used, "effort": effort_used,
        "difficulty": routing["effective_difficulty"], "repo_root": git_info["repo_root"],
        "original_cwd": str(cwd), "workdir": str(cwd), "session_id": None, "network": network,
        "sandbox": sandbox, "isolation": eff_isolation, "created_at": utc_now(), "updated_at": utc_now()})
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
    outcome = outcome_fields(report, rc, timed_out, stderr_text)
    final_status = "timed_out" if timed_out else outcome["task_status"]

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
        **outcome,
        "exit_code": rc,
        "created_at": now,
        "updated_at": now,
        "run_dir": str(run_dir),
    }

    result = {
        "task_id": tid,
        **outcome,
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
    result_bytes = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(run_dir / "result.json", result_bytes)
    task_record["result_ref"] = {"turn": None, "sha256": hashlib.sha256(result_bytes).hexdigest()}
    with locked_state() as state:
        if state["tasks"].get(tid, {}).get("status") != "reserved":
            raise StateIntegrityError("Task reservation missing or changed")
        state["tasks"][tid] = task_record

    return result


def cmd_health(_args: argparse.Namespace) -> int:
    candidates = list_codex_candidates()
    codex_bin = get_codex_bin()
    node_bin = get_node_bin()
    git_bin = get_git_bin()

    codex_ver = probe_version([codex_bin, "--version"]) if codex_bin else None
    node_ver = probe_version([node_bin, "--version"]) if node_bin else None
    git_ver = probe_version([git_bin, "--version"]) if git_bin else None
    frontier = discover_frontier_models()

    healthy = bool(
        codex_bin
        and codex_ver
        and git_bin
        and SCHEMA_PATH.exists()
    )

    payload = {
        "healthy": healthy,
        "schema_exists": SCHEMA_PATH.exists(),
        "state_dir": str(STATE_DIR),
        "codex_home": str(CODEX_HOME),
        "gemini_config_dir": str(GEMINI_CONFIG_DIR),
        "runtime_errors": [f"{name} executable not found or invalid override" for name, value in (("codex", codex_bin), ("git", git_bin), ("node", node_bin)) if not value],
        "default_quality_mode": "smart",
        "codex": {"bin": codex_bin, "version": codex_ver, "candidates": candidates},
        "node": {"bin": node_bin, "version": node_ver},
        "git": {"bin": git_bin, "version": git_ver},
        "frontier_models": {
            "exists": frontier["exists"],
            "source_file": frontier["source_file"],
            "client_version": frontier["client_version"],
            "flagship": frontier["flagship"],
            "wide_fast": frontier["wide_fast"],
            "listed_models_count": len(frontier["listed_models"]),
            "listed_slugs": frontier["listed_slugs"],
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if healthy else 1


def cmd_run(args: argparse.Namespace) -> int:
    prompt_text = sys.stdin.read() if args.prompt == "-" else args.prompt
    result = execute_single_task(
        prompt=prompt_text,
        cwd=Path(args.cwd).resolve(),
        backend=args.backend,
        difficulty=args.difficulty,
        model=args.model,
        effort=args.effort,
        quality=args.quality,
        alternate=args.alternate,
        prefer_wide=args.prefer_wide,
        sandbox=args.sandbox,
        network=args.network,
        isolation=args.isolation,
        timeout=args.timeout,
        files_hint=args.files,
        task_id=args.task_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return task_exit_code(result)


def cmd_batch(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    items = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(items, dict) and "tasks" in items:
        items = items["tasks"]
    if not isinstance(items, list) or not items:
        raise ValueError("Manifest must be a non-empty JSON list or an object with a 'tasks' list.")

    # Validate every entry before launching any worker, including the default.
    enforce_execution_policy("workspace-write", args.network)
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Manifest task must be an object")
        enforce_execution_policy(item.get("sandbox", "workspace-write"), item.get("network", False), item.get("effort"))
    default_cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()

    def _run_item(idx: int, item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        item_cwd = Path(item.get("cwd", default_cwd)).resolve()
        item_sandbox = item.get("sandbox", "workspace-write")
        item_iso = item.get("isolation", "auto")
        # Enforce worktree isolation when multiple concurrent write tasks share a Git repo
        if len(items) > 1 and item_sandbox == "workspace-write" and item_iso == "auto":
            item_iso = "worktree"
        item_alt = item.get("alternate")
        if item_alt is None and "no_alternate" in item:
            item_alt = not bool(item["no_alternate"])
        item_network = item.get("network", False)
        res = execute_single_task(
            prompt=item["prompt"],
            cwd=item_cwd,
            backend=item.get("backend", "codex"),
            difficulty=item.get("difficulty", "auto"),
            model=item.get("model"),
            effort=item.get("effort"),
            quality=item.get("quality", args.quality),
            alternate=item_alt,
            prefer_wide=bool(item.get("prefer_wide", False)),
            sandbox=item_sandbox,
            network=item_network,
            isolation=item_iso,
            timeout=int(item.get("timeout", args.timeout)),
            files_hint=item.get("files"),
            task_id=item.get("task_id"),
            dry_run=args.dry_run,
        )
        return idx, res

    ordered: list[dict[str, Any] | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as pool:
        futures = [pool.submit(_run_item, i, item) for i, item in enumerate(items)]
        for fut in as_completed(futures):
            idx, res = fut.result()
            ordered[idx] = res

    results = [r for r in ordered if r is not None]
    failed = [r for r in results if task_exit_code(r) != 0]
    summary = {
        "batch_total": len(results),
        "batch_failed": len(failed),
        "dry_run": args.dry_run,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


def cmd_resume(args: argparse.Namespace) -> int:
    if args.network is True:
        raise ValueError("D06: network access denied; trusted host authorization unavailable")
    if not args.task_id:
        raise ValueError("D06: unmanaged session resume denied; managed task ID required")
    validate_task_id(args.task_id)
    if args.dry_run:
        return _cmd_resume(args)
    root = bounded_child(RUNS_DIR, args.task_id)
    if not root.is_dir():
        raise ValueError("Original task run directory missing")
    lock = root / "resume.lock"
    reject_link(lock)
    with exclusive_state_lock(lock, timeout=0):
        return _cmd_resume(args)


def _cmd_resume(args: argparse.Namespace) -> int:
    prompt_text = sys.stdin.read() if args.prompt == "-" else args.prompt
    task_record: dict[str, Any] | None = None
    if args.task_id:
        with locked_state() as state:
            task_record = state["tasks"].get(args.task_id)
        if not task_record:
            raise ValueError(f"Unknown task_id: {args.task_id}")

    if not task_record:
        raise ValueError("D06: managed task record required")
    validate_resume_binding(task_record, args)
    backend = args.backend or task_record["backend"]
    session_id = args.session_id or (task_record["session_id"] if task_record else None)
    if not session_id:
        raise ValueError("No session_id available to resume (pass --session-id or valid --task-id).")

    workdir = Path(args.cwd or (task_record["workdir"] if task_record else ".")).resolve()
    if not workdir.exists():
        raise ValueError(f"Workdir does not exist: {workdir}")

    sandbox = args.sandbox or (task_record["sandbox"] if task_record else "workspace-write")
    network = args.network is True  # Never inherit a previous grant.
    enforce_execution_policy(sandbox, network, args.effort)
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

    resume_tid = validate_task_id(args.task_id or make_task_id("resume"))
    turn_id = make_task_id("turn")
    run_dir = bounded_child(RUNS_DIR, resume_tid, turn_id)
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

    if not task_record:
        reserve_run_dir(resume_tid)
    elif not bounded_child(RUNS_DIR, resume_tid).is_dir():
        raise StateIntegrityError("Original task run directory missing")
    run_dir.mkdir(exist_ok=False)
    (run_dir / "prompt.txt").write_text(worker_prompt, encoding="utf-8")

    with locked_state() as state:
        current = state["tasks"].get(resume_tid)
        if not current or current.get("status") in ("reserved", "running", "interrupted"):
            raise StateIntegrityError("Managed task is no longer available for resume")
        current["status"] = "running"
        current["active_turn_id"] = turn_id
        current["updated_at"] = utc_now()
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
    outcome = outcome_fields(report, rc, timed_out, stderr_text)

    result = {
        "task_id": resume_tid,
        "turn_id": turn_id,
        **outcome,
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
    result_bytes = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(run_dir / "result.json", result_bytes)
    with locked_state() as state:
        current = state["tasks"].get(resume_tid)
        if not current or current.get("active_turn_id") != turn_id or current.get("status") != "running":
            raise StateIntegrityError("Resume reservation changed")
        current.update({"model": model_used, "effort": effort_used, "sandbox": sandbox,
            "network": False, "session_id": new_session_id, "exit_code": rc,
            "status": "timed_out" if timed_out else outcome["task_status"], **outcome,
            "updated_at": utc_now(), "result_ref": {"turn": turn_id, "sha256": hashlib.sha256(result_bytes).hexdigest()}})
        current.pop("active_turn_id", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return task_exit_code(result)


def cmd_review(args: argparse.Namespace) -> int:
    if args.task_id:
        validate_task_id(args.task_id)
    task_record: dict[str, Any] | None = None
    if args.task_id:
        with locked_state() as state:
            task_record = state["tasks"].get(args.task_id)
        if not task_record:
            raise ValueError(f"Unknown task_id: {args.task_id}")

    workdir = Path(args.cwd or (task_record["workdir"] if task_record else ".")).resolve()
    if not workdir.exists():
        raise ValueError(f"Workdir does not exist: {workdir}")

    base_sha = args.base or (task_record.get("base_sha") if task_record else None)
    git_truth = collect_git_truth(workdir, base_sha)
    backend = args.backend

    if backend == "codex":
        codex_bin = get_codex_bin()
        if not codex_bin:
            raise RuntimeError("codex CLI not found")
        frontier = discover_frontier_models()
        flagship = frontier["flagship"]
        wide_fast = frontier["wide_fast"]
        flagship_slug = flagship["slug"] if flagship else None
        wide_slug = wide_fast["slug"] if wide_fast else None
        author_model = task_record.get("model") if task_record else None

        if args.model:
            review_model = args.model
        elif author_model and flagship_slug and author_model == flagship_slug and wide_slug and wide_slug != flagship_slug:
            review_model = wide_slug
        elif author_model and wide_slug and author_model == wide_slug and flagship_slug:
            review_model = flagship_slug
        else:
            review_model = flagship_slug

        if args.effort:
            review_effort = args.effort
        else:
            matched = next((m for m in frontier["listed_models"] if m["slug"] == review_model), flagship)
            effs = matched["supported_efforts"] if matched else []
            chain = ("max", "xhigh", "high") if args.quality == "max" else ("high", "xhigh", "medium")
            review_effort = pick_supported_effort(chain, effs)
    else:
        raise RuntimeError(f"Unsupported backend: {backend}")

    review_id = make_task_id("review")
    run_dir = bounded_child(RUNS_DIR, review_id)
    review_out = run_dir / "review_output.txt"

    cmd = [
        get_codex_bin() or "codex",
        "exec",
        "review",
    ]
    if review_model:
        cmd.extend(["-m", review_model])
    enforce_execution_policy("read-only", False, review_effort)
    if review_effort:
        cmd.extend(["-c", f'model_reasoning_effort="{review_effort}"'])
    cmd.extend([
        "-c",
        'sandbox_mode="read-only"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'approval_policy="never"',
        "--json",
        "-o",
        str(review_out),
    ])
    if git_truth.get("has_new_commits") and base_sha and not args.uncommitted:
        cmd.extend(["--base", base_sha])
    else:
        cmd.append("--uncommitted")
    if not git_truth.get("is_git"):
        cmd.append("--skip-git-repo-check")
    if args.prompt and not (base_sha or args.uncommitted):
        cmd.append("-")
        stdin_prompt = args.prompt
    else:
        stdin_prompt = None

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "review_id": review_id,
                    "backend": backend,
                    "review_model": review_model,
                    "review_effort": review_effort,
                    "workdir": str(workdir),
                    "command": cmd,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    run_dir = reserve_run_dir(review_id)
    rc, stdout_text, stderr_text, timed_out = run_subprocess_with_timeout(
        cmd, cwd=workdir, stdin_text=stdin_prompt, timeout=args.timeout
    )
    (run_dir / "events.jsonl").write_text(stdout_text, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")

    parsed_events = parse_codex_events(stdout_text)
    review_text = (
        review_out.read_text(encoding="utf-8", errors="replace").strip()
        if review_out.exists()
        else (parsed_events["last_agent_text"] or "\n".join(stderr_text.splitlines()[-20:]))
    )
    usage = parsed_events["usage"]
    session_id = parsed_events["session_id"]

    payload = {
        "review_id": review_id,
        "task_id": args.task_id,
        "backend": backend,
        "review_model": review_model,
        "review_effort": review_effort,
        "workdir": str(workdir),
        "session_id": session_id,
        "exit_code": rc,
        "timed_out": timed_out,
        "usage": usage,
        "review_summary": review_text[:3000],
        "git_truth": git_truth,
        "run_dir": str(run_dir),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if rc == 0 else 1


def cmd_status(args: argparse.Namespace) -> int:
    if args.task_id:
        validate_task_id(args.task_id)
    with locked_state() as state:
        tasks = state.get("tasks", {})
        if args.task_id:
            if args.task_id not in tasks:
                raise ValueError(f"Unknown task_id: {args.task_id}")
            rec = dict(tasks[args.task_id])
            rec["worktree_exists"] = bool(rec.get("worktree_path") and Path(rec["worktree_path"]).exists())
            print(json.dumps(rec, ensure_ascii=False, indent=2))
            return 0
        summary_list = []
        for tid, rec in sorted(tasks.items(), key=lambda kv: kv[1].get("updated_at", ""), reverse=True):
            summary_list.append(
                {
                    "task_id": tid,
                    "backend": rec.get("backend"),
                    "model": rec.get("model"),
                    "effort": rec.get("effort"),
                    "status": rec.get("status"),
                    "isolation": rec.get("isolation"),
                    "branch": rec.get("branch"),
                    "worktree_exists": bool(rec.get("worktree_path") and Path(rec["worktree_path"]).exists()),
                    "updated_at": rec.get("updated_at"),
                }
            )
        print(
            json.dumps(
                {
                    "rr_counter": state.get("rr_counter", 0),
                    "total_tasks": len(summary_list),
                    "tasks": summary_list,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    # A request, including a plain cleanup without force/delete-branch, is
    # not a trusted grant. Keep the worktree and task state intact.
    raise ValueError("D06: cleanup requires trusted human authorization")



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local multi-agent dispatcher (Antigravity Brain -> Codex CLI Hand).", allow_abbrev=False
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("health", help="Check local Codex CLI, Git, Node, and model cache readiness.")

    p_run = sub.add_parser(
        "run", allow_abbrev=False,
        help="Dispatch one coding/analysis task. Defaults to smart quality-quota (--quality smart) dynamic frontier routing.",
    )
    p_run.add_argument("--cwd", default=".", help="Target repository or working directory.")
    p_run.add_argument("--prompt", required=True, help="Task prompt or '-' for stdin.")
    p_run.add_argument("--backend", choices=VALID_BACKENDS, default="codex")
    p_run.add_argument("--difficulty", choices=VALID_DIFFICULTIES, default="auto")
    p_run.add_argument("--quality", choices=VALID_QUALITIES, default="smart", help="Quality/quota routing mode (default: smart).")
    p_run.add_argument("--prefer-wide", action="store_true", help="Prefer largest-context frontier sibling for wide repo sweeps.")
    p_run.add_argument("--model", default=None, help="Explicit model slug override (supports any future official slug).")
    p_run.add_argument("--effort", default=None, help="Explicit Codex reasoning effort override.")
    p_run.add_argument("--alternate", dest="alternate", action="store_true", default=None, help="Enable alternation across flagship/wide_fast on medium.")
    p_run.add_argument("--no-alternate", dest="alternate", action="store_false", help="Disable alternation on medium.")
    p_run.add_argument("--sandbox", choices=VALID_SANDBOXES, default="workspace-write")
    p_run.add_argument("--network", action="store_true", help="Network request (currently denied without trusted host authorization).")
    p_run.add_argument("--isolation", choices=VALID_ISOLATIONS, default="auto")
    p_run.add_argument("--timeout", type=int, default=600)
    p_run.add_argument("--files", nargs="*", default=None, help="Optional target file hints.")
    p_run.add_argument("--task-id", default=None)
    p_run.add_argument("--dry-run", action="store_true")

    p_batch = sub.add_parser("batch", allow_abbrev=False, help="Dispatch parallel independent tasks from a JSON manifest.")
    p_batch.add_argument("--manifest", required=True, help="Path to JSON list or {tasks:[...]} file.")
    p_batch.add_argument("--cwd", default=None, help="Default cwd when task item omits cwd.")
    p_batch.add_argument("--quality", choices=VALID_QUALITIES, default="smart")
    p_batch.add_argument("--network", action="store_true", help="Network request (currently denied).")
    p_batch.add_argument("--max-concurrency", type=int, default=3)
    p_batch.add_argument("--timeout", type=int, default=600)
    p_batch.add_argument("--dry-run", action="store_true")

    p_res = sub.add_parser("resume", allow_abbrev=False, help="Continue an existing worker session in its workdir.")
    p_res.add_argument("--task-id", default=None)
    p_res.add_argument("--session-id", default=None)
    p_res.add_argument("--cwd", default=None)
    p_res.add_argument("--backend", choices=VALID_BACKENDS, default=None)
    p_res.add_argument("--prompt", required=True, help="Follow-up prompt or '-' for stdin.")
    p_res.add_argument("--difficulty", choices=VALID_DIFFICULTIES, default="auto")
    p_res.add_argument("--quality", choices=VALID_QUALITIES, default="smart")
    p_res.add_argument("--prefer-wide", action="store_true")
    p_res.add_argument("--model", default=None)
    p_res.add_argument("--effort", default=None)
    p_res.add_argument("--alternate", dest="alternate", action="store_true", default=None)
    p_res.add_argument("--no-alternate", dest="alternate", action="store_false")
    p_res.add_argument("--sandbox", choices=VALID_SANDBOXES, default=None)
    p_res.add_argument("--network", dest="network", action="store_true", default=None, help="Network request (currently denied; grants are never inherited).")
    p_res.add_argument("--no-network", dest="network", action="store_false", help="Disable workspace-write network access on resume.")
    p_res.add_argument("--timeout", type=int, default=600)
    p_res.add_argument("--dry-run", action="store_true")

    p_rev = sub.add_parser("review", allow_abbrev=False, help="Run non-interactive read-only Codex code review.")
    p_rev.add_argument("--task-id", default=None)
    p_rev.add_argument("--cwd", default=None)
    p_rev.add_argument("--backend", choices=VALID_BACKENDS, default="codex")
    p_rev.add_argument("--quality", choices=VALID_QUALITIES, default="smart")
    p_rev.add_argument("--model", default=None)
    p_rev.add_argument("--effort", default=None)
    p_rev.add_argument("--base", default=None, help="Base Git branch or SHA.")
    p_rev.add_argument("--uncommitted", action="store_true")
    p_rev.add_argument("--prompt", default=None)
    p_rev.add_argument("--timeout", type=int, default=300)
    p_rev.add_argument("--dry-run", action="store_true")

    p_st = sub.add_parser("status", help="Inspect tracked task metadata and round-robin state.")
    p_st.add_argument("--task-id", default=None)

    p_cln = sub.add_parser("cleanup", allow_abbrev=False, help="Cleanup disabled until trusted human authorization is available.")
    p_cln.add_argument("--task-id", required=True)
    p_cln.add_argument("--delete-branch", action="store_true")
    p_cln.add_argument("--force", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handlers = {
        "health": cmd_health,
        "run": cmd_run,
        "batch": cmd_batch,
        "resume": cmd_resume,
        "review": cmd_review,
        "status": cmd_status,
        "cleanup": cmd_cleanup,
    }
    try:
        return handlers[args.subcommand](args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
