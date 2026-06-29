#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Chiron vs. conventional compression — an honest comparison, both directions.

    python3 compare.py
    python3 compare.py --json

The question is not "is Chiron a better compressor than gzip?" It is not a
general compressor at all. The point is categorical:

  * General compressors (gzip, bz2, lzma) shrink the BYTES you show them. Their
    output grows with the input, and they cannot produce a single term beyond
    what they were given.
  * Chiron, when a surface has an exact generator, stores the GENERATOR — a
    handful of bytes that do not grow with the input and that regenerate any
    term, including term one million.
  * When a surface has NO structure, Chiron abstains and the general compressors
    are the right tool. This file shows that case too, so the comparison is fair.

Deterministic, offline. Lengths only (so timestamps in container headers don't
matter).
"""
import os
import sys
import gzip
import bz2
import lzma
import json
import math
import argparse
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import collapse  # noqa: E402


def _fib(n):
    s = [0, 1]
    while len(s) < n:
        s.append(s[-1] + s[-2])
    return s[:n]


def _seq(name, n):
    if name == "powers of 2":
        return [2 ** i for i in range(n)]
    if name == "Fibonacci":
        return _fib(n)
    if name == "squares":
        return [i * i for i in range(n)]
    if name == "Catalan":
        return [math.comb(2 * i, i) // (i + 1) for i in range(n)]
    if name == "primes":
        out, c = [], 2
        while len(out) < n:
            if all(c % p for p in out if p * p <= c):
                out.append(c)
            c += 1
        return out
    if name == "random":
        rng = random.Random(1)                 # fixed seed -> reproducible
        return [rng.randint(0, 10 ** 6) for _ in range(n)]
    raise ValueError(name)


def _render(terms):
    return ",".join(str(t) for t in terms).encode()


def _law_bytes(inv):
    """Bytes needed to store the recovered generator (class + parameters)."""
    blob = json.dumps({"class": inv.model_class, "params": inv.to_dict()["params"]},
                      sort_keys=True, default=str)
    return len(blob.encode())


def _measure(terms):
    raw = _render(terms)
    row = {"raw": len(raw),
           "gzip": len(gzip.compress(raw, 9)),
           "bz2": len(bz2.compress(raw, 9)),
           "lzma": len(lzma.compress(raw))}
    try:
        inv = collapse(terms)
        if inv.verified:
            row["chiron_law"] = _law_bytes(inv)
            # prove it extrapolates: regenerate a term far past the input
            far = inv.predict(len(terms) + 200)[len(terms) + 199]
            row["extrapolates"] = "term %d = %d digits" % (
                len(terms) + 199, len(str(abs(int(far)))))
            row["model"] = inv.model_class
        else:
            row["chiron_law"] = None
            row["extrapolates"] = "abstained (no exact law)"
            row["model"] = "—"
    except Exception:
        row["chiron_law"] = None
        row["extrapolates"] = "abstained"
        row["model"] = "—"
    return row


def growth_demo(name="powers of 2", sizes=(16, 64, 256, 1024)):
    return [{"n": n, **_measure(_seq(name, n))} for n in sizes]


def cross_section(n=64):
    names = ["powers of 2", "Fibonacci", "squares", "Catalan", "primes", "random"]
    return {name: _measure(_seq(name, n)) for name in names}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    grow = growth_demo()
    cross = cross_section()
    report = {"growth_demo_powers_of_2": grow, "cross_section_n64": cross}
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print("=" * 74)
    print("CHIRON vs gzip / bz2 / lzma — structure recovery vs. byte compression")
    print("=" * 74)
    print("\nGROWTH: the same law, more terms (powers of 2). Bytes to STORE the input:")
    print("  %6s %8s %8s %8s %8s | %11s  %s"
          % ("N", "raw", "gzip", "bz2", "lzma", "chiron-law", "regenerates"))
    for r in grow:
        print("  %6d %8d %8d %8d %8d | %11s  %s"
              % (r["n"], r["raw"], r["gzip"], r["bz2"], r["lzma"],
                 str(r["chiron_law"]), r["extrapolates"]))
    print("  -> compressors grow with N and stop at the last term;")
    print("     the recovered law stays constant and regenerates terms it never saw.")

    print("\nCROSS-SECTION at N=64 (bytes; lower is tighter):")
    print("  %-13s %6s %6s %6s %6s | %11s  %s"
          % ("sequence", "raw", "gzip", "bz2", "lzma", "chiron-law", "model / status"))
    for name, r in cross.items():
        law = str(r["chiron_law"]) if r["chiron_law"] is not None else "—"
        status = r["model"] if r["chiron_law"] is not None else r["extrapolates"]
        print("  %-13s %6d %6d %6d %6d | %11s  %s"
              % (name, r["raw"], r["gzip"], r["bz2"], r["lzma"], law, status))

    print("\nReading it honestly:")
    print("  * On structured sequences Chiron stores a constant-size law and can")
    print("    produce any future term; the compressors cannot produce even one.")
    print("  * On 'random' Chiron abstains and gzip/bz2/lzma are the right tool —")
    print("    that is the correct division of labor, not a loss.")
    print("  * 'primes' has no closed form in Chiron's classes: it abstains rather")
    print("    than fabricate a rule. Compression still works on the digits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
