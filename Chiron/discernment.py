#!/usr/bin/env python3
"""
discernment.py — confidence from convergence, not authority (D-2, the capstone).

The discernment engine, assembled. A finding is examined by independent witnesses, each
blind to the others' reasoning, each answering one question:

  EPISTEMIC      does it appear true?           (chiron — a verified law)
  ONTOLOGICAL    could it survive?              (uma_bridge — robustness under perturbation)
  ADVERSARIAL    does it survive challenge?     (cross_examine — no alternative generator)
  AXIOLOGICAL    is it elegant?                 (aesthetics — beauty / parsimony)
  AXIOLOGICAL    is it worth preserving?        (ontological — V-Units value)
  CANDOR         is the explanation honest?     (candor — anti-patronization)

Confidence is the CONVERGENCE of the witnesses — not the verdict of any one of them. When a
witness dissents, that disagreement is diagnostic: it names exactly where reality, value, or
honesty pushed back. A governance gate (SoCPM) then decides proceed / escalate. This is
progressive elimination: the conclusion that survives every independent test, or an honest
account of which test it failed.

    python3 discernment.py --demo
    python3 discernment.py 1 1 2 3 5 8 13 21
    python3 discernment.py --surface "41 19 50 83 6 9 68 12" --json

Framing dial — civilian: multi-witness confidence with a named point of failure. Contractor:
independent-cross-check fusion; convergence score + dissent localization + governed call.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import uma_bridge      # noqa: E402
import cross_examine   # noqa: E402
import aesthetics      # noqa: E402
import ontological     # noqa: E402
import govern          # noqa: E402
import candor_bridge   # noqa: E402


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def discern(surface, stakes=None):
    vals = _nums(surface)
    surface_str = " ".join(str(v) for v in vals)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])

    witnesses = []

    witnesses.append(("epistemic", "appears true (verified law)", bool(inv.verified)))

    rob = _safe(lambda: uma_bridge.robustness(surface_str), {}) or {}
    witnesses.append(("ontological:robustness", "survives perturbation",
                      bool(rob.get("structure_persisted_after_evolution"))))

    xe = _safe(lambda: cross_examine.cross_examine(surface_str), {}) or {}
    witnesses.append(("adversarial", "survives cross-examination",
                      str(xe.get("verdict", "")).startswith("SURVIVES")))

    aes = _safe(lambda: aesthetics.aesthetic(surface_str), {}) or {}
    witnesses.append(("axiological:aesthetic", "elegant / parsimonious", float(aes.get("beauty", 0)) >= 0.5))

    val = _safe(lambda: ontological.v_units(surface_str), {}) or {}
    Vval = float(val.get("V_units", 0.0))
    witnesses.append(("axiological:value", "worth preserving", Vval >= 0.5))

    cand = _safe(lambda: candor_bridge.audit_finding(surface_str), {}) or {}
    witnesses.append(("candor", "explanation is honest", float(cand.get("candor_score", 0)) >= 0.6))

    affirm = sum(1 for _, _, ok in witnesses if ok)
    total = len(witnesses)
    confidence = round(affirm / total, 3)
    dissent = [w for w, _, ok in witnesses if not ok]

    Hp = float((stakes or {}).get("Hp", 0.5))
    g = govern.govern(Cx=0.6, Ar=0.7, Hp=Hp, Mc=0.6, V=(Vval if inv.verified else 0.3))

    if affirm == total and not g["redirect_or_escalate_required"]:
        verdict = "CONFIRM — all witnesses converge"
    elif affirm == 0:
        verdict = "REJECT — no witness affirms"
    elif affirm >= total - 1:
        verdict = "QUALIFIED — near-consensus" + (f"; dissent: {', '.join(dissent)}" if dissent else "; governance hold")
    else:
        verdict = "SPLIT — witnesses disagree (diagnostic)"

    return {
        "law": inv.model_class,
        "verified": bool(inv.verified),
        "witnesses": [{"witness": w, "asks": q, "affirms": ok} for w, q, ok in witnesses],
        "convergence_confidence": confidence,
        "dissent": dissent,
        "governance": {"verdict": "ESCALATE" if g["redirect_or_escalate_required"] else "PROCEED",
                       "socpm_lhs": g["socpm_lhs"]},
        "verdict": verdict,
    }


def render(d):
    L = ["=" * 64, "DISCERNMENT — independent witnesses, confidence by convergence", "=" * 64]
    L.append(f"  finding: {d['law']}  (verified={d['verified']})")
    for w in d["witnesses"]:
        mark = "✓" if w["affirms"] else "✗"
        L.append(f"     [{mark}] {w['witness']:<24} {w['asks']}")
    L.append(f"  convergence confidence ... {d['convergence_confidence']}  ({len(d['witnesses']) - len(d['dissent'])}/{len(d['witnesses'])} witnesses)")
    if d["dissent"]:
        L.append(f"  dissent (diagnostic) ..... {', '.join(d['dissent'])}")
    L.append(f"  governance ............... {d['governance']['verdict']} (SoCPM lhs {d['governance']['socpm_lhs']})")
    L.append(f"  >> {d['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


_DEMO = ["1 1 2 3 5 8 13 21 34 55", "2 4 6 8 10 12 14 16", "41 19 50 83 6 9 68 12 46"]


def _demo():
    for s in _DEMO:
        print(f"\n### {s}")
        print(render(discern(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Multi-witness discernment over a finding.")
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
    d = discern(surface)
    print(json.dumps(d, indent=2) if args.json else render(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
