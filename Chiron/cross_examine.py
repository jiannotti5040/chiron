#!/usr/bin/env python3
"""
cross_examine.py — the defense attorney (A-2, jurisprudence).

Law is adversarial. Chiron outputs the best generator; a legal suite needs a module that
actively tries to break it — to find reasonable doubt. cross_examine takes a finding and
searches for an ALTERNATIVE generator that fits comparably, and probes whether the winner
survives minor truncation. If a competing rule fits within a hair's-breadth, or the winner
flips when you drop a single term, certainty is not earned. If nothing else survives, the
finding has been cross-examined and held.

This raises or lowers legal certainty by attack, not by assertion — the adversarial process
applied to recovery.

    python3 cross_examine.py --demo
    python3 cross_examine.py 1 1 2 3 5 8 13 21
    python3 cross_examine.py --surface "2 4 8 16 32" --json

Framing dial — civilian: robustness / reasonable-doubt test on a recovered rule. Contractor:
adversarial alternative-hypothesis search against a load-bearing finding.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402

ABSTAIN = ("incompressible", "general", "random")


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def cross_examine(surface):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    cands = chiron.top_generators(vals, k=5)
    winner = cands[0] if cands else None
    alts = cands[1:] if cands else []

    if not winner or inv.model_class in ABSTAIN or "mdl_cost_bits" not in winner:
        return {
            "law": inv.model_class, "verified": bool(inv.verified),
            "winner_mdl_bits": None, "alternatives_considered": len(alts),
            "reasonable_doubt": [], "fragility": [],
            "verdict": "NO CASE — no generator to defend (honest abstention)",
        }

    doubt = []
    if winner:
        wc = float(winner["mdl_cost_bits"])
        for a in alts:
            gap = float(a["mdl_cost_bits"]) - wc
            if gap <= max(2.0, 0.10 * wc):       # within 2 bits or 10% -> comparable
                doubt.append({"alternative": a["model_class"], "mdl_gap_bits": round(gap, 2)})

    fragility = []
    for cut, label in [(vals[:-1], "drop-last-term"), (vals[1:], "drop-first-term")]:
        if len(cut) >= 4 and winner:
            try:
                w2 = chiron.top_generators(cut, k=1)[0]["model_class"]
                if w2 != winner["model_class"]:
                    fragility.append({"perturbation": label, "becomes": w2})
            except Exception:
                pass

    if not winner or inv.model_class in ABSTAIN:
        verdict = "NO CASE — no generator to defend (honest abstention)"
    elif doubt:
        verdict = "REASONABLE DOUBT — a competing generator fits comparably"
    elif fragility:
        verdict = "FRAGILE — the generator changes under minor truncation"
    else:
        verdict = "SURVIVES CROSS-EXAMINATION — decisive, stable, no surviving alternative"

    return {
        "law": inv.model_class,
        "verified": bool(inv.verified),
        "winner_mdl_bits": round(float(winner["mdl_cost_bits"]), 2) if winner else None,
        "alternatives_considered": len(alts),
        "reasonable_doubt": doubt,
        "fragility": fragility,
        "verdict": verdict,
    }


def render(x):
    L = ["=" * 62, "CROSS-EXAMINATION — adversarial test of a finding", "=" * 62]
    L.append(f"  law={x['law']}  verified={x['verified']}  winner_bits={x['winner_mdl_bits']}")
    L.append(f"  alternatives considered: {x['alternatives_considered']}")
    if x["reasonable_doubt"]:
        for d in x["reasonable_doubt"]:
            L.append(f"     DOUBT: {d['alternative']} fits within {d['mdl_gap_bits']} bits")
    if x["fragility"]:
        for f in x["fragility"]:
            L.append(f"     FRAGILE: {f['perturbation']} -> {f['becomes']}")
    L.append(f"  >> {x['verdict']}")
    L.append("=" * 62)
    return "\n".join(L)


_DEMO = ["1 1 2 3 5 8 13 21 34", "2 4 8 16 32 64", "41 19 50 83 6 9 68 12"]


def _demo():
    for s in _DEMO:
        print(f"\n### {s}")
        print(render(cross_examine(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Adversarial cross-examination of a recovered generator.")
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
    x = cross_examine(surface)
    print(json.dumps(x, indent=2) if args.json else render(x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
