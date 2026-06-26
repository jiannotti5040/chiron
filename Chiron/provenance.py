#!/usr/bin/env python3
"""
provenance.py — provenance conservation and blame (HCT A3 / T3).

HCT's load-bearing conservation law: identity-bearing structures cannot lose their history.
Every transformation appends to a content-addressed, monotone provenance chain (A3), and any
artifact can be traced to the origin that produced it (T3). This bridges cert_engine's
ProvenanceDAG onto a Chiron finding: it records the pipeline that produced a conclusion
(intake -> collapse -> certify -> govern) as a hash-linked DAG, then demonstrates the two
operations that make provenance useful — full-lineage trace and MINIMAL BLAME SET (when an
output is challenged, the smallest set of upstream commits responsible for it).

This is the difference between a system that says "here is the answer" and one that says
"here is the answer, here is every step that produced it, and here is exactly what to audit
if it is wrong."

    python3 provenance.py --demo
    python3 provenance.py 1 1 2 3 5 8 13 21
    python3 provenance.py --surface "5 10 15 20 25" --json

Framing dial — civilian: end-to-end audit trail with root-cause tracing. Contractor:
tamper-evident lineage; minimal-blame attribution for incident review.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "JDICert"))
import chiron          # noqa: E402
import cert_engine as ce   # noqa: E402


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _capsule(seed, config_hash):
    return ce.Capsule(data_version="chiron", model_version="collapse",
                      guardrail_version="lexguard", seed=int(seed),
                      config_hash=str(config_hash), runtime_signature="offline-deterministic")


def provenance(surface):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    fp = inv.generator_fingerprint
    dag = ce.ProvenanceDAG()

    stages = [("intake", " ".join(str(v) for v in vals)),
              ("collapse", inv.model_class),
              ("certify", f"verified={inv.verified}"),
              ("govern", "socpm-gate")]
    hashes, parents = [], ()
    for i, (stage, payload) in enumerate(stages):
        commit = ce.ProvenanceCommit(
            artifact_id=stage,
            artifact_hash=ce._hash_anything((stage, payload, fp)),
            capsule=_capsule(seed=i, config_hash=fp[:16]),
            parent_commit_hashes=parents,
        )
        h = dag.append(commit)
        hashes.append(h)
        parents = (h,)

    final = hashes[-1]
    upstream = dag.upstream_set(final)
    blame = dag.minimal_blame_set(final)
    return {
        "law": inv.model_class,
        "verified": bool(inv.verified),
        "stages": [s for s, _ in stages],
        "commit_chain": [h[:12] for h in hashes],
        "final_artifact": final[:12],
        "full_lineage_size": len(upstream),
        "minimal_blame_set": [h[:12] for h in blame],
        "provenance_conserved": len(upstream) >= len(stages) - 1,
        "note": "content-addressed, monotone chain (A3); any artifact traces to its origin (T3)",
    }


def render(p):
    L = ["=" * 62, "PROVENANCE — conserved history + minimal blame", "=" * 62]
    L.append(f"  law={p['law']}  verified={p['verified']}")
    L.append(f"  pipeline: {' -> '.join(p['stages'])}")
    L.append(f"  commit chain: {' -> '.join(c[:8] for c in p['commit_chain'])}")
    L.append(f"  final artifact ...... {p['final_artifact']}…")
    L.append(f"  full lineage size ... {p['full_lineage_size']} commits")
    L.append(f"  minimal blame set ... {[b[:8] for b in p['minimal_blame_set']]}")
    L.append(f"  provenance conserved  {p['provenance_conserved']}  (A3 monotone / T3 traceable)")
    L.append("=" * 62)
    return "\n".join(L)


_DEMO = ["1 1 2 3 5 8 13 21 34", "41 19 50 83 6 9 68 12"]


def _demo():
    for s in _DEMO:
        print(f"\n### {s}")
        print(render(provenance(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Provenance DAG + minimal blame over a finding.")
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
    p = provenance(surface)
    print(json.dumps(p, indent=2) if args.json else render(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
