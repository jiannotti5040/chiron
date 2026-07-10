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
  - imports / imported_by: the INTERNAL dependency graph — which vault
    modules this script imports and which import it        [static scan]
  - roles: mechanical tags derived from name patterns and provable facts
    only (benchmark/builder/server/test/certifying) — never editorial
  - whether it has a `selftest` entry point                [static scan]
  - line count                                             [static scan]
  - SPDX header present?                                   [static scan]
  - last run: command, exit code, runtime_ms, tail of stdout   [live, optional]
  - emitted artifact: latest.json summary if one exists    [live]

Top-level "graph" section: every internal import edge [importer, imported],
sorted — the manifest is a build graph, not just a list.

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


def _local_imports(path: str, stems: set) -> List[str]:
    """Top-level module names this script imports that are OTHER vault
    scripts — the internal dependency graph, from the AST, no execution."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except Exception:
        return []
    found = set()
    self_stem = os.path.basename(path)[:-3]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                found.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module.split(".")[0])
    return sorted((found & stems) - {self_stem})


def _roles(stem: str, emits_artifact: bool) -> List[str]:
    """Mechanical role tags. Derived ONLY from name patterns and provable
    facts, never from judgment — a wrong tag here would be an overclaim."""
    roles = []
    if stem.startswith(("bench_", "benchmark")):
        roles.append("benchmark")
    if stem.startswith("build"):
        roles.append("builder")
    if stem.endswith("_server"):
        roles.append("server")
    if stem.startswith("test_"):
        roles.append("test")
    if emits_artifact:
        roles.append("certifying")
    return roles


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


def _load_lexicon() -> Dict[str, Any]:
    """Per-script context (Chiron-vocabulary title + math/prog/concept lenses) for the
    dashboard. Optional: scripts not listed fall back to their docstring purpose."""
    p = os.path.join(ROOT, "lexicon.json")
    if os.path.isfile(p):
        try:
            return {k: v for k, v in json.load(open(p, encoding="utf-8")).items()
                    if not k.startswith("_")}
        except Exception:
            return {}
    return {}


def build(run: bool, timeout: int) -> Dict[str, Any]:
    lexicon = _load_lexicon()

    # pass 1: enumerate, so the import scan knows every local stem
    found: List[tuple] = []
    for dirpath, _, files in os.walk(ROOT):
        if "artifacts" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            if _runnable(path):
                found.append((fn[:-3], path))
    stems = {s for s, _ in found}

    # pass 2: per-script records, now with the internal import graph
    entries: List[Dict[str, Any]] = []
    imported_by: Dict[str, List[str]] = {}
    for stem, path in found:
        rec: Dict[str, Any] = {
            "script": stem,
            "path": os.path.relpath(path, ROOT),
            "purpose": _purpose(path),
        }
        rec.update(_scan(path))
        rec["imports"] = _local_imports(path, stems)
        for tgt in rec["imports"]:
            imported_by.setdefault(tgt, []).append(stem)
        if stem in lexicon:
            rec["title"] = lexicon[stem].get("title", "")
            rec["lens"] = {k: lexicon[stem][k] for k in ("math", "prog", "concept")
                           if k in lexicon[stem]}
            if "capabilities" in lexicon[stem]:       # optional, curated in lexicon
                rec["capabilities"] = list(lexicon[stem]["capabilities"])
        art = _artifact_summary(stem)
        rec["artifact"] = art
        rec["emits_artifact"] = art is not None
        rec["roles"] = _roles(stem, art is not None)
        if run and rec["has_selftest"] and stem not in NO_AUTORUN:
            rec["last_run"] = _run_selftest(path, timeout)
            # refresh artifact summary in case the run just emitted one
            rec["artifact"] = _artifact_summary(stem)
            rec["emits_artifact"] = rec["artifact"] is not None
            rec["roles"] = _roles(stem, rec["emits_artifact"])
        else:
            rec["last_run"] = None
        entries.append(rec)

    # reverse edges + the graph section: the manifest as a build graph
    for rec in entries:
        rec["imported_by"] = sorted(imported_by.get(rec["script"], []))
    edges = sorted([src["script"], tgt] for src in entries for tgt in src["imports"])

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
            "internal_edges": len(edges),
        },
        "graph": {
            "note": "internal import edges [importer, imported], AST-derived",
            "edges": edges,
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
    print(f"  internal edges     : {s['internal_edges']}")
    print(f"  -> {os.path.relpath(MANIFEST, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
