#!/usr/bin/env python3
"""
claim_domain.py — extract the DOMAIN of a natural-language conjecture, or
refuse to test it.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

WHY THIS MODULE EXISTS. Testing a claim outside its own stated domain is the
single most productive source of false counterexamples in this project. It has
now happened five separate times, in five different phrasings:

    "a(n) > 0 for all n > 1"          A303656, A308734
        -> flagged the published a(1) = 0, which the claim excludes
    "a(n) > 0 for all n = 3,4,..."    A208243, A218654, A236241
        -> enumeration form, unparsed; tested from n = 1
    "with the only exception n = 8"   A218585
        -> \\bexcept\\b does not match "exception"; flagged exactly n = 8
    "for all even n > 8012 and
     odd n > 15727"                   A219055, A219185
        -> parity-split; two claims merged into one, no domain extracted
    "a(n) is never 0 for n > 1"       A232111
        -> flagged the published a(0) = 0, again outside the domain

Every one of those looked like a refutation of a stated conjecture. Every one
was this same mistake. So domain extraction stops being ad-hoc per-scanner and
becomes one audited function with one rule:

    IF THE DOMAIN CANNOT BE ESTABLISHED WITH CONFIDENCE, REFUSE.

An unparsed domain is not "assume the whole sequence". It is "do not test".
"""

from __future__ import annotations

import re

# Structures that make a claim more than "P(n) for n > k". Their presence means
# the domain is not a simple threshold and the claim must not be tested.
NOT_A_SIMPLE_THRESHOLD = re.compile(
    r"except"                     # "exception", "exceptions", "except for"
    r"|\bif and only if\b|\biff\b|\bunless\b|\bassuming\b|\bmodulo\b|\bmod\b"
    r"|\bif\b|\bwhen\b|\bwhenever\b|\bprovided\b|\bconditional\b"
    r"|\beven\s+n\b|\bodd\s+n\b|\bprime\s+n\b"      # parity/primality splits
    r"|\bprobably\b|\bperhaps\b|\bseems\b|\bappears\b|\bmight\b|\blikely\b"
    r"|\beventually\b|\binfinitely\b|\balmost\s+all\b|\bdensity\b"
    r"|\bsufficiently\s+large\b|\blarge\s+enough\b",
    re.I)

# The forms that ARE a simple threshold, in the phrasings OEIS actually uses.
THRESHOLDS = [
    # "for all n > 5", "for n >= 5", "for every n ≥ 5"
    (re.compile(r"for\s+(?:all|every|each)?\s*n\s*(>=|≥|>)\s*(-?\d+)", re.I),
     "inequality"),
    # "for all n = 3,4,...", "for every n = 20, 21, ..."
    (re.compile(r"for\s+(?:all|every|each)?\s*n\s*=\s*(-?\d+)\s*,\s*-?\d+\s*,", re.I),
     "enumeration"),
    # "for n = 3, 4, ..." without the quantifier word
    (re.compile(r"\bn\s*=\s*(-?\d+)\s*,\s*-?\d+\s*,\s*\.\.\.", re.I),
     "enumeration"),
]


def domain_of(sentence: str):
    """
    Return (kind, threshold) where the claim asserts P(n) for every n > threshold,
    or ('refuse', reason) if the domain cannot be established.

    A returned threshold is always normalised to STRICT: n > threshold.
    """
    s = " ".join(sentence.split())

    blocker = NOT_A_SIMPLE_THRESHOLD.search(s)
    if blocker:
        return ("refuse", f"domain is not a simple threshold "
                          f"(matched {blocker.group(0)!r})")

    for rx, kind in THRESHOLDS:
        m = rx.search(s)
        if not m:
            continue
        if kind == "inequality":
            op, k = m.group(1), int(m.group(2))
            return ("threshold", k if op == ">" else k - 1)
        return ("threshold", int(m.group(1)) - 1)   # enumeration starts AT k

    # No domain stated at all. This is the dangerous case: it may genuinely
    # mean "for every n", or the author may have left it implicit. Callers get
    # it flagged rather than silently treated as the whole sequence.
    return ("unbounded", None)


def selftest():
    print("=" * 74)
    print("CLAIM DOMAIN EXTRACTOR — regression tests from real false positives")
    print("=" * 74)
    print("Each case below produced a false counterexample earlier in this")
    print("project. All five must now be handled.\n")

    cases = [
        # (sentence, expected kind, expected threshold, which incident)
        ("Conjecture: a(n) > 0 for all n > 1.", "threshold", 1, "A303656/A308734"),
        ("Conjecture: a(n)>0 for all n=3,4,...", "threshold", 2, "A208243/A218654"),
        ("Conjecture: a(n) > 0 for every n = 20, 21, ... .", "threshold", 19, "A236241"),
        ("Conjecture: a(n)>0 for all n>1 with the only exception n=8.",
         "refuse", None, "A218585"),
        ("Conjecture: a(n) > 0 for all even n > 8012 and odd n > 15727.",
         "refuse", None, "A219055/A219185"),
        ("A231692 includes a proof that a(n) is never 0 for n > 1.",
         "threshold", 1, "A232111"),
        ("Conjecture: a(n) > 0.", "unbounded", None, "no domain stated"),
        ("Conjecture: a(n) > 0 for sufficiently large n.", "refuse", None, "asymptotic"),
        ("Conjecture: a(n) > 0 if n is not a power of 2.", "refuse", None, "conditional"),
        ("Conjecture: a(n) > 0 for n >= 5.", "threshold", 4, "inclusive form"),
    ]
    ok = 0
    for sent, want_kind, want_thr, incident in cases:
        kind, val = domain_of(sent)
        good = kind == want_kind and (want_kind != "threshold" or val == want_thr)
        ok += good
        shown = f"{kind}" + (f" n>{val}" if kind == "threshold" else "")
        print(f"  [{'PASS' if good else 'FAIL'}] {incident:20s} -> {shown}")
        if not good:
            print(f"         {sent[:66]}")
            print(f"         expected {want_kind} {want_thr}, got {kind} {val}")
    print(f"\n  {ok}/{len(cases)} passed")
    return ok == len(cases)


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
