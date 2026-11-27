"""Read-only offline inventory of locked npm packages and installed license notices."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SAFE_PART = re.compile(r"[@A-Za-z0-9_][A-Za-z0-9_.@-]*\Z")
NOTICE = re.compile(r"(?:licen[cs]e|copying|notice|copyright)(?:[._-].*)?\Z", re.I)
LICENSES = {"MIT", "ISC", "BSD-2-Clause", "BSD-3-Clause"}

def read_json(path):
    if path.is_symlink() or getattr(path, 'is_junction', lambda: False)() or not path.is_file() or path.stat().st_size > 5*1024*1024:
        raise ValueError("unsafe or missing inventory metadata")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid inventory metadata")
    return value

def packages(root, path):
    parts = path.split("/")
    if len(parts) < 2 or parts[0] != "node_modules" or any(not SAFE_PART.fullmatch(x) or x in (".", "..") for x in parts):
        raise ValueError("unsafe package path")
    out = root
    for part in parts:
        out = out / part
        if out.is_symlink() or getattr(out, 'is_junction', lambda: False)():
            raise ValueError("linked package path")
    return out

def license_family(raw):
    value = b" ".join(raw.lower().split())
    if b"permission is hereby granted, free of charge" in value and b"the software is provided" in value:
        return "MIT"
    if b"permission to use, copy, modify, and/or distribute" in value and b"the software is provided" in value:
        return "ISC"
    if b"redistribution and use in source and binary forms" in value:
        return "BSD-3-Clause" if b"neither the name" in value or b"may be used to endorse" in value else "BSD-2-Clause-or-other"
    return "UNKNOWN"

def audit(root, phase):
    root = root.resolve(strict=True)
    lock_raw = (root/"package-lock.json").read_bytes()
    lock = read_json(root/"package-lock.json")["packages"]
    installed = read_json(root/"node_modules"/".package-lock.json")["packages"]
    if not isinstance(lock, dict) or not isinstance(installed, dict):
        raise ValueError("invalid lock inventory")
    entries, findings, hosts = [], [], Counter()
    for path, meta in sorted(lock.items()):
        if not path:
            continue
        folder = packages(root, path)
        lic = meta.get("license")
        version = meta.get("version")
        integrity = meta.get("integrity", "")
        parsed = urlsplit(meta.get("resolved", ""))
        host = parsed.hostname or "UNKNOWN"
        hosts[host] += 1
        try:
            good_integrity = integrity.startswith("sha512-") and len(base64.b64decode(integrity[7:], validate=True)) == 64
        except (ValueError, TypeError):
            good_integrity = False
        if not good_integrity or parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment or host != "registry.npmmirror.com":
            findings.append({"package":path,"kind":"lock_source_or_integrity_review"})
        if lic not in LICENSES:
            findings.append({"package":path,"kind":"license_declaration_review"})
        actual = installed.get(path)
        if actual is None:
            if not meta.get("optional") and not (phase=="runtime" and meta.get("dev")):
                findings.append({"package":path,"kind":"required_package_missing"})
            if folder.exists() and (folder/"package.json").exists():
                findings.append({"package":path,"kind":"hidden_lock_missing_package"})
            continue
        manifest = read_json(folder/"package.json")
        if actual.get("version") != version or manifest.get("version") != version:
            findings.append({"package":path,"kind":"installed_version_mismatch"})
        if manifest.get("license") != lic:
            findings.append({"package":path,"kind":"installed_license_declaration_review"})
        notices = []
        for file in sorted(folder.iterdir()):
            if not NOTICE.fullmatch(file.name):
                continue
            if file.is_symlink() or getattr(file, 'is_junction', lambda: False)() or not file.is_file() or file.stat().st_size > 2*1024*1024:
                findings.append({"package":path,"kind":"unsafe_notice"})
                continue
            raw = file.read_bytes()
            notices.append({"name":file.name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"family":license_family(raw)})
        if not notices or not any(n["family"] == lic or lic == "BSD-2-Clause" and n["family"] == "BSD-2-Clause-or-other" for n in notices):
            findings.append({"package":path,"kind":"notice_text_manual_review"})
        scripts = manifest.get("scripts", {})
        lifecycle = sorted(k for k in ("preinstall","install","postinstall") if isinstance(scripts,dict) and k in scripts)
        entries.append({"package":path,"version":version,"license":lic,"notices":notices,"lifecycle":lifecycle})
    for path in sorted(set(installed)-set(lock)):
        packages(root,path)
        findings.append({"package":path,"kind":"unlocked_installed_package"})
    fatal = {"required_package_missing","hidden_lock_missing_package","installed_version_mismatch","unlocked_installed_package","lock_source_or_integrity_review","unsafe_notice"}
    return {"phase":phase,"lockSha256":hashlib.sha256(lock_raw).hexdigest(),"locked":len(lock)-1,
            "installed":len(entries),"withNotice":sum(bool(x["notices"]) for x in entries),
            "licenseCounts":dict(Counter(str(x["license"]) for x in entries)),"registryHosts":dict(hosts),
            "findings":findings,"entries":entries,"identityChecks":"FAIL" if any(x["kind"] in fatal for x in findings) else "PASS",
            "completeLegalReview":False,"vulnerabilityAudit":"NOT_RUN","networkUsedByAudit":False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--phase",choices=("runtime","build"),required=True)
    p.add_argument("--out",required=True,type=Path)
    a = p.parse_args()
    try:
        result = audit(a.root,a.phase)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        summary = {k:v for k,v in result.items() if k not in ("entries","findings")}
        summary["findingCounts"] = dict(Counter(x["kind"] for x in result["findings"]))
        print("D22_DEPENDENCY_AUDIT "+json.dumps(summary,sort_keys=True))
        return 0 if result["identityChecks"]=="PASS" else 1
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        print("D22 dependency inventory incomplete; inspect isolated fixture locally",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
