#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
build_manifest — enumerate every runnable script in the vault and capture, for
each, what it proves, how it ran, and the artifact it left behind.

This is the connective tissue the vault was missing. The portfolio is a set of
independently-runnable, self-certifying scripts; until now nothing enumerated
them or tied each one to its result. This produces ``manifest.json`` — a single
machine-readable index the dashboard reads.

What it records per script:
  - path, stem
  - dependencies (stdlib-only vs needs numpy/scipy)        [static scan]
  - whether it has a `selftest` entry point                [static scan]
  - line count                                             [static scan]
  - SPDX header present?                                   [static scan]
  - last run: command, exit code, runtime_ms, tail of stdout   [live, optional]
  - emitted artifact: latest.json summary if one exists    [live]

Run modes:
    python3 build_manifest.py              # static index only (fast, safe)
    python3 build_manifest.py --run        # also execute each `selftest`, capture results
    python3 build_manifest.py --run --timeout 120

Writes manifest.json next to this script. Deterministic in static mode; the
--run mode records real timings so successive runs differ only in runtime_ms.

stdlib only.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest.json")
ARTIFACT_ROOT = os.path.join(ROOT, "artifacts")

# Scripts that should not be auto-run even with --run: servers (block), the
# heavy grow corpus builder, and this file itself.
NO_AUTORUN = {
    "assistant_server", "console_server",   # long-lived servers
    "chiron_grow", "president_grow", "grow_control", "grow_clean",  # mutate corpus
    "build_manifest", "ingest_pdf",
}

# Third-party imports that mean "not stdlib-only".
THIRD_PARTY = {"numpy", "scipy", "np", "pandas", "torch", "sklearn"}


def _runnable(path: str) -> bool:
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    return ("__main__" in src) or ("def main(" in src) or ("sys.argv" in src)


def _scan(path: str) -> Dict[str, Any]:
    src = open(path, encoding="utf-8", errors="replace").read()
    lines = src.count("\n") + 1
    has_spdx = "SPDX-License-Identifier" in src[:600]
    has_selftest = ("selftest" in src) or ("_selftest" in src)
    deps = set()
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    top = n.name.split(".")[0]
                    if top in THIRD_PARTY:
                        deps.add(top)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                if top in THIRD_PARTY:
                    deps.add(top)
    except SyntaxError:
        pass
    # normalize numpy alias
    if "np" in deps:
        deps.discard("np"); deps.add("numpy")
    return {
        "lines": lines,
        "has_spdx_header": has_spdx,
        "has_selftest": has_selftest,
        "dependencies": sorted(deps) if deps else [],
        "stdlib_only": not deps,
    }


def _purpose(path: str) -> str:
    """First non-empty line of the module docstring = a one-line purpose."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        doc = ast.get_docstring(tree) or ""
    except Exception:
        doc = ""
    for line in doc.splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _artifact_summary(stem: str) -> Optional[Dict[str, Any]]:
    latest = os.path.join(ARTIFACT_ROOT, stem, "latest.json")
    if not os.path.isfile(latest):
        return None
    try:
        d = json.load(open(latest, encoding="utf-8"))
    except Exception:
        return None
    return {
        "verified": d.get("verified"),
        "self_hash": d.get("self_hash"),
        "generated_utc": d.get("generated_utc"),
        "confidence": d.get("human_view", {}).get("confidence"),
        "what_was_discovered": d.get("human_view", {}).get("what_was_discovered"),
        "what_would_falsify": d.get("human_view", {}).get("what_would_falsify"),
    }


def _run_selftest(path: str, timeout: int) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, path, "selftest"], cwd=ROOT,
                              capture_output=True, text=True, timeout=timeout)
        used = "selftest"
        # Some scripts expose the selftest as a flag (--selftest) rather than a
        # positional subcommand; argparse rejects the wrong form with exit code 2.
        # Fall back so the manifest reflects the real result, not the invocation.
        if proc.returncode == 2:
            alt = subprocess.run([sys.executable, path, "--selftest"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=timeout)
            if alt.returncode != 2:
                proc, used = alt, "--selftest"
        dt = (time.perf_counter() - t0) * 1000.0
        tail = "\n".join(proc.stdout.strip().splitlines()[-3:])
        return {"command": used, "exit_code": proc.returncode,
                "runtime_ms": round(dt, 1), "stdout_tail": tail}
    except subprocess.TimeoutExpired:
        return {"command": "selftest", "exit_code": None,
                "runtime_ms": None, "stdout_tail": f"TIMEOUT after {timeout}s"}
    except Exception as e:
        return {"command": "selftest", "exit_code": None,
                "runtime_ms": None, "stdout_tail": f"ERROR: {e}"}


def build(run: bool, timeout: int) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    for dirpath, _, files in os.walk(ROOT):
        if "artifacts" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            if not _runnable(path):
                continue
            stem = fn[:-3]
            rec: Dict[str, Any] = {
                "script": stem,
                "path": os.path.relpath(path, ROOT),
                "purpose": _purpose(path),
            }
            rec.update(_scan(path))
            art = _artifact_summary(stem)
            rec["artifact"] = art
            rec["emits_artifact"] = art is not None
            if run and rec["has_selftest"] and stem not in NO_AUTORUN:
                rec["last_run"] = _run_selftest(path, timeout)
                # refresh artifact summary in case the run just emitted one
                rec["artifact"] = _artifact_summary(stem)
                rec["emits_artifact"] = rec["artifact"] is not None
            else:
                rec["last_run"] = None
            entries.append(rec)

    entries.sort(key=lambda r: r["path"])
    n = len(entries)
    return {
        "system": "CHIRON",
        "owner": "Jacob Iannotti",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "run" if run else "static",
        "summary": {
            "runnable_scripts": n,
            "with_selftest": sum(1 for e in entries if e["has_selftest"]),
            "stdlib_only": sum(1 for e in entries if e["stdlib_only"]),
            "with_spdx_header": sum(1 for e in entries if e["has_spdx_header"]),
            "emitting_artifacts": sum(1 for e in entries if e["emits_artifact"]),
        },
        "scripts": entries,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Index the vault's runnable scripts.")
    ap.add_argument("--run", action="store_true",
                    help="execute each script's selftest and record the result")
    ap.add_argument("--timeout", type=int, default=120,
                    help="per-script timeout in seconds (with --run)")
    args = ap.parse_args(argv)

    manifest = build(run=args.run, timeout=args.timeout)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    s = manifest["summary"]
    print(f"[manifest] {s['runnable_scripts']} runnable scripts indexed "
          f"({manifest['mode']} mode)")
    print(f"  with selftest      : {s['with_selftest']}")
    print(f"  stdlib-only        : {s['stdlib_only']}")
    print(f"  with SPDX header   : {s['with_spdx_header']}")
    print(f"  emitting artifacts : {s['emitting_artifacts']}")
    print(f"  -> {os.path.relpath(MANIFEST, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
