"""D22 real Git object/package checks and disposable rollback rehearsal."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rc",ROOT/"scripts/rc_package.py")
rc=importlib.util.module_from_spec(spec);spec.loader.exec_module(rc)
VERSION="v2.0.0-rc.1"
COMPONENTS=("plugins/codex-console","plugins/codex-auto-router","skills/multi-agent-dispatch")

class RCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix="alc-d22-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.commit=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
        cls.first=rc.build(ROOT,cls.commit,VERSION,cls.root/"one")
        cls.raw=(cls.root/"one"/cls.first["archive"]).read_bytes()
        cls.files,cls.manifest=rc.verify_bytes(cls.raw,cls.first["archiveSha256"],cls.commit,VERSION)
    def test_exact_commit_reproducibility(self):
        other=rc.build(ROOT,self.commit,VERSION,self.root/"two")
        self.assertEqual(other,self.first)
        self.assertEqual((self.root/"two"/other["archive"]).read_bytes(),self.raw)
        self.assertEqual((self.root/"one"/"RC-MANIFEST.json").read_bytes(),self.manifest)
        self.assertEqual(len((self.root/"one"/"SHA256SUMS.txt").read_text().splitlines()),2)
        self.assertFalse(other["releaseAuthorized"])
        print("D22_REPRO "+json.dumps({"source":self.commit,"files":other["fileCount"],"archiveBytes":other["archiveBytes"],
              "archiveSha256":other["archiveSha256"],"manifestSha256":other["manifestSha256"],"twoBuildsIdentical":True}))
    def test_required_licenses_source_not_worktree(self):
        for p in rc.REQUIRED:
            self.assertEqual(self.files[p][1],subprocess.check_output(["git","-C",str(ROOT),"show",self.commit+":"+p]))
        self.assertIn(b"Koala973",self.files["LICENSE.upstream"][1])
        self.assertIn(b"Koala973",self.files["LICENSE"][1])
        self.assertFalse(any("node_modules" in p or p.endswith(".jpg") or p.startswith(".github/") for p in self.files))
    def test_identity_and_unsafe_paths(self):
        for bad in ("main","../v2.0.0-rc.1","v2.0.0","v2.0.0-rc.0"):
            with self.assertRaises(rc.PackageError):rc.package_name(self.commit,bad)
        with self.assertRaises(rc.PackageError):rc.collect(ROOT,"0"*40)
        for bad in ("plugins/codex-console/../escape.py","plugins/codex-console/CON.json","scripts/.env","scripts/a:stream.py","scripts/a\\b.py","scripts/secret.db","scripts/a./x.py","scripts/node_modules/a.js"):
            with self.assertRaises(rc.PackageError):rc.validate_path(bad)
    def test_secret_patterns_no_value_in_error(self):
        for data in (b"gh"+b"p_"+b"x"*36,b"sk"+b"-"+b"A"*40,b"-----BEGIN "+b"PRIVATE KEY-----",b"\xff"):
            with self.assertRaises(rc.PackageError) as e:rc.check_content(data)
            self.assertNotIn(repr(data),str(e.exception))
        rc.check_content(b"placeholder = 'YOUR_API_KEY'")
    def test_tampered_sha_and_archive_refused(self):
        changed=self.raw[:-10]+bytes([self.raw[-10]^1])+self.raw[-9:]
        with self.assertRaises(rc.PackageError):rc.verify_bytes(changed,self.first["archiveSha256"],self.commit,VERSION)
        with self.assertRaises(rc.PackageError):rc.verify_bytes(self.raw,rc.digest(self.raw),self.commit,"v2.0.0-rc.2")
        malformed,_=rc.archive_bytes({**self.files,"scripts/../evil.py":(0o644,b"x")},self.commit,VERSION)
        with self.assertRaises(rc.PackageError):rc.verify_bytes(malformed,rc.digest(malformed),self.commit,VERSION)
        duplicate,_=rc.archive_bytes({**self.files,"scripts/INSTALL.sh":(0o644,b"x")},self.commit,VERSION)
        with self.assertRaises(rc.PackageError):rc.verify_bytes(duplicate,rc.digest(duplicate),self.commit,VERSION)
    def test_extract_refuses_existing_destination_and_keeps_hashes(self):
        dest=self.root/"extract"
        rc.extract_verified(self.raw,self.first["archiveSha256"],self.commit,VERSION,dest)
        for p,(_,data) in self.files.items():self.assertEqual((dest/p).read_bytes(),data)
        with self.assertRaises(FileExistsError):rc.extract_verified(self.raw,self.first["archiveSha256"],self.commit,VERSION,dest)
    def test_rollback_disposable_code_and_real_sqlite(self):
        scratch=self.root/"rollback";scratch.mkdir()
        package=rc.extract_verified(self.raw,self.first["archiveSha256"],self.commit,VERSION,scratch/"package")
        config=scratch/"中文 空格"/"config";config.mkdir(parents=True)
        backup=scratch/"prior";backup.mkdir()
        data=scratch/"persistent";data.mkdir()
        db=data/"console.sqlite"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE fixture(value TEXT)");conn.execute("INSERT INTO fixture VALUES ('keep')")
        # sqlite context manager does not close; explicitly release on Windows.
        conn.close()
        state=data/"state.json";state.write_bytes(b'{"tasks":{}}\n')
        before=[rc.digest(p.read_bytes()) for p in (db,state)]
        for component in COMPONENTS:
            live=config/component;live.mkdir(parents=True);(live/"old-marker.txt").write_bytes(b"prior")
            old=backup/component;old.parent.mkdir(parents=True,exist_ok=True);live.rename(old)
        if os.name!="nt":
            # Actual Unix installer using explicit fake Node/npm/curl; no
            # dependency installation, remote download or hot reload.
            bin=scratch/"bin";bin.mkdir()
            (bin/"node").write_text("#!/bin/sh\ncase \"$1\" in --no-warnings) exit 0;; --version) echo v22.0.0-mock; exit 0;; *) exit 99;; esac\n",encoding="utf8")
            (bin/"npm").write_text("#!/bin/sh\n[ \"$*\" = 'ci --omit=dev --no-audit --no-fund' ] && [ -f dist/app.html ]\n",encoding="utf8")
            (bin/"curl").write_text("#!/bin/sh\nexit 99\n",encoding="utf8")
            for p in bin.iterdir():p.chmod(0o755)
            env={"PATH":str(bin)+os.pathsep+os.environ.get("PATH",""),"HOME":str(scratch),
                 "GEMINI_CONFIG_DIR":str(config),"CODEX_CONSOLE_NODE_BIN":str(bin/"node"),
                 "PYTHONUTF8":"1","LC_ALL":"C"}
            result=subprocess.run(["bash",str(package/"scripts/install.sh"),"--all","--no-build","--yes"],
                cwd=package,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            # Emit only a fixed completion indicator and numeric exit status,
            # never the captured output (which includes local paths).
            self.assertIn(b"Installation complete!",result.stdout,"Unix installer did not reach completion")
            self.assertEqual(result.returncode,0,"offline Unix mock install completed but returned nonzero")
            mode="actual_unix_installer_mock_dependencies"
        else:
            # Actual native Windows installer upgrade/restore/doctor is
            # independently exercised by existing PowerShell CI lifecycle.
            # Here rehearse the package code-tree restoration with real files.
            for component in COMPONENTS:shutil.copytree(package/component,config/component)
            mode="portable_package_tree_rehearsal"
        for component in COMPONENTS:
            self.assertTrue((config/component).is_dir());self.assertFalse((config/component/"old-marker.txt").exists())
        self.assertEqual((config/"skills/multi-agent-dispatch/scripts/dispatch.py").read_bytes(),self.files["skills/multi-agent-dispatch/scripts/dispatch.py"][1])
        self.assertEqual((config/"plugins/codex-console/UI-THIRD-PARTY-NOTICES.md").read_bytes(),self.files["plugins/codex-console/UI-THIRD-PARTY-NOTICES.md"][1])
        rejected=scratch/"rejected";rejected.mkdir()
        for component in COMPONENTS:
            current=config/component;hold=rejected/component;hold.parent.mkdir(parents=True,exist_ok=True);current.rename(hold)
            (backup/component).rename(current)
            self.assertEqual((current/"old-marker.txt").read_bytes(),b"prior")
        self.assertEqual([rc.digest(p.read_bytes()) for p in (db,state)],before)
        with sqlite3.connect("file:"+db.as_posix()+"?mode=ro",uri=True) as conn:
            self.assertEqual(conn.execute("SELECT value FROM fixture").fetchone(),("keep",))
        conn.close()
        print("D22_ROLLBACK "+json.dumps({"mode":mode,"restoredComponents":3,"persistentFilesUnchanged":2,"sqliteReadable":True,"actualHost":False}))

@unittest.skipIf(os.name == "nt", "Unix Bash privacy scanner")
class PrivacyScannerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="alc-privacy-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        scripts=self.root/"scripts";scripts.mkdir()
        self.script=scripts/"privacy-check.sh"
        shutil.copyfile(ROOT/"scripts/privacy-check.sh",self.script)

    def scan(self,env=None):
        return subprocess.run(["bash",str(self.script)],env=env,capture_output=True,timeout=30)

    def test_clean(self):
        self.assertEqual(self.scan().returncode,0)

    def test_match_is_redacted(self):
        marker="synthetic-sensitive-content Z"+"Code.app"
        (self.root/"fixture.txt").write_text(marker,encoding="utf-8")
        r=self.scan()
        self.assertEqual(r.returncode,1)
        self.assertNotIn(marker.encode(),r.stdout+r.stderr)
        self.assertNotIn(b"fixture.txt",r.stdout+r.stderr)

    def test_scan_error_fails_closed(self):
        bin_dir=self.root/"bin";bin_dir.mkdir()
        grep=bin_dir/"grep";grep.write_text("#!/bin/sh\necho synthetic-private-path >&2\nexit 2\n")
        grep.chmod(0o700)
        r=self.scan(dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ["PATH"]))
        self.assertEqual(r.returncode,2)
        self.assertNotIn(b"synthetic-private-path",r.stdout+r.stderr)

if __name__=="__main__":unittest.main()
