"""D17 real interprocess, filesystem and Git fixtures. Never invokes a real model."""
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
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py"
spec=importlib.util.spec_from_file_location("d17",SOURCE)
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
BOOT="import importlib.util,sys,os,time,pathlib; s=importlib.util.spec_from_file_location('d',sys.argv[1]);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)\n"
WORKER="""
tid,cwd,gate,started=sys.argv[2:]
with d.scheduler_admission('run',tid,pathlib.Path(cwd)) as lease:
    pathlib.Path(started).write_text(lease['ticket'])
    until=time.monotonic()+20
    while not pathlib.Path(gate).exists():
        if time.monotonic()>until:raise RuntimeError('fixture gate timeout')
        time.sleep(.03)
    lease['settled']=True
"""

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="d17-");self.addCleanup(temp.cleanup)
        self.home=Path(temp.name);self.root=self.home/"状态 空格";self.root.mkdir()
        self.work=self.home/"work";self.work.mkdir()
        self.other=self.home/"other";self.other.mkdir()
        self.paths=patch.multiple(d,STATE_DIR=self.root,STATE_FILE=self.root/"state.json",LOCK_FILE=self.root/"state.lock",
            RUNS_DIR=self.root/"runs",WORKTREES_DIR=self.root/"worktrees",CODEX_HOME=self.home/"native")
        self.paths.start();self.addCleanup(self.paths.stop)
        self.env=dict(os.environ,AGY_DISPATCH_STATE_DIR=str(self.root),CODEX_HOME=str(self.home/"native"),PYTHONUTF8="1")
        self.config()
        self.ps=[];self.addCleanup(self.stop)
    def config(self,quota=80,wait=8,minfree=0,slots=2):
        cfg={"version":1,"max_slots":slots,"max_wait_seconds":wait,"min_free_bytes":minfree,
             "quota":None if quota is None else {"remaining_percent":quota,"observed_at":int(time.time())}}
        d.atomic_write_bytes(self.root/"scheduler.json",json.dumps(cfg).encode())
    def stop(self):
        for p in self.ps:
            if p.poll() is None:p.kill()
            p.communicate(timeout=10)
    def worker(self,tid,cwd):
        started=self.home/(tid+".started");gate=self.home/(tid+".gate")
        p=subprocess.Popen([sys.executable,"-I","-c",BOOT+WORKER,str(SOURCE),tid,str(cwd),str(gate),str(started)],
            env=self.env,cwd=self.home,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.ps.append(p)
        return p,started,gate
    def wait_for(self,fn,seconds=10):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            val=fn()
            if val:return val
            time.sleep(.05)
        self.fail("fixture timeout")
    def ticket(self,tid,status=None):
        with d.locked_state() as state:
            return next(((key,rec.copy()) for key,rec in d.scheduler_registry(state)["tickets"].items()
                         if rec["task_id"]==tid and (status is None or rec["status"]==status)),None)
    def finish(self,worker):
        p,started,gate=worker;gate.touch()
        _,err=p.communicate(timeout=15);self.assertEqual(p.returncode,0,err.decode("utf8","replace"))
    def git(self,cwd,*args):
        return subprocess.check_output(["git","-C",str(cwd),*args],stderr=subprocess.STDOUT,text=True,encoding="utf8").strip()
    def init_repo(self,cwd):
        self.git(cwd,"init");self.git(cwd,"config","user.name","fixture");self.git(cwd,"config","user.email","fixture@example.invalid")
        (cwd/"a.txt").write_text("base");self.git(cwd,"add",".");self.git(cwd,"commit","-m","base")
    def test_independent_parallel_fifo_and_same_scope(self):
        a=self.worker("a",self.work);self.wait_for(a[1].exists)
        b=self.worker("b",self.other);self.wait_for(b[1].exists)
        c=self.worker("c",self.work);self.wait_for(lambda:self.ticket("c","queued"))
        self.assertFalse(c[1].exists())
        e=self.worker("e",self.other);self.wait_for(lambda:self.ticket("e","queued"))
        self.finish(b);time.sleep(.3)
        self.assertFalse(e[1].exists(),"FIFO must not overtake conflicting older queued work")
        self.finish(a);self.wait_for(c[1].exists);self.wait_for(e[1].exists)
        self.finish(c);self.finish(e)
        self.assertEqual(self.ticket("c")[1]["status"],"released")
    def test_common_git_directory_conflicts(self):
        self.init_repo(self.work)
        wt=self.home/"linked";self.git(self.work,"worktree","add","-b","fixture-wt",str(wt))
        a=self.worker("a",self.work);self.wait_for(a[1].exists)
        b=self.worker("b",wt);self.wait_for(lambda:self.ticket("b","queued"))
        self.wait_for(lambda:self.ticket("b")[1]["reason"]=="scope_conflict")
        self.assertFalse(b[1].exists());self.finish(a);self.wait_for(b[1].exists);self.finish(b)
    def test_low_quota_queue_cancel_and_unknown_conservative(self):
        self.config(quota=5)
        a=self.worker("a",self.work)
        key,rec=self.wait_for(lambda:self.ticket("a","queued"))
        self.wait_for(lambda:self.ticket("a")[1]["reason"]=="quota_low")
        with contextlib.redirect_stdout(io.StringIO()):
            d.scheduler_status_cmd(d.build_parser().parse_args(["scheduler-cancel","--ticket",key]))
        _,err=a[0].communicate(timeout=15)
        self.assertNotEqual(a[0].returncode,0);self.assertFalse(a[1].exists())
        self.assertEqual(self.ticket("a")[1]["status"],"cancelled")
        self.config(quota=None)
        b=self.worker("b",self.work);self.wait_for(b[1].exists)
        c=self.worker("c",self.other);self.wait_for(lambda:self.ticket("c","queued"))
        self.assertFalse(c[1].exists());self.finish(b);self.wait_for(c[1].exists);self.finish(c)
    def test_disk_pressure_and_queue_timeout(self):
        self.config(wait=1,minfree=2**50)
        a=self.worker("a",self.work);self.wait_for(lambda:self.ticket("a","queued"))
        self.wait_for(lambda:self.ticket("a")[1]["reason"]=="disk_pressure")
        _,err=a[0].communicate(timeout=15);self.assertNotEqual(a[0].returncode,0)
        self.assertFalse(a[1].exists());self.assertEqual(self.ticket("a")[1]["status"],"cancelled")
    def test_active_exception_sticky_no_reclaim_and_migration_gate(self):
        with self.assertRaises(RuntimeError):
            with d.scheduler_admission("run","a",self.work):
                raise RuntimeError("fixture interrupted")
        self.assertEqual(self.ticket("a")[1]["status"],"uncertain")
        with d.locked_state() as state:
            with self.assertRaises(d.StateIntegrityError):d.require_storage_quiescent(state)
        (self.root/"scheduler.json").unlink()
        with self.assertRaises(d.StateIntegrityError):
            with d.scheduler_admission("run","b",self.other):self.fail("bypassed")
    def test_batch_dependency_and_cycle_prelaunch(self):
        calls=[]
        def execute(**kw):
            tid=kw["task_id"];calls.append(tid)
            return {"task_id":tid,"task_status":"failed" if tid=="a" else "completed","exit_code":1 if tid=="a" else 0}
        manifest=self.home/"manifest.json"
        manifest.write_text(json.dumps([{"task_id":"a","prompt":"a"},{"task_id":"b","prompt":"b","depends_on":["a"]},{"task_id":"c","prompt":"c","depends_on":["b"]}]))
        args=d.build_parser().parse_args(["batch","--manifest",str(manifest)])
        with patch.object(d,"execute_single_task",side_effect=execute),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.cmd_batch(args),1)
        self.assertEqual(calls,["a"])
        self.assertEqual([x["process_status"] for x in json.loads(out.getvalue())["results"][1:]],["not_started","not_started"])
        manifest.write_text(json.dumps([{"task_id":"a","prompt":"a","depends_on":["b"]},{"task_id":"b","prompt":"b","depends_on":["a"]}]))
        with patch.object(d,"execute_single_task") as run,self.assertRaises(ValueError):d.cmd_batch(args)
        run.assert_not_called()
    def test_cleanup_never_removes_dirty_or_unmerged_work(self):
        self.init_repo(self.work)
        d.ensure_state_dirs()
        wt=d.WORKTREES_DIR/"repo"/"task-1";wt.parent.mkdir()
        self.git(self.work,"worktree","add","-b","agy-worker/task-1",str(wt))
        (wt/"new.txt").write_text("unmerged");self.git(wt,"add",".");self.git(wt,"commit","-m","worker")
        (wt/"dirty.txt").write_text("preserve")
        with d.locked_state() as state:
            state["tasks"]["task-1"]={"task_id":"task-1","status":"completed","repo_root":str(self.work),
                "worktree_path":str(wt),"branch":"agy-worker/task-1","verification_status":"passed","verification_passed":True}
        args=d.build_parser().parse_args(["cleanup","--task-id","task-1"])
        with patch.object(d,"remove_worktree") as remove,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.cmd_cleanup(args),1)
        remove.assert_not_called();result=json.loads(out.getvalue())
        self.assertIn("dirty_untracked_or_ignored_files",result["blockers"])
        self.assertIn("unmerged_or_unknown_commits",result["blockers"])
        self.assertTrue((wt/"dirty.txt").is_file());self.assertTrue((wt/"new.txt").is_file())
        self.assertEqual(self.git(wt,"symbolic-ref","--short","HEAD"),"agy-worker/task-1")
if __name__=="__main__":unittest.main()
