import importlib.util
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
if __name__=="__main__":unittest.main()
