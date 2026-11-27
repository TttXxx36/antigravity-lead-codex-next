import importlib.util
import contextlib
import io
import os
import json
import pathlib
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("d14",ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class StreamTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=pathlib.Path(tmp.name)
    def snapshot(self):
        return json.loads((self.root/"stream-state.json").read_text("utf-8"))
    def invoke(self,script,timeout=10,stdin=None):
        return d.streamed_subprocess([sys.executable,"-u","-c",script],cwd=self.root,stdin_text=stdin,
            timeout=timeout,run_dir=self.root,task_id="task-1")
    def test_live_utf8_fragment_and_stderr(self):
        # Write a multibyte character across distinct writes, with real pipe traffic.
        script="import sys,time; b='{\"type\":\"item.completed\",\"text\":\"中\"}\\n'.encode('utf8'); i=b.index(bytes([228])); sys.stdout.buffer.write(b[:i+1]); sys.stdout.flush(); time.sleep(.1); sys.stdout.buffer.write(b[i+1:]); sys.stdout.flush(); sys.stderr.write('private stderr'); sys.stderr.flush(); time.sleep(1.5)"
        result=[]
        def run(): result.append(self.invoke(script))
        t=threading.Thread(target=run);t.start()
        try:
            deadline=time.monotonic()+8
            live=False
            while time.monotonic()<deadline and t.is_alive():
                try:
                    s=self.snapshot()
                    if any(e["kind"] in ("progress","heartbeat") and e["lines"]==1 for e in s["entries"]):
                        live=True
                        self.assertTrue(t.is_alive())
                        break
                except (OSError,ValueError):
                    pass
                time.sleep(.03)
            self.assertTrue(live,"no live metadata observed")
        finally:
            t.join(15)
        self.assertFalse(t.is_alive())
        rc,out,err,timed=result[0]
        self.assertEqual(rc,0);self.assertIn("中",out);self.assertEqual(err,"private stderr");self.assertFalse(timed)
        s=self.snapshot();self.assertEqual(s["entries"][-1]["kind"],"process_exit")
        self.assertNotIn("private",json.dumps(s));self.assertNotIn("中",json.dumps(s,ensure_ascii=False))
        self.assertEqual([e["seq"] for e in s["entries"]],list(range(1,len(s["entries"])+1)))
        self.assertEqual((self.root/"events.jsonl").read_bytes().decode("utf8"),out)
    def test_output_cap_fails_closed(self):
        script="import sys; sys.stdout.write('{\"type\":\"event\"}\\n'*10000); sys.stdout.flush()"
        with patch.object(d,"STREAM_STDOUT_LIMIT",1024):
            rc,out,err,timed=self.invoke(script)
        self.assertEqual(rc,125);self.assertEqual(out,"");self.assertFalse(timed)
        self.assertEqual((self.root/"events.jsonl").stat().st_size,1024)
        self.assertEqual(self.snapshot()["entries"][-1]["kind"],"stream_failed")
        self.assertIsNone(d.invocation_usage(out)["counts"]["total_tokens"])
    def test_bad_jsonl_and_oversized_line(self):
        with patch.object(d,"STREAM_LINE_LIMIT",64):
            rc,out,err,timed=self.invoke("import sys; sys.stdout.write('x'*1000); sys.stdout.flush()")
        self.assertEqual(rc,125);self.assertEqual(out,"")
        self.assertEqual(self.snapshot()["entries"][-1]["kind"],"stream_failed")
    def test_timeout_real_process(self):
        rc,out,err,timed=self.invoke("import time; print('{\"type\":\"event\"}',flush=True); time.sleep(30)",timeout=1)
        self.assertEqual(rc,124);self.assertTrue(timed);self.assertEqual(out,"")
        self.assertEqual(self.snapshot()["entries"][-1]["kind"],"timed_out")
    def test_journal_rotation_and_reopen_denied(self):
        j=d.StreamJournal(self.root,"task-1",None)
        for i in range(70): j.emit("progress",i,0,i)
        s=self.snapshot()
        self.assertEqual(len(s["entries"]),64);self.assertEqual(s["entries"][0]["seq"],7)
        self.assertEqual(s["entries"][-1]["seq"],70)
        with self.assertRaises(d.StateIntegrityError):d.StreamJournal(self.root,"task-1",None)
    def test_legacy_digest_and_opt_in(self):
        args=d.build_parser().parse_args(["run","--prompt","x"])
        self.assertFalse(args.stream_events)
        args=d.build_parser().parse_args(["run","--prompt","x","--stream-events"])
        self.assertTrue(args.stream_events)
        with self.assertRaises(ValueError):
            d.execute_single_task(prompt="x",cwd=self.root,backend="codex",difficulty="low",model=None,effort=None,
                quality="smart",alternate=None,prefer_wide=False,sandbox="read-only",isolation="inplace",
                timeout=1,files_hint=None,task_id="task-1",dry_run=True,stream_events=True)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for index,bad in enumerate(('{"type":"event","type":"other"}', '{"type":"event","x":NaN}', '[]')):
            with self.subTest(bad=bad):
                directory=self.root/str(index);directory.mkdir()
                rc,out,err,timed=d.streamed_subprocess([sys.executable,"-u","-c","print("+repr(bad)+",flush=True)"],
                    cwd=directory,stdin_text=None,timeout=5,run_dir=directory,task_id="task-1")
                self.assertEqual(rc,125);self.assertEqual(out,"");self.assertFalse(timed)
    def test_real_mock_run_resume_and_incomplete_stream_gate(self):
        state=self.root/"state";work=self.root/"work";work.mkdir()
        original=d.streamed_subprocess
        calls=[]
        def boundary(cmd,**kw):
            calls.append(kw["turn_id"])
            env=dict(os.environ,ALC_MOCK_USAGE="fixture",ALC_MOCK_CASE="B01")
            if len(calls)==3:
                return original([sys.executable,"-u","-c","import sys; sys.stdin.read(); print('broken json',flush=True)"],**kw,env=env)
            return original([sys.executable,"-I",str(ROOT/"tests/mock_codex.py"),*cmd[1:]],**kw,env=env)
        def envelope(rev):
            return json.dumps(dict(version=2,task_id="task-1",rev=rev,base_rev=rev-1,goal="fix",
                scope=["answer.txt"],accept=["test"],delta="" if rev==1 else "next"))
        def resume(rev):
            return d.build_parser().parse_args(["resume","--task-id","task-1","--protocol-v2","--prompt",envelope(rev),"--model","mock-model","--effort","low"])
        with patch.multiple(d,STATE_DIR=state,STATE_FILE=state/"state.json",LOCK_FILE=state/"state.lock",
                RUNS_DIR=state/"runs",WORKTREES_DIR=state/"worktrees"), \
                patch.object(d,"get_codex_bin",return_value="D14_MOCK_ONLY"), \
                patch.object(d,"resolve_model_and_effort",return_value=dict(model="mock-model",effort="low",effective_difficulty="low")), \
                patch.object(d,"streamed_subprocess",side_effect=boundary):
            r=d.execute_single_task(prompt=envelope(1),cwd=work,backend="codex",difficulty="low",
                model="mock-model",effort="low",quality="smart",alternate=None,prefer_wide=False,
                sandbox="workspace-write",isolation="inplace",timeout=10,files_hint=None,task_id="task-1",
                dry_run=False,protocol_v2=True,budget=d.make_budget(max_tokens=100),stream_events=True)
            self.assertEqual(r["task_status"],"completed")
            self.assertEqual(r["usage_summary"]["counts"]["total_tokens"],15)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(d.cmd_resume(resume(2)),0)
            with d.locked_state() as state_data:
                record=state_data["tasks"]["task-1"]
                self.assertTrue(record["stream_events"]);self.assertEqual(record["stream_integrity"],"complete")
                self.assertEqual(record["usage_store"]["known_sums"]["total_tokens"],30)
                turn=record["result_ref"]["turn"]
            self.assertNotEqual(turn,None)
            journal=json.loads((state/"runs"/"task-1"/turn/"stream-state.json").read_text("utf-8"))
            self.assertEqual(journal["turnId"],turn);self.assertEqual(journal["entries"][-1]["kind"],"process_exit")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(d.cmd_resume(resume(3)),1)
            with d.locked_state() as state_data:
                record=state_data["tasks"]["task-1"]
                self.assertEqual(record["stream_integrity"],"incomplete")
                self.assertEqual(record["usage_store"]["unknown_turns"]["total_tokens"],1)
            with self.assertRaisesRegex(ValueError,"incomplete stream"):
                d.cmd_resume(resume(4))
            self.assertEqual(len(calls),3)


    def test_owned_process_exit_race_permission_error(self):
        import subprocess
        # A real short-lived child, with the observed macOS group error
        # injected deterministically. No permission or unrelated PID used.
        p=subprocess.Popen([sys.executable,"-c","pass"],
            start_new_session=(os.name!="nt"),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0)
        try:
            if os.name!="nt":
                with patch.object(d.os,"killpg",side_effect=PermissionError(1,"fixture EPERM")) as group:
                    d.terminate_owned_process_tree(p)
                    p.wait(timeout=5)
                    d.terminate_owned_process_tree(p)
                    self.assertEqual(group.call_count,1,"reaped group must never be signalled again")
            else:
                p.wait(timeout=5)
                with patch.object(d.subprocess,"run") as kill:
                    d.terminate_owned_process_tree(p)
                    kill.assert_not_called()
            self.assertIsNotNone(p.returncode)
        finally:
            if p.poll() is None:p.kill()
            p.wait(timeout=5)

if __name__=="__main__":unittest.main()
