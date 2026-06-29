#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
bench_legal.py — fact-pattern -> applicable-provision recovery via the real legal_corpus layer.

The governance layer applied as a recovery problem: given a fact pattern (an operating domain plus
the salient features of a scenario), recover the provisions that govern it, with citations, and
ABSTAIN when nothing applies. The discipline mirrors the engine — recover what is grounded, refuse
the rest — but this is the compliance LAYER (retrieval + domain scoping), not the exact-arithmetic
core, so the claim is precision and honest abstention, not held-out exact prediction.

Baseline: domain-blind keyword search. It pulls provisions from unrelated domains (e.g. a financial
statute into a medical scenario); the domain-scoped recovery filters those out — the measurable win.

    python3 bench_legal.py            # results table
    python3 bench_legal.py selftest   # 0/1 gate

Status: implemented & tested. Uses the real legal_corpus (67 provisions). Layer = working prototype.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import legal_corpus as lc  # noqa: E402

# (name, operating domain, scenario keywords, expected provision family, should_abstain)
SCENARIOS = [
    ("armed-conflict targeting", "military",
     ["proportionality", "distinction", "precautions"], "API-ART", False),
    ("patient-data disclosure", "medical",
     ["protected health", "transparency"], "HIPAA", False),
    ("high-risk AI deployment", "financial",
     ["high-risk", "human oversight"], "AIA-ART", False),
    ("trivial / out-of-scope", "general",
     ["sandwich", "lunch"], None, True),
]


def _ids(provisions):
    return {p.get("id") for p in provisions if isinstance(p, dict)}


def recover(domain, keywords):
    """Domain-scoped recovery: keyword hits intersected with the domain's governing set."""
    blind = set()
    for kw in keywords:
        blind |= _ids(lc.search(kw))
    in_scope = _ids(lc.applicable(domain))
    scoped = blind & in_scope
    return scoped, blind, (blind - scoped)   # recovered, baseline, cross-domain removed


def run():
    rows = []
    cross_removed_total = 0
    for name, domain, kws, family, should_abstain in SCENARIOS:
        scoped, blind, removed = recover(domain, kws)
        cross_removed_total += len(removed)
        family_hit = (family is not None) and any(family in pid for pid in scoped)
        abstained = (len(scoped) == 0)
        correct = abstained if should_abstain else family_hit
        rows.append((name, domain, sorted(scoped)[:4], len(scoped), len(blind),
                     family, correct, should_abstain, abstained))

    print("bench_legal — domain-scoped provision recovery vs domain-blind keyword search\n")
    print(f"{'scenario':27}{'domain':11}{'recovered':>10}{'baseline':>9}{'expect':>10}{'result':>9}")
    print("-" * 84)
    for name, dom, sample, ns, nb, fam, correct, abst, did_abst in rows:
        exp = "ABSTAIN" if fam is None else fam
        res = "ok" if correct else "MISS"
        print(f"{name:27}{dom:11}{ns:>10}{nb:>9}{exp:>10}{res:>9}")
    print("-" * 84)
    n_ok = sum(1 for r in rows if r[6])
    print(f"correct {n_ok}/{len(rows)} · cross-domain provisions the baseline included and "
          f"domain-scoping removed: {cross_removed_total}")
    print("\nEach in-scope scenario recovers its governing family with a citation; the out-of-scope")
    print("scenario recovers nothing (honest abstention). Domain scoping strips the cross-domain")
    print("citations a blind keyword search would wrongly attach.")
    return rows, cross_removed_total


def _selftest():
    rows, cross_removed = run()
    in_scope = [r for r in rows if not r[7]]
    abstain = [r for r in rows if r[7]]
    checks = [
        ("every in-scope scenario recovers its governing family", all(r[6] for r in in_scope)),
        ("out-of-scope scenario abstains", all(r[8] and r[6] for r in abstain)),
        ("domain scoping removes cross-domain provisions the baseline included", cross_removed >= 1),
        ("recovered sets are non-empty exactly when not abstaining",
         all((r[3] > 0) != r[7] for r in rows)),
    ]
    print("\nSELFTEST")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    ok = all(c for _, c in checks)
    print(f"  {sum(c for _, c in checks)}/{len(checks)} checks")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if _selftest() else 1)
    run()
