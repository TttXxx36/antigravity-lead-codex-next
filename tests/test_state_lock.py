"""Actual interprocess lock regression (not a mocked lock)."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills/multi-agent-dispatch/scripts/dispatch.py'
WORKER = """
import importlib.util, sys, time, os
spec = importlib.util.spec_from_file_location('dispatch_lock_worker', sys.argv[1])
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
for _ in range(15):
    with d.locked_state() as state:
        count = state['rr_counter']
        time.sleep(.003)
        state['rr_counter'] = count + 1
        state['tasks'][f'{os.getpid()}-{count}'] = {'status': 'synthetic'}
"""


class StateLockTests(unittest.TestCase):
    def test_cross_process_updates_are_serialized(self):
        with tempfile.TemporaryDirectory(prefix='lock-regression-') as tmp:
            home = Path(tmp)
            state_dir = home / '状态 文件'
            env = {k: os.environ[k] for k in ('PATH','SystemRoot','WINDIR','TEMP','TMP') if k in os.environ}
            env.update(HOME=str(home), USERPROFILE=str(home), AGY_DISPATCH_STATE_DIR=str(state_dir), PYTHONUTF8='1')
            workers = []
            try:
                for _ in range(4):
                    workers.append(subprocess.Popen([sys.executable, '-I', '-c', WORKER, str(SOURCE)], env=env, cwd=home, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
                for p in workers:
                    _, err = p.communicate(timeout=45)
                    self.assertEqual(p.returncode, 0, err.decode('utf-8', 'replace'))
                data = json.loads((state_dir / 'state.json').read_text(encoding='utf-8'))
                self.assertEqual(data['rr_counter'], 60)
                self.assertEqual(len(data['tasks']), 60)
            finally:
                for p in workers:
                    if p.poll() is None:
                        p.kill()
                    p.communicate()

    def test_release_after_exception(self):
        spec = importlib.util.spec_from_file_location('dispatch_lock_test', SOURCE)
        d = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(d)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.lock'
            with self.assertRaisesRegex(RuntimeError, 'synthetic'):
                with d.exclusive_state_lock(path):
                    raise RuntimeError('synthetic')
            with d.exclusive_state_lock(path, timeout=1):
                self.assertTrue(path.exists())


if __name__ == '__main__':
    unittest.main()
