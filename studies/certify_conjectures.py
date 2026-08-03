#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
certify_conjectures.py — LEGACY / QUARANTINED math-artifact generator.

Author: Jacob Iannotti. Apache-2.0.

WHY THIS EXISTS. The conjecture campaign was built as ~17 standalone Python
scripts that never touched the vault's own engines. That is "some scripts",
not Chiron. Meanwhile JDICert/cert_engine.py -- 12,909 lines, 693 functions,
280/280 embedded tests passing -- sat unused, and its data model turns out to
be an exact fit for exactly this problem:

    KUOmegaPartition   K = what was exactly proven
                       U = what remains unknown, CLASSIFIED by why
    MysteryClass.XI_INFINITY      an unbounded quantifier -- the reason a
                                  bounded search can never settle a conjecture
    MysteryClass.XI_IGNORANCE     prior art not established
    Stratum.X_5_SYMBOLIC          mathematics
    Verdict.ESCALATE_HUMAN        cannot auto-approve; a human must decide

The engine already encodes the distinction this campaign spent all night
enforcing by hand: a bounded verification is a FACT, and the general statement
is an UNKNOWN of a specific kind. XI_INFINITY is that kind.

QUARANTINE NOTICE. This file serializes hand-authored prose into a governance
engine; it does not replay the computation or bind evidence to source and code
revisions. Its prior JSON files in ``studies/certificates/`` are historical,
non-evidentiary artifacts. The generator now refuses rather than creating more
of them. Use a target-specific executable research capsule for new evidence.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

VAULT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VAULT / "JDICert"))
import cert_engine as C  # noqa: E402

OUT = Path(__file__).resolve().parent / "certificates"


# ---------------------------------------------------------------------------
# The campaign's results, stated exactly as measured.
#   facts   : (id, statement, source, certainty, kind)
#   unknowns: (id, statement, MysteryClass)
# ---------------------------------------------------------------------------

RESULTS = [
    dict(
        cid="ERDOS-BASE3",
        title="Erdos (1979): for n > 8, 2^n contains the digit 2 in base 3",
        facts=[
            ("K1", "Encoder reproduces the known exceptions exactly: n in {0,2,8}, "
                   "i.e. 1, 4 and 256 are the only powers of 2 that are sums of "
                   "distinct powers of 3", "encoder validation", 1.0, "computational"),
            ("K2", "The low-64-base-3-digit shortcut agrees with full base-3 "
                   "expansion on n = 0..2999", "cross-method validation", 1.0,
             "computational"),
            ("K3", "No counterexample exists for 8 < n <= 1,000,000,000",
             "exhaustive search, exact integer arithmetic", 1.0, "computational"),
        ],
        unknowns=[
            ("U1", "Whether the statement holds for all n; the quantifier is "
                   "unbounded and no finite search can settle it",
             C.MysteryClass.XI_INFINITY),
            ("U2", "Whether this bound exceeds unpublished prior work; the "
                   "conjecture is equivalent to BB(15) halting and has been "
                   "studied by Sterin-Woods", C.MysteryClass.XI_IGNORANCE),
        ],
    ),
    dict(
        cid="A300362",
        title="Sun A300362: a(n) > 0 for all n, where a(n) counts "
              "n^2 = x^2+y^2+z^2+w^2 with x+2y and (z+2w)/3 square, w even",
        facts=[
            ("K1", "Encoder reproduces published representation counts for "
                   "n = 0..25 exactly", "OEIS b-file cross-check", 1.0,
             "computational"),
            ("K2", "a(n) > 0 for every n from 1001 to 13,264",
             "exhaustive meet-in-the-middle, exact integers", 1.0, "computational"),
            ("K3", "The published b-file covers only n <= 1000",
             "OEIS b-file inspection", 1.0, "provenance"),
        ],
        unknowns=[
            ("U1", "Whether a(n) > 0 for all n; unbounded quantifier",
             C.MysteryClass.XI_INFINITY),
            ("U2", "Whether the range 1001..13264 is genuinely unswept; Sun "
                   "routinely computes past what he publishes and no bound is "
                   "stated in the entry", C.MysteryClass.XI_IGNORANCE),
        ],
    ),
    dict(
        cid="A302920",
        title="Sun A302920: for any prime p, p^2 = x^2 + 2y^2 + 3*2^z",
        facts=[
            ("K1", "The x^2+2y^2 representability criterion (discriminant -8) "
                   "agrees with brute force on R = 0..4000",
             "cross-method validation", 1.0, "computational"),
            ("K2", "Encoder positivity matches the published terms for the "
                   "first 40 primes", "OEIS b-file cross-check", 1.0,
             "computational"),
            ("K3", "A representation exists for every prime from index 6,000 to "
                   "84,189 (p = 1,079,009)", "exhaustive search", 1.0,
             "computational"),
            ("K4", "The entry records a COMPOSITE with no representation: "
                   "m = 5884015571 = 7*17*49445509", "OEIS entry comment", 1.0,
             "provenance"),
        ],
        unknowns=[
            ("U1", "Whether a representation exists for every prime; unbounded",
             C.MysteryClass.XI_INFINITY),
            ("U2", "Whether primes beyond index 84,189 are unswept",
             C.MysteryClass.XI_IGNORANCE),
        ],
    ),
    dict(
        cid="A261303-RETRACTED",
        title="Sun/Cloitre A261303: a(n) = 0 implies 3n+2 is prime "
              "[NOVELTY CLAIM RETRACTED]",
        facts=[
            ("K1", "Encoder reproduces all 80 published terms exactly",
             "OEIS cross-check", 1.0, "computational"),
            ("K2", "Every zero encountered up to n = 1,221,434,486 produced a "
                   "prime; 14 zeros seen", "exhaustive search", 1.0,
             "computational"),
            ("K3", "A186255 publishes the zero indices out to "
                   "362,950,400,494,627, roughly 300,000x beyond this run",
             "OEIS cross-reference", 1.0, "provenance"),
            ("K4", "The novelty claim made for this result was FALSE and was "
                   "retracted; the computation stands, the claim did not",
             "self-audit", 1.0, "procedural"),
        ],
        unknowns=[
            ("U1", "Whether the implication holds for all n; unbounded",
             C.MysteryClass.XI_INFINITY),
        ],
    ),
    dict(
        cid="DGG-COUNTEREXAMPLE",
        title="Dinitz-Garg-Goemans: finite computational claims of the "
              "published counterexample",
        facts=[
            ("K1", "Fractional flow feasible at cost 58; all 2^3 unsplittable "
                   "routings enumerated; cheapest congestion-admissible costs 60",
             "exhaustive enumeration, exact integers", 1.0, "computational"),
            ("K2", "Every admissible instance with b <= 25 refutes: 456 of 456",
             "exhaustive family sweep", 1.0, "computational"),
            ("K3", "15 gates pass in the vault battery", "gate battery", 1.0,
             "computational"),
        ],
        unknowns=[
            ("U1", "Provenance of the announced counterexample; not verified here",
             C.MysteryClass.XI_IGNORANCE),
            ("U2", "Minimality of the instance; not established",
             C.MysteryClass.XI_IGNORANCE),
            ("U3", "The DGG theorem itself and its peer-review status",
             C.MysteryClass.XI_TRANSCENDENCE),
        ],
    ),
    dict(
        cid="CORPUS-TRIAGE",
        title="google-deepmind/formal-conjectures: 1,171 open conjectures, "
              "every one statused",
        facts=[
            ("K1", "850 files, 3,195 tagged theorems, 1,171 open conjectures, "
                   "all processed", "systematic sweep", 1.0, "computational"),
            ("K2", "Verdicts: 564 infinitary, 329 answer-unknown, 272 "
                   "needs-Lean-semantics, 6 finite-checkable",
             "classifier output", 1.0, "computational"),
            ("K3", "The classifier never sees the corpus's own category labels "
                   "yet independently reproduces them: 215 of 302 dischargeable "
                   "obligations sit in the 18% tagged `test`",
             "calibration cross-check", 1.0, "computational"),
            ("K4", "Zero refutations found", "systematic sweep", 1.0,
             "computational"),
        ],
        unknowns=[
            ("U1", "Whether the 272 needs-Lean cases hide finite content a "
                   "better classifier would find; a later re-triage recovered "
                   "127 candidates, so the first pass was demonstrably incomplete",
             C.MysteryClass.XI_IGNORANCE),
        ],
    ),
]


def build_context(r):
    raise RuntimeError(
        "This legacy path is quarantined: it serializes asserted prose rather "
        "than replaying mathematical evidence. Use a target-specific research "
        "capsule with executable checkers instead.")

    # Historical implementation retained below only as an audit record. It is
    # unreachable by design and must not be re-enabled without a replayable
    # evidence contract.
    part = C.KUOmegaPartition()
    for fid, stmt, src, cert, kind in r["facts"]:
        part.add_fact(C.Evidence(fid, stmt, src, cert, kind))
    for uid, stmt, cls in r["unknowns"]:
        part.add_unknown(C.Unknown(uid, stmt, cls))

    geom = C.DecisionGeometry(
        primary_stratum=C.Stratum.X_5_SYMBOLIC,   # mathematics
        secondary_strata=frozenset({C.Stratum.X_4_SOCIAL}),  # published claims
        irreversibility_index=0.35,   # a retracted claim is recoverable but costly
        affected_population_estimate=0,
    )
    payload = json.dumps(r, default=str, sort_keys=True)
    prov = C.ProvenanceMetadata(
        source_system="chiron-conjecture-campaign",
        acquisition_ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        raw_hash=sha256(payload.encode()).hexdigest(),
        confidence_score=0.95,
        entropy_estimate=0.2,
        pedigree_chain=("studies/", "OEIS", "google-deepmind/formal-conjectures"),
    )
    return C.TargetContext(
        target_id=r["cid"],
        description=r["title"],
        raw_payload=payload,
        geometry=geom,
        evidence_partition=part,
        constraints=tuple(C.ConstraintFactory.build_corpus()),
        time_to_criticality=1e6,          # no time pressure on a math claim
        provenance=prov,
        domain_tag="mathematical_claim",
    )


def main():
    print("REFUSED — this legacy generator hashes hand-authored prose rather than")
    print("replaying a computation. It is quarantined from mathematical use.")
    print("Use a target-specific executable research capsule instead.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
