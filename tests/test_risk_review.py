"""D19 actual Git fixtures and D18 mock worker integration."""
import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch
import test_orchestrator as fixture
d=fixture.d

class RiskTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.OrchestratorTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.cwd=self.f.cwd
        self.git("init","-q");self.git("config","user.name","D19 fixture");self.git("config","user.email","fixture@example.invalid")
        self.git("config","core.autocrlf","false")
        self.guide=self.cwd/"docs"/"user-guide"/"intro.md";self.guide.parent.mkdir(parents=True)
        self.guide.write_text("A short introduction.\n",encoding="utf8")
        (self.cwd/"answer.txt").write_text("mock result\n",encoding="utf8")
        self.git("add",".");self.git("commit","-qm","baseline");self.base=self.git("rev-parse","HEAD")
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.cwd),*args],stderr=subprocess.STDOUT).decode("utf8").strip()
    def edit(self,path,text):
        p=self.cwd/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding="utf8")
        self.git("add","--",path);self.git("commit","-qm","candidate");return self.git("rev-parse","HEAD")
    def run_worker(self):
        self.f.queue();a=self.f.finish(self.f.start(self.f.runargs()));self.assertEqual(a[0],0,a)
        s=self.f.status();self.assertEqual(s["status"],"verifying");return s
    def collect(self,head,approved=True):
        return d.risk_collect(self.cwd,self.base,head,approved,True,"workspace-write",False)
    def command(self,head,revision=5,approved=True):
        args=["orchestrator-risk-review","--task-id","task-1","--expected-revision",str(revision),"--head",head]
        if approved:args.append("--approve-git-checks")
        with contextlib.redirect_stdout(io.StringIO()) as out:rc=d.risk_review_command(d.build_parser().parse_args(args))
        return rc,json.loads(out.getvalue())
    def test_low_guide_pinned_diff_and_not_run_tests(self):
        h=self.edit("docs/user-guide/intro.md","A useful introduction.\n");ev=self.collect(h)
        self.assertEqual(ev["risk"],"low",ev);self.assertTrue(ev["repeatReviewMaySkip"])
        self.assertFalse(ev["requiredAudit"]);self.assertFalse(ev["accepted"]);self.assertFalse(ev["mergeAuthorized"])
        for k in ("project_tests","worktree","independent_review"):self.assertEqual(ev["checks"][k],"NOT_RUN")
    def test_security_concurrency_and_migration_must_review(self):
        for path in ("src/sandbox.py","src/scheduler.py","db/migrations/001.sql","unknown.py"):
            h=self.edit(path,"change\n");ev=self.collect(h)
            self.assertEqual(ev["risk"],"high",ev);self.assertTrue(ev["requiredAudit"]);self.assertFalse(ev["repeatReviewMaySkip"])
    def test_sensitive_content_and_structural_change(self):
        h=self.edit("docs/user-guide/intro.md","Enable network access.\n");self.assertTrue(self.collect(h)["requiredAudit"])
        h=self.edit("docs/user-guide/extra.md","ordinary content\n");self.assertTrue(self.collect(h)["requiredAudit"])
    def test_approval_required_no_subprocess(self):
        with patch.object(d,"risk_git",side_effect=AssertionError("unapproved process")):ev=self.collect(self.base,False)
        self.assertTrue(all(x=="NOT_RUN" for x in ev["checks"].values()));self.assertTrue(ev["requiredAudit"])
    def test_head_mismatch_empty_whitespace_and_unknown(self):
        ev=self.collect(self.base);self.assertEqual(ev["checks"]["diff_metadata"],"UNKNOWN")
        h=self.edit("docs/user-guide/intro.md","Trailing whitespace. \n");ev=self.collect(h)
        self.assertNotEqual(ev["checks"]["whitespace"],"PASS");self.assertFalse(ev["repeatReviewMaySkip"])
        ev=self.collect(self.base);self.assertEqual(ev["checks"]["identity"],"UNKNOWN")
        with patch.object(d,"risk_git",return_value=(None,b"")):ev=self.collect(h)
        self.assertEqual(ev["checks"]["identity"],"UNKNOWN");self.assertFalse(ev["accepted"])
    def test_external_diff_textconv_not_executed(self):
        h=self.edit("docs/user-guide/intro.md","Plain content.\n")
        self.git("config","diff.external","invalid-D19-command");self.git("config","diff.fixture.textconv","invalid-D19-command")
        (self.cwd/".gitattributes").write_text("*.md diff=fixture\n",encoding="utf8")
        ev=self.collect(h);self.assertEqual(ev["checks"]["diff_content"],"PASS",ev)
    def test_receipt_durable_idempotent_and_verify_never_accepts(self):
        s=self.run_worker();h=self.edit("docs/user-guide/intro.md","A useful introduction.\n")
        with self.assertRaises(ValueError):self.command(h,revision=4)
        rc,preview=self.command(h,approved=False);self.assertEqual(rc,1);self.assertEqual(preview["status"],"NOT_RUN")
        with d.locked_state() as state:self.assertEqual(d.risk_registry(state),{})
        rc,payload=self.command(h);self.assertEqual(rc,0,payload);receipt=payload["receipt"]
        self.assertEqual(receipt["auditDigest"],s["auditDigest"]);self.assertEqual(receipt["head"],h)
        self.assertFalse(receipt["evidence"]["accepted"]);self.assertTrue(self.command(h)[1]["duplicate"])
        with self.assertRaises(ValueError):self.command(self.base)
        self.assertEqual(self.f.status()["status"],"verifying")
        blocked=self.f.cmd("orchestrator-verify","--expected-revision","5",expect=1)
        self.assertEqual(blocked["status"],"blocked");self.assertFalse(blocked["accepted"])
        args=d.build_parser().parse_args(["orchestrator-risk-status","--task-id","task-1"])
        with contextlib.redirect_stdout(io.StringIO()) as out:d.risk_review_command(args)
        self.assertFalse(json.loads(out.getvalue())["sameRevision"])
    def test_tamper_evidence_rejected(self):
        self.run_worker();h=self.edit("docs/user-guide/intro.md","A useful introduction.\n")
        self.assertEqual(self.command(h)[0],0)
        with d.locked_state() as state:state[d.RISK_KEY]["task-1"]["evidence"]["accepted"]=True
        with self.assertRaises(d.StateIntegrityError):self.command(h)
        with self.assertRaises(d.StateIntegrityError):self.f.cmd("orchestrator-verify","--expected-revision","5",expect=1)
    def test_oversized_and_malformed_diff_never_low(self):
        self.assertIsNone(d.risk_diff_paths(b"invalid\0"))
        self.assertEqual(d.risk_classify(None,b"plain")[0],"high")
        h=self.edit("docs/user-guide/intro.md","a"*300000+"\n");ev=self.collect(h)
        self.assertEqual(ev["risk"],"high",ev);self.assertEqual(ev["checks"]["diff_content"],"UNKNOWN")
        self.assertFalse(ev["repeatReviewMaySkip"])
if __name__=="__main__":unittest.main()
