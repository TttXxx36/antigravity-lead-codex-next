"""Read existing npm cache bytes only; never fetch, extract or execute a binary."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

TARGETS = {
    "node_modules/@esbuild/linux-x64": ("node_modules/esbuild", "bin/esbuild"),
    "node_modules/@rollup/rollup-linux-x64-gnu": ("node_modules/rollup", "rollup.linux-x64-gnu.node"),
    "node_modules/@rollup/rollup-linux-x64-musl": ("node_modules/rollup", "rollup.linux-x64-musl.node"),
}
PARENT_NOTICE = {
    "node_modules/esbuild": "b40ec5baec7bb34fa5b1c09521fa3cd52d5fad7adafed74932a2010d3612a681",
    "node_modules/rollup": "fa1bd040c5bdeefe65b3821cebf474f2733ce65df13089bd151dda1778e62fe8",
}
LIMIT = 64 * 1024 * 1024
PART = re.compile(r"[@A-Za-z0-9_][@A-Za-z0-9_.+-]*\Z")
NOTICE = re.compile(r"(?:licen[cs]e|copying|notice|copyright)(?:[._-].*)?\Z", re.I)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parts(name):
    value = name.split("/")
    require(all(PART.fullmatch(x) and x not in (".", "..") for x in value), "unsafe path")
    return value


def read(root, relative, max_bytes=LIMIT):
    p = root
    for part in parts(relative):
        p = p / part
        require(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)(), "linked path")
    require(p.is_file() and p.stat().st_size <= max_bytes, "missing or oversized file")
    return p.read_bytes()


def review_one(root, cache, lock, target, parent, binary, parent_sha):
    meta = lock[target]
    require(meta.get("dev") is True and meta.get("optional") is True and meta.get("license") == "MIT", "unexpected package scope")
    integrity = meta["integrity"]
    require(integrity.startswith("sha512-"), "unsupported integrity")
    digest = base64.b64decode(integrity[7:], validate=True)
    require(len(digest) == 64, "invalid integrity length")
    h = digest.hex()
    raw = read(cache, "_cacache/content-v2/sha512/" + h[:2] + "/" + h[2:4] + "/" + h[4:], 32*1024*1024)
    require(hashlib.sha512(raw).digest() == digest, "cached tarball integrity mismatch")
    members, seen, total = {}, set(), 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r|gz") as tar:
        for item in tar:
            name = item.name.rstrip("/")
            pp = parts(name)
            require(pp[0] == "package" and name not in seen and len(seen) < 256, "unexpected tar member")
            seen.add(name)
            if item.isdir():
                continue
            require(len(pp)>1 and item.isfile() and 0 <= item.size <= LIMIT and total+item.size <= LIMIT, "unsafe tar type or size")
            rel = "/".join(pp[1:])
            data = tar.extractfile(item).read()
            total += len(data)
            require(len(data) == item.size, "short archive member")
            require(data == read(root,target+"/"+rel), "installed file differs from locked tarball")
            members[rel] = {"bytes":len(data), "sha256":sha(data)}
    require("package.json" in members and binary in members, "missing manifest or binary")
    manifest = json.loads(read(root,target+"/package.json",1024*1024))
    require(manifest.get("name")==target.removeprefix("node_modules/") and manifest.get("version")==meta["version"] and manifest.get("license")=="MIT", "manifest mismatch")
    folder = root.joinpath(*parts(target))
    actual = set()
    for f in folder.rglob("*"):
        require(not f.is_symlink() and not getattr(f,"is_junction",lambda:False)(), "unexpected installed link")
        if f.is_file():
            actual.add(f.relative_to(folder).as_posix())
        else:
            require(f.is_dir(), "unexpected installed file type")
    require(actual==set(members), "installed member set differs")
    notice = read(root,parent+"/LICENSE.md",2*1024*1024)
    require(sha(notice)==parent_sha and lock[parent]["version"]==meta["version"], "reviewed parent notice mismatch")
    return {"package":target,"version":meta["version"],"integrity":integrity,"archiveBytes":len(raw),
            "members":members,"rootNotices":sorted(x for x in members if "/" not in x and NOTICE.fullmatch(x)),
            "parent":parent,"parentLicenseSha256":parent_sha,"installedMemberMatch":True,
            "standaloneNativeRedistribution":"NOT_APPROVED_REVIEW_LINKED_DEPENDENCIES"}


def main():
    p=argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--cache",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    reports=[]
    try:
        root=a.root.resolve(strict=True)
        cache=a.cache.resolve(strict=True)
        lock=json.loads(read(root,"package-lock.json",5*1024*1024))["packages"]
        for target,(parent,binary) in TARGETS.items():
            reports.append(review_one(root,cache,lock,target,parent,binary,PARENT_NOTICE[parent]))
        result={"status":"PASS","packages":reports,"networkUsed":False,"binaryExecuted":False,"fullNativeLicenseClearance":False}
        code=0
    except (OSError,ValueError,KeyError,TypeError,AttributeError,tarfile.TarError) as exc:
        result={"status":"FAIL","completedPackages":reports,"errorType":type(exc).__name__,"reason":str(exc) if isinstance(exc,ValueError) and type(exc) is ValueError else "input unavailable or malformed","networkUsed":False,"fullNativeLicenseClearance":False}
        code=1
    with a.out.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print("D22_NATIVE_TARBALL_REVIEW",result["status"],len(reports),"packages verified")
    return code


if __name__=="__main__":
    raise SystemExit(main())
