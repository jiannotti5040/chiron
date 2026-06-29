#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Performance profile — where the time goes, so optimization is evidence-driven.

    python3 profile.py
    python3 profile.py --json

Times collapse across hypothesis classes and input sizes, and the cipher solver,
using a median over repeats. Timings are indicative (wall clock), not a contract;
the engine's guarantees are correctness and determinism, not latency. The optional
C hot-path (`chiron.py bench-native`) and memory compaction (`chiron.py compact`)
are the existing accelerators and are reported here for orientation.
"""
import os
import sys
import json
import time
import math
import statistics
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chiron import collapse, solve_cipher  # noqa: E402


def _fib(n):
    s = [0, 1]
    while len(s) < n:
        s.append(s[-1] + s[-2])
    return s[:n]


def _gen(kind, n):
    if kind == "arithmetic":
        return [3 + 4 * i for i in range(n)]
    if kind == "geometric":
        return [2 ** i for i in range(n)]
    if kind == "polynomial_deg3":
        return [i ** 3 - 2 * i + 7 for i in range(n)]
    if kind == "fibonacci":
        return _fib(n)
    if kind == "catalan":
        return [math.comb(2 * i, i) // (i + 1) for i in range(n)]
    raise ValueError(kind)


def _median_ms(fn, repeats=7):
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000.0)
    return round(statistics.median(ts), 3)


def profile():
    classes = ["arithmetic", "geometric", "polynomial_deg3", "fibonacci", "catalan"]
    sizes = [12, 25, 50, 100]
    by_class = {}
    for kind in classes:
        row = {}
        for n in sizes:
            seq = _gen(kind, n)
            row["n%d" % n] = _median_ms(lambda s=seq: collapse(s))
        by_class[kind] = row
    cipher = _median_ms(lambda: solve_cipher("WKLV LV D ORQJHU VHFUHW PHVVDJH WR GHFRGH"))
    # find the slowest single measurement
    slowest = max(((k, n, v) for k, row in by_class.items() for n, v in row.items()),
                  key=lambda t: t[2])
    return {"collapse_ms_by_class_and_size": by_class,
            "cipher_solve_ms": cipher,
            "slowest_case": {"class": slowest[0], "size": slowest[1], "ms": slowest[2]},
            "sizes": sizes, "classes": classes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    p = profile()
    if args.json:
        print(json.dumps(p, indent=2))
        return 0
    print("=" * 64)
    print("CHIRON PERFORMANCE PROFILE  (median ms; wall clock, indicative)")
    print("=" * 64)
    header = "  %-18s" % "class" + "".join("%9s" % ("n=%d" % n) for n in p["sizes"])
    print(header)
    for kind in p["classes"]:
        row = p["collapse_ms_by_class_and_size"][kind]
        print("  %-18s" % kind + "".join("%9s" % row["n%d" % n] for n in p["sizes"]))
    print("\n  cipher solve (ciphertext-only) ... %s ms" % p["cipher_solve_ms"])
    s = p["slowest_case"]
    print("  slowest collapse case ............ %s at %s -> %s ms"
          % (s["class"], s["size"], s["ms"]))
    print("\n  notes:")
    print("   * exact rational arithmetic; cost grows with terms and class richness")
    print("     (holonomic/Catalan is the heaviest fitter).")
    print("   * optional C hot-path:  python3 chiron.py bench-native")
    print("   * memory compaction:    python3 chiron.py compact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
