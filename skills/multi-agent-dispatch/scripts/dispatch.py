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
import sqlite3
import queue
import threading
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
SCHEMA_V2_PATH = SKILL_DIR / "resources" / "report_schema_v2.json"

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


def strict_state_json(raw: bytes) -> Any:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate state JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("Non-finite state JSON number")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys, parse_constant=reject_constant)


def decode_state(raw: bytes) -> dict[str, Any]:
    data = strict_state_json(raw)
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



# D15: explicit, plugin-owned SQLite migration. state.json is either the
# authoritative legacy document OR an incompatible-to-legacy storage marker.
# The marker is published last, never used as a second write destination.
def state_bytes(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def state_digest(raw):
    return hashlib.sha256(raw).hexdigest()


def storage_marker(raw):
    value = strict_state_json(raw)
    if not isinstance(value, dict) or "storage" not in value:
        return None
    if (set(value) != {"storage", "database", "backup", "backup_sha256"} or
            value.get("storage") != "sqlite-v1" or
            not isinstance(value.get("database"), str) or
            not re.fullmatch(r"dispatch-state-[0-9a-f]{32}\.sqlite", value["database"]) or
            not isinstance(value.get("backup_sha256"), str) or
            not re.fullmatch(r"[0-9a-f]{64}", value["backup_sha256"]) or
            value.get("backup") != "state.pre-sqlite-" + value["backup_sha256"] + ".json"):
        raise StateIntegrityError("D15: invalid storage marker; no fallback")
    return value


def owned_storage_path(name):
    reject_link(STATE_DIR)
    root = STATE_DIR.resolve()
    native = CODEX_HOME.resolve()
    if root == native or root.is_relative_to(native):
        raise StateIntegrityError("D15: plugin state cannot reside inside native Codex home")
    if Path(name).name != name:
        raise StateIntegrityError("D15: invalid storage filename")
    path = STATE_DIR / name
    reject_link(path)
    return path


def store_rows(data):
    validated = decode_state(state_bytes(data))
    request_records(validated)
    tasks = validated.pop("tasks")
    meta = state_bytes(validated).decode("utf-8")
    rows = []
    seen = set()
    for tid in sorted(tasks):
        validate_task_id(tid)
        if tid.casefold() in seen or tasks[tid].get("task_id",tid) != tid:
            raise StateIntegrityError("D15: invalid or ambiguous task identity")
        seen.add(tid.casefold())
        payload = state_bytes(tasks[tid]).decode("utf-8")
        rows.append((tid, payload, state_digest(payload.encode("utf-8"))))
    meta_sha = state_digest(meta.encode("utf-8"))
    manifest = state_digest((meta_sha+"\n"+"\n".join(tid+"\t"+sha for tid,_,sha in rows)).encode("ascii"))
    return meta, meta_sha, rows, manifest


def store_open(marker, initialize=False):
    path = owned_storage_path(marker["database"])
    for suffix in ("-wal","-shm","-journal"):
        reject_link(Path(str(path)+suffix))
    if initialize:
        with path.open("xb"):
            pass
    if not path.is_file():
        raise StateIntegrityError("D15: authoritative database missing; no JSON fallback")
    db = sqlite3.connect(path.absolute().as_uri()+"?mode=rw",uri=True,timeout=3,isolation_level=None)
    try:
        db.execute("PRAGMA busy_timeout=3000")
        if initialize:
            mode=db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        else:
            mode=db.execute("PRAGMA journal_mode").fetchone()[0]
        if mode.lower() != "wal":
            raise StateIntegrityError("D15: expected SQLite WAL mode")
        db.execute("PRAGMA synchronous=FULL")
        return db
    except BaseException:
        db.close()
        raise


def store_read(db):
    if db.execute("PRAGMA user_version").fetchone()[0] != 1:
        raise StateIntegrityError("D15: unsupported state schema")
    meta = db.execute("SELECT meta_json,meta_sha256,revision,task_count,manifest_sha256 FROM dispatch_meta WHERE id=1").fetchone()
    if meta is None:
        raise StateIntegrityError("D15: missing metadata")
    payload, digest, rev, count, manifest = meta
    if (not isinstance(payload,str) or state_digest(payload.encode("utf-8"))!=digest or
            type(rev) is not int or rev<1 or type(count) is not int or count<0):
        raise StateIntegrityError("D15: metadata integrity failure")
    data=strict_state_json(payload.encode("utf-8"))
    if not isinstance(data,dict) or "tasks" in data:
        raise StateIntegrityError("D15: invalid metadata object")
    rows=db.execute("SELECT task_id,payload,payload_sha256 FROM dispatch_tasks ORDER BY task_id").fetchall()
    if len(rows)!=count:
        raise StateIntegrityError("D15: task count mismatch")
    tasks={}
    for tid, body, checksum in rows:
        validate_task_id(tid)
        if not isinstance(body,str) or state_digest(body.encode("utf-8"))!=checksum:
            raise StateIntegrityError("D15: task checksum mismatch")
        tasks[tid]=strict_state_json(body.encode("utf-8"))
    data["tasks"]=tasks
    if store_rows(data)[3]!=manifest:
        raise StateIntegrityError("D15: state manifest mismatch")
    return data, rev


def store_write(db,data,revision,previous=None):
    meta,digest,rows,manifest=store_rows(data)
    old={} if previous is None else {tid:body for tid,body,_ in store_rows(previous)[2]}
    if not set(old).issubset(data["tasks"]):
        raise StateIntegrityError("D15: automatic task deletion unsupported")
    changed=[row for row in rows if old.get(row[0])!=row[1]]
    db.executemany("INSERT INTO dispatch_tasks(task_id,payload,payload_sha256) VALUES(?,?,?) "
                   "ON CONFLICT(task_id) DO UPDATE SET payload=excluded.payload,payload_sha256=excluded.payload_sha256",changed)
    db.execute("INSERT INTO dispatch_meta(id,meta_json,meta_sha256,revision,task_count,manifest_sha256) VALUES(1,?,?,?,?,?) "
               "ON CONFLICT(id) DO UPDATE SET meta_json=excluded.meta_json,meta_sha256=excluded.meta_sha256,"
               "revision=excluded.revision,task_count=excluded.task_count,manifest_sha256=excluded.manifest_sha256",
               (meta,digest,revision,len(rows),manifest))
    checked,rev=store_read(db)
    if rev!=revision or state_bytes(checked)!=state_bytes(data):
        raise StateIntegrityError("D15: transaction verification mismatch")


def preserve_named_state(name, raw):
    target=owned_storage_path(name)
    if target.exists():
        if target.read_bytes()!=raw:
            raise StateIntegrityError("D15: backup name collision; original untouched")
    else:
        atomic_write_bytes(target,raw)
    return target


@contextlib.contextmanager
def sqlite_locked_state(marker):
    try:
        with contextlib.closing(store_open(marker)) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                data,rev=store_read(db)
                previous=state_bytes(data)
                yield data
                if state_bytes(data)!=previous:
                    # Recovery snapshot is a backup, never a competing writer.
                    backup={"version":1,"database":marker["database"],"revision":rev,
                            "sha256":state_digest(previous),"payload":previous.decode("utf-8")}
                    atomic_write_bytes(owned_storage_path(marker["database"]+".previous.json"),state_bytes(backup))
                    store_write(db,data,rev+1,strict_state_json(previous))
                db.execute("COMMIT")
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
    except sqlite3.Error as exc:
        raise StateIntegrityError("D15: database unavailable or transaction failed; no fallback") from exc


def require_storage_quiescent(data):
    if any(rec.get("status") in ("reserved","running","interrupted") or rec.get("active_turn_id")
           for rec in data["tasks"].values()):
        raise StateIntegrityError("D15: stop and reconcile active tasks before storage change")
    if any(op["status"] in ("pending","uncertain") for op in request_records(data).values()):
        raise StateIntegrityError("D15: reconcile outstanding request reservations")


def cmd_state_storage(args):
    action=args.subcommand
    if action in ("state-migrate","state-rollback") and not args.confirm_quiescent:
        raise ValueError("D15: stop all old CLI/MCP instances and explicitly confirm quiescence")
    # Reject native or linked roots before creating any migration directories.
    owned_storage_path("state.json")
    ensure_state_dirs()
    reject_link(STATE_DIR)
    reject_link(LOCK_FILE)
    with exclusive_state_lock(LOCK_FILE):
        reject_link(STATE_FILE)
        if not STATE_FILE.is_file():
            raise StateIntegrityError("D15: existing state required")
        raw=STATE_FILE.read_bytes()
        marker=storage_marker(raw)
        if action=="state-migrate":
            if marker:
                with sqlite_locked_state(marker) as data:
                    count=len(data["tasks"])
                result={"status":"already_migrated","database":marker["database"],"tasks":count}
            else:
                data=decode_state(raw)
                store_rows(data)
                require_storage_quiescent(data)
                sha=state_digest(raw)
                marker={"storage":"sqlite-v1","database":"dispatch-state-"+uuid.uuid4().hex+".sqlite",
                        "backup":"state.pre-sqlite-"+sha+".json","backup_sha256":sha}
                preserve_named_state(marker["backup"],raw)
                with contextlib.closing(store_open(marker,initialize=True)) as db:
                    db.execute("BEGIN IMMEDIATE")
                    try:
                        db.execute("PRAGMA user_version=1")
                        db.execute("CREATE TABLE dispatch_meta(id INTEGER PRIMARY KEY CHECK(id=1),meta_json TEXT NOT NULL,"
                                   "meta_sha256 TEXT NOT NULL,revision INTEGER NOT NULL,task_count INTEGER NOT NULL,manifest_sha256 TEXT NOT NULL)")
                        db.execute("CREATE TABLE dispatch_tasks(task_id TEXT PRIMARY KEY,payload TEXT NOT NULL,payload_sha256 TEXT NOT NULL)")
                        store_write(db,data,1)
                        if db.execute("PRAGMA quick_check").fetchone()[0]!="ok":
                            raise StateIntegrityError("D15: new database quick_check failed")
                        db.execute("COMMIT")
                        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    except BaseException:
                        if db.in_transaction:
                            db.execute("ROLLBACK")
                        raise
                # Last operation: a crash before this leaves original JSON authoritative.
                atomic_write_bytes(STATE_FILE,state_bytes(marker))
                result={"status":"migrated","database":marker["database"],"backup":marker["backup"],"tasks":len(data["tasks"])}
        elif action=="state-rollback":
            if marker is None:
                result={"status":"already_json","tasks":len(decode_state(raw)["tasks"])}
            else:
                with sqlite_locked_state(marker) as data:
                    require_storage_quiescent(data)
                    exported=state_bytes(data)
                preserve_named_state("state.rollback-"+state_digest(exported)+".json",exported)
                atomic_write_bytes(STATE_FILE,exported)
                result={"status":"rolled_back","database_preserved":marker["database"],"tasks":len(data["tasks"])}
        elif action=="state-recover":
            if marker is None:
                raise StateIntegrityError("D15: recovery export requires active storage marker")
            if args.source=="initial":
                recovered=owned_storage_path(marker["backup"]).read_bytes()
                if state_digest(recovered)!=marker["backup_sha256"]:
                    raise StateIntegrityError("D15: initial backup checksum mismatch")
            else:
                backup=strict_state_json(owned_storage_path(marker["database"]+".previous.json").read_bytes())
                if (not isinstance(backup,dict) or backup.get("version")!=1 or
                        backup.get("database")!=marker["database"] or not isinstance(backup.get("payload"),str)):
                    raise StateIntegrityError("D15: invalid recovery snapshot")
                recovered=backup["payload"].encode("utf-8")
                if state_digest(recovered)!=backup.get("sha256"):
                    raise StateIntegrityError("D15: recovery checksum mismatch")
            recovered_data=decode_state(recovered)
            store_rows(recovered_data)
            target=preserve_named_state("state.recovery-"+state_digest(recovered)+".json",recovered)
            result={"status":"recovery_exported_not_activated","file":target.name,"source":args.source,
                    "tasks":len(recovered_data["tasks"]),"warning":"Review possible post-backup changes before any manual activation"}
        else:
            raise ValueError("D15: unknown storage operation")
    print(json.dumps(result,ensure_ascii=False))
    return 0


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
                marker = storage_marker(raw)
                if marker is None:
                    data = decode_state(raw)
            except (ValueError, UnicodeError) as exc:
                backup = preserve_corrupt_state(raw)
                raise StateIntegrityError(f"Invalid dispatcher state; original untouched; copy: {backup}") from exc
            if marker is not None:
                with sqlite_locked_state(marker) as data:
                    yield data
                return
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


def reserve_run_dir(task_id: str, record: dict[str, Any] | None = None, request_id: str | None = None) -> Path:
    """Atomically reserve ID under lock; orphaned directories are never reused."""
    tid = validate_task_id(task_id)
    with locked_state() as state:
        run_dir = bounded_child(RUNS_DIR, tid)
        requests = request_records(state)
        keyed = [op for op in requests.values() if op["task_id"].casefold() == tid.casefold()]
        if keyed or request_id is not None:
            op = requests.get(validate_task_id(request_id).casefold()) if request_id is not None else None
            if (op is None or op["task_id"] != tid or op["kind"] != "run" or op["status"] != "pending"):
                raise ValueError("D13: task ID reserved by a keyed operation")
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

    diff_cmd = [git_bin, "-C", str(workdir), "diff", "--no-ext-diff", "--no-textconv", "--stat"]
    if base_sha:
        diff_cmd.append(base_sha)
    diff_proc = subprocess.run(diff_cmd, capture_output=True, text=True, encoding="utf-8")

    return {
        "is_git": True,
        "head_sha": current_sha,
        "base_sha": base_sha,
        "has_new_commits": bool(base_sha and current_sha and current_sha != base_sha),
        "metadata_complete": all(p.returncode == 0 for p in (status_proc, head_proc, diff_proc))
            and all(len([ln for ln in p.stdout.splitlines() if ln.strip()]) <= 40 for p in (status_proc, diff_proc)),
        "status_short": cap_lines(status_proc.stdout, 40),
        "diff_stat": cap_lines(diff_proc.stdout, 40),
    }


# D10 explicit, bounded request/worker-report protocol. The envelope is data,
# never an authorization grant. Legacy v1 remains the default.
PROTOCOL_LIMIT = 8192

def protocol_json(raw: str) -> Any:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > PROTOCOL_LIMIT:
        raise ValueError("D10: protocol payload exceeds byte budget")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("D10: duplicate JSON key")
            result[key] = value
        return result
    def reject_constant(_):
        raise ValueError("D10: non-finite JSON value")
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    except RecursionError as exc:
        raise ValueError("D10: JSON nesting exceeds parser limit") from exc


def protocol_text(value: Any, limit: int, *, allow_empty: bool = False) -> bool:
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return allow_empty or bool(value.strip())


def protocol_strings(value: Any, count: int, length: int) -> bool:
    return isinstance(value, list) and len(value) <= count and all(protocol_text(s, length) for s in value)


def parse_task_envelope(raw: str, task_id: str | None, current_rev: int) -> dict[str, Any]:
    value = protocol_json(raw)
    if not isinstance(value, dict) or set(value) != {"version", "task_id", "rev", "base_rev", "goal", "scope", "accept", "delta"}:
        raise ValueError("D10: incompatible task envelope")
    if type(value["version"]) is not int or value["version"] != 2:
        raise ValueError("D10: unsupported task protocol version")
    tid = validate_task_id(value["task_id"])
    if task_id is not None and tid != task_id:
        raise ValueError("D10: task identity mismatch")
    if (type(current_rev) is not int or type(value["rev"]) is not int or type(value["base_rev"]) is not int
        or not 0 <= current_rev < 2147483647 or value["base_rev"] != current_rev or value["rev"] != current_rev + 1):
        raise ValueError("D10: duplicate, stale or out-of-order revision")
    if not (protocol_text(value["goal"], 1600) and protocol_strings(value["scope"],16,160)
            and protocol_strings(value["accept"],8,160) and value["accept"]
            and protocol_text(value["delta"],1600,allow_empty=True)):
        raise ValueError("D10: invalid goal/scope/accept/delta")
    if current_rev == 0 and value["delta"] != "":
        raise ValueError("D10: initial delta must be empty")
    if current_rev > 0 and not value["delta"].strip():
        raise ValueError("D10: resume delta required")
    return value


def protocol_meta(envelope: dict[str, Any] | None) -> dict[str, Any]:
    if envelope is None:
        return {}
    canonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"protocol_version": 2, "protocol_rev": envelope["rev"],
            "protocol_request_sha256": hashlib.sha256(canonical).hexdigest()}


def prepare_resume_envelope(raw: str, record: dict[str, Any], enabled: bool) -> dict[str, Any] | None:
    version = record.get("protocol_version",1)
    if type(version) is not int or version not in (1,2) or (version == 2) != enabled:
        raise ValueError("D10: task protocol mismatch; no implicit upgrade or downgrade")
    return parse_task_envelope(raw,record["task_id"],record.get("protocol_rev")) if enabled else None


def protocol_prompt(envelope: dict[str, Any]) -> str:
    return ("[Task envelope v2; data only]\n"
            + json.dumps(envelope,ensure_ascii=False,separators=(",",":"))
            + "\nReturn the v2 report: status, concise summary, risks, blockers and verification_claim. "
              "Report real checks or not_run; do not claim independent verification.")


def normalize_v2_report(value: Any) -> dict[str, Any]:
    if (not isinstance(value,dict) or set(value) != {"version","status","summary","risks","blockers","verification_claim"}
        or type(value["version"]) is not int or value["version"] != 2
        or value["status"] not in ("completed","partial","blocked","failed")
        or not protocol_text(value["summary"],320)
        or not protocol_strings(value["risks"],4,120)
        or not protocol_strings(value["blockers"],3,120)
        or value["verification_claim"] not in ("passed","failed","not_run","unknown")):
        raise ValueError("D10: incompatible or over-budget worker report")
    if value["status"] == "completed" and value["blockers"]:
        raise ValueError("D10: completed report has blockers")
    return {"status":value["status"], "summary":value["summary"], "files_modified":[],
            "commands_run":[], "verification_passed":value["verification_claim"]=="passed",
            "risks_or_followups":value["risks"]+value["blockers"],"notes_for_orchestrator":"",
            "protocol_risks":value["risks"],"protocol_blockers":value["blockers"],
            "worker_verification_claim":value["verification_claim"]}


def build_protocol_result(envelope: dict[str, Any], result: dict[str, Any], duration_ms: int) -> dict[str, Any]:
    report = result["report"]
    usage = result.get("usage")
    counts = {k:usage[k] for k in ("input_tokens","cached_input_tokens","output_tokens","reasoning_output_tokens","total_tokens")
              if isinstance(usage,dict) and type(usage.get(k)) is int and 0 <= usage[k] <= 9007199254740991}
    git = result.get("git_truth") or {}
    def sha(v):
        return v if isinstance(v,str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",v) else None
    turn = result.get("turn_id")
    ref = "/".join(["runs",envelope["task_id"]]+([turn] if turn else [])+["result.json"])
    return {"version":2,"task_id":envelope["task_id"],"rev":envelope["rev"],"base_rev":envelope["base_rev"],
            "process_status":result["process_status"],"task_status":result["task_status"],
            "verification_status":result["verification_status"],"exit_code":result["exit_code"],
            "summary":report["summary"],"risks":report.get("protocol_risks",report["risks_or_followups"]),
            "blockers":report.get("protocol_blockers",[]),
            "worker_verification_claim":report.get("worker_verification_claim","unknown"),
            "process_error":result["process_status"] != "exited" or result["task_status"] == "failed",
            "duration_ms":duration_ms,"usage":{"source":"cli_reported" if counts else "unknown","counts":counts},
            "git":{"head_sha":sha(git.get("head_sha")),"base_sha":sha(git.get("base_sha"))},
            "result_ref":ref}

# D11: opt-in task-local context. These are conservative local counters,
# not a tokenizer, provider context limit, or authorization decision.
CONTEXT_MAX_TURNS = 8
CONTEXT_MAX_BYTES = 16384
CONTEXT_MAX_GENERATIONS = 32
CONTEXT_SECRET_PATTERN = re.compile(
    r"(?i)(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|AKIA[A-Z0-9]{16})\b|"
    r"\b(?:api[_-]?key|access[_-]?token|password|authorization)\s*[:=]\s*\S+)"
)


def context_check_text(value: Any) -> None:
    # Never import environment, credentials, raw logs or model replies into
    # the board. Heuristic only: callers must not supply secrets.
    if isinstance(value,str):
        if CONTEXT_SECRET_PATTERN.search(value):
            raise ValueError("D11: potential credential in context; use a nonsecret reference")
    elif isinstance(value,list):
        for item in value:
            context_check_text(item)
    elif isinstance(value,dict):
        for item in value.values():
            context_check_text(item)


def context_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()


def initial_context(envelope: dict[str, Any], sandbox: str, base_sha: str | None) -> dict[str, Any]:
    context_check_text(envelope)
    return {"version":1,"task_id":envelope["task_id"],"rev":1,
            "stable":{k:envelope[k] for k in ("goal","scope","accept")},
            "constraints":{"sandbox":sandbox,"network":False,"base_sha":base_sha},
            "generation":1,"turns":1,"prompt_bytes":0,"checkpoint":None,
            "retired_sessions":[],"last_result_ref":None}


def context_prepare(raw: str, record: dict[str, Any], rebuild: bool, sandbox: str | None = None) -> tuple[dict[str, Any],dict[str, Any],str]:
    old = record.get("context_board")
    if not isinstance(old,dict) or old.get("version") != 1 or old.get("task_id") != record["task_id"] or old.get("rev") != record.get("protocol_rev") or context_digest(old) != record.get("context_digest"):
        raise ValueError("D11: missing or inconsistent task context")
    value = protocol_json(raw)
    keys={"version","task_id","rev","base_rev","delta"}
    if not isinstance(value,dict) or set(value) != (keys | {"checkpoint"} if rebuild else keys):
        raise ValueError("D11: invalid delta envelope")
    context_check_text(value)
    if record.get("protocol_version",2) != 2 or old["constraints"]["network"] is not False:
        raise ValueError("D11: incompatible context constraints")
    effective_sandbox = sandbox or old["constraints"]["sandbox"]
    if effective_sandbox not in ("read-only","workspace-write") or (old["constraints"]["sandbox"]=="read-only" and effective_sandbox!="read-only"):
        raise ValueError("D11: context sandbox escalation denied")
    if record.get("sandbox",old["constraints"]["sandbox"]) != old["constraints"]["sandbox"]:
        raise ValueError("D11: persisted sandbox does not match context")
    stable=old["stable"]
    envelope=parse_task_envelope(json.dumps({k:value[k] for k in keys}|stable,ensure_ascii=False),record["task_id"],record["protocol_rev"])
    # Normal resume only sends the delta plus revision and existing identity.
    prompt="[Task delta v2; preserve prior constraints]\n"+json.dumps({k:value[k] for k in sorted(keys)},ensure_ascii=False,separators=(",",":"))
    next_board=json.loads(json.dumps(old,ensure_ascii=False))
    next_board["rev"]=envelope["rev"]
    next_board["constraints"]["sandbox"]=effective_sandbox
    if rebuild:
        cp=value["checkpoint"]
        if not isinstance(cp,dict) or set(cp)!={"summary","decisions","pending"} or not protocol_text(cp["summary"],1200) or not protocol_strings(cp["decisions"],8,160) or not protocol_strings(cp["pending"],8,160):
            raise ValueError("D11: rebuild needs explicit reviewed checkpoint")
        if old["generation"] >= CONTEXT_MAX_GENERATIONS:
            raise ValueError("D11: context generation limit; manual review required")
        if record.get("session_id"):
            next_board["retired_sessions"].append(record["session_id"])
        next_board.update(generation=old["generation"]+1,turns=1,prompt_bytes=0,checkpoint=cp)
        prompt="[Rebuild task context; preserve all constraints]\n"+json.dumps(
            {"task":envelope,"constraints":next_board["constraints"],"checkpoint":cp},
            ensure_ascii=False,separators=(",",":"))
    else:
        next_board["turns"]+=1
        if old["turns"] >= CONTEXT_MAX_TURNS:
            raise ValueError("D11: context threshold reached; supply reviewed checkpoint with --rebuild-context")
    return envelope,next_board,prompt


def context_account(board: dict[str, Any], prompt: str) -> None:
    board["prompt_bytes"]+=len(prompt.encode("utf-8"))
    if board["prompt_bytes"]>CONTEXT_MAX_BYTES:
        raise ValueError("D11: local prompt byte threshold exceeded; reduce delta or explicitly rebuild context")


def context_state_fields(board: dict[str, Any] | None) -> dict[str, Any]:
    return {} if board is None else {"context_board":board,"context_digest":context_digest(board)}


def context_session(events: str, previous: str | None, rebuild: bool) -> str:
    # Do not recursively extract IDs from arbitrary worker output.
    ids=set()
    for line in events.splitlines():
        try:
            event=json.loads(line)
        except (ValueError,RecursionError):
            continue
        if isinstance(event,dict) and event.get("type")=="thread.started":
            value=event.get("thread_id")
            if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}",value):
                raise StateIntegrityError("D11: invalid session identity")
            ids.add(value)
    if len(ids)!=1:
        raise StateIntegrityError("D11: missing or conflicting session identity; inspect local evidence")
    session=next(iter(ids))
    if previous is not None and ((session==previous)==rebuild):
        raise StateIntegrityError("D11: unexpected session identity; no fallback or automatic retry")
    return session


def context_assert_session_owner(state: dict[str,Any], tid: str, session: str | None, board: dict[str,Any]) -> None:
    if not session or session in board["retired_sessions"]:
        raise StateIntegrityError("D11: retired or missing session")
    for other,rec in state["tasks"].items():
        if other!=tid and (rec.get("session_id")==session or session in (rec.get("context_board") or {}).get("retired_sessions",[])):
            raise StateIntegrityError("D11: session belongs to another task")


def context_protect_legacy_session(state: dict[str,Any], tid: str, session: str | None) -> None:
    # A legacy record cannot claim a blackboard session or retired identity.
    if session is None:
        return
    for other,rec in state["tasks"].items():
        board=rec.get("context_board")
        if other!=tid and isinstance(board,dict) and (session==rec.get("session_id") or session in board.get("retired_sessions",[])):
            raise StateIntegrityError("D11: legacy task cannot use a blackboard session")


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


# D12: only terminal CLI usage, one sample per owned invocation.
# Cache and reasoning counts are subcategories, not additional totals.
USAGE_FIELDS=("input_tokens","cached_input_tokens","output_tokens","reasoning_output_tokens","total_tokens")
USAGE_MAX=9007199254740991


def usage_int(v):
    return v if type(v) is int and 0 <= v <= USAGE_MAX else None


def invocation_usage(events: str) -> dict[str,Any]:
    samples=[]
    invalid=False
    def unique_keys(pairs):
        out={}
        for key,value in pairs:
            if key in out:
                raise ValueError("Duplicate JSONL key")
            out[key]=value
        return out
    def reject_constant(_):
        raise ValueError("Non-finite JSONL value")
    for line in events.splitlines():
        if not line.strip():
            continue
        try:
            ev=json.loads(line,object_pairs_hook=unique_keys,parse_constant=reject_constant)
        except (ValueError,RecursionError):
            invalid=True
            continue
        if not isinstance(ev,dict):
            invalid=True
            continue
        if ev.get("type") in ("error","turn.failed"):
            invalid=True
        if ev.get("type")!="turn.completed":
            continue
        if not isinstance(ev.get("usage"),dict):
            invalid=True
            continue
        counts={k:usage_int(ev["usage"].get(k)) for k in USAGE_FIELDS}
        model=ev.get("model")
        model=model if isinstance(model,str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}",model) else None
        turn=ev.get("turn_id")
        turn=turn if isinstance(turn,str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}",turn) else None
        if "total_tokens" in ev["usage"] and counts["total_tokens"] is None:
            invalid=True
        samples.append((turn,counts,model))
    # Multiple terminal records with no identity are ambiguous, even identical.
    # Identical repeated identified events are deduplicated, never summed.
    unique=[]
    for sample in samples:
        if sample not in unique:
            unique.append(sample)
    if invalid or len(unique)!=1 or (len(samples)>1 and unique[0][0] is None):
        return {"source":"unknown","counts":{k:None for k in USAGE_FIELDS},"actual_model":None,"gemini_source":"unknown","gemini_tokens":None}
    _,counts,model=unique[0]
    if counts["cached_input_tokens"] is not None and counts["input_tokens"] is not None and counts["cached_input_tokens"]>counts["input_tokens"]:
        counts["cached_input_tokens"]=None
    if counts["reasoning_output_tokens"] is not None and counts["output_tokens"] is not None and counts["reasoning_output_tokens"]>counts["output_tokens"]:
        counts["reasoning_output_tokens"]=None
    a,b=counts["input_tokens"],counts["output_tokens"]
    if a is not None and b is not None:
        derived=usage_int(a+b)
        if counts["total_tokens"] is not None and counts["total_tokens"]!=derived:
            counts["total_tokens"]=None
        else: # derived from observed fields, no estimate
            counts["total_tokens"]=derived
    else:
        # A total without both components has not established compatible semantics.
        counts["total_tokens"]=None
    return {"source":"cli_reported" if any(v is not None for v in counts.values()) else "unknown",
            "counts":counts,"actual_model":model,"gemini_source":"unknown","gemini_tokens":None}


def make_budget(max_turns=None,max_tokens=None,max_seconds=None):
    limits={"turns":max_turns,"tokens":max_tokens,"seconds":max_seconds}
    for k,v in limits.items():
        if v is not None and (type(v) is not int or not 1<=v<= (10000 if k=="turns" else 1000000000)):
            raise ValueError("D12: invalid positive budget limit")
    return limits


def new_usage_store(prior_unknown=False):
    return {"version":1,"attempts":0,"duration_ms":0,"prior_unknown":prior_unknown,
            "known_sums":{k:0 for k in USAGE_FIELDS},"unknown_turns":{k:0 for k in USAGE_FIELDS},
            "last_attempt":None,"last_model":None}


def budget_timeout(limits,store,requested):
    if not isinstance(limits,dict) or set(limits)!={"turns","tokens","seconds"}:
        raise StateIntegrityError("D12: malformed persisted budget")
    make_budget(limits["turns"],limits["tokens"],limits["seconds"])
    if not isinstance(store,dict) or store.get("version")!=1 or type(store.get("prior_unknown")) is not bool or usage_int(store.get("attempts")) is None or usage_int(store.get("duration_ms")) is None:
        raise StateIntegrityError("D12: malformed persisted usage")
    for field in ("known_sums","unknown_turns"):
        if not isinstance(store.get(field),dict) or set(store[field])!=set(USAGE_FIELDS) or any(usage_int(v) is None for v in store[field].values()):
            raise StateIntegrityError("D12: malformed persisted usage counts")
    if any(v>store["attempts"] for v in store["unknown_turns"].values()):
        raise StateIntegrityError("D12: invalid unknown attempt counts")
    if type(requested) is not int or requested<=0:
        raise ValueError("D12: timeout must be positive")
    if limits["turns"] is not None and (store["prior_unknown"] or store["attempts"]>=limits["turns"]):
        raise ValueError("D12: turn budget exhausted or prior count unknown")
    if limits["tokens"] is not None:
        if store["prior_unknown"] or store["unknown_turns"]["total_tokens"]:
            raise ValueError("D12: token budget cannot be verified; prior usage unknown")
        if store["known_sums"]["total_tokens"]>=limits["tokens"]:
            raise ValueError("D12: token budget exhausted; next turn blocked")
    if limits["seconds"] is not None:
        remaining=(limits["seconds"]*1000-store["duration_ms"])//1000
        if store["prior_unknown"] or remaining<1:
            raise ValueError("D12: execution time budget exhausted or unknown")
        requested=min(requested,remaining)
    return requested


def finish_usage(store,sample,duration_ms,attempt):
    if store["last_attempt"]==attempt:
        raise StateIntegrityError("D12: duplicate usage settlement")
    out=json.loads(json.dumps(store))
    out["attempts"]+=1
    out["duration_ms"]+=duration_ms
    out["last_attempt"]=attempt
    out["last_model"]=sample["actual_model"]
    for k in USAGE_FIELDS:
        v=sample["counts"][k]
        if v is None or out["known_sums"][k]+v>USAGE_MAX:
            out["unknown_turns"][k]+=1
        else:
            out["known_sums"][k]+=v
    return out


def usage_summary(store):
    return {"attempts":store["attempts"],"duration_ms":store["duration_ms"],
            "counts":{k:None if store["prior_unknown"] or store["unknown_turns"][k] else store["known_sums"][k] for k in USAGE_FIELDS},
            "actual_model":store["last_model"],"gemini_source":"unknown","gemini_tokens":None}


def validate_cached_route(model,effort):
    if model is None and effort is None:
        return
    cache=discover_frontier_models()
    match=next((m for m in cache["listed_models"] if m["slug"]==model),None)
    if match is None or (effort is not None and effort not in match["supported_efforts"]):
        raise ValueError("D12: inherited route no longer confirmed by local capabilities cache")


def budget_route(difficulty,prompt,files_hint,model,effort,quality,prefer_wide):
    # Explicit opt-in, cached capabilities only; do not assume future effort names.
    level,reason=classify_difficulty(prompt,files_hint) if difficulty=="auto" else (difficulty,"explicit complexity")
    frontier=discover_frontier_models()
    selected=next((m for m in frontier["listed_models"] if m["slug"]==model),None) if model else (
        (frontier["wide_fast"] or frontier["flagship"]) if level=="low" or prefer_wide else (frontier["flagship"] or frontier["wide_fast"]))
    if model and selected is None:
        raise ValueError("D12: requested model not present in local capabilities cache")
    supported=selected["supported_efforts"] if selected else []
    if effort is not None and effort not in supported:
        raise ValueError("D12: requested effort not confirmed by local capabilities cache")
    orders={"low":("low","medium","high"),"medium":("medium","high","low"),"hard":("high","xhigh","medium"),"extreme":("xhigh","high","medium")}
    order=orders[level] if quality!="max" else ("xhigh","high","medium","low")
    chosen=effort or next((e for e in order if e in supported),None)
    return {"model":selected["slug"] if selected else None,"effort":chosen,
            "effective_difficulty":level,"route_note":"D12 cached capabilities; "+reason,
            "cache_client_version":frontier["client_version"],"capability_source":"local_cache" if selected else "unknown"}


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
            detail = ev.get("error")
            msg = ev.get("message") or (detail.get("message") if isinstance(detail, dict) else None)
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
    protocol_v2: bool = False,
) -> dict[str, Any]:
    """Report is a worker claim, not independent proof of verification."""
    candidate_text = ""
    if report_path.is_file():
        try:
            if protocol_v2:
                with report_path.open("rb") as source:
                    payload = source.read(PROTOCOL_LIMIT + 1)
                    if len(payload) <= PROTOCOL_LIMIT:
                        candidate_text = payload.decode("utf-8")
            else:
                candidate_text = report_path.read_text(encoding="utf-8", errors="strict").strip()
        except (OSError, UnicodeError):
            pass
    parsed = None
    if candidate_text:
        try:
            value = protocol_json(candidate_text) if protocol_v2 else json.loads(candidate_text)
            if protocol_v2:
                parsed = normalize_v2_report(value)
            elif (isinstance(value, dict)
                and set(value) == {"status", "summary", "files_modified", "commands_run",
                                   "verification_passed", "risks_or_followups", "notes_for_orchestrator"}
                and value["status"] in ("completed", "partial", "blocked", "failed")
                and isinstance(value["summary"], str) and value["summary"].strip()
                and isinstance(value["notes_for_orchestrator"], str)
                and type(value["verification_passed"]) is bool
                and all(isinstance(value[k], list) and all(isinstance(x, str) for x in value[k])
                        for k in ("files_modified", "commands_run", "risks_or_followups"))):
                parsed = value
        except (ValueError, TypeError, RecursionError):
            pass
    if parsed is None:
        tail = "" if protocol_v2 else "\n".join((candidate_text or fallback_text or stderr_text).splitlines()[-20:])[:1500]
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
            parsed["summary"] = "Worker emitted an error; inspect local result." if protocol_v2 else "\n".join(event_errors)[:1500]
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
    if record.get("stream_events") is True and record.get("stream_integrity") != "complete":
        raise ValueError("D14: incomplete stream requires reconciliation; no resume")


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
    protocol_v2: bool = False,
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
        str(SCHEMA_V2_PATH if protocol_v2 else SCHEMA_PATH),
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
    protocol_v2: bool = False,
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
        str(SCHEMA_V2_PATH if protocol_v2 else SCHEMA_PATH),
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
        # Never signal a numeric process group after Popen has reaped its
        # leader: the ID could be reused. A short-lived zombie on macOS may
        # also cause killpg to return EPERM during the exit race.
        if proc.returncode is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Reap an exiting owned child. If still alive, only target that
            # Popen child; descendants are unverified. All callers are on
            # failure/interruption paths, never infer success from this.
            try:
                proc.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                proc.kill()


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


# D14: opt-in bounded streaming. Only fixed metadata is published; raw bytes
# remain in local run artifacts. An interrupted producer never gets replayed.
STREAM_STDOUT_LIMIT = 4 * 1024 * 1024
STREAM_STDERR_LIMIT = 1024 * 1024
STREAM_LINE_LIMIT = 64 * 1024
STREAM_WINDOW = 64
STREAM_SEGMENT_BYTES = 256 * 1024
STREAM_SAFE_SEQ = 2**53 - 1
STREAM_TERMINAL = ("process_exit", "timed_out", "stream_failed", "launch_failed", "interrupted")


class RotatingStreamSink:
    """Append-only bounded segments plus the legacy bounded compatibility mirror.

    The total invocation cap is still enforced by accept(); no old segment is
    deleted, reused or silently dropped. A failed write cannot publish success.
    """
    def __init__(self, directory, name, mirror):
        self.directory, self.name, self.mirror = directory, name, mirror
        self.parts, self.part, self.digest, self.size = [], None, None, 0
        if type(STREAM_SEGMENT_BYTES) is not int or STREAM_SEGMENT_BYTES <= 0:
            raise ValueError("D14: invalid segment size")

    def __enter__(self):
        return self

    def _close_part(self):
        if self.part is None:
            return
        stream = self.part
        try:
            stream.flush()
            os.fsync(stream.fileno())
            self.parts.append({"name": Path(stream.name).name, "bytes": self.size,
                               "sha256": self.digest.hexdigest()})
        finally:
            self.part = None
            stream.close()

    def write(self, data):
        self.mirror.write(data)
        offset = 0
        while offset < len(data):
            if self.part is None:
                target = self.directory / (self.name + ".part-%04d" % (len(self.parts)+1))
                reject_link(target)
                self.part = target.open("xb")
                self.digest, self.size = hashlib.sha256(), 0
            end = offset + min(len(data)-offset, STREAM_SEGMENT_BYTES-self.size)
            portion = data[offset:end]
            if self.part.write(portion) != len(portion):
                raise OSError("D14: short segment write")
            self.digest.update(portion)
            self.size += len(portion)
            offset = end
            if self.size == STREAM_SEGMENT_BYTES:
                self._close_part()

    def flush(self):
        self.mirror.flush()
        if self.part is not None:
            self.part.flush()

    def finish(self):
        self._close_part()
        self.mirror.flush()
        os.fsync(self.mirror.fileno())
        return list(self.parts)

    def __exit__(self, *_):
        self.finish()


def stream_segment_manifest(run_dir, stdout, stderr):
    target = run_dir / "stream-segments.json"
    reject_link(target)
    if target.exists():
        raise StateIntegrityError("D14: existing segment manifest")
    data = {"version": 1, "segmentBytes": STREAM_SEGMENT_BYTES,
            "stdout": stdout.finish(), "stderr": stderr.finish()}
    atomic_write_bytes(target, (json.dumps(data, separators=(",", ":"))+"\n").encode("utf-8"))


class StreamJournal:
    def __init__(self, directory, task_id, turn_id, sequence_base=0, sequence_scope="task"):
        if type(sequence_base) is not int or not 0 <= sequence_base < STREAM_SAFE_SEQ or sequence_scope not in ("task","since_upgrade"):
            raise StateIntegrityError("D14: invalid task sequence base")
        if turn_id is None and (sequence_base != 0 or sequence_scope != "task"):
            raise StateIntegrityError("D14: invalid initial sequence")
        self.sequence_base, self.sequence_scope = sequence_base, sequence_scope
        self.path = directory / "stream-state.json"
        reject_link(self.path)
        if self.path.exists():
            raise StateIntegrityError("D14: existing stream journal")
        self.task_id = validate_task_id(task_id)
        self.turn_id = validate_task_id(turn_id) if turn_id is not None else None
        self.seq = 0
        self.entries = []

    def emit(self, kind, stdout_bytes=0, stderr_bytes=0, lines=0):
        if self.sequence_base + self.seq >= STREAM_SAFE_SEQ:
            raise StateIntegrityError("D14: task sequence exhausted")
        self.seq += 1
        self.entries.append({"seq": self.seq, "taskSeq": self.sequence_base+self.seq, "kind": kind,
            "at": time.time_ns() // 1000000, "stdoutBytes": stdout_bytes,
            "stderrBytes": stderr_bytes, "lines": lines})
        self.entries = self.entries[-STREAM_WINDOW:]
        payload = {"version": 2, "taskId": self.task_id,
                   "turnId": self.turn_id or "initial", "sequenceBase": self.sequence_base,
                   "sequenceScope": self.sequence_scope, "entries": self.entries}
        atomic_write_bytes(self.path, (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def stream_checkpoint(directory, task_id, turn_id):
    """Read a bounded terminal snapshot; legacy v1 is an explicit upgrade epoch."""
    target = directory / "stream-state.json"
    reject_link(target)
    if not target.is_file():
        raise StateIntegrityError("D14: missing stream journal")
    with target.open("rb") as f:
        raw = f.read(16385)
    if len(raw) > 16384:
        raise StateIntegrityError("D14: oversized stream journal")
    value = strict_state_json(raw)
    if (not isinstance(value,dict) or type(value.get("version")) is not int
        or value["version"] not in (1,2) or value.get("taskId") != task_id
        or value.get("turnId") != (turn_id or "initial")):
        raise StateIntegrityError("D14: stream journal identity")
    entries = value.get("entries")
    if not isinstance(entries,list) or not 1<=len(entries)<=STREAM_WINDOW:
        raise StateIntegrityError("D14: invalid journal window")
    version = value["version"]
    base = value.get("sequenceBase",0)
    scope = value.get("sequenceScope","since_upgrade")
    if (version==2 and (type(base) is not int or not 0<=base<STREAM_SAFE_SEQ
        or scope not in ("task","since_upgrade") or (turn_id is None and (base!=0 or scope!="task")))):
        raise StateIntegrityError("D14: invalid journal sequence scope")
    previous = None
    for e in entries:
        if (not isinstance(e,dict) or type(e.get("seq")) is not int or not 1<=e["seq"]<=STREAM_SAFE_SEQ
            or e.get("kind") not in ("queued","running","progress","heartbeat",*STREAM_TERMINAL)
            or (previous is not None and (e["seq"]!=previous["seq"]+1 or previous["kind"] in STREAM_TERMINAL))
            or (version==2 and (type(e.get("taskSeq")) is not int or e["taskSeq"]!=base+e["seq"] or e["taskSeq"]>STREAM_SAFE_SEQ))):
            raise StateIntegrityError("D14: invalid journal event sequence")
        previous = e
    if previous["kind"] not in STREAM_TERMINAL:
        raise StateIntegrityError("D14: journal has no terminal receipt")
    return {"version":version,"lastTaskSeq":previous["taskSeq"] if version==2 else 0,
            "sequenceScope":scope if version==2 else "since_upgrade",
            "terminal":previous["kind"],"sha256":hashlib.sha256(raw).hexdigest()}


def prior_stream_sequence(record, task_id):
    ref = record.get("result_ref")
    if not isinstance(ref,dict) or "turn" not in ref:
        raise StateIntegrityError("D14: missing prior result reference")
    turn = ref["turn"]
    root = bounded_child(RUNS_DIR, task_id)
    directory = root if turn is None else bounded_child(root, validate_task_id(turn))
    checkpoint = stream_checkpoint(directory,task_id,turn)
    if checkpoint["terminal"] != "process_exit":
        raise StateIntegrityError("D14: prior journal is not a complete process exit")
    if checkpoint["version"] == 2:
        if record.get("stream_checkpoint") != checkpoint:
            raise StateIntegrityError("D14: prior stream checkpoint changed")
    elif "stream_checkpoint" in record:
        raise StateIntegrityError("D14: prior stream checkpoint downgraded")
    return checkpoint["lastTaskSeq"], checkpoint["sequenceScope"]


def streamed_subprocess(cmd, *, cwd, stdin_text, timeout, run_dir, task_id, turn_id=None, env=None,
                        sequence_base=0, sequence_scope="task"):
    """Bounded concurrent pipe drain with a replayable, metadata-only journal.

    Raw artifacts are capped per invocation, not silently truncated to success.
    On quota, malformed JSONL, pipe failure or deadline, terminate only the owned
    process tree. Uncertain termination cannot report task success.
    """
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("D14: positive timeout required")
    reject_link(run_dir)
    journal = StreamJournal(run_dir, task_id, turn_id, sequence_base, sequence_scope)
    journal.emit("queued")
    chunks = queue.Queue(maxsize=32)
    stop = threading.Event()
    counts = {"stdout": 0, "stderr": 0}
    limits = {"stdout": STREAM_STDOUT_LIMIT, "stderr": STREAM_STDERR_LIMIT}
    output = bytearray()
    errors = bytearray()
    line = bytearray()
    lines = 0
    proc = None
    eof = set()
    failure = None
    timed_out = False

    def enqueue(item):
        while not stop.is_set():
            try:
                chunks.put(item, timeout=.1)
                return
            except queue.Full:
                continue

    def reader(name, pipe):
        try:
            while not stop.is_set():
                data = pipe.read1(8192)
                if not data:
                    enqueue((name, None))
                    return
                enqueue((name, data))
        except (OSError, ValueError):
            enqueue(("pipe_error", None))
        finally:
            pipe.close()

    def writer(pipe):
        try:
            if stdin_text is not None:
                pipe.write(stdin_text.encode("utf-8"))
                pipe.flush()
        except (OSError, ValueError, UnicodeError):
            enqueue(("stdin_error", None))
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    def parse_line(raw):
        nonlocal lines
        if len(raw) > STREAM_LINE_LIMIT:
            raise ValueError("line_limit")
        if not raw.strip():
            return
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate_key")
                result[key] = value
            return result
        def reject_constant(_):
            raise ValueError("nonfinite_number")
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=unique, parse_constant=reject_constant)
        if not isinstance(value, dict):
            raise ValueError("invalid_jsonl")
        lines += 1

    def accept(name, data, sink):
        nonlocal line
        remaining = limits[name] - counts[name]
        portion = data[:remaining]
        sink.write(portion)
        sink.flush()
        counts[name] += len(portion)
        (output if name == "stdout" else errors).extend(portion)
        if len(data) > remaining:
            raise ValueError("output_limit")
        if name == "stdout":
            line.extend(portion)
            while True:
                at = line.find(b"\n")
                if at < 0:
                    break
                parse_line(line[:at])
                del line[:at+1]
            if len(line) > STREAM_LINE_LIMIT:
                raise ValueError("line_limit")

    stdout_file, stderr_file = run_dir / "events.jsonl", run_dir / "stderr.log"
    for target in (stdout_file, stderr_file):
        reject_link(target)
    with stdout_file.open("xb") as stdout_mirror, stderr_file.open("xb") as stderr_mirror, \
         RotatingStreamSink(run_dir,"events.jsonl",stdout_mirror) as stdout_sink, \
         RotatingStreamSink(run_dir,"stderr.log",stderr_mirror) as stderr_sink:
        try:
            proc = subprocess.Popen(cmd, cwd=str(cwd), env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=(os.name != "nt"),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        except OSError as exc:
            stream_segment_manifest(run_dir,stdout_sink,stderr_sink)
            journal.emit("launch_failed")
            return 127, "", "[dispatcher] Launch failed: " + type(exc).__name__, False
        started = time.monotonic()
        last_publish = started
        last_counts = (0, 0)
        threads = [
            threading.Thread(target=reader, args=("stdout", proc.stdout), daemon=True),
            threading.Thread(target=reader, args=("stderr", proc.stderr), daemon=True),
            threading.Thread(target=writer, args=(proc.stdin,), daemon=True)]
        try:
            journal.emit("running")
            for thread in threads:
                thread.start()
            while True:
                now = time.monotonic()
                if now - started >= timeout:
                    timed_out = True
                    failure = "timeout"
                    break
                try:
                    name, data = chunks.get(timeout=min(.1, max(.001, timeout-(now-started))))
                except queue.Empty:
                    name, data = None, None
                if name in ("pipe_error", "stdin_error"):
                    failure = name
                    break
                if name in ("stdout", "stderr"):
                    if data is None:
                        eof.add(name)
                    else:
                        try:
                            accept(name, data, stdout_sink if name=="stdout" else stderr_sink)
                        except (ValueError, UnicodeError, RecursionError):
                            failure = "invalid_or_oversized_output"
                            break
                now = time.monotonic()
                totals = (counts["stdout"], counts["stderr"])
                if now-last_publish >= 1 or (totals != last_counts and now-last_publish >= .25):
                    journal.emit("progress" if totals != last_counts else "heartbeat", *totals, lines)
                    last_publish, last_counts = now, totals
                if len(eof)==2 and proc.poll() is not None and not threads[2].is_alive() and chunks.empty():
                    if line:
                        try:
                            parse_line(line)
                        except (ValueError, UnicodeError, RecursionError):
                            failure = "invalid_or_oversized_output"
                    break
            if failure is not None:
                terminate_owned_process_tree(proc)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            else:
                proc.wait(timeout=5)
            stream_segment_manifest(run_dir,stdout_sink,stderr_sink)
            journal.emit("timed_out" if timed_out else "stream_failed" if failure else "process_exit",
                         counts["stdout"], counts["stderr"], lines)
        except BaseException:
            try:
                terminate_owned_process_tree(proc)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait(timeout=5)
            finally:
                try:
                    journal.emit("interrupted", counts["stdout"], counts["stderr"], lines)
                except (OSError, StateIntegrityError):
                    pass
            raise
        finally:
            stop.set()
            # Do not close a pipe from another thread while a read is blocked.
            # Daemon readers cannot block CLI shutdown if an escaped child holds it.
            for thread, pipe in zip(threads, (proc.stdout, proc.stderr, proc.stdin)):
                if thread.ident is not None:
                    thread.join(timeout=.2)
                else:
                    pipe.close()
        if failure:
            # Incomplete streams cannot be used for session/usage inference.
            return (124 if timed_out else 125), "", "[dispatcher] D14 " + failure, timed_out
        return proc.returncode, output.decode("utf-8"), errors.decode("utf-8", "replace"), False


def mark_stream_interrupted(task_id, turn_id):
    # A failure between process launch and durable settlement cannot reopen the
    # task or claim zero use. Retain the active turn for forensic reconciliation.
    with locked_state() as state:
        record = state["tasks"].get(task_id)
        if not record or record.get("status") != "running" or record.get("active_turn_id") != turn_id:
            raise StateIntegrityError("D14: stream reservation changed")
        store = record.get("usage_store", new_usage_store(prior_unknown=True))
        record.update(status="interrupted", stream_integrity="incomplete",
                      usage_store={**store, "prior_unknown": True}, updated_at=utc_now())


def invoke_worker(cmd, *, cwd, stdin_text, timeout, run_dir, task_id, turn_id=None, stream_events=False,
                  sequence_base=0, sequence_scope="task"):
    if stream_events:
        try:
            return streamed_subprocess(cmd, cwd=cwd, stdin_text=stdin_text, timeout=timeout,
                                       run_dir=run_dir, task_id=task_id, turn_id=turn_id,
                                       sequence_base=sequence_base, sequence_scope=sequence_scope)
        except BaseException:
            mark_stream_interrupted(task_id, turn_id)
            raise
    rc, out, err, timed_out = run_subprocess_with_timeout(cmd, cwd=cwd, stdin_text=stdin_text, timeout=timeout)
    (run_dir / "events.jsonl").write_text(out, encoding="utf-8")
    (run_dir / "stderr.log").write_text(err, encoding="utf-8")
    return rc, out, err, timed_out


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
    protocol_v2: bool = False,
    blackboard: bool = False,
    budget: dict[str,Any] | None = None,
    use_budget_route: bool = False,
    request_id: str | None = None,
    stream_events: bool = False,
) -> dict[str, Any]:
    if type(stream_events) is not bool or (stream_events and not protocol_v2):
        raise ValueError('D14: streaming requires explicit v2 protocol')
    limits=make_budget() if budget is None else make_budget(budget['turns'],budget['tokens'],budget['seconds'])
    store=new_usage_store()
    timeout=budget_timeout(limits,store,timeout)
    if blackboard and not protocol_v2:
        raise ValueError('D11: blackboard requires protocol v2')
    if blackboard and files_hint:
        raise ValueError('D11: use envelope scope instead of separate files hints')
    enforce_execution_policy(sandbox, network, effort)
    envelope = parse_task_envelope(prompt,task_id,0) if protocol_v2 else None
    if envelope is not None:
        task_id = envelope["task_id"]
        prompt = protocol_prompt(envelope)
    cwd = configured_path(cwd)
    if not cwd.exists() or not cwd.is_dir():
        raise ValueError(f"Target cwd does not exist or is not a directory: {cwd}")

    git_info = inspect_git(cwd)
    eff_isolation, isolation_reason = resolve_isolation(isolation, sandbox, git_info)
    board = initial_context(envelope,sandbox,git_info["head_sha"]) if blackboard else None
    tid = validate_task_id(task_id if task_id is not None else make_task_id("run"))

    if backend == "codex":
        codex_bin = get_codex_bin()
        if not codex_bin:
            raise RuntimeError("codex CLI not found")
        routing = budget_route(difficulty,prompt,files_hint,model,effort,quality,prefer_wide) if use_budget_route else resolve_model_and_effort(
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
    if board is not None:
        context_account(board,worker_prompt)

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
            is_git_repo=git_info["is_git_repo"], protocol_v2=protocol_v2,
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
        "sandbox": sandbox, "isolation": eff_isolation, "created_at": utc_now(), "updated_at": utc_now(), **protocol_meta(envelope), **context_state_fields(board), "budget":limits,"usage_store":store,"budget_route":use_budget_route,"stream_events":stream_events}, request_id=request_id)
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
        is_git_repo=git_info["is_git_repo"], protocol_v2=protocol_v2,
    )
    if stream_events:
        with locked_state() as state:
            current = state["tasks"][tid]
            if current.get("status") != "reserved":
                raise StateIntegrityError("D14: reservation changed")
            current.update(status="running", updated_at=utc_now(), workdir=str(workdir),
                           worktree_path=worktree_path, branch=branch_name)
    started = time.monotonic_ns()
    rc, stdout_text, stderr_text, timed_out = invoke_worker(
        cmd, cwd=workdir, stdin_text=worker_prompt, timeout=timeout,
        run_dir=run_dir, task_id=tid, stream_events=stream_events
    )
    duration_ms = (time.monotonic_ns() - started) // 1000000
    parsed_events = parse_codex_events(stdout_text)
    report = parse_report_file(
        report_path,
        parsed_events["last_agent_text"],
        stderr_text,
        rc,
        event_errors=parsed_events["errors"], protocol_v2=protocol_v2,
    )
    try:
        session_id = context_session(stdout_text,None,False) if board is not None else parsed_events["session_id"]
    except (ValueError, StateIntegrityError):
        if stream_events:
            mark_stream_interrupted(tid, None)
        raise
    sample=invocation_usage("" if stream_events and rc != 0 else stdout_text)
    usage={k:v for k,v in sample["counts"].items() if v is not None} or None
    store=finish_usage(store,sample,duration_ms,"initial")

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
        **protocol_meta(envelope),
        "budget":limits,"usage_store":store,"budget_route":use_budget_route,"stream_events":stream_events,
        **({"stream_integrity": "incomplete" if rc in (124,125,127) else "complete"} if stream_events else {}),
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
        "usage_telemetry":sample,"usage_summary":usage_summary(store),
        "report": report,
        "git_truth": git_truth,
        "run_dir": str(run_dir),
    }
    if envelope is not None:
        result["protocol_result"] = build_protocol_result(envelope,result,duration_ms)
    result_bytes = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(run_dir / "result.json", result_bytes)
    task_record["result_ref"] = {"turn": None, "sha256": hashlib.sha256(result_bytes).hexdigest()}
    if stream_events:
        task_record["stream_checkpoint"] = stream_checkpoint(run_dir,tid,None)
    if board is not None:
        board["last_result_ref"] = task_record["result_ref"]
        task_record.update(context_state_fields(board))
    with locked_state() as state:
        if board is not None:
            context_assert_session_owner(state,tid,session_id,board)
        else:
            context_protect_legacy_session(state,tid,session_id)
        if state["tasks"].get(tid, {}).get("status") != ("running" if stream_events else "reserved"):
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



# D13: opt-in, persistent CLI request reservations. A key is not authorization.
REQUEST_REGISTRY = "dispatch_requests_v1"
REQUEST_LIMIT = 4096

def request_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("ascii")).hexdigest()

def request_records(state: dict[str, Any]) -> dict[str, Any]:
    records = state.get(REQUEST_REGISTRY, {})
    if not isinstance(records, dict) or len(records) > REQUEST_LIMIT:
        raise StateIntegrityError("D13: invalid request registry")
    seen = set()
    for key, op in records.items():
        if (not isinstance(key, str) or not isinstance(op, dict)
                or key != key.casefold()
                or not isinstance(op.get("task_id"), str)
                or op.get("kind") not in ("run", "resume", "review")
                or op.get("status") not in ("pending", "returned", "uncertain")
                or type(op.get("ordinal")) is not int or op["ordinal"] <= 0
                or op["ordinal"] in seen
                or type(op.get("revision")) is not int or op["revision"] <= 0
                or type(op.get("stagnant")) is not int or op["stagnant"] < 0
                or not isinstance(op.get("fingerprint"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", op["fingerprint"])
                or not isinstance(op.get("scope"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", op["scope"])
                or (op["status"] == "returned" and
                    (type(op.get("exit_code")) is not int or op["exit_code"] not in (0, 1)))
                or any(op.get(k) is not None and
                       (not isinstance(op[k], str) or not re.fullmatch(r"[0-9a-f]{64}", op[k]))
                       for k in ("progress", "failure"))):
            raise StateIntegrityError("D13: malformed request entry")
        validate_task_id(key)
        validate_task_id(op["task_id"])
        seen.add(op["ordinal"])
    if seen != set(range(1, len(records) + 1)):
        raise StateIntegrityError("D13: noncontiguous request audit")
    return records

def request_scope(envelope: dict[str, Any]) -> str:
    return request_hash({k: envelope[k] for k in ("goal", "scope", "accept")})

def request_response(key: str, op: dict[str, Any], conflict: bool = False) -> int:
    # Return original operation metadata, never a second worker result or approval.
    print(json.dumps({"request_id": key, "task_id": op["task_id"],
        "operation": op["kind"], "revision": op["revision"],
        "operation_status": op["status"], "duplicate": not conflict,
        "conflict": conflict, "original_exit_code": op.get("exit_code"),
        "result_ref": op.get("result_ref"), "review_id": op.get("review_id"),
        "verification_passed": False}, ensure_ascii=False))
    return op["exit_code"] if not conflict and op["status"] == "returned" else 2

def request_progress(record: dict[str, Any]) -> str | None:
    # Use only independently collected Git metadata, never a model summary.
    # A missing/ambiguous/truncated observation is not evidence of progress.
    ref = record.get("result_ref")
    if not isinstance(ref, dict) or not isinstance(ref.get("sha256"), str):
        raise StateIntegrityError("D13: missing terminal result reference")
    parts = [record["task_id"]]
    if ref.get("turn") is not None:
        parts.append(validate_task_id(ref["turn"]))
    p = bounded_child(RUNS_DIR, *parts) / "result.json"
    reject_link(p)
    with p.open("rb") as f:
        raw = f.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise StateIntegrityError("D13: terminal artifact invalid or oversized")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or data.get("task_id") != record["task_id"] or data.get("turn_id") != ref.get("turn"):
        raise StateIntegrityError("D13: terminal artifact identity mismatch")
    git = data.get("git_truth")
    if (not isinstance(git, dict) or git.get("is_git") is not True
            or git.get("metadata_complete") is not True
            or not isinstance(git.get("head_sha"), str)
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", git["head_sha"]) is None
            or any(not isinstance(git.get(k), str) for k in ("status_short", "diff_stat"))):
        return None
    # Conservative metadata fingerprint: same-size edits can look unchanged.
    return request_hash({k: git[k] for k in ("head_sha", "status_short", "diff_stat")})

def guarded_dispatch(args: argparse.Namespace, handler) -> int:
    kind = args.subcommand
    tid = getattr(args, "task_id", None)
    raw_key = getattr(args, "request_id", None)
    retry = getattr(args, "retry_of", None)
    if raw_key is None:
        if retry is not None:
            raise ValueError("D13: retry requires a new request_id")
        if tid is not None and not args.dry_run:
            with locked_state() as state:
                if any(op["task_id"].casefold() == tid.casefold() for op in request_records(state).values()):
                    raise ValueError("D13: managed keyed task requires request_id")
        return handler(args)
    if args.dry_run:
        raise ValueError("D13: dry-run does not reserve request IDs; omit request_id for preview")
    key = validate_task_id(raw_key).casefold()
    tid = validate_task_id(tid)
    if kind in ("run", "resume"):
        if not args.protocol_v2:
            raise ValueError("D13: keyed worker operations require protocol v2")
        if args.prompt == "-":
            args.prompt = sys.stdin.read(PROTOCOL_LIMIT + 1)
        if not isinstance(args.prompt, str) or len(args.prompt.encode("utf-8")) > PROTOCOL_LIMIT:
            raise ValueError("D13: request exceeds protocol bound")
    params = {k: v for k, v in vars(args).items() if k not in ("request_id",) and not k.startswith("_")}
    if params.get("stream_events") is False:
        params.pop("stream_events")  # preserve D13 request digest on upgrade
    if params.get("cwd") is not None:
        params["cwd"] = str(configured_path(params["cwd"]))
    digest = request_hash(params)
    with locked_state() as state:
        records = request_records(state)
        old = records.get(key)
        if old is not None:
            return request_response(key, old, old["fingerprint"] != digest or old["task_id"] != tid)
        if len(records) >= REQUEST_LIMIT:
            raise StateIntegrityError("D13: request audit full; no automatic deletion")
        previous = sorted((op for op in records.values() if op["task_id"].casefold() == tid.casefold()),
                          key=lambda op: op["ordinal"])
        if any(op["task_id"] != tid for op in previous):
            raise ValueError("D13: task identity is case ambiguous")
        if any(op["status"] != "returned" for op in previous):
            raise ValueError("D13: unresolved operation; reconcile manually, no automatic retry")
        record = state["tasks"].get(tid)
        workers = [op for op in previous if op["kind"] in ("run", "resume")]
        if kind == "run":
            if previous or any(k.casefold() == tid.casefold() for k in state["tasks"]) or retry is not None:
                raise ValueError("D13: initial request requires a new task")
            enforce_execution_policy(args.sandbox, args.network, args.effort)
            envelope = parse_task_envelope(args.prompt, tid, 0)
            scope = request_scope(envelope)
            rev = envelope["rev"]
        else:
            if not workers or not record or record.get("protocol_version") != 2:
                raise ValueError("D13: keyed continuation requires a keyed v2 initial task")
            last = workers[-1]
            if record.get("protocol_rev") != last["revision"] or record.get("status") in ("reserved", "running", "interrupted"):
                raise StateIntegrityError("D13: managed task revision/terminal state changed")
            scope = workers[0]["scope"]
            if kind == "resume":
                validate_resume_binding(record, args)
                enforce_execution_policy(args.sandbox or record["sandbox"], args.network is True, args.effort)
                budget_timeout(record.get("budget", make_budget()),
                               record.get("usage_store", new_usage_store(prior_unknown=True)), args.timeout)
                if record.get("context_board") is not None:
                    envelope, _, _ = context_prepare(args.prompt, record, args.rebuild_context, args.sandbox)
                else:
                    envelope = prepare_resume_envelope(args.prompt, record, True)
                if request_scope(envelope) != scope:
                    raise ValueError("D13: task scope changed; use a reviewed new task")
                rev = envelope["rev"]
                if last["stagnant"] >= 2:
                    raise ValueError("D13: no observed progress in two continuations")
                if last["exit_code"] != 0:
                    # A fresh key does not itself approve retry of an old operation.
                    if (retry is None or records.get(validate_task_id(retry).casefold()) is not last
                            or record.get("process_status") != "failed" or record.get("task_status") != "failed"):
                        raise ValueError("D13: known failed operation needs explicit retry-of; uncertain/partial/timeout not retried")
                    if sum(op.get("retry_of") is not None for op in workers) >= 2:
                        raise ValueError("D13: retry limit reached")
                    if len(workers) >= 2 and last.get("failure") is not None and workers[-2].get("failure") == last["failure"]:
                        raise ValueError("D13: repeated failure signature")
                elif retry is not None:
                    raise ValueError("D13: retry-of requires a failed prior worker operation")
            else:
                if retry is not None:
                    raise ValueError("D13: review does not authorize worker retry")
                if sum(op["kind"] == "review" for op in previous) >= 2:
                    raise ValueError("D13: review limit reached; independent human review required")
                if args.cwd is not None and configured_path(args.cwd) != configured_path(record["workdir"]):
                    raise ValueError("D13: review scope mismatch")
                if args.base is not None and args.base != record.get("base_sha"):
                    raise ValueError("D13: review base mismatch")
                if any(v is not None for v in record.get("budget", make_budget()).values()):
                    raise ValueError("D12: associated review outside managed budget settlement")
                enforce_execution_policy("read-only", False, args.effort)
                rev = record["protocol_rev"]
        op = {"task_id": tid, "kind": kind, "revision": rev, "scope": scope,
              "ordinal": len(records)+1, "fingerprint": digest, "status": "pending",
              "retry_of": retry.casefold() if retry is not None else None,
              "stagnant": 0, "progress": None, "failure": None,
              "created_at": utc_now()}
        records[key] = op
        state[REQUEST_REGISTRY] = records
    # Reservation is durable before handler or child launch. Crash/exception
    # leaves a pending/uncertain operation; no lease expiry may relaunch it.
    try:
        rc = handler(args)
        if type(rc) is not int or rc not in (0, 1):
            raise StateIntegrityError("D13: invalid handler outcome")
        with locked_state() as state:
            records = request_records(state)
            op = records.get(key)
            if op is None or op["status"] != "pending" or op["fingerprint"] != digest:
                raise StateIntegrityError("D13: request reservation changed")
            if kind != "review":
                record = state["tasks"].get(tid)
                if (not record or record.get("protocol_rev") != rev
                        or record.get("status") in ("reserved", "running", "interrupted")):
                    raise StateIntegrityError("D13: missing terminal worker state")
                progress = request_progress(record)
                op["progress"] = progress
                op["result_ref"] = record["result_ref"]
                if rc != 0:
                    op["failure"] = request_hash({k: record.get(k) for k in ("process_status", "task_status", "exit_code")})
                if kind == "resume":
                    op["stagnant"] = last["stagnant"] + 1 if progress is None or progress == last["progress"] else 0
            else:
                op["review_id"] = getattr(args, "_d13_review_id", None)
            op.update(status="returned", exit_code=rc, updated_at=utc_now())
        return rc
    except Exception:
        with locked_state() as state:
            op = request_records(state).get(key)
            if op is not None and op["status"] == "pending" and op["fingerprint"] == digest:
                op.update(status="uncertain", updated_at=utc_now())
        raise

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
        protocol_v2=args.protocol_v2, blackboard=args.blackboard,
        budget=make_budget(args.max_turns,args.max_tokens,args.max_seconds),use_budget_route=args.budget_route,
        request_id=getattr(args, 'request_id', None), stream_events=getattr(args, 'stream_events', False),
    )
    print(json.dumps(result.get("protocol_result",result), ensure_ascii=False, separators=(",",":") if args.protocol_v2 else None, indent=None if args.protocol_v2 else 2))
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
        if "protocol_v2" in item or "envelope" in item or "blackboard" in item:
            raise ValueError("D10: structured protocol is supported on run/resume only; batch stays v1")
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
    limits=task_record.get("budget",make_budget())
    store=task_record.get("usage_store",new_usage_store(prior_unknown=True))
    effective_timeout=budget_timeout(limits,store,args.timeout)
    stream_events=task_record.get("stream_events",False)
    if type(stream_events) is not bool or (stream_events and not args.protocol_v2):
        raise StateIntegrityError("D14: persisted streaming mode or protocol invalid")
    board = None
    if task_record.get("context_board") is not None:
        if not args.protocol_v2:
            raise ValueError("D11: blackboard task requires v2 delta envelope")
        envelope,board,prompt_text=context_prepare(prompt_text,task_record,args.rebuild_context,args.sandbox)
    else:
        if args.rebuild_context:
            raise ValueError("D11: rebuild requires a blackboard task")
        envelope = prepare_resume_envelope(prompt_text,task_record,args.protocol_v2)
        if envelope is not None:
            prompt_text = protocol_prompt(envelope)
    backend = args.backend or task_record["backend"]
    session_id = args.session_id or (task_record["session_id"] if task_record else None)
    if not session_id:
        raise ValueError("No session_id available to resume (pass --session-id or valid --task-id).")
    with locked_state() as state:
        if board is not None:
            context_assert_session_owner(state,task_record["task_id"],session_id,task_record["context_board"])
        else:
            context_protect_legacy_session(state,task_record["task_id"],session_id)

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
            routing = budget_route(args.difficulty,prompt_text,None,args.model,args.effort,args.quality,args.prefer_wide) if task_record.get("budget_route") else resolve_model_and_effort(
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

    if task_record.get("budget_route"):
        validate_cached_route(model_used,effort_used)
        if (model_used,effort_used)!=(task_record.get("model"),task_record.get("effort")):
            if not protocol_text(args.route_reason,320):
                raise ValueError("D12: model/effort change requires explicit route reason")
            context_check_text(args.route_reason)
            routing["change_reason"]=args.route_reason
        elif args.route_reason is not None:
            raise ValueError("D12: route reason supplied without change")
    resume_tid = validate_task_id(args.task_id or make_task_id("resume"))
    turn_id = make_task_id("turn")
    run_dir = bounded_child(RUNS_DIR, resume_tid, turn_id)
    report_path = run_dir / "last_message.json"
    worker_prompt = build_worker_prompt(prompt_text, sandbox=sandbox, network=network, is_resume=not args.rebuild_context)
    if board is not None:
        context_account(board,worker_prompt)
    def resume_command():
        common=dict(codex_bin=get_codex_bin() or "codex",model=model_used,effort=effort_used,sandbox=sandbox,network=network,report_path=report_path,is_git_repo=git_info["is_git_repo"],protocol_v2=args.protocol_v2)
        return build_codex_exec_cmd(workdir=workdir,**common) if args.rebuild_context else build_codex_resume_cmd(session_id=session_id,**common)

    if args.dry_run:
        preview_cmd = resume_command()
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
        if current.get("usage_store",new_usage_store(prior_unknown=True)) != store or current.get("budget",make_budget()) != limits:
            raise StateIntegrityError("D12: usage or budget changed before reservation")
        budget_timeout(limits,store,effective_timeout)
        sequence_base, sequence_scope = prior_stream_sequence(current,resume_tid) if stream_events else (0,"task")
        if envelope is not None:
            if current.get("protocol_rev") != envelope["base_rev"] or current.get("protocol_version") != 2:
                raise StateIntegrityError("D10: revision changed before reservation")
            if board is not None and current.get("context_digest") != task_record.get("context_digest"):
                raise StateIntegrityError("D11: context changed before reservation")
            if board is not None:
                context_assert_session_owner(state,resume_tid,session_id,task_record["context_board"])
            current.update(protocol_meta(envelope))
            current.update(context_state_fields(board))
        if board is None:
            context_protect_legacy_session(state,resume_tid,session_id)
        current["status"] = "running"
        current["active_turn_id"] = turn_id
        current["updated_at"] = utc_now()
    cmd = resume_command()
    started = time.monotonic_ns()
    rc, stdout_text, stderr_text, timed_out = invoke_worker(
        cmd, cwd=workdir, stdin_text=worker_prompt, timeout=effective_timeout,
        run_dir=run_dir, task_id=resume_tid, turn_id=turn_id, stream_events=stream_events,
        sequence_base=sequence_base, sequence_scope=sequence_scope
    )
    duration_ms = (time.monotonic_ns() - started) // 1000000
    parsed_events = parse_codex_events(stdout_text)
    report = parse_report_file(
        report_path,
        parsed_events["last_agent_text"],
        stderr_text,
        rc,
        event_errors=parsed_events["errors"], protocol_v2=args.protocol_v2,
    )
    try:
        new_session_id = context_session(stdout_text,session_id,args.rebuild_context) if board is not None else (parsed_events["session_id"] or session_id)
    except (ValueError, StateIntegrityError):
        if stream_events:
            mark_stream_interrupted(resume_tid, turn_id)
        raise
    sample=invocation_usage("" if stream_events and rc != 0 else stdout_text)
    usage={k:v for k,v in sample["counts"].items() if v is not None} or None
    store=finish_usage(store,sample,duration_ms,turn_id)

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
        "usage_telemetry":sample,"usage_summary":usage_summary(store),
        "report": report,
        "git_truth": git_truth,
        "run_dir": str(run_dir),
    }
    if envelope is not None:
        result["protocol_result"] = build_protocol_result(envelope,result,duration_ms)
    result_bytes = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(run_dir / "result.json", result_bytes)
    with locked_state() as state:
        current = state["tasks"].get(resume_tid)
        if not current or current.get("active_turn_id") != turn_id or current.get("status") != "running":
            raise StateIntegrityError("Resume reservation changed")
        current.update({"model": model_used, "effort": effort_used, "sandbox": sandbox,
            "network": False, "session_id": new_session_id, "exit_code": rc,
            "budget":limits,"usage_store":store,
            "status": "timed_out" if timed_out else outcome["task_status"], **outcome,
            "updated_at": utc_now(), "result_ref": {"turn": turn_id, "sha256": hashlib.sha256(result_bytes).hexdigest()}})
        if board is not None:
            context_assert_session_owner(state,resume_tid,new_session_id,board)
            board["last_result_ref"] = current["result_ref"]
            current.update(context_state_fields(board))
        else:
            context_protect_legacy_session(state,resume_tid,new_session_id)
        if stream_events:
            current["stream_integrity"] = "incomplete" if rc in (124,125,127) else "complete"
            current["stream_checkpoint"] = stream_checkpoint(run_dir,resume_tid,turn_id)
        current.pop("active_turn_id", None)
    print(json.dumps(result.get("protocol_result",result), ensure_ascii=False, separators=(",",":") if envelope else None, indent=None if envelope else 2))
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

    if task_record and any(v is not None for v in task_record.get("budget",make_budget()).values()):
        raise ValueError("D12: associated review is outside managed budget settlement; use reviewed managed resume")

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
    args._d13_review_id = review_id
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
            usage_store=rec.pop("usage_store",None)
            if usage_store is not None:
                rec["usage_summary"]=usage_summary(usage_store)
                rec["usage_summary"]["pending"]=rec.get("status") in ("reserved","running","interrupted")
                if rec["usage_summary"]["pending"]:
                    rec["usage_summary"]["counts"]={k:None for k in USAGE_FIELDS}
            board = rec.pop("context_board",None)
            if board is not None:
                rec["context"] = {k:board[k] for k in ("rev","generation","turns","prompt_bytes")}
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
    p_run.add_argument("--request-id", default=None, help="Persistent D13 operation ID (v2 only).")
    p_run.add_argument("--stream-events", action="store_true", help="D14 bounded streaming (explicit v2 only; inherited by resume).")
    p_run.add_argument("--max-turns", type=int, default=None)
    p_run.add_argument("--max-tokens", type=int, default=None)
    p_run.add_argument("--max-seconds", type=int, default=None)
    p_run.add_argument("--budget-route", action="store_true", help="Use only cached model/effort capabilities.")
    p_run.add_argument("--blackboard", action="store_true", help="Opt-in task-local context with v2 protocol.")
    p_run.add_argument("--protocol-v2", action="store_true", help="Experimental bounded v2 JSON envelope via --prompt; default remains v1.")
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
    p_res.add_argument("--request-id", default=None)
    p_res.add_argument("--retry-of", default=None, help="Explicit previous failed request; not an authorization grant.")
    p_res.add_argument("--route-reason", default=None, help="Required for model/effort changes of budget-routed tasks.")
    p_res.add_argument("--rebuild-context", action="store_true", help="Explicit new session with reviewed checkpoint; blackboard only.")
    p_res.add_argument("--protocol-v2", action="store_true", help="Continue an existing v2 task using the next revision envelope.")
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
    p_rev.add_argument("--request-id", default=None)
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

    for operation in ("state-migrate","state-rollback"):
        p_storage=sub.add_parser(operation,allow_abbrev=False,help="Explicit offline state migration/rollback; stop all CLI/MCP instances first.")
        p_storage.add_argument("--confirm-quiescent",action="store_true")
    p_recover=sub.add_parser("state-recover",allow_abbrev=False,help="Export validated recovery backup without activating it.")
    p_recover.add_argument("--source",choices=("initial","previous"),default="previous")

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
        "state-migrate": cmd_state_storage,
        "state-rollback": cmd_state_storage,
        "state-recover": cmd_state_storage,
    }
    try:
        if args.subcommand in ('run', 'resume', 'review'):
            return guarded_dispatch(args, handlers[args.subcommand])
        return handlers[args.subcommand](args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
