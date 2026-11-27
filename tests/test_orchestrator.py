"""D18 durable orchestration. All worker launches are local deterministic mocks."""
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
spec=importlib.util.spec_from_file_location("d18",SOURCE)
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

def envelope(tid="task-1",rev=1,goal="fix",delta=None):
    return json.dumps(dict(version=2,task_id=tid,rev=rev,base_rev=rev-1,goal=goal,
        scope=["answer.txt"],accept=["test"],delta=("" if rev==1 else "next") if delta is None else delta))

def setup(root):
    d.STATE_DIR=root/"state";d.STATE_FILE=d.STATE_DIR/"state.json";d.LOCK_FILE=d.STATE_DIR/"state.lock"
    d.RUNS_DIR=d.STATE_DIR/"runs";d.WORKTREES_DIR=d.STATE_DIR/"worktrees"

def worker(root,argv):
    setup(root)
    args=d.build_parser().parse_args(argv)
    original=d.run_subprocess_with_timeout
    def boundary(cmd,**kw):
        with (root/"launches").open("a",encoding="utf-8") as f:f.write("launch\n")
        if os.environ.get("D18_CRASH")=="1":
            # Simulate dispatcher death at the real worker-launch boundary;
            # no child is launched, but the durable state must not be retried.
            os._exit(71)
        if os.environ.get("D18_TIMEOUT")=="1":
            return original([sys.executable,"-I","-c","import time;time.sleep(20)"],**{**kw,"timeout":1})
        time.sleep(.2)
        return original([sys.executable,"-I",str(ROOT/"tests/mock_codex.py"),*cmd[1:]],**kw)
    try:
        with patch.object(d,"get_codex_bin",return_value="D18_MOCK_ONLY"), \
             patch.object(d,"resolve_model_and_effort",return_value=dict(model="mock-model",effort="low",effective_difficulty="low")), \
             patch.object(d,"run_subprocess_with_timeout",side_effect=boundary):
            return d.guarded_dispatch(args,{"run":d.cmd_run,"resume":d.cmd_resume,"review":d.cmd_review}[args.subcommand])
    except Exception as exc:
        print(json.dumps({"error":str(exc)}))
        return 2

class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="d18-");self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);setup(self.root);d.STATE_DIR.mkdir()
        self.cwd=self.root/"work";self.cwd.mkdir()
        self.configure()
        self.ps=[];self.addCleanup(self.stop)
    def configure(self,quota=80):
        d.atomic_write_bytes(d.STATE_DIR/"scheduler.json",json.dumps(dict(version=1,max_slots=2,max_wait_seconds=5,
            min_free_bytes=0,quota=dict(remaining_percent=quota,observed_at=int(time.time())))).encode())
    def stop(self):
        for p in self.ps:
            if p.poll() is None:p.kill()
            p.communicate(timeout=10)
    def cmd(self,kind,*args,tid="task-1",expect=0):
        argv=d.build_parser().parse_args([kind,"--task-id",tid,*args])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.orchestrator_command(argv),expect)
        return json.loads(out.getvalue())
    def queue(self,tid="task-1",key="req-1"):
        return self.cmd("orchestrator-queue","--request-id",key,"--prompt",envelope(tid),"--cwd",str(self.cwd),tid=tid)
    def runargs(self,tid="task-1",key="req-1",rev=1,retry=None):
        a=["run" if rev==1 else "resume","--task-id",tid,"--request-id",key,"--protocol-v2",
           "--prompt",envelope(tid,rev),"--model","mock-model","--effort","low"]
        if rev==1:a+=["--cwd",str(self.cwd),"--isolation","inplace"]
        if retry:a+=["--retry-of",retry]
        return a
    def start(self,args,case="B01",**extra):
        env=dict(os.environ,ALC_MOCK_CASE=case,**extra)
        p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--worker",str(self.root),*args],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",env=env)
        self.ps.append(p);return p
    def finish(self,p):
        out,err=p.communicate(timeout=35);return p.returncode,out,err
    def calls(self):
        file=self.root/"launches"
        return len(file.read_text().splitlines()) if file.exists() else 0
    def status(self,tid="task-1"):
        return self.cmd("orchestrator-status",tid=tid)
    def test_success_verifying_not_completed_and_audit(self):
        q=self.queue();self.assertEqual(q["status"],"queued")
        self.assertEqual(self.finish(self.start(self.runargs()))[0],0)
        s=self.status();self.assertEqual(s["status"],"verifying");self.assertFalse(s["accepted"]);self.assertFalse(s["mergeAuthorized"])
        self.assertEqual(s["revision"],5);self.assertEqual(s["requestStatus"],"returned")
        duplicate=self.finish(self.start(self.runargs()));self.assertEqual(duplicate[0],0);self.assertTrue(json.loads(duplicate[1])["duplicate"]);self.assertEqual(self.calls(),1)
        page=self.cmd("orchestrator-audit","--limit","2");self.assertTrue(page["hasMore"])
        tail=self.cmd("orchestrator-audit","--cursor",str(page["nextCursor"]));self.assertEqual([e["event"] for e in page["events"]+tail["events"]],["queue","reserve","ticket","admit","result_ready"])
        self.assertEqual(tail["events"][0]["previous"],page["events"][-1]["digest"])
        b=self.cmd("orchestrator-verify","--expected-revision",str(s["revision"]),expect=1)
        self.assertEqual(b["status"],"blocked");self.assertEqual(b["reason"],"trusted_acceptance_unavailable")
        self.assertFalse(b["accepted"]);self.assertEqual(self.calls(),1)
    def test_acceptance_preview_pins_evidence_without_accepting(self):
        self.queue();self.assertEqual(self.finish(self.start(self.runargs()))[0],0)
        s=self.status()
        before=d.STATE_FILE.read_bytes()
        p=self.cmd("orchestrator-acceptance-preview","--expected-revision",str(s["revision"]))
        self.assertEqual(p["revision"],s["revision"])
        self.assertEqual(p["auditDigest"],s["auditDigest"])
        self.assertEqual(p["checks"]["workerArtifact"],"PASS")
        self.assertEqual(p["checks"]["trustedAuthority"],"NOT_CONFIGURED")
        self.assertEqual(p["checks"]["independentReview"],"NOT_RUN")
        self.assertFalse(p["accepted"]);self.assertFalse(p["mergeAuthorized"]);self.assertFalse(p["stateChanged"])
        self.assertEqual(p["evidenceDigest"],d.request_hash({k:v for k,v in p.items() if k!="evidenceDigest"}))
        self.assertEqual(d.STATE_FILE.read_bytes(),before)
        self.assertEqual(self.status()["status"],"verifying")
        with self.assertRaises(ValueError):
            self.cmd("orchestrator-acceptance-preview","--expected-revision",str(s["revision"]-1))
        (d.RUNS_DIR/"task-1"/"result.json").write_text("{}",encoding="utf8")
        q=self.cmd("orchestrator-acceptance-preview","--expected-revision",str(s["revision"]))
        self.assertEqual(q["checks"]["workerArtifact"],"FAIL")
        self.assertFalse(q["readyForIndependentReview"])
        self.assertNotEqual(q["evidenceDigest"],p["evidenceDigest"])
        self.assertEqual(d.STATE_FILE.read_bytes(),before)

    def test_queue_cancel_cas_and_no_bypass(self):
        self.queue()
        with self.assertRaises(ValueError):self.cmd("orchestrator-cancel","--expected-revision","2")
        legacy=self.runargs();i=legacy.index("--request-id");del legacy[i:i+2]
        self.assertEqual(self.finish(self.start(legacy))[0],2)
        self.assertEqual(self.finish(self.start(self.runargs(key="other")))[0],2)
        changed=self.runargs();changed[changed.index("--prompt")+1]=envelope(goal="changed")
        self.assertEqual(self.finish(self.start(changed))[0],2)
        self.assertEqual(self.finish(self.start(self.runargs(tid="task-2")))[0],2)
        s=self.cmd("orchestrator-cancel","--expected-revision","1");self.assertEqual(s["status"],"cancelled")
        self.assertEqual(self.finish(self.start(self.runargs()))[0],2);self.assertEqual(self.calls(),0)
    def test_concurrent_duplicate_sqlite_restart(self):
        # D15 migration occurs only on disposable, quiescent state.
        with d.locked_state() as state:state["rr_counter"]=0
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(d.cmd_state_storage(d.build_parser().parse_args(["state-migrate","--confirm-quiescent"])),0)
        self.queue()
        p=self.start(self.runargs());q=self.start(self.runargs())
        a,b=self.finish(p),self.finish(q)
        self.assertIn(0,(a[0],b[0]),(a,b));self.assertEqual(self.calls(),1)
        self.assertEqual(self.status()["status"],"verifying")
        before=self.status()["revision"];self.assertEqual(self.finish(self.start(self.runargs()))[0],0)
        self.assertEqual(self.status()["revision"],before)
        with d.locked_state() as state:
            with self.assertRaises(d.StateIntegrityError):d.require_storage_quiescent(state)
    def test_abrupt_dispatch_crash_recover_no_replay(self):
        self.queue()
        a=self.finish(self.start(self.runargs(),D18_CRASH="1"));self.assertEqual(a[0],71,a)
        r=self.cmd("orchestrator-recover")
        self.assertEqual(r["status"],"running");self.assertTrue(r["leaseOutstanding"]);self.assertEqual(r["action"],"manual_reconciliation_required")
        self.assertEqual(r["requestStatus"],"pending");self.assertEqual(self.finish(self.start(self.runargs()))[0],2)
        self.assertEqual(self.finish(self.start(self.runargs(key="other")))[0],2)
        self.assertEqual(self.calls(),1)
        with self.assertRaises(ValueError):self.cmd("orchestrator-cancel","--expected-revision",str(r["revision"]))
    def test_known_failure_explicit_retry_repeated_failure_guard(self):
        self.queue()
        a=self.finish(self.start(self.runargs(),case="B04"));self.assertEqual(a[0],1,a)
        s=self.status();self.assertEqual(s["status"],"failed")
        with self.assertRaises(ValueError):self.cmd("orchestrator-retry","--request-id","req-2","--prompt",envelope(rev=2),"--expected-revision","1")
        q=self.cmd("orchestrator-retry","--request-id","req-2","--prompt",envelope(rev=2),"--expected-revision",str(s["revision"]))
        self.assertEqual(q["attempt"],1)
        self.assertEqual(self.finish(self.start(self.runargs(key="req-2",rev=2)))[0],2)
        a=self.finish(self.start(self.runargs(key="req-2",rev=2,retry="req-1"),case="B04"));self.assertEqual(a[0],1,a)
        s=self.status();self.assertEqual(s["status"],"failed")
        with self.assertRaisesRegex(ValueError,"repeated failure"):
            self.cmd("orchestrator-retry","--request-id","req-3","--prompt",envelope(rev=3),"--expected-revision",str(s["revision"]))
        self.assertEqual(self.status()["revision"],s["revision"])
        self.assertEqual(self.finish(self.start(self.runargs(key="req-3",rev=3,retry="req-2"),case="B04"))[0],2)
        self.assertEqual(self.calls(),2)
    def test_real_timeout_retains_uncertain_lease(self):
        self.queue()
        a=self.finish(self.start(self.runargs(),D18_TIMEOUT="1"));self.assertEqual(a[0],1,a)
        s=self.status();self.assertEqual(s["status"],"timed_out");self.assertTrue(s["leaseOutstanding"])
        self.assertEqual(self.finish(self.start(self.runargs()))[0],1);self.assertEqual(self.calls(),1)
        with self.assertRaises(ValueError):self.cmd("orchestrator-retry","--request-id","req-2","--prompt",envelope(rev=2),"--expected-revision",str(s["revision"]))
    def test_tampered_artifact_and_fake_acceptance_refused(self):
        self.queue();self.assertEqual(self.finish(self.start(self.runargs()))[0],0)
        s=self.status()
        with d.locked_state() as state:
            rec=d.orchestrator_lookup(state,"task-1")
            with self.assertRaises(d.StateIntegrityError):d.orchestrator_append(rec,"accept","trusted_acceptance_unavailable")
        (d.RUNS_DIR/"task-1"/"result.json").write_text("{}",encoding="utf8")
        b=self.cmd("orchestrator-verify","--expected-revision",str(s["revision"]),expect=1)
        self.assertEqual(b["reason"],"artifact_invalid");self.assertFalse(b["accepted"])
    def test_corrupt_audit_fails_closed(self):
        self.queue()
        with d.locked_state() as state:
            state[d.ORCHESTRATOR_KEY]["task-1"]["events"][0]["reason"]="queued_cancelled"
        with self.assertRaises(d.StateIntegrityError):self.status()
        self.assertEqual(self.finish(self.start(self.runargs()))[0],2);self.assertEqual(self.calls(),0)
    def test_scheduler_missing_and_queue_timeout_block(self):
        self.queue();(d.STATE_DIR/"scheduler.json").unlink()
        self.assertEqual(self.finish(self.start(self.runargs()))[0],2)
        self.assertEqual(self.status()["status"],"queued")
        self.configure(quota=5)
        a=self.finish(self.start(self.runargs()));self.assertEqual(a[0],2,a)
        s=self.status();self.assertEqual(s["status"],"blocked");self.assertTrue(s["leaseOutstanding"]);self.assertEqual(self.calls(),0)
if __name__=="__main__":
    if len(sys.argv)>2 and sys.argv[1]=="--worker":raise SystemExit(worker(Path(sys.argv[2]),sys.argv[3:]))
    unittest.main()
