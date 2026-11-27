import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("d07",ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
def report(status="completed",passed=True):
    return dict(status=status,summary="mock",files_modified=[],commands_run=[],
                verification_passed=passed,risks_or_followups=[],notes_for_orchestrator="")

class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.path=self.root/"report.json"
    def test_bug001_missing_even_if_fallback_claims_success(self):
        r=d.parse_report_file(self.path,json.dumps(report()),"",0)
        self.assertEqual(r["status"],"partial")
        self.assertFalse(r["verification_passed"])
        self.assertEqual(r["verification_status"],"not_run")
    def test_bug002_nonzero_overrides_completed(self):
        self.path.write_text(json.dumps(report()),encoding="utf8")
        r=d.parse_report_file(self.path,None,"",7)
        self.assertEqual(r["status"],"failed")
        self.assertFalse(r["verification_passed"])
        self.assertEqual(d.task_exit_code({"exit_code":7,**d.outcome_fields(r,7,False,"")}),1)
    def test_schema_and_model_claim_not_independent(self):
        self.path.write_text(json.dumps(report()),encoding="utf8")
        r=d.parse_report_file(self.path,None,"",0)
        self.assertEqual(r["status"],"completed")
        self.assertTrue(r["worker_claimed_verification_passed"])
        self.assertFalse(r["verification_passed"])
        self.assertEqual(r["verification_status"],"unknown")
        self.path.write_text('{"summary":"fake","verification_passed":true}',encoding="utf8")
        self.assertEqual(d.parse_report_file(self.path,None,"",0)["status"],"partial")
    def test_error_event_and_blocked(self):
        self.path.write_text(json.dumps(report()),encoding="utf8")
        self.assertEqual(d.parse_report_file(self.path,None,"",0,["failed event"])["status"],"failed")
        self.path.write_text(json.dumps(report("blocked",False)),encoding="utf8")
        r=d.parse_report_file(self.path,None,"",0)
        self.assertEqual(d.task_exit_code({"exit_code":0,**d.outcome_fields(r,0,False,"")}),1)
    def test_startup_error(self):
        rc,out,err,timeout=d.run_subprocess_with_timeout([str(self.root/"absent.exe")],cwd=self.root,stdin_text=None,timeout=2)
        self.assertEqual(rc,127)
        self.assertFalse(timeout)
        r=d.parse_report_file(self.path,None,err,rc)
        self.assertEqual(d.outcome_fields(r,rc,timeout,err)["process_status"],"launch_failed")
    def test_owned_process_tree_timeout(self):
        # Parent launches a child which will write a marker after the timeout.
        # No real Codex, no arbitrary process targeting.
        marker=self.root/"escaped"
        ready=self.root/"ready"
        child="import time,pathlib,sys; pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(4); pathlib.Path(sys.argv[2]).write_text('escaped')"
        parent="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2],sys.argv[3]]); time.sleep(60)"
        rc,out,err,timed=d.run_subprocess_with_timeout([sys.executable,"-c",parent,child,str(ready),str(marker)],cwd=self.root,stdin_text=None,timeout=2)
        self.assertTrue(ready.exists(),"child never started; test invalid")
        self.assertEqual(rc,124)
        self.assertTrue(timed)
        time.sleep(3.2)
        self.assertFalse(marker.exists(),"descendant survived timeout")
    def test_real_local_process_exit_and_utf8(self):
        rc,out,err,timed=d.run_subprocess_with_timeout([sys.executable,"-X","utf8","-c","print('测试'); raise SystemExit(7)"],cwd=self.root,stdin_text=None,timeout=5)
        self.assertEqual(rc,7);self.assertIn("测试",out);self.assertFalse(timed)

if __name__=="__main__":unittest.main()
