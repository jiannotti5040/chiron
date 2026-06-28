#!/usr/bin/env python3
"""
semic_energy.py — the three-level epistemic stack over semic.

Per review: layer the energy formulation ABOVE exact collapse, never replacing it.

  Level 1  EXACT SYMBOLIC RECOVERY   semic.collapse + held-out verification -> CERTIFIED / REFUSED
  Level 2  CONSTRAINT MANIFOLD       the generator space (the subset lattice over the edge universe)
  Level 3  ENERGY LANDSCAPE          when Level 1 REFUSES, rank generators by the Gibbs measure
                                     p_T(S) ~ exp(-E(S)/T) and return them as APPROXIMATE

The deterministic guarantee is preserved: the energy layer NEVER certifies. Exact collapse certifies
or refuses; only on refusal does Level 3 offer energy-ranked approximations, always labelled
uncertified, with the landscape entropy reported so a flat (genuinely ambiguous) landscape is
distinguished from a sharp basin. SEMIC stays exact collapse; energy is approximate exploration
*around* it.

    python3 semic_energy.py demo
    python3 semic_energy.py selftest

Status: implemented & tested. Builds only on semic's exact, stdlib core.
"""
import os
import sys
import math
import json
import argparse
from decimal import Decimal, getcontext
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import semic  # noqa: E402

getcontext().prec = 60


def _dec(fr: Fraction) -> Decimal:
    return Decimal(fr.numerator) / Decimal(fr.denominator)


def energy_landscape(family, T="0.5", k=5):
    """Level 2 + 3: rank the constraint manifold by Gibbs probability at temperature T.
    Returns (top-k rows [(S, energy, prob)], entropy_nats, relative_entropy in [0,1])."""
    space = semic.candidate_space(family)                       # Level 2: the constraint manifold
    Td = Decimal(str(T))
    Es = [(S, semic.energy(family, S)) for S in space]          # exact Fraction energies
    Emin = min(E for _, E in Es)
    weights = [(S, (-(_dec(E) - _dec(Emin)) / Td).exp()) for S, E in Es]
    Z = sum(x for _, x in weights)
    rows = sorted([(S, E, x / Z) for (S, E), (_, x) in zip(Es, weights)],
                  key=lambda r: (-r[2], _dec(r[1]), sorted(r[0])))
    H = -sum(float(p) * math.log(float(p)) for _, _, p in rows if p > 0)
    Hmax = math.log(len(rows)) if len(rows) > 1 else 1.0
    return rows[:k], H, (H / Hmax if Hmax > 0 else 0.0)


def three_level(family, T="0.5", k=5):
    """Run the full stack. Level 1 if exact collapse verifies; otherwise Level 3 (approximate)."""
    v = semic.certify(family)
    gen = semic.collapse(family)
    if v.verified:
        return {"level": 1, "verdict": "CERTIFIED", "generator": sorted(gen),
                "heldout_residuals": v.heldout_residuals,
                "note": "exact collapse verified on held-out data"}
    rows, H, Hrel = energy_landscape(family, T, k)
    return {
        "level": 3, "verdict": "APPROXIMATE", "uncertified": True,
        "constraint_space_size": len(semic.candidate_space(family)),
        "temperature": str(T),
        "candidates": [{"generator": [list(e) for e in sorted(S)],
                        "energy": str(E), "probability": round(float(p), 4)} for S, E, p in rows],
        "landscape_entropy_nats": round(H, 4), "relative_entropy": round(Hrel, 4),
        "note": ("exact collapse REFUSED; these are energy-ranked approximations, NOT verified"
                 + (" — landscape is flat (genuinely ambiguous)" if Hrel > 0.85
                    else " — a basin is present (a most-probable approximation exists)")),
    }


def _print(label, r):
    print(f"\n[{label}] -> Level {r['level']} / {r['verdict']}")
    if r["level"] == 1:
        print("  generator:", r["generator"], "| held-out residuals:", r["heldout_residuals"])
    else:
        print(f"  constraint space: {r['constraint_space_size']} | T={r['temperature']} "
              f"| rel.entropy={r['relative_entropy']} (uncertified={r['uncertified']})")
        for c in r["candidates"][:3]:
            print(f"    p={c['probability']:.3f}  E={c['energy']}  {c['generator']}")
        print("  note:", r["note"])


def demo():
    fish = [semic.surface_skeleton(t) for t in semic.FISH_FAMILY_TEXT]
    refused = fish + [semic.surface_skeleton(list(semic.CONTROLS_TEXT.values())[0])]
    _print("clean fish family", three_level(fish))
    _print("contaminated family (control mixed in)", three_level(refused))


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    fish = [semic.surface_skeleton(t) for t in semic.FISH_FAMILY_TEXT]
    r1 = three_level(fish)
    ok("verifiable family -> Level 1 CERTIFIED", r1["level"] == 1 and r1["verdict"] == "CERTIFIED")
    ok("certified generator is the recovered invariant",
       r1["generator"] == sorted(semic.collapse(fish)))

    refused = fish + [semic.surface_skeleton(list(semic.CONTROLS_TEXT.values())[0])]
    r3 = three_level(refused)
    ok("refused family -> Level 3 APPROXIMATE", r3["level"] == 3 and r3["verdict"] == "APPROXIMATE")
    ok("Level 3 is explicitly uncertified", r3.get("uncertified") is True)
    ok("Level 3 NEVER certifies", r3["verdict"] != "CERTIFIED")
    ok("Level 3 returns ranked candidates with probabilities",
       len(r3["candidates"]) >= 1 and all("probability" in c for c in r3["candidates"]))
    ok("candidate probabilities are a descending distribution",
       all(r3["candidates"][i]["probability"] >= r3["candidates"][i + 1]["probability"]
           for i in range(len(r3["candidates"]) - 1)))

    # the lowest-energy candidate (top of the ranking) is the deterministic collapse generator
    top = r3["candidates"][0]["generator"]
    ok("energy peak == exact collapse generator",
       sorted(tuple(e) for e in top) == sorted(tuple(e) for e in semic.collapse(refused)))

    passed = sum(1 for _, c in checks if c)
    print("semic_energy self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Three-level epistemic stack over semic.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("demo")
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        demo(); return 0
    return 0 if _selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
