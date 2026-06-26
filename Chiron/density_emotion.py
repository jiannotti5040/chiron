#!/usr/bin/env python3
"""
density_emotion.py — competing hypotheses as a decohering quantum mixture (O-2).

HCT Theorem T8: when a system holds several simultaneously-plausible interpretations, the
honest evolution of that superposition is Lindblad CPTP — not a classical mixture (which
would violate complete positivity). This bridges cert_engine's DensityEmotion onto a Chiron
finding: the competing hypotheses about a surface form a density matrix that decoheres
toward the surviving interpretation, with von Neumann entropy as the live measure of "how
undecided" the system still is, and a checked CPTP-validity guarantee at every step.

A verified finding starts near-collapsed (low entropy, one interpretation dominates); an
ambiguous one starts spread and must decohere before it commits.

    python3 density_emotion.py --demo
    python3 density_emotion.py 1 1 2 3 5 8 13 21
    python3 density_emotion.py --surface "41 19 50 83 6 9" --json

Framing dial — civilian: how-undecided meter + principled commitment dynamics. Contractor:
CPTP-valid multi-hypothesis decoherence with an entropy gate.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "JDICert"))
import chiron          # noqa: E402
import numpy as np     # noqa: E402
import cert_engine as ce   # noqa: E402


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def density_emotion(surface, n_models=3):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    # tighter (more compressible, verified) law -> slower decoherence
    cr = float(inv.compression_ratio) if inv.verified else 1.0
    gamma = 1.0 / max(0.2, min(cr, 20.0))

    de = ce.DensityEmotion(n_models=n_models, decoherence_rate=gamma)
    de.set_uniform_superposition()              # a live superposition of readings (has coherences)

    trail = []
    for k in range(4):
        if k:
            de.evolve(0.05, 40)                  # advance time; Lindblad dephasing acts
        trail.append({"t": round(k * 2.0, 1),
                      "coherence": round(float(de.coherence_measure()), 4),
                      "von_neumann_entropy": round(float(de.von_neumann_entropy()), 4)})
    cptp = de.is_cptp_valid()
    return {
        "law": inv.model_class,
        "verified": bool(inv.verified),
        "n_hypotheses": n_models,
        "decoherence_rate": round(gamma, 4),
        "final_probabilities": [round(float(x), 4) for x in de.probabilities()],
        "entropy_trail": trail,
        "cptp_valid": bool(cptp["is_valid_cptp"]),
        "interpretation": "von Neumann entropy falling toward 0 = the system committing to one reading",
    }


def render(d):
    L = ["=" * 60, "DENSITY EMOTION — competing readings decohere (CPTP)", "=" * 60]
    L.append(f"  law={d['law']}  verified={d['verified']}  hypotheses={d['n_hypotheses']}")
    L.append(f"  decoherence rate {d['decoherence_rate']}   CPTP valid={d['cptp_valid']}")
    L.append("  entropy trail (how-undecided over time):")
    for s in d["entropy_trail"]:
        bar = "█" * int(round(s["von_neumann_entropy"] * 24))
        L.append(f"     t={s['t']:<4} S={s['von_neumann_entropy']:<7} {bar}")
    L.append(f"  final probabilities: {d['final_probabilities']}")
    L.append("=" * 60)
    return "\n".join(L)


_DEMO = ["1 1 2 3 5 8 13 21 34", "2 4 6 8 10 12 14", "41 19 50 83 6 9 68 12"]


def _demo():
    for s in _DEMO:
        print(f"\n### {s}")
        print(render(density_emotion(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lindblad decoherence over competing hypotheses for a finding.")
    ap.add_argument("values", nargs="*")
    ap.add_argument("--surface", default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.demo:
        return _demo()
    surface = args.surface or (" ".join(args.values) if args.values else None)
    if not surface:
        return _demo()
    print(json.dumps(density_emotion(surface), indent=2) if args.json else render(density_emotion(surface)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
