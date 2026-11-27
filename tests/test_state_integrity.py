"""D04: real filesystem/process regression, never calls a model."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/multi-agent-dispatch/scripts/dispatch.py"
spec = importlib.util.spec_from_file_location("d04_dispatch", SOURCE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

BOOT = """
import importlib.util, sys, time, os
from pathlib import Path
s=importlib.util.spec_from_file_location('d',sys.argv[1]);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
"""


class StateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="d04-state-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "状态 空格"
        self.paths = patch.multiple(d, STATE_DIR=self.root, STATE_FILE=self.root/"state.json",
            LOCK_FILE=self.root/"state.lock", RUNS_DIR=self.root/"runs", WORKTREES_DIR=self.root/"worktrees")
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.env = {k: os.environ[k] for k in ("PATH","SystemRoot","WINDIR","TEMP","TMP") if k in os.environ}
        self.env.update(HOME=self.tmp.name, USERPROFILE=self.tmp.name, CODEX_HOME=self.tmp.name,
            AGY_DISPATCH_STATE_DIR=str(self.root), GEMINI_CONFIG_DIR=self.tmp.name, PYTHONUTF8="1")
        d.ensure_state_dirs()

    def worker(self, code):
        p = subprocess.Popen([sys.executable,"-I","-c",BOOT+code,str(SOURCE)], env=self.env,
            cwd=self.tmp.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop, p)
        return p

    @staticmethod
    def stop(p):
        if p.poll() is None:
            p.kill()
        p.communicate(timeout=15)

    def test_corrupt_bytes_unchanged_and_copied(self):
        for raw in (b"{broken", b"[]", b'{"tasks":[]}', b'{"tasks":{},"rr_counter":true}', b'{"tasks":{},"tasks":{}}', b'{"tasks":{},"rr_counter":NaN}', b"\xff"):
            with self.subTest(raw=raw):
                d.STATE_FILE.write_bytes(raw)
                with self.assertRaises(d.StateIntegrityError):
                    with d.locked_state() as state:
                        self.fail("corrupt state yielded")
                self.assertEqual(d.STATE_FILE.read_bytes(), raw)
                self.assertIn(raw, [p.read_bytes() for p in self.root.glob("state.corrupt-*.json")])

    def test_previous_valid_bytes_backed_up(self):
        with d.locked_state() as state:
            state["rr_counter"] = 1
        previous = d.STATE_FILE.read_bytes()
        with d.locked_state() as state:
            state["rr_counter"] = 2
        self.assertEqual(d.STATE_FILE.with_suffix(".json.bak").read_bytes(), previous)
        self.assertEqual(json.loads(d.STATE_FILE.read_bytes())["rr_counter"], 2)

    def test_failed_atomic_replace_preserves_state(self):
        with d.locked_state() as state:
            state["rr_counter"] = 1
        original = d.STATE_FILE.read_bytes()
        real_replace = os.replace
        def fail_state(src, dst):
            if Path(dst) == d.STATE_FILE:
                raise OSError("synthetic replacement failure")
            return real_replace(src,dst)
        with patch.object(d.os, "replace", side_effect=fail_state):
            with self.assertRaises(OSError):
                with d.locked_state() as state:
                    state["rr_counter"] = 2
        self.assertEqual(d.STATE_FILE.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_portable_ids_and_path_traversal(self):
        for bad in ("", ".", "..", "../outside", r"a\b", "a/b", "C:drive", "NUL", "CON.txt",
                    "COM1", "name.", "name.lock", "a..b", "a b", "a"*81):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                d.reserve_run_dir(bad)
        self.assertEqual(list(d.RUNS_DIR.iterdir()), [])
        self.assertEqual(d.reserve_run_dir("valid-01").name,"valid-01")

    def test_duplicate_and_orphan_rejected(self):
        d.reserve_run_dir("Task-1", {"backend":"mock"})
        with self.assertRaises(ValueError):
            d.reserve_run_dir("task-1")
        (d.RUNS_DIR/"orphan").mkdir()
        with self.assertRaises(ValueError):
            d.reserve_run_dir("orphan")
        self.assertEqual(json.loads(d.STATE_FILE.read_bytes())["tasks"]["Task-1"]["status"],"reserved")

    def test_duplicate_reservation_across_processes(self):
        code = """
try:
    d.reserve_run_dir('race', {'backend':'mock'})
    sys.exit(0)
except ValueError:
    sys.exit(17)
"""
        workers = [self.worker(code) for _ in range(4)]
        for p in workers:
            _, err = p.communicate(timeout=45)
            self.assertIn(p.returncode,(0,17),err.decode("utf8","replace"))
        self.assertEqual(sorted(p.returncode for p in workers),[0,17,17,17])
        self.assertEqual(len(json.loads(d.STATE_FILE.read_bytes())["tasks"]),1)

    def test_crash_releases_lock_preserves_old_state(self):
        with d.locked_state() as state:
            state["rr_counter"]=8
        ready = self.root/"ready"
        p = self.worker("""
with d.locked_state() as state:
    state['rr_counter']=999
    (d.STATE_DIR/'ready').write_text('yes',encoding='utf-8')
    time.sleep(60)
""")
        deadline=time.monotonic()+15
        while not ready.exists() and p.poll() is None and time.monotonic()<deadline:
            time.sleep(.05)
        self.assertTrue(ready.exists())
        with self.assertRaises(TimeoutError):
            with d.exclusive_state_lock(d.LOCK_FILE,timeout=.15):
                self.fail("lock acquired while held")
        p.kill()
        p.communicate(timeout=15)
        with d.locked_state() as state:
            self.assertEqual(state["rr_counter"],8)
            state["rr_counter"]=9
        self.assertEqual(json.loads(d.STATE_FILE.read_bytes())["rr_counter"],9)

    def test_link_escape_rejected_when_supported(self):
        outside=Path(self.tmp.name)/"outside"
        outside.mkdir()
        link=d.RUNS_DIR/"escape"
        try:
            link.symlink_to(outside,target_is_directory=True)
        except OSError:
            self.skipTest("runner does not permit symlink creation")
        with self.assertRaises((ValueError,d.StateIntegrityError)):
            d.bounded_child(d.RUNS_DIR,"escape","child")
        self.assertEqual(list(outside.iterdir()),[])

    def test_invalid_state_blocks_worker_before_cli(self):
        d.STATE_FILE.write_bytes(b"{broken")
        route={"model":"mock","effort":"low","effective_difficulty":"low"}
        git={"is_git_repo":False,"repo_root":None,"head_sha":None}
        with patch.object(d,"get_codex_bin",return_value=sys.executable), patch.object(d,"inspect_git",return_value=git), patch.object(d,"resolve_model_and_effort",return_value=route), patch.object(d,"run_subprocess_with_timeout") as run:
            with self.assertRaises(d.StateIntegrityError):
                d.execute_single_task(prompt="synthetic",cwd=Path(self.tmp.name),backend="codex",
                    difficulty="low",model="mock",effort="low",quality="balanced",alternate=False,
                    prefer_wide=False,sandbox="workspace-write",network=False,isolation="inplace",timeout=3,
                    files_hint=None,task_id="blocked",dry_run=False)
            run.assert_not_called()


    def test_dispatch_resume_and_duplicate_with_real_mock_process(self):
        mock = ROOT / "tests/mock_codex.py"
        work = Path(self.tmp.name) / "项目"
        work.mkdir()
        route = {"model":"mock","effort":"low","effective_difficulty":"low"}
        original = d.run_subprocess_with_timeout
        calls = []
        def boundary(cmd, **kwargs):
            self.assertEqual(cmd[0], "MOCK_ONLY")
            self.assertEqual(cmd[1], "exec")
            calls.append(cmd[2])
            kwargs["env"] = dict(self.env, ALC_MOCK_CASE="B01")
            return original([sys.executable,"-I",str(mock),*cmd[1:]],**kwargs)
        with patch.object(d,"get_codex_bin",return_value="MOCK_ONLY"), patch.object(d,"resolve_model_and_effort",return_value=route), patch.object(d,"run_subprocess_with_timeout",side_effect=boundary):
            def dispatch():
                return d.execute_single_task(prompt="synthetic",cwd=work,backend="codex",
                    difficulty="low",model="mock",effort="low",quality="balanced",alternate=False,
                    prefer_wide=False,sandbox="workspace-write",network=False,isolation="inplace",
                    timeout=15,files_hint=None,task_id="mock-task",dry_run=False)
            result = dispatch()
            self.assertEqual(result["exit_code"],0)
            self.assertEqual(result["report"]["status"],"completed")
            self.assertEqual(result["task_status"],"completed")
            self.assertFalse(result["verification_passed"])
            self.assertEqual(result["verification_status"],"unknown")
            # Legacy network request is deliberately not inherited on resume.
            with d.locked_state() as state:
                state["tasks"]["mock-task"]["network"] = True
            with self.assertRaises(ValueError):
                dispatch()
            self.assertEqual(len(calls),1)
            args = d.build_parser().parse_args(["resume","--task-id","mock-task","--prompt","synthetic followup"])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(d.cmd_resume(args),0)
            resumed = json.loads(output.getvalue())
            self.assertEqual(resumed["session_id"],result["session_id"])
            self.assertFalse(resumed["network"])
            self.assertFalse(resumed["verification_passed"])
            self.assertEqual(len(calls),2)
            self.assertEqual((work/"answer.txt").read_text(encoding="utf-8"),"mock resume\n")
            self.assertTrue((Path(resumed["run_dir"])/"result.json").is_file())
            state=json.loads(d.STATE_FILE.read_bytes())
            self.assertEqual(state["tasks"]["mock-task"]["status"],"completed")
            self.assertEqual(len(state["tasks"]),1)

    def test_resume_lock_refuses_parallel_resume(self):
        d.reserve_run_dir("resume-race", {"backend":"mock"})
        root=d.RUNS_DIR/"resume-race"
        args=d.build_parser().parse_args(["resume","--task-id","resume-race","--prompt","synthetic"])
        with d.exclusive_state_lock(root/"resume.lock"):
            with patch.object(d,"_cmd_resume") as handler:
                with self.assertRaises(TimeoutError):
                    d.cmd_resume(args)
                handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
