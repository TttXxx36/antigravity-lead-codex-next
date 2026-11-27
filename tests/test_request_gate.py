"""D13: real local processes with deterministic CLI mock only."""
import importlib.util
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
spec=importlib.util.spec_from_file_location("d13",ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

def setup(root):
    d.STATE_DIR=root/"state";d.STATE_FILE=d.STATE_DIR/"state.json";d.LOCK_FILE=d.STATE_DIR/"state.lock"
    d.RUNS_DIR=d.STATE_DIR/"runs";d.WORKTREES_DIR=d.STATE_DIR/"worktrees"

def envelope(tid,rev=1,goal="fix",scope=None):
    return json.dumps(dict(version=2,task_id=tid,rev=rev,base_rev=rev-1,
        goal=goal,scope=scope or ["answer.txt"],accept=["test"],delta="" if rev==1 else "next"))

def worker(root, argv):
    setup(root)
    args=d.build_parser().parse_args(argv)
    original=d.run_subprocess_with_timeout
    def boundary(cmd, **kw):
        with (root/"launches").open("a",encoding="utf-8") as f:
            f.write("launch\n")
        time.sleep(.4)
        return original([sys.executable,"-I",str(ROOT/"tests/mock_codex.py"),*cmd[1:]],**kw)
    handlers={"run":d.cmd_run,"resume":d.cmd_resume,"review":d.cmd_review}
    route=dict(model="mock-model",effort="low",effective_difficulty="low")
    try:
        with patch.object(d,"get_codex_bin",return_value="D13_MOCK_ONLY"), patch.object(d,"resolve_model_and_effort",return_value=route), patch.object(d,"run_subprocess_with_timeout",side_effect=boundary):
            return d.guarded_dispatch(args,handlers[args.subcommand])
    except Exception as exc:
        print(json.dumps({"error":str(exc)}))
        return 2

class RequestGateTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);setup(self.root)
        self.cwd=self.root/"work";self.cwd.mkdir()
    def run_args(self,key="req-1",tid="task-1",goal="fix"):
        return ["run","--request-id",key,"--task-id",tid,"--protocol-v2","--cwd",str(self.cwd),"--isolation","inplace","--model","mock-model","--effort","low","--prompt",envelope(tid,goal=goal)]
    def resume_args(self,key,rev,extra=()):
        return ["resume","--request-id",key,"--task-id","task-1","--protocol-v2","--prompt",envelope("task-1",rev),"--model","mock-model","--effort","low",*extra]
    def start(self,args,case="B01"):
        env=os.environ.copy();env["ALC_MOCK_CASE"]=case
        return subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--worker",str(self.root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",env=env)
    def finish(self,p):
        out,err=p.communicate(timeout=30)
        return p.returncode,out,err
    def calls(self):
        p=self.root/"launches"
        return len(p.read_text().splitlines()) if p.exists() else 0
    def test_concurrent_duplicate_restart_and_conflict(self):
        p=self.start(self.run_args());q=self.start(self.run_args())
        a,b=self.finish(p),self.finish(q)
        self.assertIn(0,(a[0],b[0]),(a,b))
        self.assertEqual(self.calls(),1,(a,b))
        rc,out,err=self.finish(self.start(self.run_args()))
        self.assertEqual(rc,0,(out,err));self.assertTrue(json.loads(out)["duplicate"])
        for args in (self.run_args(goal="other"),self.run_args(tid="task-2")):
            rc,out,err=self.finish(self.start(args))
            self.assertEqual(rc,2,(out,err));self.assertTrue(json.loads(out)["conflict"])
        self.assertEqual(self.calls(),1)
    def test_pending_reservation_crash_blocks_restart(self):
        args=d.build_parser().parse_args(self.run_args())
        def interrupted(_):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            d.guarded_dispatch(args,interrupted)
        rc,out,err=self.finish(self.start(self.run_args()))
        self.assertEqual(rc,2,(out,err));self.assertEqual(json.loads(out)["operation_status"],"pending")
        self.assertEqual(self.finish(self.start(self.run_args("different")))[0],2)
        self.assertEqual(self.calls(),0)
    def test_no_progress_and_unkeyed_continuation(self):
        a=self.finish(self.start(self.run_args()));self.assertEqual(a[0],0,a)
        legacy=self.resume_args("req-2",2);del legacy[1:3]
        self.assertEqual(self.finish(self.start(legacy))[0],2)
        for rev in (2,3):
            a=self.finish(self.start(self.resume_args("req-"+str(rev),rev)));self.assertEqual(a[0],0,a)
        self.assertEqual(self.finish(self.start(self.resume_args("req-4",4)))[0],2)
        self.assertEqual(self.calls(),3)
    def test_failure_requires_retry_and_repeated_failure_stops(self):
        a=self.finish(self.start(self.run_args(),case="B04"));self.assertEqual(a[0],1,a)
        self.assertEqual(self.finish(self.start(self.resume_args("r2",2),case="B04"))[0],2)
        a=self.finish(self.start(self.resume_args("r2",2,["--retry-of","req-1"]),case="B04"));self.assertEqual(a[0],1,a)
        self.assertEqual(self.finish(self.start(self.resume_args("r3",3,["--retry-of","r2"]),case="B04"))[0],2)
        self.assertEqual(self.calls(),2)
    def test_scope_and_network_rejected_before_launch(self):
        a=self.finish(self.start(self.run_args()));self.assertEqual(a[0],0,a)
        args=self.resume_args("r2",2);args[args.index("--prompt")+1]=envelope("task-1",2,goal="changed")
        self.assertEqual(self.finish(self.start(args))[0],2)
        self.assertEqual(self.finish(self.start(self.resume_args("r3",2,["--network"])))[0],2)
        self.assertEqual(self.calls(),1)
    def test_review_cap_and_no_approval_claim(self):
        a=self.finish(self.start(self.run_args()));self.assertEqual(a[0],0,a)
        # Exercise wrapper with a synthetic reviewer; no merge or verification.
        for key in ("rev1","rev2"):
            args=d.build_parser().parse_args(["review","--task-id","task-1","--request-id",key])
            self.assertEqual(d.guarded_dispatch(args,lambda _:0),0)
        args=d.build_parser().parse_args(["review","--task-id","task-1","--request-id","rev3"])
        with self.assertRaises(ValueError):d.guarded_dispatch(args,lambda _:self.fail("review launched"))
        self.assertEqual(self.calls(),1)

if __name__=="__main__":
    if len(sys.argv)>2 and sys.argv[1]=="--worker":
        raise SystemExit(worker(Path(sys.argv[2]),sys.argv[3:]))
    unittest.main()
