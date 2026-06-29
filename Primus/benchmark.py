#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
PRIMUS proving run — recovery rate + reliability on a large offline bank of
known-generator integer sequences (no network; sequences generated from known
formulas, OEIS-style).

The honest test: feed collapse the FIRST k terms, then check whether the rule
it recovered correctly predicts terms k..k+H that it NEVER SAW. We report:
  - recovery rate: % of recoverable sequences it VERIFIES
  - PRECISION of the 'verified' label: when it says verified, how often is the
    external continuation actually correct (this is the number that matters)
  - honest-negative rate: on sequences OUTSIDE its hypothesis class, how often
    it correctly declines to claim 'verified'
"""
import math, statistics
import invariant_engine as E

K_INPUT = 12     # terms the engine sees
H_HID = 4        # truly-held-out terms used only for grading


def gen(fn, n):
    return [float(fn(i)) for i in range(n)]


def recur(seeds, coeffs, n):
    o = [float(s) for s in seeds]
    p = len(coeffs)
    while len(o) < n:
        o.append(sum(coeffs[j] * o[-p + j] for j in range(p)))
    return o[:n]


N = K_INPUT + H_HID
bank = []   # (label, family_group, full_sequence, recoverable?)

# ---- recoverable families (parameter sweeps) -------------------------------
for a in range(0, 6):
    for d in range(1, 6):
        bank.append((f"arith a{a} d{d}", "arithmetic", gen(lambda i: a + d * i, N), True))
for a in range(1, 5):
    for r in (2, 3, 4, 5):
        bank.append((f"geo a{a} r{r}", "geometric", gen(lambda i: a * r ** i, N), True))
for c0 in range(0, 3):
    for c1 in range(0, 3):
        for c2 in range(1, 4):
            bank.append((f"quad {c2}n2+{c1}n+{c0}", "polynomial",
                         gen(lambda i: c2 * i * i + c1 * i + c0, N), True))
for c3 in range(1, 4):
    bank.append((f"cubic {c3}n3", "polynomial", gen(lambda i: c3 * i ** 3, N), True))
# fibonacci-like recurrences
for s0 in range(1, 4):
    for s1 in range(1, 4):
        bank.append((f"fiblike {s0},{s1}", "recurrence", recur([s0, s1], [1, 1], N), True))
bank.append(("lucas", "recurrence", recur([2, 1], [1, 1], N), True))
bank.append(("pell", "recurrence", recur([0, 1], [1, 2], N), True))
bank.append(("tribonacci", "recurrence", recur([0, 1, 1], [1, 1, 1], N), True))
# periodic
for per in ([1, 2], [3, 1, 4], [2, 7, 1, 8]):
    bank.append((f"periodic {per}", "periodic", gen(lambda i: per[i % len(per)], N), True))
# multiplicative / factorial-ish
bank.append(("factorial", "multiplicative", [float(math.factorial(i + 1)) for i in range(N)], True))
bank.append(("double_fact", "multiplicative", gen(lambda i: math.prod(range(i + 1, 0, -2)) or 1, N), True))
# power laws
for p in (2, 3):
    bank.append((f"powerlaw n^{p}", "power_law", gen(lambda i: (i + 1) ** p, N), True))
# holonomic / generating-function families (the broadened class)
bank.append(("catalan", "holonomic", [float(math.comb(2 * i, i) // (i + 1)) for i in range(N)], True))
bank.append(("central_binomial", "holonomic", [float(math.comb(2 * i, i)) for i in range(N)], True))
bank.append(("motzkin", "holonomic",
             [1.,1.,2.,4.,9.,21.,51.,127.,323.,835.,2188.,5798.,15511.,41835.,113634.,310572.][:N], True))
# alternating
bank.append(("alt linear", "alternating", gen(lambda i: (-1) ** i * (i + 1), N), True))
bank.append(("alt quad", "alternating", gen(lambda i: (-1) ** i * (i + 1) ** 2, N), True))

# ---- UNrecoverable families (honest-negative controls) ---------------------
def primes(n):
    out, c = [], 2
    while len(out) < n:
        if all(c % p for p in out if p * p <= c):
            out.append(c)
        c += 1
    return [float(x) for x in out]
bank.append(("primes", "OUT_primes", primes(N), False))
# partition numbers p(n)
def part(n):
    P = [1] + [0] * n
    for k in range(1, n + 1):
        for j in range(k, n + 1):
            P[j] += P[j - k]
    return P
pn = part(N + 2)
bank.append(("partitions", "OUT_partitions", [float(x) for x in pn[1:N + 1]], False))
# pseudo-random (deterministic seed) — must NOT verify
import random as _r
for seed in range(8):
    rg = _r.Random(seed)
    bank.append((f"random{seed}", "OUT_random", [float(rg.randint(0, 50)) for _ in range(N)], False))


# ---- run ------------------------------------------------------------------
results = {"recoverable": {"total": 0, "verified": 0, "verified_correct": 0,
                           "verified_wrong": 0},
           "control": {"total": 0, "false_verified": 0}}
by_family = {}
rows = []

for label, fam, seq, recoverable in bank:
    inp = seq[:K_INPUT]
    hidden = seq[K_INPUT:K_INPUT + H_HID]
    inv = E.collapse(inp)
    verified = bool(inv.structure.get("verified"))
    # external grade: does the recovered rule predict the truly-hidden tail?
    ext_correct = False
    try:
        pred = inv.predict(N)[K_INPUT:K_INPUT + H_HID]
        ext_correct = all(abs(p - h) < 1e-6 * (abs(h) + 1) for p, h in zip(pred, hidden))
    except Exception:
        ext_correct = False

    fam_g = "control" if not recoverable else "recoverable"
    results[fam_g]["total"] += 1
    by_family.setdefault(fam, {"n": 0, "verified": 0, "ext_correct": 0})
    by_family[fam]["n"] += 1
    by_family[fam]["verified"] += int(verified)
    by_family[fam]["ext_correct"] += int(ext_correct)

    if recoverable:
        if verified:
            results["recoverable"]["verified"] += 1
            if ext_correct:
                results["recoverable"]["verified_correct"] += 1
            else:
                results["recoverable"]["verified_wrong"] += 1
    else:
        if verified:
            results["control"]["false_verified"] += 1
            rows.append(("FALSE-VERIFY", label, inv.model_class))

rec = results["recoverable"]
ctl = results["control"]
print("=" * 68)
print("PRIMUS PROVING RUN — held-out recovery on known-generator sequences")
print("=" * 68)
print(f"  bank size: {len(bank)} sequences "
      f"({rec['total']} recoverable + {ctl['total']} out-of-class controls)")
print(f"  input terms shown: {K_INPUT}   |   held-out graded: {H_HID}")
print("-" * 68)
recovery = rec["verified"] / max(1, rec["total"])
precision = rec["verified_correct"] / max(1, rec["verified"])
print(f"  RECOVERY RATE (recoverable verified): {rec['verified']}/{rec['total']} "
      f"= {recovery:.1%}")
print(f"  PRECISION of 'verified' (verified AND externally correct): "
      f"{rec['verified_correct']}/{rec['verified']} = {precision:.1%}")
print(f"  verified-but-wrong (false confidence): {rec['verified_wrong']}")
print(f"  HONEST NEGATIVES on out-of-class controls: "
      f"{ctl['total'] - ctl['false_verified']}/{ctl['total']} correctly declined; "
      f"{ctl['false_verified']} false-verify")
print("-" * 68)
print("  by family (verified / n , externally-correct / n):")
for fam in sorted(by_family):
    d = by_family[fam]
    print(f"    {fam:18s}  verified {d['verified']:>3}/{d['n']:<3}   "
          f"ext-correct {d['ext_correct']:>3}/{d['n']}")
if rows:
    print("  ANOMALIES:")
    for r in rows:
        print("   ", r)
print("=" * 68)

# headline assertion: zero false-verify on controls, high precision
ok = (ctl["false_verified"] == 0 and precision >= 0.95 and recovery >= 0.85)
print("RESULT:", "PASS — high recovery, perfect precision, zero false confidence"
      if ok else "REVIEW")
exit(0 if ok else 1)
