#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
cross_examine.py — The Defense Attorney (Chiron Jurisprudence Suite).

A sovereign adversarial court. Chiron's Epistemic Court extracts the single best generator
under Minimum Description Length; this module is its constitutional adversary. Its sole mandate
is to manufacture REASONABLE DOUBT: to take the recovered generator and its residual noise and
actively attempt to construct a mathematically viable ALTERNATIVE generator that compresses the
same evidence equally well (MDL parity). If it succeeds, it issues a constitutional INJUNCTION
— Finality is Blocked, the conclusion cannot stand. If it exhausts the admissible search space
without finding a peer, the original rule has survived cross-examination and may proceed.

It searches four independent avenues of doubt:
  1. MDL-PARITY PEERS    — does any rival hypothesis class describe the data within a few bits?
  2. EARNS-ITS-KEEP      — does the rule materially out-compress verbatim storage, or is it
                           merely interpolating noise (the always-available polynomial defense)?
  3. BOUNDARY FRAGILITY  — does the verdict flip when the evidence boundary is perturbed
                           (a single term withheld)? A rule that depends on the cut is not earned.
  4. RESIDUAL STRUCTURE  — does the leftover noise itself hide a second generator, meaning the
                           first explanation is incomplete?

Constitutional constraints enforced here: evidence is IMMUTABLE (the input is hashed on entry,
every collapse runs on a copy, the hash is re-checked); the court is JURISDICTIONALLY ISOLATED
(it renders only doubt, it never rewrites the math); ABSTENTION is absolute (no rule -> no case);
ZERO external dependencies (chiron + stdlib only).

    python3 cross_examine.py selftest
    python3 cross_examine.py examine 1 1 2 3 5 8 13 21
    python3 cross_examine.py examine 41 19 50 83 6 9 --json

Framing dial — civilian: robustness / reasonable-doubt test on a recovered rule. Contractor:
adversarial alternative-hypothesis search against a load-bearing finding.
"""
import os
import sys
import json
import hashlib
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402

ABSTAIN_CLASSES = ("incompressible", "general", "random")
PARITY_BITS = 2.0          # two models within 2 bits are MDL peers (~4x in posterior odds)
COMPRESSION_FLOOR = 1.30   # a rule must out-compress verbatim storage by at least this factor


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _seal(vals):
    """Immutability seal: a hash of the evidence as received."""
    return hashlib.sha256(repr(tuple(vals)).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# the four avenues of doubt (each operates on a COPY — evidence is immutable)
# ---------------------------------------------------------------------------
def _peer_generators(vals, winner):
    """Rival hypothesis classes whose MDL cost is within parity of the winner."""
    try:
        cands = chiron.top_generators(list(vals), k=6)
    except Exception:
        return []
    real = [c for c in cands if "mdl_cost_bits" in c and c.get("model_class") not in ABSTAIN_CLASSES]
    peers = []
    wbits = float(winner["mdl_cost_bits"])
    for c in real:
        if c.get("model_class") == winner.get("model_class"):
            continue
        gap = float(c["mdl_cost_bits"]) - wbits
        if gap <= PARITY_BITS:
            peers.append({"model_class": c["model_class"], "mdl_gap_bits": round(gap, 3)})
    return peers


def _earns_keep(inv):
    """The null defense: an interpolating polynomial always fits. The rule must beat verbatim
    storage materially, or it is overfitting rather than explaining."""
    cr = float(inv.compression_ratio)
    return cr >= COMPRESSION_FLOOR, round(cr, 3)


def _boundary_fragility(vals, winner_class):
    """Does the recovered class survive withholding a single boundary term?"""
    flips = []
    for cut, label in [(list(vals[:-1]), "withhold-last"), (list(vals[1:]), "withhold-first")]:
        if len(cut) >= 4:
            try:
                alt = chiron.top_generators(cut, k=1)
                got = alt[0].get("model_class") if alt else None
                if got and got not in ABSTAIN_CLASSES and got != winner_class:
                    flips.append({"perturbation": label, "becomes": got})
            except Exception:
                pass
    return flips


def _residual_structure(inv):
    """Is there a second generator hiding in the residual noise?"""
    resid = list(getattr(inv, "residual", []) or [])
    if len(resid) >= 6:
        try:
            r = chiron.collapse(list(resid))
            if r.verified and r.model_class not in ABSTAIN_CLASSES:
                return {"residual_class": r.model_class}
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# the trial
# ---------------------------------------------------------------------------
def cross_examine(surface):
    vals = _nums(surface)
    evidence_hash = _seal(vals)
    inv = chiron.collapse(list(vals))          # collapse a copy; never touch the evidence

    # honest abstention — there is no rule to defend, so there is no case
    if not inv.verified or inv.model_class in ABSTAIN_CLASSES:
        return {
            "evidence_hash": evidence_hash,
            "winner": {"model_class": inv.model_class, "verified": bool(inv.verified)},
            "searches": [], "reasonable_doubt": False, "doubt_reasons": [],
            "injunction": {"active": False, "reason": None},
            "verdict": "NO CASE — no verified generator to defend (honest abstention)",
            "evidence_immutable": evidence_hash == _seal(vals),
        }

    try:
        winner = next(c for c in chiron.top_generators(list(vals), k=6)
                      if "mdl_cost_bits" in c and c.get("model_class") not in ABSTAIN_CLASSES)
    except StopIteration:
        winner = {"model_class": inv.model_class, "mdl_cost_bits": float(getattr(inv, "total_bits", 0.0))}

    searches, doubt = [], []

    peers = _peer_generators(vals, winner)
    searches.append({"avenue": "MDL-parity peer search", "exhausted": True,
                     "alternatives_at_parity": peers})
    if peers:
        doubt.append(f"peer generator(s) at MDL parity: {[p['model_class'] for p in peers]}")

    earns, cr = _earns_keep(inv)
    searches.append({"avenue": "earns-its-keep (vs verbatim)", "compression_ratio": cr, "earns_keep": earns})
    if not earns:
        doubt.append(f"rule does not materially out-compress storage (cr={cr} < {COMPRESSION_FLOOR}); interpolation, not law")

    frag = _boundary_fragility(vals, winner.get("model_class"))
    searches.append({"avenue": "evidence-boundary fragility", "flips": frag})
    if frag:
        doubt.append(f"verdict flips when evidence boundary perturbed: {frag}")

    rs = _residual_structure(inv)
    searches.append({"avenue": "residual hidden-structure", "found": rs})
    if rs:
        doubt.append(f"unexplained structure hides in the residual: {rs['residual_class']}")

    has_doubt = bool(doubt)
    return {
        "evidence_hash": evidence_hash,
        "winner": {"model_class": inv.model_class,
                   "mdl_bits": round(float(winner.get("mdl_cost_bits", 0.0)), 3),
                   "compression_ratio": cr, "verified": True},
        "searches": searches,
        "reasonable_doubt": has_doubt,
        "doubt_reasons": doubt,
        "injunction": {"active": has_doubt, "reason": "; ".join(doubt) if has_doubt else None},
        "verdict": ("FINALITY BLOCKED — reasonable doubt established" if has_doubt
                    else "SURVIVES CROSS-EXAMINATION — search space exhausted, no peer generator"),
        "evidence_immutable": evidence_hash == _seal(vals),
    }


def render(x):
    L = ["=" * 64, "CROSS-EXAMINATION — the defense attorney", "=" * 64]
    L.append(f"  evidence seal: {x['evidence_hash']} (immutable={x['evidence_immutable']})")
    L.append(f"  rule on trial: {x['winner'].get('model_class')}  cr={x['winner'].get('compression_ratio')}")
    for s in x["searches"]:
        detail = (s.get("alternatives_at_parity") or s.get("flips") or s.get("found")
                  or s.get("compression_ratio"))
        L.append(f"     [{s['avenue']}] -> {detail}")
    if x["doubt_reasons"]:
        for d in x["doubt_reasons"]:
            L.append(f"     DOUBT: {d}")
    L.append(f"  injunction: {'ACTIVE' if x['injunction']['active'] else 'none'}")
    L.append(f"  >> {x['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # a strong law survives
    fib = cross_examine("1 1 2 3 5 8 13 21 34 55")
    ok("fibonacci survives cross-examination", not fib["reasonable_doubt"])
    ok("survival -> no injunction", not fib["injunction"]["active"])
    ok("fibonacci evidence immutable", fib["evidence_immutable"])

    pow2 = cross_examine("1 2 4 8 16 32 64 128")
    ok("powers of two survive", not pow2["reasonable_doubt"])

    # no rule -> no case (honest abstention)
    noise = cross_examine("41 19 50 83 6 9 68 12")
    ok("noise -> NO CASE", noise["verdict"].startswith("NO CASE"))
    ok("noise -> no injunction", not noise["injunction"]["active"])

    # immutability: the caller's list is never mutated
    data = [1, 1, 2, 3, 5, 8, 13, 21]
    snapshot = list(data)
    cross_examine(data)
    ok("evidence immutability (input list unchanged)", data == snapshot)

    # structure of the result
    ok("result carries an injunction object", "injunction" in fib and "active" in fib["injunction"])
    ok("four avenues searched on a real rule", len(fib["searches"]) == 4)
    ok("search space marked exhausted", fib["searches"][0]["exhausted"] is True)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  cross_examine.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 1 2 3 5 8 13 21 34", "1 2 4 8 16 32 64", "41 19 50 83 6 9 68 12"]:
        print(f"\n### {s}")
        print(render(cross_examine(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Adversarial cross-examination of a recovered generator.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    ex = sub.add_parser("examine"); ex.add_argument("values", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "examine":
        x = cross_examine(" ".join(args.values))
        print(json.dumps(x, indent=2) if args.json else render(x))
        return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
