#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
bench_proverbs.py — semic on a multi-proverb corpus, against a surface (bag-of-words) baseline.

Demonstrates the invariant-recovery architecture in the semantic domain: surface-DIFFERENT proverbs
that share one underlying invariant collapse to one generator; structurally different families
collapse to different generators; mixed/garbled controls are refused. A bag-of-words baseline, by
contrast, groups by shared words and conflates families that share surface vocabulary (fish, give,
day) even when their invariants differ — exactly the failure the exact engine avoids.

    python3 bench_proverbs.py            # results table
    python3 bench_proverbs.py selftest   # 0/1 gate

Status: implemented & tested. Uses the real semic engine.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import semic  # noqa: E402

# Two families. Every line is a surface-distinct proverb; members of a family share ONE invariant.
FAMILIES = {
    "provision (give vs teach)": [
        "give a man a fish and he will eat for a day; teach a man to fish and he will eat for a lifetime",
        "give a man bread and he eats for a day; teach a man to farm and he eats for a lifetime",
        "give a man fire to warm him for a night; teach a man to build fire to warm him forever",
        "give a man a candle for a night; teach a man to build and he has light for life",
    ],
    "dole (transfer only)": [
        "give a man a fish for a day; give a man bread for a meal",
        "give a man money for a day; give a man food for a day",
        "give a man a candle for a night; give a man fire for a night",
    ],
}

CONTROLS = list(semic.CONTROLS_TEXT.items())   # must be refused


def _bow(text):
    return frozenset(w for w in text.lower().replace(",", " ").replace(";", " ").replace(".", " ").split())


def _jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def run():
    rows, generators = [], {}
    for fam, lines in FAMILIES.items():
        skeletons = [semic.surface_skeleton(t) for t in lines]
        gen = semic.collapse(skeletons)
        v = semic.certify(skeletons)
        generators[fam] = gen
        rows.append((fam, len(lines), sorted(gen), v.verified, all(r == 0 for r in v.heldout_residuals)))

    distinct = len({frozenset(g) for g in generators.values()})

    # controls: each appended to the fish family must break verification (refusal)
    base = [semic.surface_skeleton(t) for t in semic.FISH_FAMILY_TEXT]
    refused = sum(1 for _, t in CONTROLS if not semic.certify(base + [semic.surface_skeleton(t)]).verified)

    # baseline: surface bag-of-words. Count cross-family pairs MORE similar than the least-similar
    # within-family pair — i.e. cases where surface words would mis-group the invariants.
    all_items = [(fam, t) for fam, lines in FAMILIES.items() for t in lines]
    within_min, cross_max = 1.0, 0.0
    for i in range(len(all_items)):
        for j in range(i + 1, len(all_items)):
            s = _jaccard(_bow(all_items[i][1]), _bow(all_items[j][1]))
            if all_items[i][0] == all_items[j][0]:
                within_min = min(within_min, s)
            else:
                cross_max = max(cross_max, s)
    baseline_confused = cross_max >= within_min

    print("bench_proverbs — semic invariant recovery vs bag-of-words\n")
    print(f"{'family':30}{'variants':>9}{'verified':>9}{'held-out':>9}  generator")
    print("-" * 92)
    for fam, n, gen, ver, he in rows:
        g = ", ".join(f"{o}->{h}" for o, h in gen)
        print(f"{fam:30}{n:>9}{('yes' if ver else 'no'):>9}{('exact' if he else '—'):>9}  {g}")
    print("-" * 92)
    print(f"distinct invariants recovered: {distinct}/{len(FAMILIES)} · controls refused: "
          f"{refused}/{len(CONTROLS)}")
    print(f"baseline (bag-of-words): within-family min sim {within_min:.2f} vs cross-family max sim "
          f"{cross_max:.2f} -> {'CONFLATES the two invariants' if baseline_confused else 'separates'}")
    print("\nsemic separates families by the recovered invariant, not shared words; the surface")
    print("baseline cannot, because the two families share vocabulary (fish, give, day).")
    return rows, distinct, refused, baseline_confused


def _selftest():
    rows, distinct, refused, baseline_confused = run()
    checks = [
        ("every family verifies", all(r[3] for r in rows)),
        ("held-out exact for every family", all(r[4] for r in rows)),
        ("distinct families -> distinct generators", distinct == len(FAMILIES)),
        ("all controls refused", refused == len(CONTROLS)),
        ("bag-of-words baseline conflates the invariants", baseline_confused),
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
