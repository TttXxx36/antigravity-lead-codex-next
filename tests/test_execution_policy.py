import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('d06_dispatch', ROOT/'skills/multi-agent-dispatch/scripts/dispatch.py')
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

class ExecutionPolicyTests(unittest.TestCase):
    def test_policy_never_treats_request_as_grant(self):
        for v in (True, 1, "false", None, {}):
            with self.subTest(v=v), self.assertRaises(ValueError):
                d.enforce_execution_policy("workspace-write", v)
        d.enforce_execution_policy("workspace-write", False)
        d.enforce_execution_policy("read-only", False)
        with self.assertRaises(ValueError):
            d.enforce_execution_policy("danger-full-access", False)
        with self.assertRaises(ValueError):
            d.enforce_execution_policy("workspace-write", False, 'high"\\n')

    def test_batch_preflight_all_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'batch.json'
            for bad in ({"network":True},{"network":"false"},{"sandbox":"danger-full-access"}):
                path.write_text(json.dumps([{"prompt":"first"},{"prompt":"bad",**bad}]),encoding='utf8')
                args=d.build_parser().parse_args(['batch','--manifest',str(path)])
                with patch.object(d,'execute_single_task') as run, self.assertRaises(ValueError):
                    d.cmd_batch(args)
                run.assert_not_called()
            path.write_text('[{"prompt":"first","network":false}]',encoding='utf8')
            args=d.build_parser().parse_args(['batch','--manifest',str(path),'--network'])
            with patch.object(d,'execute_single_task') as run, self.assertRaises(ValueError):
                d.cmd_batch(args)
            run.assert_not_called()

    def test_resume_binding_and_no_unmanaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            record={'session_id':'session1','workdir':tmp,'sandbox':'read-only','status':'completed','network':True}
            for extra in (['--session-id','different'],['--cwd',str(Path(tmp)/'other')],['--sandbox','workspace-write']):
                args=d.build_parser().parse_args(['resume','--task-id','test','--prompt','x',*extra])
                with self.assertRaises(ValueError):
                    d.validate_resume_binding(record,args)
            args=d.build_parser().parse_args(['resume','--session-id','session1','--prompt','x'])
            with patch.object(d,'_cmd_resume') as run, self.assertRaises(ValueError):
                d.cmd_resume(args)
            run.assert_not_called()

    def test_cleanup_destructive_flags_rejected(self):
        for flag in ('--force','--delete-branch'):
            args=d.build_parser().parse_args(['cleanup','--task-id','test',flag])
            with patch.object(d,'remove_worktree') as remove, self.assertRaises(ValueError):
                d.cmd_cleanup(args)
            remove.assert_not_called()

    def test_abbreviated_flag_rejected(self):
        with self.assertRaises(SystemExit):
            d.build_parser().parse_args(['run','--prompt','x','--net'])

if __name__=='__main__':
    unittest.main()
