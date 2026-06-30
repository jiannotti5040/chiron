#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
bench_compression.py — Chiron vs general-purpose compressors on a labeled sequence corpus.

A demonstration of the surface -> search -> MDL -> held-out -> accept/refuse architecture
against simpler baselines on a concrete task. Here the task is sequence compression
with a twist the baselines cannot match: PREDICTION. gzip/bz2/lzma shrink the bytes you give them;
they cannot regenerate a term they were never shown. Chiron recovers a constant-size generator,
verifies it by predicting held-out terms at exact equality, and abstains on the incompressible.

    python3 bench_compression.py            # results table
    python3 bench_compression.py selftest   # 0/1 gate

Status: implemented & tested. Uses the real chiron engine (no reimplementation).
"""
import os
import sys
import gzip
import bz2
import lzma
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron  # noqa: E402

HOLDOUT = 3

# (name, family, full sequence) — algebraically generated; the last HOLDOUT terms are withheld.
CORPUS = [
    ("arithmetic",    "polynomial",  [4, 7, 10, 13, 16, 19, 22, 25, 28, 31]),
    ("geometric",     "geometric",   [3, 6, 12, 24, 48, 96, 192, 384, 768, 1536]),
    ("squares",       "polynomial",  [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]),
    ("cubes",         "polynomial",  [1, 8, 27, 64, 125, 216, 343, 512, 729, 1000]),
    ("fibonacci",     "recurrence",  [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]),
    ("lucas",         "recurrence",  [2, 1, 3, 4, 7, 11, 18, 29, 47, 76, 123, 199]),
    ("triangular",    "polynomial",  [1, 3, 6, 10, 15, 21, 28, 36, 45, 55]),
    ("pow2_plus1",    "mixed",       [2, 3, 5, 9, 17, 33, 65, 129, 257, 513]),
]

# Controls — no closed-form generator; the engine MUST abstain (no false verify).
CONTROLS = [
    ("random_a", [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]),
    ("random_b", [8, 6, 7, 5, 3, 0, 9, 2, 4, 1, 7]),
]


def _bits_of(seq, algo):
    raw = ",".join(str(x) for x in seq).encode("utf-8")
    comp = {"gzip": gzip.compress, "bz2": bz2.compress, "lzma": lzma.compress}[algo](raw)
    return len(comp) * 8


def _chiron_bits(inv):
    d = inv.to_dict()
    return float(d.get("model_bits", 0.0))


def run():
    rows = []
    recovered = held_exact = 0
    for name, fam, seq in CORPUS:
        train = seq[:-HOLDOUT]
        inv = chiron.collapse(train)
        ok = bool(inv.verified)
        he = False
        cbits = _chiron_bits(inv) if ok else float("nan")
        if ok:
            recovered += 1
            pred = inv.predict(len(seq))
            he = [Fraction(x) for x in seq[-HOLDOUT:]] == list(pred[-HOLDOUT:])
            held_exact += int(he)
        rows.append((name, fam, ok, he, cbits,
                     _bits_of(seq, "gzip"), _bits_of(seq, "bz2"), _bits_of(seq, "lzma")))
    false_verify = sum(1 for _, s in CONTROLS if chiron.collapse(s[:-HOLDOUT]).verified)

    print("bench_compression — Chiron vs general-purpose compressors\n")
    print(f"{'sequence':14}{'class':12}{'rec':>4}{'held-out':>9}{'chiron':>9}{'gzip':>7}{'bz2':>7}{'lzma':>7}")
    print("-" * 79)
    for name, fam, ok, he, cb, g, b, l in rows:
        cb_s = f"{cb:.0f}" if cb == cb else "—"
        print(f"{name:14}{fam:12}{('yes' if ok else 'no'):>4}{('exact' if he else '—'):>9}"
              f"{cb_s:>9}{g:>7}{b:>7}{l:>7}")
    print("-" * 79)
    print(f"recovered {recovered}/{len(CORPUS)} · held-out exact {held_exact}/{len(CORPUS)} · "
          f"false-verify on controls {false_verify}/{len(CONTROLS)}")
    print("\nbits = description length. Chiron stores a CONSTANT-size law (independent of length) and")
    print("predicts the withheld tail exactly; gzip/bz2/lzma store the literal terms and cannot")
    print("regenerate an unseen term at all. The architecture's payoff is prediction, not just size.")
    return recovered, held_exact, false_verify, rows


def _selftest():
    recovered, held_exact, false_verify, rows = run()
    checks = [
        ("majority of corpus recovered", recovered >= len(CORPUS) - 1),
        ("recovered generators predict held-out exactly", held_exact == recovered),
        ("zero false-verify on controls", false_verify == 0),
        ("chiron law beats lzma on a long sequence",
         any(r[4] == r[4] and r[4] < r[7] for r in rows)),
    ]
    print("\nSELFTEST")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    ok = all(c for _, c in checks)
    print(f"  {sum(c for _, c in checks)}/{len(checks)} checks")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if _selftest() else 1)
    run()
