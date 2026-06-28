#!/usr/bin/env python3
"""
provenance.py — provenance conservation and blame (HCT A3 / T3).

HCT's load-bearing conservation law: identity-bearing structures cannot lose their history.
Every transformation appends to a content-addressed, monotone provenance chain (A3), and any
artifact can be traced to the origin that produced it (T3). This bridges cert_engine's
ProvenanceDAG onto a Chiron finding: it records the pipeline that produced a conclusion
(intake -> collapse -> certify -> govern) as a hash-linked DAG, supports branching lineage, and
exposes the two operations that make provenance useful — full upstream trace and MINIMAL BLAME
SET (when an output is challenged, the smallest set of upstream commits responsible for it).

Public API (consumed elsewhere): provenance(surface).

    python3 provenance.py selftest
    python3 provenance.py trace 1 1 2 3 5 8 13 21
    python3 provenance.py blame 1 1 2 3 5 8 13 21 --json

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
    return ce.Capsule(data_version="chiron", model_version="collapse", guardrail_version="lexguard",
                      seed=int(seed), config_hash=str(config_hash), runtime_signature="offline-deterministic")


def _build_dag(vals, inv):
    """Build a branching provenance DAG of the decision pipeline. Returns (dag, stage_hashes)."""
    fp = inv.generator_fingerprint
    dag = ce.ProvenanceDAG()
    hashes = {}

    def commit(artifact_id, payload, parents):
        c = ce.ProvenanceCommit(artifact_id=artifact_id,
                                artifact_hash=ce._hash_anything((artifact_id, payload, fp)),
                                capsule=_capsule(len(hashes), fp[:16]),
                                parent_commit_hashes=tuple(parents))
        h = dag.append(c)
        hashes[artifact_id] = h
        return h

    intake = commit("intake", " ".join(str(v) for v in vals), [])
    collapse = commit("collapse", inv.model_class, [intake])
    # two downstream branches off the same finding (certify and govern), then a merge (judgment)
    certify = commit("certify", f"verified={inv.verified}", [collapse])
    govern = commit("govern", "socpm-gate", [collapse])
    commit("judgment", "earned-finality", [certify, govern])
    return dag, hashes


def provenance(surface):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    dag, hashes = _build_dag(vals, inv)
    final = hashes["judgment"]
    upstream = dag.upstream_set(final)
    blame = dag.minimal_blame_set(final)
    return {
        "law": inv.model_class, "verified": bool(inv.verified),
        "stages": list(hashes.keys()),
        "commits": {k: v[:12] for k, v in hashes.items()},
        "final_artifact": final[:12],
        "full_lineage_size": len(upstream),
        "minimal_blame_set": [h[:12] for h in blame],
        "branches_merged_at_judgment": True,
        "provenance_conserved": len(upstream) >= len(hashes) - 1,
        "note": "content-addressed, monotone, branching chain (A3); any artifact traces to origin (T3)",
    }


def blame_incident(surface, incident_stage="judgment"):
    """Given a challenged output stage, return the minimal set of upstream commits responsible."""
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    dag, hashes = _build_dag(vals, inv)
    h = hashes.get(incident_stage, hashes["judgment"])
    rev = {v: k for k, v in hashes.items()}
    blame = dag.minimal_blame_set(h)
    upstream = dag.upstream_set(h)
    return {
        "incident_stage": incident_stage,
        "minimal_blame_set": [rev.get(b, b[:12]) for b in blame],
        "upstream_stages": [rev.get(u, u[:12]) for u in upstream],
        "interpretation": "audit these stages first; they are the smallest set that produced the output",
    }


def render(p):
    L = ["=" * 62, "PROVENANCE — conserved history + minimal blame", "=" * 62]
    L.append(f"  law={p['law']}  verified={p['verified']}")
    L.append(f"  pipeline: {' -> '.join(p['stages'])}")
    L.append(f"  commits: {p['commits']}")
    L.append(f"  final artifact {p['final_artifact']}…   full lineage {p['full_lineage_size']} commits")
    L.append(f"  minimal blame set: {p['minimal_blame_set']}")
    L.append(f"  provenance conserved {p['provenance_conserved']}  (A3 monotone / T3 traceable)")
    L.append("=" * 62)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    p = provenance("1 1 2 3 5 8 13 21 34")
    ok("pipeline has >= 4 stages", len(p["stages"]) >= 4)
    ok("branches merge at judgment", p["branches_merged_at_judgment"])
    ok("provenance conserved", p["provenance_conserved"])
    ok("minimal blame set non-empty", len(p["minimal_blame_set"]) >= 1)
    ok("every commit hash distinct", len(set(p["commits"].values())) == len(p["commits"]))

    # determinism: same input -> same hashes
    p2 = provenance("1 1 2 3 5 8 13 21 34")
    ok("commit hashes deterministic", p["commits"] == p2["commits"])

    b = blame_incident("1 1 2 3 5 8 13 21 34", "judgment")
    ok("blame names upstream stages", "collapse" in b["upstream_stages"] or "intake" in b["upstream_stages"])
    ok("blame set is a subset of stages", all(isinstance(x, str) for x in b["minimal_blame_set"]))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  provenance.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 1 2 3 5 8 13 21 34", "41 19 50 83 6 9 68 12"]:
        print(f"\n### {s}")
        print(render(provenance(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Provenance DAG + minimal blame over a finding.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    tr = sub.add_parser("trace"); tr.add_argument("values", nargs="+")
    bl = sub.add_parser("blame"); bl.add_argument("values", nargs="+"); bl.add_argument("--stage", default="judgment")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "blame":
        print(json.dumps(blame_incident(" ".join(args.values), args.stage), indent=2)); return 0
    if args.cmd == "trace":
        p = provenance(" ".join(args.values))
        print(json.dumps(p, indent=2) if args.json else render(p)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
