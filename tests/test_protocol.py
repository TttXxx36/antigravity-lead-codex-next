import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("d10",ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.task=dict(version=2,task_id="task-1",rev=1,base_rev=0,goal="修复",scope=["a.py"],accept=["test"],delta="")
        self.report=dict(version=2,status="completed",summary="synthetic",risks=["risk"],blockers=[],verification_claim="passed")
    def test_request_and_schema(self):
        self.assertEqual(d.parse_task_envelope(json.dumps(self.task),"task-1",0),self.task)
        schema=json.loads((ROOT/"protocols/task-v2.schema.json").read_text())
        self.assertEqual(set(schema["required"]),set(self.task))
        schema=json.loads(d.SCHEMA_V2_PATH.read_text())
        self.assertEqual(set(schema["required"]),set(self.report))
    def test_invalid_requests(self):
        for patch in ({"version":1},{"version":True},{"rev":True},{"rev":2},{"base_rev":-1},{"task_id":"../x"},{"goal":" "},{"scope":["x"]*17},{"accept":[]},{"delta":"unexpected"},{"network":True},{"goal":"x"*1601},{"goal":"\u0000"},{"goal":"\ud800"}):
            with self.subTest(patch=patch),self.assertRaises((ValueError,UnicodeError)):
                d.parse_task_envelope(json.dumps({**self.task,**patch}),None,0)
        with self.assertRaises(ValueError):d.parse_task_envelope(json.dumps(self.task),"other",0)
        with self.assertRaises(ValueError):d.protocol_json('{"rev":1,"rev":2}')
        with self.assertRaises(ValueError):d.protocol_json('{"x":NaN}')
        with self.assertRaises(ValueError):d.protocol_json("中"*3000)
    def test_resume_revision_and_downgrade(self):
        rec={"task_id":"task-1","protocol_version":2,"protocol_rev":2}
        val={**self.task,"rev":3,"base_rev":2,"delta":"change"}
        self.assertEqual(d.prepare_resume_envelope(json.dumps(val),rec,True),val)
        for v in ({**val,"rev":2,"base_rev":1},{**val,"rev":4},{**val,"delta":""}):
            with self.assertRaises(ValueError):d.prepare_resume_envelope(json.dumps(v),rec,True)
        with self.assertRaises(ValueError):d.prepare_resume_envelope("v1",rec,False)
        with self.assertRaises(ValueError):d.prepare_resume_envelope(json.dumps(val),{"task_id":"task-1"},True)
    def test_report_claim_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"report.json"
            p.write_text(json.dumps(self.report),encoding="utf8")
            report=d.parse_report_file(p,None,"",0,protocol_v2=True)
            self.assertEqual(report["status"],"completed")
            self.assertTrue(report["worker_claimed_verification_passed"])
            self.assertFalse(report["verification_passed"])
            self.assertEqual(report["verification_status"],"unknown")
            self.assertEqual(report["protocol_risks"],["risk"])
            self.assertEqual(d.parse_report_file(p,None,"",7,protocol_v2=True)["status"],"failed")
    def test_incompatible_and_overbudget_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"report.json"
            for patch in ({"version":1},{"summary":"x"*321},{"risks":["x"]*5},{"blockers":["blocked"]},{"verification_claim":True},{"unknown":1}):
                p.write_text(json.dumps({**self.report,**patch}),encoding="utf8")
                r=d.parse_report_file(p,"unsafe fallback","",0,protocol_v2=True)
                self.assertEqual(r["status"],"partial")
                self.assertEqual(r["verification_status"],"not_run")
                self.assertFalse(r["verification_passed"])
                self.assertNotIn("unsafe fallback",r["summary"])
            for payload in ("x"*9000,json.dumps(self.report)+" "*9000,"["*3000+"]"*3000):
                p.write_text(payload,encoding="utf8")
                self.assertEqual(d.parse_report_file(p,None,"",0,protocol_v2=True)["status"],"partial")
    def test_program_evidence_not_fabricated(self):
        r={"report":{"summary":"s","risks_or_followups":["r"]},"process_status":"exited","task_status":"completed","verification_status":"unknown","exit_code":0,"usage":{"input_tokens":8,"output_tokens":-1,"total_tokens":True,"secret":"x"},"git_truth":{"head_sha":"a"*40,"base_sha":"invalid"}}
        out=d.build_protocol_result(self.task,r,20)
        self.assertEqual(out["usage"],{"source":"cli_reported","counts":{"input_tokens":8}})
        self.assertEqual(out["git"],{"head_sha":"a"*40,"base_sha":None})
        self.assertEqual(out["result_ref"],"runs/task-1/result.json")
        self.assertEqual(out["verification_status"],"unknown")
        schema=json.loads((ROOT/"protocols/result-v2.schema.json").read_text())
        self.assertEqual(set(out),set(schema["required"]))
if __name__=="__main__":unittest.main()
