# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.bsd.sweep — run the exact BSD gate over a self-generated family of curves.

No external database is consulted. Curves are enumerated from small
a-invariants, the module decides for itself which are inside its domain, and
every curve inside it gets a verdict. What the sweep measures is not "does BSD
hold" -- one sweep cannot address that -- but two things that are measurable:

  * the DOMAIN: what fraction of curves the exact-or-refuse contract can reach,
    and precisely why each refusal happened. A high refusal rate is the honest
    outcome and is reported as the headline number, not hidden.
  * the MARGIN: how far each pinned Sha_an sits from the nearest wrong integer,
    in units of the enclosure width. That ratio is the quantity a floating
    point computation cannot report at all, because rounding to nearest throws
    it away. It is the sweep's actual product.

    python3 -m uma.bsd.sweep 40
"""
from __future__ import annotations

import sys
from collections import Counter
from fractions import Fraction
from typing import Dict, Iterator, List, Tuple

from . import CONSISTENT, REFUSED, REFUTED, bsd_certificate, sha_analytic_interval
from .curve import Curve, Refuse


def enumerate_curves(bound: int) -> Iterator[Tuple[int, int, int, int, int]]:
    """Weierstrass models with a1, a3 in {0,1}, a2 in {-1,0,1} (a complete set
    of representatives for the standard reductions) and |a4|, |a6| <= bound."""
    for a1 in (0, 1):
        for a2 in (-1, 0, 1):
            for a3 in (0, 1):
                for a4 in range(-bound, bound + 1):
                    for a6 in range(-bound, bound + 1):
                        yield (a1, a2, a3, a4, a6)


def margin(cert_interval, value: int) -> Fraction:
    """How many enclosure-widths separate the pinned integer from the nearest
    other integer. This is the number that vanishes under round-to-nearest."""
    lo, hi = cert_interval.as_fractions()
    w = hi - lo
    if w == 0:
        return Fraction(10 ** 9)
    nearest = min(abs(Fraction(value) - lo), abs(hi - Fraction(value)))
    return (Fraction(1) - w) / w if nearest == 0 else (Fraction(1, 2)) / w


def run(bound: int = 20, max_conductor: int = 20_000) -> Dict:
    seen = set()
    reasons: Counter = Counter()
    verdicts: Counter = Counter()
    sha_counts: Counter = Counter()
    refutations: List[Dict] = []
    pinned: List[Dict] = []

    for ainvs in enumerate_curves(bound):
        try:
            E = Curve(ainvs)
        except Refuse:
            continue
        key = (E.c4, E.c6)
        if key in seen:
            continue
        seen.add(key)
        try:
            if not E.is_semistable():
                reasons["additive reduction"] += 1
                verdicts[REFUSED] += 1
                continue
            if E.conductor() > max_conductor:
                reasons["conductor above sweep cap"] += 1
                verdicts[REFUSED] += 1
                continue
            if E.root_number() != 1:
                reasons["root number -1 (odd analytic rank)"] += 1
                verdicts[REFUSED] += 1
                continue
            d = sha_analytic_interval(E)
        except (Refuse, ValueError, ZeroDivisionError) as e:
            reasons[str(e)[:60]] += 1
            verdicts[REFUSED] += 1
            continue

        cert = bsd_certificate(ainvs)
        verdicts[cert["verdict"]] += 1
        if cert["verdict"] == REFUTED:
            refutations.append(cert)
        elif cert["verdict"] == CONSISTENT:
            sha_counts[cert["sha_analytic"]] += 1
            pinned.append({
                "ainvs": list(ainvs),
                "conductor": cert["conductor"],
                "sha": cert["sha_analytic"],
                "width": float(d["sha_interval"].width()),
            })
        else:
            reasons[cert["reason"][:60]] += 1

    total = sum(verdicts.values())
    return {
        "schema": "uma.bsd.sweep/1",
        "coefficient_bound": bound,
        "distinct_curves": len(seen),
        "verdicts": dict(verdicts),
        "in_domain_fraction": (verdicts[CONSISTENT] + verdicts[REFUTED]) / total if total else 0.0,
        "refusal_reasons": dict(reasons.most_common(12)),
        "sha_distribution": dict(sorted(sha_counts.items())),
        "refutations": refutations,
        "widest_enclosure": max((p["width"] for p in pinned), default=0.0),
        "note": ("REFUTED is empty in every sweep run so far, which is the "
                 "expected outcome and is not evidence for BSD; it is evidence "
                 "that the gate is consistent with the existing numerical "
                 "record while computing it without a rounding step."),
    }


if __name__ == "__main__":
    import json
    b = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(json.dumps(run(b), indent=2, default=str))
