"""D22 deterministic *unpublished source RC* builder and strict local verifier.

No model, dependency installation, network, signing, tag, release or upload.
Build only exact Git HEAD blobs; extract only into a new caller-owned directory.
SHA256 verifies integrity relative to a separately trusted digest, not publisher identity.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

MAX_FILES=512
MAX_FILE=4*1024*1024
MAX_TOTAL=32*1024*1024
MAX_ARCHIVE=MAX_TOTAL+2*1024*1024
SHA1=re.compile(r"[a-f0-9]{40}\Z")
SHA256=re.compile(r"[a-f0-9]{64}\Z")
VERSION=re.compile(r"v2\.0\.0-rc\.[1-9][0-9]{0,2}\Z")
SEGMENT=re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,119}\Z")
RESERVED=re.compile(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z")
ROOT_FILES={"LICENSE","LICENSE.upstream","README.md","README_EN.md","README_UPSTREAM.md","CHANGELOG.md","AGENTS.md"}
DOC_FILES={"docs/"+x for x in ("ARCHITECTURE.md","BENCHMARK.md","CAPABILITIES.md","CODEX_TASK.md","DOCTOR.md","GOVERNANCE.md","UPSTREAM.md","WINDOWS_INSTALL.md","LOCAL_ACCEPTANCE.md","TOKEN_BUDGET.md","RESULTS.md","MIGRATION.md","RELEASE_CANDIDATE.md","EXECUTION_STATUS.json","ROADMAP.md","REMAINING_WORK.md","ISSUES_AND_BUGS.md")}
PREFIXES=("plugins/codex-console/","plugins/codex-auto-router/","skills/multi-agent-dispatch/","scripts/","protocols/","benchmarks/","tests/","docs/decisions/")
IMAGES={"img/logo.svg","img/preview-console.svg"}
EXT={".py",".mjs",".js",".json",".md",".sh",".ps1",".html",".css",".svg",".yml"}
DENIED_PARTS={".git",".env","node_modules","__pycache__","release-artifacts","rc-artifacts","sessions","runs","worktrees","credentials","secrets","auth.json","state.json","id_rsa","id_ed25519"}
SECRET_PATTERNS=tuple(re.compile(x) for x in (
    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    rb"(?<![A-Za-z0-9])gh[opusr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])",
    rb"github_pat_[A-Za-z0-9_]{40,}",
    rb"(?<![A-Za-z0-9])(?:sk-proj-|sk-ant-api03-|sk-)[A-Za-z0-9_-]{32,}",
    rb"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![0-9A-Z])",
    rb"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])",
))
REQUIRED={"LICENSE","LICENSE.upstream","README.md","README_EN.md","CHANGELOG.md","docs/MIGRATION.md","docs/RELEASE_CANDIDATE.md",
          "plugins/codex-console/dist/app.html","plugins/codex-console/package-lock.json","scripts/install.sh",
          "scripts/install.ps1","scripts/rc_package.py","skills/multi-agent-dispatch/scripts/dispatch.py"}
MANIFEST="RC-MANIFEST.json"


class PackageError(ValueError):pass


def digest(data):return hashlib.sha256(data).hexdigest()


def git_blob(data):return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def canonical(obj):
    return (json.dumps(obj,ensure_ascii=True,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("ascii")


def selected(path):
    return path in ROOT_FILES or path in DOC_FILES or path in IMAGES or path.startswith(PREFIXES)


def validate_path(path):
    if not isinstance(path,str) or len(path)>210 or "\\" in path or not selected(path):
        raise PackageError("D22: outside source allowlist")
    for part in path.split("/"):
        if not SEGMENT.fullmatch(part) or part.endswith(".") or RESERVED.fullmatch(part) or part.casefold() in DENIED_PARTS:
            raise PackageError("D22: unsafe or private source path")
    if path not in ROOT_FILES and Path(path).suffix.lower() not in EXT:
        raise PackageError("D22: unapproved file type")
    return path


def check_content(data):
    if len(data)>MAX_FILE:raise PackageError("D22: file limit")
    try:data.decode("utf-8",errors="strict")
    except UnicodeError as exc:raise PackageError("D22: non-text or unsupported source") from exc
    if b"\0" in data or any(p.search(data) for p in SECRET_PATTERNS):
        # Deliberately no raw match, filename, path or credential in error.
        raise PackageError("D22: suspected sensitive source content")


def valid_identity(commit,version):
    if not isinstance(commit,str) or not SHA1.fullmatch(commit) or not isinstance(version,str) or not VERSION.fullmatch(version):
        raise PackageError("D22: full source SHA and explicit v2.0.0-rc.N required")


def package_name(commit,version):
    valid_identity(commit,version)
    return "antigravity-lead-codex-"+version+"-"+commit[:12]


def git(root,args,input=None):
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull,GIT_TERMINAL_PROMPT="0",
               GIT_NO_REPLACE_OBJECTS="1",GIT_NO_LAZY_FETCH="1",GIT_ALLOW_PROTOCOL="",GIT_OPTIONAL_LOCKS="0")
    try:
        p=subprocess.run(["git","-c","protocol.allow=never","-c","core.fsmonitor=false","-C",str(root),*args],
                         input=input,stdin=subprocess.DEVNULL if input is None else None,
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:raise PackageError("D22: Git unavailable") from exc
    if p.returncode!=0 or len(p.stdout)>MAX_ARCHIVE or len(p.stderr)>65536:
        raise PackageError("D22: Git object read failed")
    return p.stdout


def collect(root,commit):
    if not isinstance(commit,str) or not SHA1.fullmatch(commit):raise PackageError("D22: exact commit SHA required")
    if git(root,["rev-parse","--verify","HEAD^{commit}"]).strip()!=commit.encode("ascii"):
        raise PackageError("D22: current HEAD must match requested source")
    raw=git(root,["ls-tree","-r","-l","-z",commit])
    if not raw.endswith(b"\0"):raise PackageError("D22: invalid tree")
    entries=[];seen=set();total=0
    for item in raw[:-1].split(b"\0"):
        try:
            meta,name=item.split(b"\t",1);path=name.decode("utf8");mode,kind,sha,size=meta.decode("ascii").split()
        except (ValueError,UnicodeError) as exc:raise PackageError("D22: malformed tree") from exc
        if not selected(path):continue
        validate_path(path)
        if path.casefold() in seen or kind!="blob" or mode not in ("100644","100755") or not SHA1.fullmatch(sha) or not size.isdecimal():
            raise PackageError("D22: case collision, nonregular tree entry or invalid blob")
        n=int(size);total+=n;seen.add(path.casefold())
        if n>MAX_FILE or total>MAX_TOTAL or len(entries)>=MAX_FILES:raise PackageError("D22: package limit")
        entries.append((path,mode,sha,n))
    if not REQUIRED.issubset({x[0] for x in entries}):raise PackageError("D22: required source missing")
    entries.sort(key=lambda x:x[0])
    objects=git(root,["cat-file","--batch"],input=b"".join(x[2].encode("ascii")+b"\n" for x in entries))
    buf=io.BytesIO(objects);files={}
    for path,mode,sha,n in entries:
        if buf.readline()!=f"{sha} blob {n}\n".encode("ascii"):raise PackageError("D22: blob header mismatch")
        data=buf.read(n)
        if len(data)!=n or buf.read(1)!=b"\n" or git_blob(data)!=sha:raise PackageError("D22: blob identity mismatch")
        try:check_content(data)
        except PackageError as exc:
            # Identify the exact immutable blob, never disclose filename or matched contents.
            raise PackageError(str(exc)+"; blob "+sha) from None
        files[path]=(0o755 if mode=="100755" else 0o644,data)
    if buf.read(1):raise PackageError("D22: extra object bytes")
    return files


def manifest_for(files,commit,version):
    return {"format":"alc-source-rc-v1","version":version,"commit":commit,
            "sourcePackageOnly":True,"releaseAuthorized":False,
            "files":[{"path":p,"mode":mode,"size":len(data),"sha256":digest(data)}
                     for p,(mode,data) in sorted(files.items())]}


def archive_bytes(files,commit,version):
    prefix=package_name(commit,version)
    manifest=canonical(manifest_for(files,commit,version))
    dest=io.BytesIO()
    # USTAR fixed metadata and gzip stored DEFLATE blocks: no filesystem
    # metadata, locale, timestamp, source tree checkout conversion or filename.
    with gzip.GzipFile(filename="",mode="wb",compresslevel=0,mtime=0,fileobj=dest) as gz:
        with tarfile.open(fileobj=gz,mode="w|",format=tarfile.USTAR_FORMAT) as tar:
            for path,(mode,data) in sorted({**files,MANIFEST:(0o644,manifest)}.items()):
                item=tarfile.TarInfo(prefix+"/"+path);item.size=len(data);item.mode=mode
                item.uid=item.gid=item.mtime=0;item.uname=item.gname=""
                tar.addfile(item,io.BytesIO(data))
    return dest.getvalue(),manifest


def parse_json(data):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise PackageError("D22: duplicate manifest key")
            d[k]=v
        return d
    def constant(_):raise PackageError("D22: invalid manifest number")
    try:return json.loads(data.decode("utf8"),object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,ValueError,RecursionError) as exc:raise PackageError("D22: invalid manifest") from exc


def verify_bytes(raw,expected_sha,commit,version):
    prefix=package_name(commit,version)
    if not isinstance(expected_sha,str) or not SHA256.fullmatch(expected_sha) or len(raw)>MAX_ARCHIVE or digest(raw)!=expected_sha:
        raise PackageError("D22: archive SHA256 mismatch or limit")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw),mode="rb") as gz:
            expanded=gz.read(MAX_ARCHIVE+1)
        if len(expanded)>MAX_ARCHIVE:raise PackageError("D22: expanded archive limit")
        files={};seen=set();total=0
        with tarfile.open(fileobj=io.BytesIO(expanded),mode="r:") as tar:
            for item in tar:
                if len(seen)>MAX_FILES or not item.name.startswith(prefix+"/") or item.type!=tarfile.REGTYPE or item.linkname:
                    raise PackageError("D22: archive member refused")
                p=item.name[len(prefix)+1:]
                if p!=MANIFEST:validate_path(p)
                if p.casefold() in seen or item.size<0 or item.size>MAX_FILE or item.mode not in (0o644,0o755) or item.uid!=0 or item.gid!=0 or item.mtime!=0 or item.uname or item.gname or item.pax_headers:
                    raise PackageError("D22: archive metadata refused")
                seen.add(p.casefold());total+=item.size
                if total>MAX_TOTAL:raise PackageError("D22: total member limit")
                f=tar.extractfile(item)
                if f is None:raise PackageError("D22: missing regular file")
                data=f.read(item.size+1)
                if len(data)!=item.size:raise PackageError("D22: truncated member")
                if p!=MANIFEST:check_content(data)
                files[p]=(item.mode,data)
        if MANIFEST not in files or not REQUIRED.issubset(files):raise PackageError("D22: required files missing")
        mode,m=files.pop(MANIFEST)
        if mode!=0o644 or parse_json(m)!=manifest_for(files,commit,version) or m!=canonical(manifest_for(files,commit,version)):
            raise PackageError("D22: manifest mismatch")
        # Reject concatenated/extra archive contents, alternate headers, and
        # noncanonical encodings. Recreate exact deterministic archive locally.
        regenerated,manifest=archive_bytes(files,commit,version)
        if regenerated!=raw:raise PackageError("D22: noncanonical archive")
        return files,manifest
    except (OSError,EOFError,tarfile.TarError) as exc:raise PackageError("D22: invalid archive") from exc


def read_archive(file):
    with Path(file).open("rb") as f:
        raw=f.read(MAX_ARCHIVE+1)
    if len(raw)>MAX_ARCHIVE:raise PackageError("D22: archive limit")
    return raw


def build(root,commit,version,out):
    name=package_name(commit,version)
    files=collect(root,commit)
    raw,manifest=archive_bytes(files,commit,version);sha=digest(raw)
    verify_bytes(raw,sha,commit,version)
    out=Path(out);out.mkdir(parents=False,exist_ok=False)
    archive=out/(name+".tar.gz")
    archive.write_bytes(raw);(out/MANIFEST).write_bytes(manifest)
    (out/"SHA256SUMS.txt").write_bytes((sha+"  "+archive.name+"\n"+digest(manifest)+"  "+MANIFEST+"\n").encode("ascii"))
    return {"source":commit,"version":version,"fileCount":len(files),"archive":archive.name,
            "archiveBytes":len(raw),"archiveSha256":sha,"manifestSha256":digest(manifest),
            "secretPatternScan":"PASS","sourceOnly":True,"releaseAuthorized":False}


def extract_verified(raw,expected_sha,commit,version,out):
    files,manifest=verify_bytes(raw,expected_sha,commit,version)
    out=Path(out);out.mkdir(parents=False,exist_ok=False)
    for p,(mode,data) in sorted({**files,MANIFEST:(0o644,manifest)}.items()):
        dest=out/p;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as f:f.write(data)
        if os.name!="nt":dest.chmod(mode)
    return out


def main():
    p=argparse.ArgumentParser(allow_abbrev=False);sub=p.add_subparsers(dest="command",required=True)
    b=sub.add_parser("build",allow_abbrev=False);b.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    b.add_argument("--out",required=True,type=Path)
    v=sub.add_parser("verify",allow_abbrev=False);v.add_argument("--archive",required=True,type=Path);v.add_argument("--sha256",required=True);v.add_argument("--extract-to",type=Path)
    for cmd in (b,v):
        cmd.add_argument("--commit",required=True);cmd.add_argument("--version",required=True)
    a=p.parse_args()
    try:
        if a.command=="build":
            result=build(a.root,a.commit,a.version,a.out)
            print("D22_RC "+json.dumps(result,separators=(",",":")))
        else:
            raw=read_archive(a.archive)
            if a.extract_to is not None:extract_verified(raw,a.sha256,a.commit,a.version,a.extract_to)
            else:verify_bytes(raw,a.sha256,a.commit,a.version)
            print("PASS: exact RC archive and manifest integrity; no install or release")
    except (OSError,PackageError) as exc:
        # No OS exception path leakage, no raw sensitive content.
        print(str(exc) if isinstance(exc,PackageError) else "D22: local file operation failed")
        return 1
    return 0


if __name__=="__main__":raise SystemExit(main())
