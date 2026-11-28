import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from native_tarball_review import review_one


class NativeTarballReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"root"
        self.cache=Path(self.tmp.name)/"cache"
        self.target="node_modules/@esbuild/linux-x64"
        self.parent="node_modules/esbuild"
        self.binary="bin/esbuild"
        self.license=b"synthetic license notice"
        self.files={"package.json":json.dumps({"name":"@esbuild/linux-x64","version":"1.0.0","license":"MIT"}).encode(),
                    self.binary:b"synthetic binary bytes","README.md":b"synthetic readme"}
        for p,b in self.files.items():
            f=self.root/self.target/p
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(b)
        (self.root/self.parent).mkdir(parents=True)
        (self.root/self.parent/"LICENSE.md").write_bytes(self.license)
        self.make_cache()

    def make_cache(self,extra=None):
        b=io.BytesIO()
        with tarfile.open(fileobj=b,mode="w:gz") as t:
            for p,data in self.files.items():
                m=tarfile.TarInfo("package/"+p)
                m.size=len(data)
                t.addfile(m,io.BytesIO(data))
            if extra:
                t.addfile(extra)
        raw=b.getvalue()
        digest=hashlib.sha512(raw).digest()
        h=digest.hex()
        self.cached=self.cache/"_cacache/content-v2/sha512"/h[:2]/h[2:4]/h[4:]
        self.cached.parent.mkdir(parents=True,exist_ok=True)
        self.cached.write_bytes(raw)
        self.lock={self.target:{"version":"1.0.0","license":"MIT","dev":True,"optional":True,"integrity":"sha512-"+base64.b64encode(digest).decode()},
                   self.parent:{"version":"1.0.0"}}

    def review(self):
        return review_one(self.root,self.cache,self.lock,self.target,self.parent,self.binary,hashlib.sha256(self.license).hexdigest())

    def test_match(self):
        result=self.review()
        self.assertEqual(len(result["members"]),3)
        self.assertEqual(result["rootNotices"],[])
        self.assertTrue(result["installedMemberMatch"])

    def test_cache_tamper(self):
        self.cached.write_bytes(b"bad")
        with self.assertRaises(ValueError): self.review()

    def test_installed_tamper(self):
        (self.root/self.target/self.binary).write_bytes(b"bad")
        with self.assertRaises(ValueError): self.review()

    def test_extra_installed(self):
        (self.root/self.target/"extra").write_bytes(b"extra")
        with self.assertRaises(ValueError): self.review()

    def test_parent_notice(self):
        (self.root/self.parent/"LICENSE.md").write_bytes(b"changed")
        with self.assertRaises(ValueError): self.review()

    def test_traversal(self):
        m=tarfile.TarInfo("package/../escape")
        m.type=tarfile.DIRTYPE
        self.make_cache(m)
        with self.assertRaises(ValueError): self.review()

    def test_link(self):
        m=tarfile.TarInfo("package/link")
        m.type=tarfile.SYMTYPE
        m.linkname="README.md"
        self.make_cache(m)
        with self.assertRaises(ValueError): self.review()


if __name__=="__main__":
    unittest.main()
