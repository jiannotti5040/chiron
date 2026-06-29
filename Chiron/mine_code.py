#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Code-repository mining — collapse every Python source file to its relabel-invariant
structural skeleton and find structural clones.

    python3 mine_code.py [DIR]          # default: this folder
    python3 mine_code.py --json [DIR]

Two files with the same skeleton are clones through renaming and reformatting — the
fingerprint is unchanged by variable names or whitespace. This is the engine's
`collapse` operating on the code domain, which is one of its strongest.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import collapse  # noqa: E402


def py_files(root):
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in sorted(files):
            if f.endswith(".py"):
                out.append(os.path.join(dirpath, f))
    return out


def mine(root):
    rows, by_skel = [], {}
    for path in py_files(root):
        try:
            src = open(path, encoding="utf-8", errors="replace").read()
            inv = collapse({"code": src})
            skel = inv.structure.get("skeleton_hash")
            nodes = inv.structure.get("n_nodes")
        except Exception as e:
            skel, nodes = None, None
            inv = None
        rel = os.path.relpath(path, root)
        rows.append({"file": rel, "model_class": getattr(inv, "model_class", "?"),
                     "n_nodes": nodes, "skeleton": skel})
        if skel:
            by_skel.setdefault(skel, []).append(rel)
    clones = [{"skeleton": k[:12], "files": v} for k, v in by_skel.items() if len(v) > 1]
    return {"root": root, "files_scanned": len(rows),
            "distinct_skeletons": len(by_skel), "clone_groups": clones, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = mine(args.dir)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0
    print("=" * 66)
    print("CODE MINING — structural skeletons over %s" % out["root"])
    print("=" * 66)
    print("  files scanned ......... %d" % out["files_scanned"])
    print("  distinct skeletons .... %d" % out["distinct_skeletons"])
    print("  structural clones ..... %d group(s)" % len(out["clone_groups"]))
    for c in out["clone_groups"]:
        print("    clone skeleton %s:" % c["skeleton"])
        for f in c["files"]:
            print("        - %s" % f)
    print("\n  largest files by AST node count:")
    for r in sorted([r for r in out["rows"] if r["n_nodes"]],
                    key=lambda r: -r["n_nodes"])[:8]:
        print("    %6d nodes  %s" % (r["n_nodes"], r["file"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
