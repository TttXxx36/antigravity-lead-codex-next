import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/multi-agent-dispatch/scripts/dispatch.py"
spec = importlib.util.spec_from_file_location("d03_dispatch", SOURCE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class PlatformTests(unittest.TestCase):
    def test_reserved_windows_paths(self):
        for value in (r"C:\tmp\NUL.txt", r"C:\tmp\COM1", r"C:\tmp\bad.", r"C:\tmp\a:b",
                      r"\\?\C:\tmp\a", r"C:\tmp\LPT².log", r"C:\tmp\bad "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                d.validate_windows_path(value)
        d.validate_windows_path(r"C:\中文 空格\普通文件.txt")
        d.validate_windows_path("C:\\" + "\\".join(["a" * 70] * 5))

    def test_explicit_native_executable(self):
        with patch.dict(os.environ, {"CODEX_BIN": sys.executable}):
            self.assertEqual(d.get_codex_bin(), str(d.configured_path(sys.executable)))

    def test_missing_override_no_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"CODEX_BIN": str(Path(tmp) / "missing.exe")}):
                self.assertIsNone(d.get_codex_bin())
                self.assertEqual(d.list_codex_candidates(), [])

    def test_no_relative_path_search(self):
        with patch.dict(os.environ, {"PATH": ".", "CODEX_BIN": ""}):
            self.assertEqual(d.binary_candidates("codex"), [])

    def test_native_extension_windows(self):
        if os.name != "nt":
            return
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "codex.cmd"
            p.write_text("@exit /b 0", encoding="utf-8")
            with patch.dict(os.environ, {"CODEX_BIN": str(p)}):
                self.assertIsNone(d.get_codex_bin())

    def test_custom_roots_and_unicode_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "中文 空格"
            root.mkdir()
            long_root = root.joinpath("a"*55, "b"*55, "c"*55)
            long_root.mkdir(parents=True)
            env = dict(os.environ, CODEX_HOME=str(root / "codex home"),
                       GEMINI_CONFIG_DIR=str(root / "gemini config"),
                       AGY_DISPATCH_STATE_DIR=str(long_root / "state"),
                       CODEX_BIN=sys.executable, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
            code = """import importlib.util, json, sys
s=importlib.util.spec_from_file_location('d',sys.argv[1]);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
d.ensure_state_dirs()
print(json.dumps([str(d.CODEX_HOME),str(d.GEMINI_CONFIG_DIR),str(d.STATE_DIR),str(d.MODELS_CACHE_PATHS[0])],ensure_ascii=False))
"""
            out = subprocess.run([sys.executable, "-c", code, str(SOURCE)], env=env, capture_output=True,
                                 text=True, encoding="utf-8", timeout=30, check=True)
            self.assertEqual(json.loads(out.stdout), [env["CODEX_HOME"], env["GEMINI_CONFIG_DIR"],
                env["AGY_DISPATCH_STATE_DIR"], str(Path(env["CODEX_HOME"]) / "models_cache.json")])
            self.assertTrue(Path(env["AGY_DISPATCH_STATE_DIR"]).is_dir())

    def test_health_missing_exe_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, CODEX_BIN=str(Path(tmp) / "missing.exe"), CODEX_HOME=tmp,
                       AGY_DISPATCH_STATE_DIR=tmp, GEMINI_CONFIG_DIR=tmp, PYTHONUTF8="1")
            p = subprocess.run([sys.executable, str(SOURCE), "health"], env=env,
                               capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(p.returncode, 1)
            self.assertIn("codex executable not found", " ".join(json.loads(p.stdout)["runtime_errors"]))


if __name__ == "__main__":
    unittest.main()
