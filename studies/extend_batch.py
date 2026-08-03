#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
extend_batch.py — push OEIS conjectures past their published b-files.

Published data never contradicts a published claim: authors check it before
submitting. The only unswept ground is beyond where the author stopped. Every
encoder must reproduce the published terms before it may extend anything.
"""
import sys, time
from math import isqrt
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import entry, bfile

# a(n) needs pi(k*n) for k < n, so the sieve must cover n^2 for the largest n
# reached. An earlier version sieved to 3e6 and crashed the moment it passed
# the published range -- the encoder was correct, the BOUND was not.
LIM = 30_000_000
print(f"  sieving to {LIM:,} ...", flush=True)
S = bytearray([1])*(LIM+1); S[0:2]=b"\x00\x00"
for i in range(2, isqrt(LIM)+1):
    if S[i]: S[i*i::i] = bytearray(len(S[i*i::i]))
PI = [0]*(LIM+1); c = 0
for i in range(LIM+1):
    if S[i]: c += 1
    PI[i] = c
print(f"  sieve ready (max n reachable = {isqrt(LIM):,})", flush=True)

def a237578(n):
    """a(n) = |{0<k<n : pi(k*n) is prime}|"""
    c = 0
    for k in range(1, n):
        v = k*n
        if v > LIM: break
        if S[PI[v]]: c += 1
    return c

def run(label, anum, fn, budget=600):
    e = entry(anum)
    data = [int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
    bt, st = bfile(anum, len(data))
    off = int((e.get('offset') or '1,1').split(',')[0])
    print(f"\n{'='*74}\n{label}  (A{anum:06d})\n{'='*74}")
    print(f"  {e.get('name','')[:96]}")
    print(f"  b-file: {st}, {len(bt)} terms")
    ok = all(fn(off+i) == bt[i] for i in range(min(30, len(bt))))
    print(f"  encoder reproduces first 30 published terms: {ok}")
    if not ok:
        print("  ENCODER INVALID — refusing to extend."); return
    nmax = isqrt(LIM)
    start = off+len(bt); t0 = time.time(); n = start; zeros = []
    while time.time()-t0 < budget and n < nmax:
        if fn(n) == 0:
            zeros.append(n); print(f"  *** a({n}) = 0 — CANDIDATE COUNTEREXAMPLE"); break
        if n % 500 == 0: print(f"    n={n:,}  ({time.time()-t0:.0f}s)", flush=True)
        n += 1
    print(f"  extended n = {start:,} .. {n:,}   ({time.time()-t0:.0f}s)")
    print(f"  counterexamples: {zeros if zeros else 'NONE'}")
    if not zeros:
        print(f"  {n-start:,} values beyond the published b-file.")

if __name__ == "__main__":
    run("A237578  pi(k*n) prime", 237578, a237578)
