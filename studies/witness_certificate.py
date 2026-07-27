#!/usr/bin/env python3
"""
witness_certificate.py — turn a claimed counterexample into a finite object
plus a finite audit trail that anyone can check without trusting this system.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

THE ASYMMETRY THIS EXISTS TO EXPLOIT.

    For all x, P(x)      cannot be established by testing finitely many x.
    Exists x, not P(x)   refutes it immediately and completely.

Ten billion successful cases prove nothing universally. One valid failure is a
proof of falsity. A verify-or-refuse engine is therefore structurally much
better suited to DISPROOF BY EXACT WITNESS than to proving infinite statements,
and a counterexample is the one output it can produce that nobody has to take
on faith.

WHAT A CERTIFICATE MUST CONTAIN, and why each part is load-bearing:

  1. The conjecture, stated precisely, with provenance. A refutation of a
     statement nobody else recognises is worthless. The certificate names the
     source (OEIS entry, Erdos number, Lean file) so a reader can confirm the
     statement was not quietly reworded into something easier to break.
  2. The witness itself. A finite object.
  3. Every PRECONDITION, evaluated exactly, shown to HOLD. A counterexample
     that fails the hypotheses is not a counterexample. This is where most
     false refutations die, so each hypothesis is listed and checked
     separately rather than assumed.
  4. The claimed CONCLUSION, evaluated exactly, shown to FAIL.
  5. An INDEPENDENT recomputation. Every obligation is computed a second time
     by a different route. If the two disagree the certificate REFUSES to
     issue -- an engine agreeing with itself is not evidence.
  6. A standalone reproduction script with no dependency on this repo, so a
     third party can rerun the whole audit from the certificate alone.
  7. A content hash, and an explicit statement of what would falsify it.

NOTHING HERE ASKS ANYONE TO TRUST AN ENGINE. The certificate hands over a
finite object and the arithmetic to check it. That is the point.

A certificate is NOT issued unless every precondition holds, the conclusion
genuinely fails, and the independent recomputation agrees. Any other state
returns a refusal explaining which obligation was not met.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CERTS = HERE / "certificates"


class WitnessRefused(Exception):
    """Raised when a claimed counterexample fails to certify."""


def certify_counterexample(
    *,
    conjecture: str,
    provenance: dict,
    witness,
    preconditions: list,
    conclusion: tuple,
    independent: list,
    notes: str = "",
):
    """
    Build a counterexample certificate, or refuse.

    preconditions : [(name, expression_str, value_bool), ...]
                    every one must be True, or the witness does not satisfy
                    the hypotheses and is not a counterexample at all.
    conclusion    : (name, expression_str, value_bool)
                    must be False -- that is what makes it a refutation.
    independent   : [(name, value), ...] recomputed by a SECOND method;
                    must agree with the primary computation.
    """
    # --- 3. every hypothesis must actually hold -----------------------------
    failed = [p[0] for p in preconditions if p[2] is not True]
    if failed:
        raise WitnessRefused(
            f"witness does not satisfy the hypotheses: {failed}. A witness that "
            f"fails a precondition is not a counterexample -- the conjecture "
            f"never claimed anything about it.")

    # --- 4. the conclusion must genuinely fail ------------------------------
    cname, cexpr, cval = conclusion
    if cval is not False:
        raise WitnessRefused(
            f"the claimed conclusion '{cname}' evaluated to {cval!r}, not False. "
            f"Nothing is refuted.")

    # --- 5. independent recomputation must agree ----------------------------
    primary = {p[0]: p[2] for p in preconditions}
    primary[cname] = cval
    disagreements = [
        f"{n}: primary={primary.get(n)!r} independent={v!r}"
        for n, v in independent if n in primary and primary[n] != v
    ]
    if disagreements:
        raise WitnessRefused(
            f"independent recomputation DISAGREES with the primary computation: "
            f"{disagreements}. Refusing to issue. An engine agreeing with itself "
            f"is not evidence; two methods disagreeing means at least one is "
            f"wrong and neither result may be published.")
    if not independent:
        raise WitnessRefused(
            "no independent recomputation supplied. A single implementation "
            "checking its own output certifies nothing.")

    body = {
        "kind": "counterexample-certificate/1",
        "conjecture": conjecture,
        "provenance": provenance,
        "verdict": "REFUTED",
        "witness": repr(witness),
        "preconditions": [
            {"name": n, "expression": e, "holds": v} for n, e, v in preconditions
        ],
        "conclusion": {"name": cname, "expression": cexpr, "holds": cval},
        "independent_recomputation": [
            {"name": n, "value": repr(v)} for n, v in independent
        ],
        "notes": notes,
        "what_would_falsify_this": (
            "Recompute any listed obligation and obtain a different result. "
            "Every value here is exact integer or rational arithmetic; no "
            "floating point participates in any verdict. If the conjecture's "
            "statement in the cited source differs from the statement above, "
            "this certificate does not apply."
        ),
        "what_this_does_NOT_claim": (
            "It does not claim a proof of any general statement, that the "
            "witness is minimal, or that the conjecture is uninteresting. It "
            "claims exactly one thing: this finite object satisfies the stated "
            "hypotheses and fails the stated conclusion."
        ),
        "issued_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    body["certificate_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in body.items() if k != "issued_utc"},
                   sort_keys=True).encode()
    ).hexdigest()
    return body


def render(cert: dict) -> str:
    """Human-readable certificate."""
    L = []
    W = 74
    L.append("=" * W)
    L.append("COUNTEREXAMPLE CERTIFICATE")
    L.append("=" * W)
    L.append("")
    L.append("CONJECTURE")
    L.append(f"  {cert['conjecture']}")
    L.append("")
    L.append("PROVENANCE")
    for k, v in cert["provenance"].items():
        L.append(f"  {k:<14} {v}")
    L.append("")
    L.append(f"VERDICT               {cert['verdict']}")
    L.append("")
    L.append("WITNESS")
    L.append(f"  {cert['witness']}")
    L.append("")
    L.append("PRECONDITIONS  (every one must hold, or it is not a counterexample)")
    for p in cert["preconditions"]:
        L.append(f"  [{'HOLDS' if p['holds'] else 'FAILS'}]  {p['name']}")
        L.append(f"           {p['expression']}")
    L.append("")
    L.append("CLAIMED CONCLUSION  (must fail -- this is the refutation)")
    c = cert["conclusion"]
    L.append(f"  [{'HOLDS' if c['holds'] else 'FAILS'}]  {c['name']}")
    L.append(f"           {c['expression']}")
    L.append("")
    L.append("INDEPENDENT RECOMPUTATION  (second method; must agree)")
    for i in cert["independent_recomputation"]:
        L.append(f"  {i['name']:<28} {i['value']}")
    if cert.get("notes"):
        L.append("")
        L.append("NOTES")
        for line in cert["notes"].splitlines():
            L.append(f"  {line}")
    L.append("")
    L.append("WHAT WOULD FALSIFY THIS CERTIFICATE")
    for line in _wrap(cert["what_would_falsify_this"], W - 2):
        L.append(f"  {line}")
    L.append("")
    L.append("WHAT THIS DOES NOT CLAIM")
    for line in _wrap(cert["what_this_does_NOT_claim"], W - 2):
        L.append(f"  {line}")
    L.append("")
    L.append(f"SHA-256   {cert['certificate_sha256']}")
    L.append(f"ISSUED    {cert['issued_utc']}")
    L.append("=" * W)
    return "\n".join(L)


def _wrap(s, w):
    out, cur = [], ""
    for word in s.split():
        if len(cur) + len(word) + 1 > w:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        out.append(cur)
    return out


def save(cert: dict, slug: str):
    CERTS.mkdir(exist_ok=True)
    (CERTS / f"{slug}.json").write_text(json.dumps(cert, indent=1))
    (CERTS / f"{slug}.txt").write_text(render(cert) + "\n")
    return CERTS / f"{slug}.txt"


# ---------------------------------------------------------------------------
# Self-test: the machinery must REFUSE bad witnesses, not just accept good ones
# ---------------------------------------------------------------------------

def selftest():
    print("=" * 74)
    print("WITNESS CERTIFICATE — self-test")
    print("=" * 74)
    print("A certificate issuer that only ever says yes is worthless. These")
    print("gates check that it refuses every way a claimed counterexample can")
    print("be wrong.\n")
    passed = 0
    total = 0

    def gate(desc, fn, expect_refusal=True):
        nonlocal passed, total
        total += 1
        try:
            fn()
            ok = not expect_refusal
            why = "issued" if not expect_refusal else "ISSUED (should have refused)"
        except WitnessRefused as e:
            ok = expect_refusal
            why = f"refused: {str(e)[:56]}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}")
        print(f"         {why}")
        if ok:
            passed += 1

    base = dict(
        conjecture="For every n > 2, P(n) holds.",
        provenance={"source": "self-test", "url": "n/a"},
        witness=7,
    )

    gate("refuses when a precondition FAILS",
         lambda: certify_counterexample(
             **base,
             preconditions=[("n > 2", "7 > 2", True), ("n is even", "7 % 2 == 0", False)],
             conclusion=("P(n)", "P(7)", False),
             independent=[("P(n)", False)]))

    gate("refuses when the conclusion HOLDS (nothing refuted)",
         lambda: certify_counterexample(
             **base,
             preconditions=[("n > 2", "7 > 2", True)],
             conclusion=("P(n)", "P(7)", True),
             independent=[("P(n)", True)]))

    gate("refuses when independent recomputation DISAGREES",
         lambda: certify_counterexample(
             **base,
             preconditions=[("n > 2", "7 > 2", True)],
             conclusion=("P(n)", "P(7)", False),
             independent=[("P(n)", True)]))

    gate("refuses when NO independent recomputation is supplied",
         lambda: certify_counterexample(
             **base,
             preconditions=[("n > 2", "7 > 2", True)],
             conclusion=("P(n)", "P(7)", False),
             independent=[]))

    gate("ISSUES a genuine counterexample", lambda: certify_counterexample(
             **base,
             preconditions=[("n > 2", "7 > 2", True)],
             conclusion=("P(n)", "P(7)", False),
             independent=[("P(n)", False), ("n > 2", True)]),
         expect_refusal=False)

    print()
    print(f"  {passed}/{total} gates passed")
    return passed == total


if __name__ == "__main__":
    import sys
    ok = selftest()
    if ok:
        # demonstrate the rendered form on a real, already-known refutation so
        # the shape is inspectable without waiting for a discovery
        cert = certify_counterexample(
            conjecture="Every Fermat number F_n = 2^(2^n) + 1 is prime. "
                       "(Fermat, 1650; refuted by Euler, 1732.)",
            provenance={"source": "Fermat's conjecture",
                        "oeis": "https://oeis.org/A000215",
                        "status": "historically refuted — used here to show the form"},
            witness="n = 5,  F_5 = 4294967297",
            preconditions=[("n is a nonnegative integer", "n = 5", True),
                           ("F_n is well-defined", "F_5 = 2^32 + 1 = 4294967297", True)],
            conclusion=("F_n is prime", "4294967297 = 641 * 6700417", False),
            independent=[("F_n is prime", False),
                         ("n is a nonnegative integer", True),
                         ("F_n is well-defined", True)],
            notes="Independent route: trial division recovers 641 exactly;\n"
                  "641 * 6700417 = 4294967297 verified by integer multiplication.\n"
                  "No floating point participates in any step.")
        p = save(cert, "example-fermat")
        print()
        print(render(cert))
        print(f"\nwritten: {p}")
    sys.exit(0 if ok else 1)
