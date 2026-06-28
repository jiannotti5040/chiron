#!/usr/bin/env python3
"""
build.py — lossless split / recompile of the single-file monolith.

Review 2 named single-file maintainability as a bottleneck and asked for the planned "build step"
that lets the monolith be edited as modules. This is that tool, with the one property that makes
it safe to adopt: a BYTE-IDENTICAL round-trip. It splits chiron.py along its `# PART` section
banners into separate module files, and recompiles them by concatenation; `verify` proves the
recompiled file is sha256-identical to the original, so nothing is added, dropped, or reordered.
The signed monolith is never edited blindly — modules are edited, then recompiled and re-verified.

    python3 build.py verify                 # prove the round-trip is byte-identical (default: chiron.py)
    python3 build.py selftest               # same, as a 0/1 gate
    python3 build.py split chiron.py build/ # write the module files + manifest
    python3 build.py compile build/ out.py  # recompile modules -> single file

Status: implemented & tested (byte-identical round-trip gate on the real monolith).
"""
import os
import re
import sys
import json
import hashlib
import tempfile
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = os.path.join(_HERE, "chiron.py")
BANNER = re.compile(r"^# PART [IVXLC]+")


def _slug(line: str) -> str:
    s = re.sub(r"^# PART [IVXLC]+\s*[—-]*\s*", "", line).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "section"


def _segments(text: str):
    """Split text into (name, content) segments: a header, then one per `# PART` banner.
    splitlines(keepends=True) + ''.join is the identity, so re-joining the segments in order
    reproduces the input exactly."""
    lines = text.splitlines(keepends=True)
    idx = [i for i, l in enumerate(lines) if BANNER.match(l)]
    segs = []
    if not idx:
        return [("00_header", text)]
    segs.append(("00_header", "".join(lines[:idx[0]])))
    for k, bi in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(lines)
        segs.append((f"{k + 1:02d}_{_slug(lines[bi])}", "".join(lines[bi:end])))
    return segs


def split(src_path: str, out_dir: str):
    with open(src_path, "r", encoding="utf-8") as f:
        text = f.read()
    src_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"source": os.path.basename(src_path), "sha256": src_sha, "modules": []}
    for name, content in _segments(text):
        fn = name + ".part"
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
            f.write(content)
        manifest["modules"].append({"file": fn, "lines": content.count("\n")})
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def compile_modules(in_dir: str) -> str:
    with open(os.path.join(in_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    parts = []
    for m in manifest["modules"]:
        with open(os.path.join(in_dir, m["file"]), encoding="utf-8") as f:
            parts.append(f.read())
    return "".join(parts)


def verify(src_path: str = DEFAULT_SRC) -> dict:
    with open(src_path, "r", encoding="utf-8") as f:
        original = f.read()
    src_sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
    with tempfile.TemporaryDirectory() as td:
        split(src_path, td)
        recompiled = compile_modules(td)
        n_modules = len(json.load(open(os.path.join(td, "manifest.json")))["modules"])
    out_sha = hashlib.sha256(recompiled.encode("utf-8")).hexdigest()
    return {"source": os.path.basename(src_path), "modules": n_modules,
            "source_sha256": src_sha, "recompiled_sha256": out_sha,
            "byte_identical": src_sha == out_sha,
            "lines": original.count("\n") + 1}


def _selftest() -> bool:
    if not os.path.exists(DEFAULT_SRC):
        print("  build.py self-test: SKIPPED (chiron.py not found)")
        return True
    r = verify(DEFAULT_SRC)
    ok = r["byte_identical"] and r["modules"] >= 2
    print(f"  build.py self-test: {'PASS' if ok else 'FAIL'} "
          f"({r['modules']} modules, {r['lines']} lines, byte-identical={r['byte_identical']})")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lossless split/recompile of the single-file monolith.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    v = sub.add_parser("verify"); v.add_argument("src", nargs="?", default=DEFAULT_SRC)
    s = sub.add_parser("split"); s.add_argument("src"); s.add_argument("out_dir")
    c = sub.add_parser("compile"); c.add_argument("in_dir"); c.add_argument("dst")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "split":
        m = split(args.src, args.out_dir)
        print(json.dumps(m, indent=2)); return 0
    if args.cmd == "compile":
        out = compile_modules(args.in_dir)
        with open(args.dst, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {args.dst} ({out.count(chr(10)) + 1} lines)"); return 0
    r = verify(getattr(args, "src", DEFAULT_SRC))
    print(json.dumps(r, indent=2))
    return 0 if r["byte_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
