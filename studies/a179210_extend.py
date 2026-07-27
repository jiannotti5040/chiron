#!/usr/bin/env python3
"""
A179210 — the shortest published verification range found: 69 terms.

  a(n) = smallest prime q such that (r-q)/(q-p) = n, where p < q < r are
         CONSECUTIVE primes (0 if no such q exists).
  Conjecture: a(n) > 0 for all n >= 1.

WHY THIS IS THE BEST TARGET SO FAR. The b-file stops at n = 69. Every other
conjecture examined tonight had 1,000 to 6,000 published terms; this one has
sixty-nine. Essentially the whole claim is unswept.

METHOD. Rather than search per n, make ONE pass over consecutive prime triples.
For each (p,q,r) with gaps g1 = q-p and g2 = r-q, if g1 divides g2 then q is a
witness for n = g2/g1. A single sweep therefore fills in many n at once, and
the smallest q found for each n is a(n).

An n with NO witness anywhere in the swept range is a CANDIDATE counterexample
-- candidate, because absence in a bounded sweep is not absence, and the
distinction is the whole discipline here.
"""
import sys, time
from math import isqrt
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from oeis_novelty import entry, bfile

LIM = 200_000_000
print(f"  sieving primes to {LIM:,} ...", flush=True)
t0=time.time()
S = bytearray([1])*(LIM+1); S[0:2]=b"\x00\x00"
for i in range(2, isqrt(LIM)+1):
    if S[i]: S[i*i::i] = bytearray(len(S[i*i::i]))
print(f"  sieve built in {time.time()-t0:.0f}s", flush=True)

e = entry(179210)
data=[int(x) for x in e['data'].split(',') if x.strip().lstrip('-').isdigit()]
bt,st = bfile(179210, len(data))
print(f"  b-file: {st}, {len(bt)} terms  (n = 1..{len(bt)})")

# one sweep over consecutive prime triples
print("  sweeping consecutive prime triples ...", flush=True)
t0=time.time()
best = {}                      # n -> smallest witness q
prev = None; cur = None
for v in range(2, LIM+1):
    if not S[v]: continue
    if prev is not None and cur is not None:
        g1 = cur - prev; g2 = v - cur
        if g1 and g2 % g1 == 0:
            n = g2 // g1
            if n >= 1 and n not in best:
                best[n] = cur
    prev, cur = cur, v
print(f"  swept to {LIM:,} in {time.time()-t0:.0f}s; witnesses found for "
      f"{len(best):,} distinct n", flush=True)

print("\n  VALIDATION — recomputed a(n) vs published, n = 1..69:")
mismatch=[]
for i,pub in enumerate(bt, start=1):
    got = best.get(i, 0)
    if got != pub: mismatch.append((i, got, pub))
print(f"    all {len(bt)} published terms reproduced exactly: {not mismatch}")
if mismatch:
    for m in mismatch[:8]: print(f"      n={m[0]}: computed {m[1]}  published {m[2]}")
    print("    ENCODER INVALID — refusing to report anything past the b-file.")
    sys.exit(1)

top = max(best)
missing = [n for n in range(1, min(top, 20000)+1) if n not in best]
print(f"\n  BEYOND THE PUBLISHED RANGE (n > {len(bt)}):")
print(f"    largest n with a witness: {top:,}")
print(f"    n in [1, {min(top,20000):,}] with NO witness in the swept range: "
      f"{len(missing)}")
if missing:
    print(f"    first few: {missing[:20]}")
    print(f"    *** these are CANDIDATES only — absence in a bounded sweep is")
    print(f"        not absence. Each needs a deeper targeted search before")
    print(f"        anything is claimed.")
else:
    print(f"    every n from 1 to {min(top,20000):,} has a witness — "
          f"{min(top,20000)-len(bt):,} values beyond the b-file, none zero.")
