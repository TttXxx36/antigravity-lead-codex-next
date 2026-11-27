"""Offline repair of duplicate npm CycloneDX 1.5 leaf instance refs.

Keep original evidence immutable. Reject ambiguous inputs, not a full schema
validator or a new claim about actual tarball contents.
"""
import argparse
import base64
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
import uuid


class RepairError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RepairError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def load_json(data):
    def reject_constant(value):
        raise RepairError("nonfinite JSON value")
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)


def repair(raw, lock):
    require(raw.get("bomFormat") == "CycloneDX" and raw.get("specVersion") == "1.5", "unsupported format")
    require(set(raw) <= {"$schema", "bomFormat", "specVersion", "serialNumber", "version", "metadata", "components", "dependencies"}, "unsupported document fields")
    require(lock.get("lockfileVersion") == 3, "unsupported lock")
    result = deepcopy(raw)
    root = result["metadata"]["component"]
    components = result["components"]
    nodes = result["dependencies"]
    packages = lock["packages"]
    by_ref = defaultdict(list)
    by_path = {}
    paths = {}
    allowed = {"bom-ref", "type", "name", "version", "scope", "description", "purl", "properties", "externalReferences", "hashes", "licenses", "author", "group"}
    require(set(result["metadata"]) <= {"timestamp", "tools", "component", "properties", "lifecycles"}, "unsupported metadata fields")
    for component in [root, *components]:
        require(set(component) <= allowed, "unsupported component fields")
        ref = component["bom-ref"]
        name = component["name"]
        require(isinstance(name, str) and isinstance(ref, str), "invalid identity")
        pv = [p["value"] for p in component.get("properties", []) if p["name"] == "cdx:npm:package:path"]
        require(len(pv) == 1, "missing or ambiguous package path")
        path = pv[0]
        require(isinstance(path, str) and path not in by_path and path in packages, "path not unique or locked")
        require(path == "" if component is root else bool(re.fullmatch(r"node_modules/(?:@[^/]+/)?[^/]+(?:/node_modules/(?:@[^/]+/)?[^/]+)*", path)), "unsupported package path")
        require(not any(part in {".", ".."} for part in path.split("/")) and "\\" not in path, "unsafe path")
        entry = packages[path]
        require(not entry.get("link") and component["version"] == entry["version"] and ref == name + "@" + component["version"], "package identity mismatch")
        if component is root:
            require(name == entry.get("name", lock.get("name")), "root name mismatch")
        else:
            require(path.rsplit("node_modules/", 1)[-1] == name, "package name/path mismatch")
            hashes = [h["content"] for h in component.get("hashes", []) if h["alg"] == "SHA-512"]
            integrity = entry.get("integrity", "")
            require(integrity.startswith("sha512-"), "unsupported integrity")
            digest = base64.b64decode(integrity[7:], validate=True)
            require(len(digest) == 64 and hashes == [digest.hex()], "lock hash mismatch")
        by_ref[ref].append(component)
        by_path[path] = component
        paths[id(component)] = path
    require(paths[id(root)] == "", "root path mismatch")
    require(all(set(n) == {"ref", "dependsOn"} and isinstance(n["dependsOn"], list) and len(n["dependsOn"]) == len(set(n["dependsOn"])) and all(x in by_ref for x in n["dependsOn"]) for n in nodes), "invalid dependency node")
    require(Counter(n["ref"] for n in nodes) == Counter({ref: len(cs) for ref, cs in by_ref.items()}), "node multiplicity mismatch")
    duplicates = {ref: cs for ref, cs in by_ref.items() if len(cs) > 1}
    require(root["bom-ref"] not in duplicates, "duplicate root")
    new_refs = {}
    mapping = []
    for ref, cs in duplicates.items():
        require(all(n["dependsOn"] == [] for n in nodes if n["ref"] == ref), "duplicate nonleaf node")
        for component in cs:
            path = paths[id(component)]
            require(not any(packages[path].get(k) for k in ("dependencies", "optionalDependencies", "peerDependencies", "bundleDependencies", "bundledDependencies")), "duplicate lock entry not a leaf")
            new = "urn:alc:npm-path:" + quote(path, safe="")
            require(new not in by_ref and new not in new_refs.values(), "new ref collision")
            new_refs[path] = new
            mapping.append({"old": ref, "path": path, "new": new})
            component["bom-ref"] = new
    if not duplicates:
        return result, []
    repaired_nodes = []
    seen_targets = set()
    for node in nodes:
        ref = node["ref"]
        if ref in duplicates:
            continue
        parent_path = paths[id(by_ref[ref][0])]
        edges = []
        for child in node["dependsOn"]:
            if child not in duplicates:
                edges.append(child)
                continue
            name = duplicates[child][0]["name"]
            entry = packages[parent_path]
            require(name in entry.get("dependencies", {}) or name in entry.get("optionalDependencies", {}), "ambiguous incoming dependency")
            bases = [parent_path]
            while bases[-1]:
                v = bases[-1]
                bases.append(v.rsplit("/node_modules/", 1)[0] if "/node_modules/" in v else "")
            candidates = [(b + "/" if b else "") + "node_modules/" + name for b in bases]
            target = next((p for p in candidates if p in packages), None)
            require(target in new_refs and any(by_path[target] is c for c in duplicates[child]), "ambiguous or shadowed resolution")
            edges.append(new_refs[target])
            seen_targets.add(target)
        repaired_nodes.append({"ref": ref, "dependsOn": edges})
    require(seen_targets == set(new_refs), "unreferenced duplicate instance")
    repaired_nodes.extend({"ref": ref, "dependsOn": []} for ref in new_refs.values())
    result["dependencies"] = repaired_nodes
    refs = [root["bom-ref"]] + [c["bom-ref"] for c in components]
    require(len(refs) == len(set(refs)) and Counter(n["ref"] for n in repaired_nodes) == Counter(refs), "derived ref uniqueness failure")
    require(all(x in set(refs) for n in repaired_nodes for x in n["dependsOn"]), "derived edge closure failure")
    return result, mapping


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    for arg in ("raw", "lock", "out", "report"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    try:
        paths = (args.raw, args.lock, args.out, args.report)
        require(len({x.resolve() for x in paths}) == 4, "inputs and outputs must be distinct")
        require(not args.out.exists() and not args.report.exists(), "outputs already exist")
        require(all(x.stat().st_size <= 16 * 1024 * 1024 for x in (args.raw, args.lock)), "input size limit")
        raw_bytes, lock_bytes = args.raw.read_bytes(), args.lock.read_bytes()
        out, mapping = repair(load_json(raw_bytes), load_json(lock_bytes))
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()
        if mapping:
            out["serialNumber"] = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, raw_hash + ":alc-leaf-ref-repair-v2"))
        encoded = (json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
        report = {"rawSha256": raw_hash, "lockSha256": hashlib.sha256(lock_bytes).hexdigest(), "derivedSha256": hashlib.sha256(encoded).hexdigest(), "components": len(out["components"]), "dependencyNodes": len(out["dependencies"]), "uniqueRefs": len(set(n["ref"] for n in out["dependencies"])), "mapping": mapping, "scope": "duplicate leaf repair, structural checks only; not full schema, tarball, or legal validation"}
        with args.out.open("xb") as f:
            f.write(encoded)
        with args.report.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        print("PASS: SBOM structural repair;", report["components"], "components;", report["uniqueRefs"], "unique graph refs;", len(mapping), "rewrites")
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RecursionError) as exc:
        print("FAIL: SBOM repair rejected input or output:", type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
