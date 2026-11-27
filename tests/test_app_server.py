"""D20 actual local stdio processes, no native server or real model."""
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import test_orchestrator as fixture
d=fixture.d
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"skills/multi-agent-dispatch/scripts/codex_app_server.py"
spec=importlib.util.spec_from_file_location("d20",SOURCE)
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
MOCK=ROOT/"tests/mock_app_server.py"
class AppServerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="d20-");self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.log=self.root/"rpc.log"
        self.env=dict(os.environ,PYTHONUTF8="1")
    def session(self,mode="normal",usage=None,timeout=5,version="0.170.0"):
        s=a.ProbeSession([sys.executable,"-I",str(MOCK),mode,str(self.log)],self.root,self.env,version,timeout,usage)
        self.addCleanup(s.close);return s
    def methods(self):return self.log.read_text(encoding="utf8").splitlines() if self.log.exists() else []
    def test_default_and_experimental_flag_never_route_native(self):
        for flag in ("0","1","true",""):
            with patch.dict(os.environ,{"ALC_APP_SERVER_EXPERIMENTAL":flag}),patch.object(d,"get_codex_bin",side_effect=AssertionError("plan must not probe executable")):
                plan=d.app_server_plan()
                self.assertEqual(plan["executionBackend"],"cli");self.assertEqual(plan["requested"],flag=="1")
                self.assertEqual(plan["nativeProtocol"],"NOT_RUN");self.assertFalse(plan["automaticReplay"])
        cmd=d.build_codex_exec_cmd(codex_bin="mock-only",workdir=self.root,model=None,effort=None,sandbox="read-only",report_path=self.root/"r.json",is_git_repo=False)
        self.assertEqual(cmd[1],"exec");self.assertIn('approval_policy="never"',cmd);self.assertIn("sandbox_workspace_write.network_access=false",cmd)
    def test_pending_dispatch_no_fallback(self):
        f=fixture.OrchestratorTests();f.setUp();self.addCleanup(f.doCleanups)
        f.queue();res=f.finish(f.start(f.runargs(),D18_CRASH="1"));self.assertEqual(res[0],71,res)
        with patch.dict(os.environ,{"ALC_APP_SERVER_EXPERIMENTAL":"1"}):
            self.assertEqual(d.app_server_plan("task-1")["executionBackend"],"blocked")
        self.assertEqual(f.calls(),1)
    def test_handshake_reuse_and_compact_receipt(self):
        usage=a.UsageSnapshot("thread-fixture","turn-fixture")
        with self.session(usage=usage) as s:
            for _ in range(4):
                result=s.read("thread-fixture");self.assertEqual(result["status"],"idle")
                self.assertFalse(result["accepted"]);self.assertNotIn("preview",result)
            self.assertEqual(s.spawns,1)
            self.assertEqual(s.connection.terminal["workerStatus"],"completed")
            self.assertFalse(s.connection.terminal["accepted"])
            self.assertEqual(usage.receipt()["total"]["totalTokens"],15)
            self.assertIsNone(usage.receipt()["billableUsage"])
        self.assertEqual(self.methods(),["initialize","initialized"]+["thread/read"]*4)
    def test_explicit_reconnect_read_only_and_no_duplicate_usage(self):
        usage=a.UsageSnapshot("thread-fixture","turn-fixture")
        s=self.session(usage=usage);s.connect();s.read("thread-fixture")
        s.reconnect();s.read("thread-fixture")
        self.assertEqual(s.spawns,2);self.assertEqual(usage.receipt()["total"]["totalTokens"],15)
        self.assertEqual(usage.receipt()["integrity"],"unknown");self.assertTrue(usage.receipt()["gap"])
        s.close();self.assertEqual(self.methods(),["initialize","initialized","thread/read"]*2)
    def test_disconnect_timeout_unsupported_and_no_auto_replay(self):
        for mode in ("disconnect","timeout","unsupported"):
            self.log.unlink(missing_ok=True);s=self.session(mode=mode,timeout=2)
            s.connect()
            with self.assertRaises(a.ProtocolError):s.read("thread-fixture")
            self.assertEqual(s.spawns,1);self.assertTrue(s.connection.closed);s.close()
            self.assertEqual(self.methods(),["initialize","initialized","thread/read"],mode)
    def test_mismatch_malformed_oversize_and_approval_fail_closed(self):
        for mode in ("wrong_id","wrong_thread","malformed","oversize","approval"):
            self.log.unlink(missing_ok=True);s=self.session(mode=mode);s.connect()
            with self.assertRaises(a.ProtocolError):s.read("thread-fixture")
            self.assertTrue(s.connection.closed);s.close()
            self.assertEqual(self.methods(),["initialize","initialized","thread/read"],mode)
    def test_version_and_mutation_methods_refused(self):
        s=self.session(mode="version_mismatch")
        with self.assertRaises(a.ProtocolError):s.connect()
        self.assertEqual(self.methods(),["initialize"]);self.log.unlink()
        with self.session() as s:
            for name in ("thread/start","thread/resume","turn/start","command/exec","account/login/start"):
                with self.assertRaises(a.ProtocolError):s.connection._call(name,{})
                with self.assertRaises(a.ProtocolError):s.connection._send({"method":name})
            self.assertEqual(s.read("thread-fixture")["status"],"idle")
        self.assertEqual(self.methods(),["initialize","initialized","thread/read"])
    def test_policy_receipts_strict_parity_never_grant(self):
        base=dict(cwd=str(self.root),approvalPolicy="never",model="mock",reasoningEffort="low",sandbox={"type":"readOnly","networkAccess":False})
        self.assertTrue(a.policy_matches(base,self.root,"read-only","mock","low"))
        for changed in (dict(approvalPolicy="on-request"),dict(sandbox={"type":"readOnly","networkAccess":True}),dict(sandbox={"type":"dangerFullAccess"}),dict(activePermissionProfile={"type":"unknown"}),dict(model="different")):
            self.assertFalse(a.policy_matches({**base,**changed},self.root,"read-only","mock","low"))
        policy={"type":"workspaceWrite","networkAccess":False,"writableRoots":[str(self.root)],"excludeTmpdirEnvVar":True,"excludeSlashTmp":True}
        self.assertTrue(a.policy_matches({**base,"sandbox":policy},self.root,"workspace-write"))
        self.assertFalse(a.policy_matches({**base,"sandbox":{**policy,"writableRoots":[str(self.root.parent)]}},self.root,"workspace-write"))
        self.assertFalse(a.policy_matches({**base,"sandbox":{**policy,"excludeSlashTmp":False}},self.root,"workspace-write"))
    def test_usage_invalid_regression_and_terminal_identity(self):
        u=a.UsageSnapshot("t","turn")
        def event(n):
            return {"method":"thread/tokenUsage/updated","params":{"threadId":"t","turnId":"turn","tokenUsage":{"total":{"inputTokens":n,"cachedInputTokens":0,"outputTokens":n,"reasoningOutputTokens":0,"totalTokens":2*n}}}}
        self.assertIsNone(u.receipt()["total"]);u.observe(event(10));u.observe(event(10));u.observe(event(9))
        self.assertEqual(u.receipt()["total"]["totalTokens"],20);self.assertEqual(u.receipt()["integrity"],"unknown")
        event_wrong={"method":"turn/completed","params":{"threadId":"other","turn":{"id":"turn","status":"completed"}}}
        self.assertIsNone(a.terminal_claim(event_wrong,"t","turn"))
        self.assertFalse(a.terminal_claim({"method":"turn/completed","params":{"threadId":"t","turn":{"id":"turn","status":"completed"}}},"t","turn")["accepted"])
        for raw in (b'{"x":NaN}\n',b'{"x":1,"x":2}\n',b'{}',b'[]\n'):
            with self.assertRaises(a.ProtocolError):a.strict_frame(raw)
    def test_fixture_reuse_benchmark(self):
        cold=[]
        for _ in range(6):
            start=time.monotonic()
            with self.session() as s:s.read("thread-fixture")
            cold.append((time.monotonic()-start)*1000)
        start=time.monotonic()
        with self.session() as s:
            for _ in range(6):s.read("thread-fixture")
            self.assertEqual(s.spawns,1)
        reused=(time.monotonic()-start)*1000
        self.assertEqual(self.methods().count("initialize"),7)
        print("D20_BENCH "+json.dumps({"fixtureOnly":True,"coldSpawns":6,"reuseSpawns":1,"reads":6,"coldTotalMs":round(sum(cold),3),"reuseTotalMs":round(reused,3),"coldMedianMs":round(statistics.median(cold),3)}))
if __name__=="__main__":unittest.main()
