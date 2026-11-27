import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from repair_sbom import repair, RepairError, load_json


def fixture():
    digest = bytes(range(64))
    integrity = "sha512-" + base64.b64encode(digest).decode()
    packages = {"": {"name": "root", "version": "1.0.0", "dependencies": {"a": "1", "b": "1"}}}
    def component(name, path):
        result = {"name": name, "version": "1.0.0", "bom-ref": name+"@1.0.0", "type": "library", "properties": [{"name": "cdx:npm:package:path", "value": path}]}
        if path:
            result["hashes"] = [{"alg": "SHA-512", "content": digest.hex()}]
            packages[path] = {"version": "1.0.0", "integrity": integrity}
        return result
    root = component("root", "")
    a = component("a", "node_modules/a")
    b = component("b", "node_modules/b")
    x = component("leaf", "node_modules/a/node_modules/leaf")
    y = component("leaf", "node_modules/b/node_modules/leaf")
    for p in ("a", "b"):
        packages["node_modules/"+p]["dependencies"] = {"leaf": "1"}
    raw = {"bomFormat": "CycloneDX", "specVersion": "1.5", "metadata": {"component": root}, "components": [a,b,x,y], "dependencies": [{"ref": "root@1.0.0", "dependsOn": ["a@1.0.0","b@1.0.0"]}, {"ref": "a@1.0.0", "dependsOn": ["leaf@1.0.0"]}, {"ref": "b@1.0.0", "dependsOn": ["leaf@1.0.0"]}, {"ref": "leaf@1.0.0", "dependsOn": []}, {"ref": "leaf@1.0.0", "dependsOn": []}]}
    return raw, {"lockfileVersion": 3, "name": "root", "packages": packages}


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.lock = fixture()
    def test_repair(self):
        original = deepcopy(self.raw)
        out, mapping = repair(self.raw, self.lock)
        self.assertEqual(self.raw, original)
        self.assertEqual(len(mapping), 2)
        self.assertEqual(len(out["components"]), 4)
        graph = {n["ref"]: n["dependsOn"] for n in out["dependencies"]}
        self.assertEqual(len(graph), 5)
        for item in mapping:
            self.assertEqual(graph[item["path"].split("/")[1]+"@1.0.0"], [item["new"]])
    def test_clean(self):
        self.raw["components"].pop()
        self.raw["dependencies"].pop()
        self.raw["dependencies"][2]["dependsOn"] = []
        out, mapping = repair(self.raw, self.lock)
        self.assertEqual(out, self.raw)
        self.assertEqual(mapping, [])
    def test_missing_path(self):
        self.raw["components"][0]["properties"] = []
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_hash(self):
        self.raw["components"][0]["hashes"][0]["content"] = "0"*128
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_nonleaf(self):
        self.raw["dependencies"][-1]["dependsOn"] = ["a@1.0.0"]
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_locked_nonleaf(self):
        self.lock["packages"]["node_modules/a/node_modules/leaf"]["dependencies"] = {"a": "1"}
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_dangling(self):
        self.raw["dependencies"][0]["dependsOn"].append("missing")
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_ambiguous(self):
        del self.lock["packages"]["node_modules/a"]["dependencies"]
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_missing_node(self):
        self.raw["dependencies"].pop()
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_unreferenced(self):
        self.raw["dependencies"][1]["dependsOn"] = []
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_duplicate_key(self):
        with self.assertRaises(RepairError): load_json('{"x":1,"x":2}')
    def test_root(self):
        self.lock["packages"][""]["name"] = "wrong"
        with self.assertRaises(RepairError): repair(self.raw, self.lock)
    def test_cli_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            raw, lock, out, report = [p/x for x in ("raw.json", "lock.json", "derived.json", "report.json")]
            raw.write_text(json.dumps(self.raw), encoding="utf-8")
            lock.write_text(json.dumps(self.lock), encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).resolve().parents[1]/"scripts/repair_sbom.py"), "--raw", str(raw), "--lock", str(lock), "--out", str(out), "--report", str(report)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            original = out.read_bytes()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            self.assertEqual(out.read_bytes(), original)
            self.assertEqual(json.loads(raw.read_bytes()), self.raw)


if __name__ == "__main__":
    unittest.main()
