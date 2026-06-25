#!/usr/bin/env python3
"""
Certify a Chiron finding (B-3).

Chiron carries the full certification depth (Daubert / FRE 702 / FRCP 26 analysis,
attestation, the certificate format) but only runs it on a JDICert DecisionContext.
This bridges it onto a `collapse()` finding: recover the rule, build the certificate,
and run the legal-admissibility analysis over it.

    python3 certify_finding.py "1 1 2 3 5 8 13"
    python3 certify_finding.py --json "2 4 8 16 32"

Framing dial — civilian: high-stakes decision assurance for a recovered conclusion.
Contractor: a Daubert-admissible, attested certificate for an autonomous-decision step.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiron  # noqa: E402


def _nums(s):
    parts = str(s).replace(",", " ").split()
    try:
        return [int(x) if float(x).is_integer() else float(x) for x in parts]
    except ValueError:
        return None


def certify_finding(surface):
    nums = _nums(surface)
    inv = chiron.collapse(nums if nums else str(surface))
    d = inv.to_dict()
    hr = chiron.human_report(inv)
    cert = {
        "sections": [
            {"title": "Recovery", "content": {"model_class": d["model_class"],
                                              "verified": d["verified"],
                                              "compression_ratio": d["compression_ratio"]}},
            {"title": "Belief", "content": hr["human_view"]},
            {"title": "Machine View", "content": hr["machine_view"]},
            {"title": "Residual", "content": {"residual": d["residual"]}},
        ],
        "merkle_root": chiron.org_sha(d),
        "replay_seed": str(surface),                       # re-running collapse reproduces it
        "governance_timeline": [{"phase": "recovery", "policy_intact": True}],
    }
    adm = chiron.analyze_legal_admissibility(cert)
    return {"finding": d, "human_report": hr, "certificate": cert, "admissibility": adm}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surface", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = certify_finding(" ".join(args.surface))
    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0
    d = out["finding"]
    adm = out["admissibility"]
    overall = adm.get("overall_assessment") or adm.get("overall") or "—"
    deployable = adm.get("court_deployable", adm.get("deployable", "—"))
    findings = adm.get("daubert_findings", adm.get("daubert", []))
    sat = sum(1 for f in findings if str(f.get("finding", "")).startswith("satisf"))
    print("=" * 62)
    print("CERTIFY A FINDING — recovery + legal-admissibility analysis")
    print("=" * 62)
    print("  recovered ........ %s   verified=%s" % (d["model_class"], d["verified"]))
    print("  merkle root ...... %s" % out["certificate"]["merkle_root"][:24])
    print("  replay seed ...... present (re-run collapse to reproduce)")
    print("  Daubert factors .. %d/%d satisfied" % (sat, len(findings)))
    print("  overall .......... %s" % overall)
    print("  court-deployable . %s" % deployable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
