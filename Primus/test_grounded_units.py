# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Regression gates for issue #3 — grounded facts must not verify across units.

WHY THIS FILE EXISTS

On 2026-08-15 an external audit reproduced three false verifications in
`primus.grounded`. Every one of them stamped VERIFIED on a claim whose digits
agreed with a supplied fact while the *thing being counted* did not:

    "Revenue was $4.2M."   against  Revenue = 4200000 vehicles   -> VERIFIED
    "Readiness was 74%."   against  Readiness = 74 (no unit)     -> VERIFIED
    "Species was 2."       against  specie = 2                   -> VERIFIED

The gate battery was green through all three, because nothing in it asked.
That is the failure this file repairs: the battery now asks.

THE INVARIANT

Agreeing digits are not agreeing facts. A claim is VERIFIED only when the
subject resolves to exactly one supplied fact AND the semantic unit on both
sides is the same — where "no unit" is itself a unit that only matches "no
unit". Anything else REFUSES. A dollar figure never confirms a vehicle count,
a percentage never confirms a bare number, and a subject the caller did not
write is never silently folded onto one they did.

These are written as fail-first cases: run this against the code as it stood
before the repair and all three FALSE VERIFICATION gates fail.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from fractions import Fraction  # noqa: E402
from primus.grounded import (  # noqa: E402
    _measure, _unit_of, check_text, normalise_subject,
)


def _statuses(text, facts):
    return [c["status"] for c in check_text(text, facts)["claims"]]


def _reasons(text, facts):
    return [c.get("reason", "") for c in check_text(text, facts)["claims"]]


def main() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    # ---- issue #3, the three reproduced false verifications ----------------

    gate("#3a a dollar figure does not verify against a vehicle count",
         _statuses("Revenue was $4.2M.",
                   {"Revenue": {"value": 4_200_000, "unit": "vehicles"}})
         == ["REFUSED"])

    gate("#3a the refusal names the unit disagreement",
         "unit" in _reasons("Revenue was $4.2M.",
                            {"Revenue": {"value": 4_200_000,
                                         "unit": "vehicles"}})[0].lower())

    gate("#3b a percentage does not verify against a unitless fact",
         _statuses("Readiness was 74%.", {"Readiness": {"value": 74}})
         == ["REFUSED"])

    gate("#3c a subject the caller did not write does not fold onto one they did",
         _statuses("Species was 2.", {"specie": {"value": 2}}) == ["REFUSED"])

    gate("#3c normalisation is injective on the colliding pair",
         normalise_subject("Species") != normalise_subject("specie"))

    # ---- the magnitude/currency split the repair introduces ----------------

    gate("a magnitude suffix scales the number without erasing the currency",
         _statuses("Revenue was $4.2M.",
                   {"Revenue": {"value": 4_200_000, "unit": "usd"}})
         == ["VERIFIED"])

    gate("...and a wrong magnitude against the right currency still refutes",
         _statuses("Revenue was $4.3M.",
                   {"Revenue": {"value": 4_200_000, "unit": "usd"}})
         == ["REFUTED"])

    gate("a bare number does not verify against a fact that states a unit",
         _statuses("Revenue was 4200000.",
                   {"Revenue": {"value": 4_200_000, "unit": "usd"}})
         == ["REFUSED"])

    gate("a unitless claim still verifies against a unitless fact",
         _statuses("Serviceable vehicles was 412.",
                   {"serviceable vehicles": 412}) == ["VERIFIED"])

    gate("percent matches percent",
         _statuses("Readiness was 74%.",
                   {"Readiness": {"value": 74, "unit": "percent"}})
         == ["VERIFIED"])

    gate("a claim carrying two different units refuses rather than picking",
         _statuses("Revenue was $4.2 percent.",
                   {"Revenue": {"value": 4.2, "unit": "usd"}}) == ["REFUSED"])

    # ---- the property that must hold no matter what ------------------------

    # Across a grid of unit pairings, VERIFIED may appear only where the unit
    # the claim actually asserts equals the unit the fact actually records.
    #
    # Both sides are read back from the engine rather than assumed from the
    # spelling: "412M" asserts a magnitude and no semantic unit, and a fact
    # recorded as 412 million is likewise 412000000 with no semantic unit, so
    # those two agreeing is correct rather than a leak. Comparing the labels
    # I typed instead of the units the engine parsed would test my grid, not
    # the gate.
    written = ["", "%", "$", "M", " percent", " thousand"]
    fact_units = [None, "percent", "usd", "vehicles", "million", "thousand"]
    leaks = []
    for form in written:
        prefix = "$" if form == "$" else ""
        suffix = "" if form == "$" else form
        text = "Readiness was %s412%s." % (prefix, suffix)
        for fact_unit in fact_units:
            facts = {"Readiness": {"value": 412, "unit": fact_unit}}
            claim = check_text(text, facts)["claims"]
            if not claim:
                continue
            claim = claim[0]
            if claim["status"] != "VERIFIED":
                continue
            _, fact_semantic, _ = _measure(Fraction(412), _unit_of(fact_unit))
            if claim["asserted_unit"] != fact_semantic:
                leaks.append((text, claim["asserted_unit"], fact_unit,
                              fact_semantic))
    gate("VERIFIED never crosses a unit boundary  (%d leaks)" % len(leaks),
         not leaks)
    for text, a, fu, fs in leaks:
        print("        %r asserted %r verified against fact unit %r (semantic %r)"
              % (text, a, fu, fs))

    print("\n  grounded unit regression: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    if failures:
        print("  FAILED: " + "; ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
