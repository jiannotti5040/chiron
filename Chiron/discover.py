#!/usr/bin/env python3
"""
Cross-domain discovery — find surfaces that share ONE generator across different
domains (the same rule wearing two disguises).

    python3 discover.py                       # a built-in mixed-domain corpus
    python3 discover.py "1 2 1 2 1 2" "abab" "10 20 10 20"   # your own surfaces
    python3 discover.py --json ...

Each surface is collapsed to its generator, reduced to a domain-agnostic structural
skeleton, and grouped. A group that contains more than one domain is a cross-domain
twin: numeric, string, and code surfaces the engine has proven share one rule.
"""
import os
import sys
import json
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import collapse, _structural_class  # noqa: E402

DEFAULT = [
    "1 2 1 2 1 2 1 2",          # numeric, period 2
    "abababab",                  # string, period 2  -> twin of the above
    "3 1 4 3 1 4 3 1 4",        # numeric, period 3
    "xyzxyzxyz",                 # string, period 3  -> twin
    "2 4 6 8 10 12 14",         # numeric, arithmetic
    "5 10 15 20 25 30 35",      # numeric, arithmetic -> twin
    "0 1 1 2 3 5 8 13",         # numeric, linear recurrence
    "racecar",                   # string, mirror symmetry
]


def _surface(raw):
    """Parse a token string as a numeric sequence if possible, else a string."""
    parts = str(raw).replace(",", " ").split()
    try:
        nums = [int(p) if float(p).is_integer() else float(p) for p in parts]
        if len(nums) >= 3:
            return nums
    except ValueError:
        pass
    return str(raw)


def analyze(raws):
    items = []
    for raw in raws:
        surf = _surface(raw)
        inv = collapse(surf)
        items.append({
            "input": raw,
            "domain": inv.domain,
            "model_class": inv.model_class,
            "verified": bool(inv.verified),
            "skeleton": _structural_class(inv) if inv.verified else None,
        })
    groups = defaultdict(list)
    for it in items:
        if it["skeleton"]:
            groups[it["skeleton"]].append(it)
    twins = []
    for skel, members in groups.items():
        domains = {m["domain"] for m in members}
        if len(members) > 1:
            twins.append({"skeleton": skel, "cross_domain": len(domains) > 1,
                          "domains": sorted(domains),
                          "members": [m["input"] for m in members]})
    twins.sort(key=lambda t: (not t["cross_domain"], t["skeleton"]))
    return {"items": items, "twins": twins,
            "cross_domain_twins": sum(1 for t in twins if t["cross_domain"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surfaces", nargs="*", help="surfaces; numeric sequences or strings")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    raws = args.surfaces or DEFAULT
    out = analyze(raws)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0
    print("=" * 68)
    print("CROSS-DOMAIN DISCOVERY")
    print("=" * 68)
    print("\nSurfaces collapsed:")
    for it in out["items"]:
        skel = it["skeleton"] or "— (abstained)"
        print("  %-22s %-9s %-22s %s" % (it["input"][:22], it["domain"],
                                         it["model_class"], skel))
    print("\nShared generators:")
    if not out["twins"]:
        print("  (none)")
    for t in out["twins"]:
        tag = "CROSS-DOMAIN" if t["cross_domain"] else "same-domain"
        print("  [%s] skeleton '%s' across %s" % (tag, t["skeleton"], ", ".join(t["domains"])))
        for m in t["members"]:
            print("        - %s" % m)
    print("\n%d cross-domain twin group(s): one proven rule, different domains."
          % out["cross_domain_twins"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
