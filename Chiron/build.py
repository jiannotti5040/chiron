#!/usr/bin/env python3
"""
build.py — lossless split / recompile of the single-file engines (chiron AND semic).

Review 2 named single-file maintainability as a bottleneck and asked for the planned "build step"
that lets a monolith be navigated and edited as modules. This is that tool, generalized to both
engines, with the one property that makes it safe to adopt: a BYTE-IDENTICAL round-trip. It splits
a file along its natural section seams into module parts, and recompiles them by concatenation;
`verify` proves the recompiled file is sha256-identical to the original, so nothing is added,
dropped, or reordered. The canonical runtime stays the single file; modules are a verified view.

    python3 build.py verify-all                 # prove both chiron and semic round-trip (default gate)
    python3 build.py selftest                   # same, as a 0/1 gate
    python3 build.py verify chiron              # one target
    python3 build.py split semic   modules/semic    # write the module parts + manifest
    python3 build.py compile modules/semic out.py   # recompile parts -> single file

Generated module trees are written under modules/ (gitignored) — run on demand, not committed.

Status: implemented & tested (byte-identical round-trip gate on chiron.py and semic.py).
"""
import os
import re
import sys
import json
import hashlib
import tempfile
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))

# Each engine declares how its natural section seams are detected. Losslessness holds for any seam
# choice (split + join is the identity); the seams just make the parts align with real sections.
TARGETS = {
    "chiron": {"file": "chiron.py", "kind": "banner", "pattern": r"^# PART [IVXLC]+"},
    "semic":  {"file": "semic.py",  "kind": "divider_title"},
}

_DIVIDER = re.compile(r"^#\s*=+\s*$")
_TITLE = re.compile(r"^#\s+(\d+\.|[A-Z])")


def _seam_predicate(target):
    if target["kind"] == "banner":
        rx = re.compile(target["pattern"])
        return lambda lines, i: bool(rx.match(lines[i]))
    # "divider_title": a full '# ====' divider immediately followed by a section title line
    return lambda lines, i: bool(_DIVIDER.match(lines[i]) and i + 1 < len(lines) and _TITLE.match(lines[i + 1]))


def _slug(line, fallback="section"):
    s = re.sub(r"^#\s*(PART\s+[IVXLC]+)?\s*[—:.-]*\s*", "", line).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:48] or fallback


def _segments(text, target):
    """(name, content) segments: a header, then one per detected seam. splitlines(keepends=True)
    + ''.join is the identity, so re-joining the segments in order reproduces the input exactly."""
    lines = text.splitlines(keepends=True)
    seam = _seam_predicate(target)
    idx = [i for i in range(len(lines)) if seam(lines, i)]
    if not idx:
        return [("00_header", text)]
    segs = [("00_header", "".join(lines[:idx[0]]))]
    for k, bi in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(lines)
        title = lines[bi] if target["kind"] == "banner" else lines[bi + 1] if bi + 1 < len(lines) else lines[bi]
        segs.append((f"{k + 1:02d}_{_slug(title)}", "".join(lines[bi:end])))
    return segs


def split(target_name, out_dir):
    t = TARGETS[target_name]
    src = os.path.join(_HERE, t["file"])
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"target": target_name, "source": t["file"],
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "modules": []}
    for name, content in _segments(text, t):
        fn = name + ".part"
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
            f.write(content)
        manifest["modules"].append({"file": fn, "lines": content.count("\n")})
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def compile_modules(in_dir):
    with open(os.path.join(in_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    parts = []
    for m in manifest["modules"]:
        with open(os.path.join(in_dir, m["file"]), encoding="utf-8") as f:
            parts.append(f.read())
    return "".join(parts)


def verify(target_name):
    t = TARGETS[target_name]
    src = os.path.join(_HERE, t["file"])
    with open(src, "r", encoding="utf-8") as f:
        original = f.read()
    with tempfile.TemporaryDirectory() as td:
        m = split(target_name, td)
        recompiled = compile_modules(td)
        n_modules = len(m["modules"])
    src_sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
    out_sha = hashlib.sha256(recompiled.encode("utf-8")).hexdigest()
    return {"target": target_name, "file": t["file"], "modules": n_modules,
            "byte_identical": src_sha == out_sha, "lines": original.count("\n") + 1,
            "sha256": src_sha}


def verify_all():
    return {name: verify(name) for name in TARGETS if os.path.exists(os.path.join(_HERE, TARGETS[name]["file"]))}


def _selftest():
    results = verify_all()
    ok = True
    for name, r in results.items():
        good = r["byte_identical"] and r["modules"] >= 2
        ok = ok and good
        print(f"  build.py [{name}]: {'PASS' if good else 'FAIL'} "
              f"({r['modules']} modules, {r['lines']} lines, byte-identical={r['byte_identical']})")
    if not results:
        print("  build.py self-test: SKIPPED (no engine files found)")
        return True
    print(f"  build.py self-test: {'PASS' if ok else 'FAIL'} ({len(results)} targets)")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lossless split/recompile of the single-file engines.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("verify-all")
    v = sub.add_parser("verify"); v.add_argument("target", choices=list(TARGETS))
    s = sub.add_parser("split"); s.add_argument("target", choices=list(TARGETS)); s.add_argument("out_dir")
    c = sub.add_parser("compile"); c.add_argument("in_dir"); c.add_argument("dst")
    args = ap.parse_args(argv)

    if args.cmd in (None, "selftest"):
        return 0 if _selftest() else 1
    if args.cmd == "verify-all":
        r = verify_all(); print(json.dumps(r, indent=2))
        return 0 if all(x["byte_identical"] for x in r.values()) else 1
    if args.cmd == "verify":
        r = verify(args.target); print(json.dumps(r, indent=2))
        return 0 if r["byte_identical"] else 1
    if args.cmd == "split":
        print(json.dumps(split(args.target, args.out_dir), indent=2)); return 0
    if args.cmd == "compile":
        out = compile_modules(args.in_dir)
        with open(args.dst, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {args.dst} ({out.count(chr(10)) + 1} lines)"); return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
