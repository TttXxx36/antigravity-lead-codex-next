"""D15 disposable state tests; no real model or production data."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py"
spec=importlib.util.spec_from_file_location("d15",SOURCE)
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
BOOT="import importlib.util,sys,os; s=importlib.util.spec_from_file_location('d',sys.argv[1]);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)\n"

class StoreTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="d15-")
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name);self.root=self.home/"状态 空格";self.native=self.home/"native";self.native.mkdir()
        paths=patch.multiple(d,STATE_DIR=self.root,STATE_FILE=self.root/"state.json",LOCK_FILE=self.root/"state.lock",
            RUNS_DIR=self.root/"runs",WORKTREES_DIR=self.root/"worktrees",CODEX_HOME=self.native)
        paths.start();self.addCleanup(paths.stop)
        self.env=dict(os.environ,AGY_DISPATCH_STATE_DIR=str(self.root),CODEX_HOME=str(self.native),PYTHONUTF8="1")
        with d.locked_state() as data:
            data["rr_counter"]=2
            data["tasks"]["task-a"]={"task_id":"task-a","status":"completed","note":"中文","usage_store":d.new_usage_store()}
            data["extra"]={"preserve":["unknown",1]}
        self.original=d.STATE_FILE.read_bytes()
    def command(self,*args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.cmd_state_storage(d.build_parser().parse_args(list(args))),0)
        return json.loads(out.getvalue())
    def migrate(self):
        return self.command("state-migrate","--confirm-quiescent")
    def snapshot(self):
        with d.locked_state() as data:return json.loads(json.dumps(data))
    def marker(self):return d.storage_marker(d.STATE_FILE.read_bytes())
    def worker(self,code):
        return subprocess.Popen([sys.executable,"-I","-c",BOOT+code,str(SOURCE)],env=self.env,cwd=self.home,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def test_roundtrip_backup_idempotent_and_native_unchanged(self):
        native=self.native/"state_5.sqlite"
        with contextlib.closing(sqlite3.connect(native)) as db, db:
            db.execute("CREATE TABLE sentinel(value TEXT)");db.execute("INSERT INTO sentinel VALUES('keep')")
        before=native.read_bytes()
        m=self.migrate();marker=self.marker()
        self.assertEqual(m["status"],"migrated")
        self.assertEqual((self.root/marker["backup"]).read_bytes(),self.original)
        with self.assertRaises(ValueError):d.decode_state(d.STATE_FILE.read_bytes())
        self.assertEqual(self.command("state-migrate","--confirm-quiescent")["database"],m["database"])
        self.assertEqual(self.snapshot(),d.decode_state(self.original))
        with d.locked_state() as data:data["tasks"]["task-a"]["note"]="new"
        current=self.snapshot()
        self.assertEqual(self.command("state-rollback","--confirm-quiescent")["status"],"rolled_back")
        self.assertEqual(d.decode_state(d.STATE_FILE.read_bytes()),current)
        self.assertTrue((self.root/m["database"]).is_file())
        self.assertEqual(native.read_bytes(),before)
    def test_concurrent_transactions(self):
        self.migrate()
        code="""for i in range(5):
    with d.locked_state() as data:
        data['rr_counter']+=1
        data['tasks'][f'worker-{os.getpid()}-{i}']={'status':'completed'}
"""
        ps=[self.worker(code) for _ in range(3)]
        try:
            for p in ps:
                _,err=p.communicate(timeout=40);self.assertEqual(p.returncode,0,err.decode("utf8","replace"))
        finally:
            for p in ps:
                if p.poll() is None:p.kill()
                p.communicate()
        current=self.snapshot()
        self.assertEqual(current["rr_counter"],17);self.assertEqual(len(current["tasks"]),16)
    def test_abrupt_exit_before_commit(self):
        self.migrate()
        code="""original=d.store_write
def crash(*args,**kwargs):
    original(*args,**kwargs)
    os._exit(17)
d.store_write=crash
with d.locked_state() as data:
    data['rr_counter']=99
    data['tasks']['crash']={'status':'completed'}
"""
        p=self.worker(code)
        _,err=p.communicate(timeout=30);self.assertEqual(p.returncode,17,err.decode("utf8","replace"))
        current=self.snapshot();self.assertEqual(current["rr_counter"],2);self.assertNotIn("crash",current["tasks"])
    def test_publish_failure_leaves_json_and_retry(self):
        original=d.atomic_write_bytes
        def fail(target,payload):
            if target==d.STATE_FILE:raise OSError("fixture publish failure")
            return original(target,payload)
        with patch.object(d,"atomic_write_bytes",side_effect=fail):
            with self.assertRaises(OSError):self.migrate()
        self.assertEqual(d.STATE_FILE.read_bytes(),self.original)
        self.assertEqual(len(list(self.root.glob("dispatch-state-*.sqlite"))),1)
        self.assertEqual(self.migrate()["status"],"migrated")
        self.assertEqual(self.snapshot(),d.decode_state(self.original))
    def test_corruption_no_fallback_recovery_export(self):
        self.migrate()
        with d.locked_state() as data:data["rr_counter"]=3
        marker=self.marker();raw=d.STATE_FILE.read_bytes()
        with contextlib.closing(sqlite3.connect(self.root/marker["database"])) as db, db:
            db.execute("UPDATE dispatch_tasks SET payload_sha256='invalid' WHERE task_id='task-a'")
        with self.assertRaises(d.StateIntegrityError):self.snapshot()
        with self.assertRaises(d.StateIntegrityError):self.command("state-rollback","--confirm-quiescent")
        for source in ("initial","previous"):
            rec=self.command("state-recover","--source",source)
            self.assertEqual(rec["status"],"recovery_exported_not_activated")
            self.assertEqual(d.decode_state((self.root/rec["file"]).read_bytes())["rr_counter"],2)
        self.assertEqual(d.STATE_FILE.read_bytes(),raw)
    def test_quiescent_and_native_path_gate(self):
        with self.assertRaises(ValueError):self.command("state-migrate")
        with d.locked_state() as data:data["tasks"]["task-a"]["status"]="running"
        with self.assertRaises(d.StateIntegrityError):self.migrate()
        with d.locked_state() as data:data["tasks"]["task-a"]["status"]="completed"
        with patch.object(d,"CODEX_HOME",self.root):
            with self.assertRaises(d.StateIntegrityError):self.migrate()
        self.assertFalse(list(self.root.glob("dispatch-state-*.sqlite")))
    def test_request_registry_and_no_automatic_deletion(self):
        key="req-a"
        op={"task_id":"task-a","kind":"run","revision":1,"scope":"1"*64,"ordinal":1,
            "fingerprint":"2"*64,"status":"returned","stagnant":0,"progress":None,"failure":None,
            "exit_code":0}
        with d.locked_state() as data:data[d.REQUEST_REGISTRY]={key:op}
        self.migrate()
        self.assertEqual(d.request_records(self.snapshot())[key],op)
        with self.assertRaises(d.StateIntegrityError):
            with d.locked_state() as data:data["tasks"].pop("task-a")
        self.assertIn("task-a",self.snapshot()["tasks"])

    def test_keyed_stream_worker_and_resume_in_sqlite(self):
        self.migrate()
        work=self.home/"work";work.mkdir()
        original=d.streamed_subprocess
        calls=[]
        def boundary(cmd,**kw):
            calls.append(kw["turn_id"])
            return original([sys.executable,"-I",str(ROOT/"tests/mock_codex.py"),*cmd[1:]],
                            **kw,env=dict(os.environ,ALC_MOCK_USAGE="fixture",ALC_MOCK_CASE="B01"))
        def envelope(rev):
            return json.dumps(dict(version=2,task_id="task-b",rev=rev,base_rev=rev-1,goal="fix",
                scope=["answer.txt"],accept=["test"],delta="" if rev==1 else "next"))
        run=["run","--task-id","task-b","--request-id","req-b1","--protocol-v2","--stream-events",
             "--cwd",str(work),"--isolation","inplace","--model","mock-model","--effort","low","--max-tokens","100","--prompt",envelope(1)]
        resume=["resume","--task-id","task-b","--request-id","req-b2","--protocol-v2",
                "--model","mock-model","--effort","low","--prompt",envelope(2)]
        with patch.object(d,"get_codex_bin",return_value="D15_MOCK_ONLY"), \
             patch.object(d,"resolve_model_and_effort",return_value=dict(model="mock-model",effort="low",effective_difficulty="low")), \
             patch.object(d,"streamed_subprocess",side_effect=boundary):
            for args,handler in ((run,d.cmd_run),(run,d.cmd_run),(resume,d.cmd_resume),(resume,d.cmd_resume)):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(d.guarded_dispatch(d.build_parser().parse_args(args),handler),0)
        self.assertEqual(len(calls),2)
        state=self.snapshot()
        task=state["tasks"]["task-b"]
        self.assertEqual(task["status"],"completed")
        self.assertEqual(task["protocol_rev"],2)
        self.assertEqual(task["usage_store"]["known_sums"]["total_tokens"],30)
        self.assertEqual(task["stream_integrity"],"complete")
        requests=d.request_records(state)
        self.assertEqual(requests["req-b1"]["status"],"returned")
        self.assertEqual(requests["req-b2"]["status"],"returned")
        self.assertEqual(self.command("state-rollback","--confirm-quiescent")["status"],"rolled_back")
        self.assertEqual(d.decode_state(d.STATE_FILE.read_bytes()),state)

if __name__=="__main__":unittest.main()
