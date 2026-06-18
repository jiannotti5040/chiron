#!/usr/bin/env python3
"""
Chiron benchmark — a reproducible, offline measurement of what the engine can
actually do, scored for the one property that matters: it never claims a rule it
cannot verify.

    python3 benchmark.py            # human-readable summary; exits nonzero on any false positive
    python3 benchmark.py --json     # machine-readable results

Two suites, plus two corroborating checks already embedded in the engine:

  1. OEIS-core sequences.  Ground truth is generated from first principles inside
     this file (no network, no transcription risk); every sequence is a real OEIS
     entry, cited by A-number. Each is split train / held-out. The engine sees only
     the training prefix and must predict the held-out tail exactly, or abstain.
     A "false positive" is the only failure that counts: verified == True while the
     prediction is wrong. We compare against a naive finite-difference polynomial
     extrapolator (the textbook method, which cannot abstain) to show the lift.

  2. Classical ciphers.  English plaintexts are encoded with nine classical schemes
     and handed to the solver ciphertext-only. We measure how many it cracks
     (recovered plaintext == original), versus a rot13-only baseline.

  3. Corroboration.  run_gauntlet() (labeled recovery + zero false-verify on
     controls) and fuzz_test() (thousands of randomized in-class / shuffled cases)
     are surfaced verbatim from the engine.

Deterministic. Offline. One command. The score the engine can publish.
"""
import os
import sys
import json
import math
import argparse
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import collapse, solve_cipher, run_gauntlet, fuzz_test  # noqa: E402


# ---------------------------------------------------------------------------
# Ground truth — generated, not transcribed. Each generator returns the first
# n terms of a real OEIS sequence. `in_scope` records whether the sequence is
# algebraically generated (constant / arithmetic / geometric / polynomial /
# linear-recurrence / holonomic) and therefore inside the engine's recovery
# classes. Out-of-scope sequences (primes, partitions, totient, ...) are the
# honesty test: the correct behavior is to ABSTAIN, never to guess.
# ---------------------------------------------------------------------------
def _fib(n, a, b):
    s = [a, b]
    while len(s) < n:
        s.append(s[-1] + s[-2])
    return s[:n]


def _rec2(n, a, b, p, q):          # a(k) = p*a(k-1) + q*a(k-2)
    s = [a, b]
    while len(s) < n:
        s.append(p * s[-1] + q * s[-2])
    return s[:n]


def _primes(n):
    out, c = [], 2
    while len(out) < n:
        if all(c % p for p in out if p * p <= c):
            out.append(c)
        c += 1
    return out


def _partitions(n):
    p = [1] + [0] * (n + 5)
    for k in range(1, n + 6):
        for m in range(k, n + 6):
            p[m] += p[m - k]
    return p[:n]


def _totient(n):
    def phi(m):
        r, mm, d = m, m, 2
        while d * d <= mm:
            if mm % d == 0:
                while mm % d == 0:
                    mm //= d
                r -= r // d
            d += 1
        if mm > 1:
            r -= r // mm
        return r
    return [phi(m) for m in range(1, n + 1)]


def _numdiv(n):
    return [sum(1 for d in range(1, m + 1) if m % d == 0) for m in range(1, n + 1)]


def _sigma(n):
    return [sum(d for d in range(1, m + 1) if m % d == 0) for m in range(1, n + 1)]


def _bell(n):
    row = [1]
    bells = [1]
    for _ in range(1, n):
        nxt = [row[-1]]
        for x in row:
            nxt.append(nxt[-1] + x)
        row = nxt
        bells.append(row[0])
    return bells[:n]


def _dblfact_odd(n):
    out, v = [], 1
    for k in range(n):
        out.append(v)
        v *= (2 * k + 1)
    return out


N = 18  # terms generated per sequence
SEQUENCES = [
    # (A-number, name, terms, in_scope)
    ("A000012", "all ones",                  [1] * N,                               True),
    ("A000027", "natural numbers",           [i + 1 for i in range(N)],             True),
    ("A005843", "even numbers",              [2 * i for i in range(N)],             True),
    ("A005408", "odd numbers",               [2 * i + 1 for i in range(N)],         True),
    ("A000079", "powers of 2",               [2 ** i for i in range(N)],            True),
    ("A000244", "powers of 3",               [3 ** i for i in range(N)],            True),
    ("A000290", "squares",                   [i * i for i in range(N)],             True),
    ("A000578", "cubes",                     [i ** 3 for i in range(N)],            True),
    ("A000217", "triangular numbers",        [i * (i + 1) // 2 for i in range(N)],  True),
    ("A000292", "tetrahedral numbers",       [i * (i + 1) * (i + 2) // 6 for i in range(N)], True),
    ("A002378", "pronic numbers",            [i * (i + 1) for i in range(N)],       True),
    ("A000326", "pentagonal numbers",        [i * (3 * i - 1) // 2 for i in range(N)], True),
    ("A000384", "hexagonal numbers",         [i * (2 * i - 1) for i in range(N)],   True),
    ("A000225", "Mersenne (2^n - 1)",        [2 ** i - 1 for i in range(N)],        True),
    ("A000045", "Fibonacci",                 _fib(N, 0, 1),                         True),
    ("A000032", "Lucas",                     _fib(N, 2, 1),                         True),
    ("A000129", "Pell",                      _rec2(N, 0, 1, 2, 1),                  True),
    ("A001045", "Jacobsthal",                _rec2(N, 0, 1, 1, 2),                  True),
    ("A000108", "Catalan",                   [math.comb(2 * i, i) // (i + 1) for i in range(N)], True),
    ("A000142", "factorials",                [math.factorial(i) for i in range(N)], True),
    ("A000984", "central binomial",          [math.comb(2 * i, i) for i in range(N)], True),
    ("A001147", "double factorial (2n-1)!!", _dblfact_odd(N),                       True),
    # ---- out of scope: the correct answer is to abstain ----
    ("A000040", "primes",                    _primes(N),                            False),
    ("A000041", "partitions",                _partitions(N),                        False),
    ("A000010", "Euler totient",             _totient(N),                           False),
    ("A000005", "number of divisors",        _numdiv(N),                            False),
    ("A000203", "sum of divisors",           _sigma(N),                             False),
    ("A000110", "Bell numbers",              _bell(N),                              False),
    ("A000312", "n^n",                       [i ** i if i else 1 for i in range(N)], False),
]

HOLDOUT = 4  # terms hidden from the engine and used to test the prediction


def _as_fracs(xs):
    return [Fraction(x) for x in xs]


def _terms_equal(a, b):
    try:
        return Fraction(a) == Fraction(b)
    except (TypeError, ValueError):
        return a == b


def _baseline_predict(train, total):
    """Naive finite-difference (Newton forward) extrapolation: the unique
    lowest-degree polynomial through the training points, evaluated past the end.
    This is what a careful analyst does by hand. It cannot abstain — it always
    emits a number — so it is exactly wrong on anything that is not polynomial."""
    t = _as_fracs(train)
    m = len(t)
    diffs = [t[:]]
    while len(diffs[-1]) > 1:
        prev = diffs[-1]
        diffs.append([prev[i + 1] - prev[i] for i in range(len(prev) - 1)])
    head = [row[0] for row in diffs]            # k-th forward difference at index 0
    out = []
    for j in range(total):
        out.append(sum(Fraction(math.comb(j, k)) * head[k] for k in range(m)))
    return out


def run_sequences():
    rows = []
    chiron = {"recovered": 0, "abstained": 0, "false_positive": 0}
    base = {"correct": 0, "wrong": 0}
    in_scope = {"total": 0, "recovered": 0}
    for a, name, terms, scope in SEQUENCES:
        train, held = terms[:-HOLDOUT], terms[-HOLDOUT:]
        # --- Chiron ---
        verified = False
        predicted = None
        try:
            inv = collapse(train)
            verified = bool(inv.verified)
            if verified:
                pred = inv.predict(len(terms))
                predicted = list(pred[-HOLDOUT:])
        except Exception:
            verified = False
        if verified and predicted is not None and all(
                _terms_equal(p, h) for p, h in zip(predicted, held)):
            outcome = "recovered"
            chiron["recovered"] += 1
        elif verified:
            outcome = "FALSE_POSITIVE"
            chiron["false_positive"] += 1
        else:
            outcome = "abstained"
            chiron["abstained"] += 1
        # --- naive polynomial baseline ---
        try:
            bp = _baseline_predict(train, len(terms))[-HOLDOUT:]
            base_ok = all(_terms_equal(p, h) for p, h in zip(bp, held))
        except Exception:
            base_ok = False
        base["correct" if base_ok else "wrong"] += 1
        if scope:
            in_scope["total"] += 1
            in_scope["recovered"] += 1 if outcome == "recovered" else 0
        rows.append({"oeis": a, "name": name, "in_scope": scope,
                     "chiron": outcome, "baseline": "correct" if base_ok else "wrong"})
    return {
        "n": len(SEQUENCES),
        "holdout_terms": HOLDOUT,
        "chiron": chiron,
        "chiron_in_scope_recovery": {
            "recovered": in_scope["recovered"], "of": in_scope["total"],
            "rate": round(in_scope["recovered"] / in_scope["total"], 3) if in_scope["total"] else 0.0},
        "baseline_naive_polynomial": base,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Cipher suite — encode English plaintexts with classical schemes, then hand the
# ciphertext (only) to the solver and see if it recovers the plaintext.
# ---------------------------------------------------------------------------
PLAINTEXTS = [
    "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG",
    "DEFEND THE EAST WALL OF THE CASTLE AT DAWN",
    "MEET ME AT THE OLD BRIDGE WHEN THE CLOCK STRIKES NINE",
    "KNOWLEDGE IS POWER GUARD IT WELL AND USE IT WISELY",
]
_MORSE_ENC = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..',
}


def _caesar(s, k):
    return "".join(chr((ord(c) - 65 + k) % 26 + 65) if c.isalpha() else c for c in s)


def _atbash(s):
    return "".join(chr(65 + 25 - (ord(c) - 65)) if c.isalpha() else c for c in s)


def _a1z26(s):
    return " ".join(str(ord(c) - 64) for c in s if c.isalpha())


def _to_b64(s):
    import base64
    return base64.b64encode(s.encode()).decode()


def _to_hex(s):
    return s.encode().hex()


def _to_bin(s):
    return " ".join(format(b, "08b") for b in s.encode())


def _to_morse(s):
    return " / ".join(" ".join(_MORSE_ENC[c] for c in w) for w in s.split())


CIPHERS = [
    ("caesar_3", lambda s: _caesar(s, 3)),
    ("caesar_7", lambda s: _caesar(s, 7)),
    ("caesar_19", lambda s: _caesar(s, 19)),
    ("rot13", lambda s: _caesar(s, 13)),
    ("atbash", _atbash),
    ("a1z26", _a1z26),
    ("base64", _to_b64),
    ("hex", _to_hex),
    ("binary", _to_bin),
    ("morse", _to_morse),
    ("reverse", lambda s: s[::-1]),
]


def _norm(s):
    return "".join(ch for ch in str(s).upper() if ch.isalpha())


def run_ciphers():
    by_method, rows = {}, []
    cracked = total = base_cracked = 0
    for mname, enc in CIPHERS:
        by_method.setdefault(mname, {"cracked": 0, "of": 0})
        for pt in PLAINTEXTS:
            ct = enc(pt)
            total += 1
            by_method[mname]["of"] += 1
            try:
                got = solve_cipher(ct)["plaintext"]
            except Exception:
                got = ""
            ok = _norm(got) == _norm(pt)
            if ok:
                cracked += 1
                by_method[mname]["cracked"] += 1
            # baseline: only ever try rot13
            base_ok = _norm(_caesar(ct, 13)) == _norm(pt)
            base_cracked += 1 if base_ok else 0
            rows.append({"method": mname, "cracked": ok})
    return {
        "total": total, "cracked": cracked,
        "rate": round(cracked / total, 3) if total else 0.0,
        "by_method": by_method,
        "baseline_rot13_only": {"cracked": base_cracked, "of": total},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--fuzz", type=int, default=5000, help="fuzz cases (0 to skip)")
    args = ap.parse_args()

    seqs = run_sequences()
    ciphers = run_ciphers()
    gauntlet = run_gauntlet()
    fuzz = fuzz_test(args.fuzz, seed=1) if args.fuzz else None

    false_positives = (
        seqs["chiron"]["false_positive"]
        + gauntlet["false_verify"]
        + (fuzz["false_verify_shuffled"] if fuzz else 0)
    )
    report = {
        "sequences": seqs, "ciphers": ciphers,
        "gauntlet": gauntlet, "fuzz": fuzz,
        "false_positives_total": false_positives,
        "verdict": "PASS" if false_positives == 0 else "FALSE_POSITIVE_DETECTED",
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0 if false_positives == 0 else 1

    s, c = seqs, ciphers
    print("=" * 70)
    print("CHIRON BENCHMARK — reproducible, offline, deterministic")
    print("=" * 70)
    print("\nOEIS-CORE SEQUENCES  (train on a prefix, predict %d held-out terms)" % s["holdout_terms"])
    print("  sequences tested ........ %d real OEIS-core entries" % s["n"])
    print("  recovered (exact) ....... %d   [verified rule, held-out terms predicted exactly]"
          % s["chiron"]["recovered"])
    print("  abstained ............... %d   [no verified rule — correctly declined to guess]"
          % s["chiron"]["abstained"])
    print("  FALSE POSITIVES ......... %d   [claimed a rule that was wrong]"
          % s["chiron"]["false_positive"])
    isr = s["chiron_in_scope_recovery"]
    print("  in-scope recovery ....... %d/%d (%.0f%%)   [of the algebraically-generated entries]"
          % (isr["recovered"], isr["of"], isr["rate"] * 100))
    b = s["baseline_naive_polynomial"]
    print("  naive-polynomial baseline %d correct / %d confidently WRONG  (it cannot abstain)"
          % (b["correct"], b["wrong"]))

    print("\nCLASSICAL CIPHERS  (ciphertext-only recovery)")
    print("  cracked ................. %d/%d (%.0f%%)" % (c["cracked"], c["total"], c["rate"] * 100))
    print("  rot13-only baseline ..... %d/%d" % (c["baseline_rot13_only"]["cracked"], c["total"]))
    miss = [m for m, v in c["by_method"].items() if v["cracked"] < v["of"]]
    print("  per-scheme .............. " + ", ".join(
        "%s %d/%d" % (m, v["cracked"], v["of"]) for m, v in c["by_method"].items()))
    if miss:
        print("  (incomplete schemes: %s)" % ", ".join(miss))

    print("\nCORROBORATION (embedded in the engine)")
    g = gauntlet
    print("  gauntlet ................ %s — recovered %d/%d, false-verify on controls %d"
          % (g["verdict"], g["recovered"], g["recoverable_tested"], g["false_verify"]))
    if fuzz:
        print("  fuzz (%d cases) ....... in-class verified %d, false-verify %d, crashes %d"
              % (fuzz["total"], fuzz["verified_inclass"],
                 fuzz["false_verify_shuffled"], fuzz["crashes"]))

    print("\n" + "-" * 70)
    print("TOTAL FALSE POSITIVES ACROSS ALL SUITES: %d" % false_positives)
    print("VERDICT: %s" % report["verdict"])
    print("-" * 70)
    return 0 if false_positives == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
