import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dependency_audit", ROOT / "scripts/audit_dependency_notices.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class DependencyAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="alc-dependency-audit-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.modules = self.root / "node_modules"
        self.package = self.modules / "fixture"
        self.package.mkdir(parents=True)
        self.meta = {"version": "1.0.0", "license": "MIT",
                     "resolved": "https://registry.npmmirror.com/fixture/-/fixture-1.0.0.tgz",
                     "integrity": "sha512-" + base64.b64encode(b"a" * 64).decode()}
        self.lock = self.root / "package-lock.json"
        self.lock.write_bytes((json.dumps({"packages": {"": {}, "node_modules/fixture": self.meta}}, indent=2) + "\n").encode())
        self.hidden(self.meta)
        (self.package / "package.json").write_text(json.dumps({"version": "1.0.0", "license": "MIT"}), encoding="utf-8")
        (self.package / "LICENSE").write_text("Permission is hereby granted, free of charge. The software is provided as is.", encoding="utf-8")

    def hidden(self, meta):
        (self.modules / ".package-lock.json").write_text(json.dumps({"packages": {"node_modules/fixture": meta}}), encoding="utf-8")

    def test_matching_metadata_and_notice(self):
        result = audit.audit(self.root, "runtime")
        self.assertEqual(result["identityChecks"], "PASS")
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["completeLegalReview"])
        self.assertEqual(result["vulnerabilityAudit"], "NOT_RUN")

    def test_hidden_lock_source_and_integrity_mismatch(self):
        for patch in ({"resolved": "https://example.invalid/other.tgz"}, {"integrity": "sha512-" + base64.b64encode(b"b" * 64).decode()}):
            with self.subTest(patch=patch):
                self.hidden(dict(self.meta, **patch))
                result = audit.audit(self.root, "runtime")
                self.assertEqual(result["identityChecks"], "FAIL")
                self.assertIn("installed_lock_source_or_integrity_mismatch", [f["kind"] for f in result["findings"]])

    def test_missing_hidden_lock_integrity(self):
        meta = dict(self.meta)
        del meta["integrity"]
        self.hidden(meta)
        self.assertEqual(audit.audit(self.root, "runtime")["identityChecks"], "FAIL")

    def test_line_endings_record_raw_and_lf_digest(self):
        lf = audit.audit(self.root, "runtime")
        self.lock.write_bytes(self.lock.read_bytes().replace(b"\n", b"\r\n"))
        crlf = audit.audit(self.root, "runtime")
        self.assertNotEqual(lf["lockSha256"], crlf["lockSha256"])
        self.assertEqual(lf["lockLfSha256"], crlf["lockLfSha256"])

    @unittest.skipIf(os.name == "nt", "symlink fixture requires Unix permissions")
    def test_linked_metadata_and_modules_rejected(self):
        target = self.root / "other-lock.json"
        self.lock.rename(target)
        self.lock.symlink_to(target)
        with self.assertRaises(ValueError):
            audit.audit(self.root, "runtime")
        self.lock.unlink()
        target.rename(self.lock)
        other = self.root / "other-modules"
        self.modules.rename(other)
        self.modules.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unsafe installed package root"):
            audit.audit(self.root, "runtime")


if __name__ == "__main__":
    unittest.main()
