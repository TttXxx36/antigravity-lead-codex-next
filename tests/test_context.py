import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("d11",ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class ContextTests(unittest.TestCase):
    def setUp(self):
        self.initial=dict(version=2,task_id="task-1",rev=1,base_rev=0,goal="stable",scope=["a.py"],accept=["test"],delta="")
        self.board=d.initial_context(self.initial,"read-only","a"*40)
        self.record=dict(task_id="task-1",protocol_rev=1,session_id="session-a",context_board=self.board,context_digest=d.context_digest(self.board))
        self.delta=dict(version=2,task_id="task-1",rev=2,base_rev=1,delta="next")
    def test_delta_only_and_immutable_stable_context(self):
        e,b,p=d.context_prepare(json.dumps(self.delta),self.record,False)
        self.assertEqual(e["goal"],"stable");self.assertNotIn('"goal"',p)
        self.assertEqual(b["stable"],self.board["stable"])
        self.assertEqual(self.board["rev"],1);self.assertEqual(b["rev"],2)
    def test_cross_task_stale_tamper_rejected(self):
        for patch in ({"task_id":"other"},{"rev":1},{"base_rev":0},{"goal":"new"},{"network":True}):
            with self.assertRaises(ValueError):d.context_prepare(json.dumps(self.delta|patch),self.record,False)
        self.board["stable"]["goal"]="tampered"
        with self.assertRaises(ValueError):d.context_prepare(json.dumps(self.delta),self.record,False)
    def test_secret_marker_rejected(self):
        for raw in ("password=synthetic-secret","api_key: fixture-value","-----BEGIN PRIVATE KEY-----"):
            with self.assertRaises(ValueError):d.initial_context(self.initial|{"goal":raw},"read-only",None)
            with self.assertRaises(ValueError):d.context_prepare(json.dumps(self.delta|{"delta":raw}),self.record,False)
    def test_byte_budget(self):
        d.context_account(self.board,"中"*100)
        self.assertEqual(self.board["prompt_bytes"],300)
        with self.assertRaises(ValueError):d.context_account(self.board,"x"*d.CONTEXT_MAX_BYTES)
    def test_session_identity(self):
        event=lambda v:json.dumps({"type":"thread.started","thread_id":v})
        self.assertEqual(d.context_session(event("a"),None,False),"a")
        self.assertEqual(d.context_session(event("a"),"a",False),"a")
        self.assertEqual(d.context_session(event("b"),"a",True),"b")
        for raw,prev,rebuild in ((event("b"),"a",False),(event("a"),"a",True),("",None,False),(event("a")+"\n"+event("b"),None,False),(json.dumps({"type":"item.completed","thread_id":"a"}),None,False)):
            with self.assertRaises(d.StateIntegrityError):d.context_session(raw,prev,rebuild)
    def test_retired_or_other_session_rejected(self):
        self.board["retired_sessions"]=["old"]
        for session in ("old","foreign"):
            with self.assertRaises(d.StateIntegrityError):d.context_assert_session_owner({"tasks":{"other":{"session_id":"foreign"}}},"task-1",session,self.board)
if __name__=="__main__":unittest.main()
