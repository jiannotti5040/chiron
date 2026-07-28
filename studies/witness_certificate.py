#!/usr/bin/env python3
"""
witness_certificate.py — RETIRED generic counterexample issuer.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

This module is deliberately disabled.  Its former API accepted booleans and
expression strings supplied by the caller, rather than executing the stated
mathematics.  That meant a caller could make it emit a ``REFUTED`` object
without a recomputable witness.  Hashing such an object only proved that the
unsupported assertion had not changed; it did not make the assertion true.

No existing artifact in ``studies/certificates/`` is mathematical evidence.
They are retained as historical, non-evidentiary records rather than deleted.
New counterexamples must use a target-specific, executable replay checker with
an independent implementation; a Lean witness is additionally required before
any claim about a pinned Formal Conjectures statement is submitted publicly.
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
    """Refuse the retired data-only certificate format unconditionally."""
    raise WitnessRefused(
        "The generic witness certificate issuer is retired: it did not execute "
        "caller-supplied expressions. Build a target-specific replay checker "
        "with independently executable primary and secondary checks instead.")


def render(cert: dict) -> str:
    """Render a historical object with an unavoidable non-evidentiary warning."""
    L = []
    W = 74
    L.append("=" * W)
    L.append("LEGACY / NON-EVIDENTIARY COUNTEREXAMPLE ARTIFACT")
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
    raise WitnessRefused(
        "Refusing to save a certificate from the retired generic issuer. Use a "
        "target-specific replayable case instead.")


# ---------------------------------------------------------------------------
# Self-test: retirement itself is the safety gate.
# ---------------------------------------------------------------------------

def selftest():
    print("=" * 74)
    print("WITNESS CERTIFICATE — retirement self-test")
    print("=" * 74)
    print("The generic format is disabled because it accepted asserted boolean")
    print("values rather than replaying mathematical obligations.\n")
    try:
        certify_counterexample(
            conjecture="For every n > 2, P(n) holds.",
            provenance={"source": "self-test"}, witness=7,
            preconditions=[("n > 2", "7 > 2", True)],
            conclusion=("P(n)", "P(7)", False),
            independent=[("P(n)", False)])
    except WitnessRefused as exc:
        print(f"  [PASS] refuses every attempted issuance: {exc}")
        return True
    print("  [FAIL] retired issuer emitted a certificate")
    return False


if __name__ == "__main__":
    import sys
    ok = selftest()
    sys.exit(0 if ok else 1)
