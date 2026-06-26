#!/usr/bin/env python3
"""
candor_bridge.py — explanation before assertion (D-1, discernment).

The whole vault circles one obsession: a machine must be honest about the limits of its own
knowledge and must not patronize. CANDOR is that instinct as an instrument — it scores any
piece of reasoning for condescension, unearned confidence, evasion, and opacity. This bridge
points it at Chiron's OWN output: it audits the human-readable explanation a finding produces
and confirms the engine speaks candidly (what was found, why it is believed, what would
falsify it) — and it audits any external text on demand.

A discernment engine's primary product is an explanation that survives examination. This is
the check that the explanation is candid before it is trusted.

    python3 candor_bridge.py --demo
    python3 candor_bridge.py --finding "1 1 2 3 5 8 13 21"
    echo "Great question! Don't worry, obviously yes." | python3 candor_bridge.py

Framing dial — civilian: honesty / anti-patronization audit of any explanation. Contractor:
candor gate on machine-generated reporting before it reaches a decision-maker.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "Candor"))
import chiron          # noqa: E402
import candor          # noqa: E402


def _flatten(obj):
    if isinstance(obj, dict):
        return " ".join(_flatten(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return " ".join(_flatten(v) for v in obj)
    return str(obj) if isinstance(obj, str) else ""


def audit_text(text):
    a = candor.audit(text)
    return {
        "candor_score": round(float(a.candor_score), 4),
        "grade": a.grade,
        "axes": {k: round(float(v), 4) for k, v in a.scores.items()},
        "n_findings": len(a.findings),
        "limits": a.limits,
    }


def audit_finding(surface):
    if isinstance(surface, str):
        vals = [int(x) if x.lstrip("-").isdigit() else float(x)
                for x in surface.replace(",", " ").split()]
    else:
        vals = list(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    hr = chiron.human_report(inv)
    text = _flatten(hr.get("human_view", hr))
    out = audit_text(text)
    out["law"] = inv.model_class
    out["audited_explanation"] = text[:240]
    return out


def render(a, title="CANDOR AUDIT"):
    L = ["=" * 60, title, "=" * 60]
    if "law" in a:
        L.append(f"  auditing Chiron's own explanation of: {a['law']}")
    L.append(f"  candor score .. {a['candor_score']}   [{a['grade']}]")
    for k, v in a["axes"].items():
        bar = "█" * int(round(v * 20))
        L.append(f"     {k:<22} {v:<6} {bar}")
    L.append(f"  findings: {a['n_findings']}")
    L.append("=" * 60)
    return "\n".join(L)


def _demo():
    print("### a patronizing answer (should score deeply uncandid)")
    print(render(audit_text("Great question! Don't worry, this is obviously simple and everyone knows it's definitely true."),
                 "CANDOR AUDIT — external text"))
    print("\n### Chiron's own explanation of a verified finding (should stay candid)")
    print(render(audit_finding("1 1 2 3 5 8 13 21 34"), "CANDOR AUDIT — engine self-check"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Candor audit of an explanation or a finding.")
    ap.add_argument("--finding", default=None, help="audit Chiron's explanation of this surface")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.demo:
        return _demo()
    if args.finding:
        a = audit_finding(args.finding)
        print(json.dumps(a, indent=2) if args.json else render(a, "CANDOR AUDIT — engine self-check"))
        return 0
    text = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not text.strip():
        return _demo()
    a = audit_text(text)
    print(json.dumps(a, indent=2) if args.json else render(a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
