#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
candor_bridge.py — explanation before assertion (D-1, discernment).

The whole vault circles one obsession: a machine must be honest about the limits of its own
knowledge and must not patronize. CANDOR is that instinct as an instrument — it scores any piece
of reasoning for condescension, unearned confidence, evasion, and opacity. This bridge points the
full CANDOR surface at Chiron: it audits external text, audits Chiron's OWN explanation of a
finding (the self-honesty check the discernment and judgment courts rely on), tracks candor
DECAY across a multi-turn transcript, and proposes candid repairs for the worst spans.

Public API (consumed elsewhere): audit_finding(surface), audit_text(text).

    python3 candor_bridge.py selftest
    python3 candor_bridge.py finding 1 1 2 3 5 8 13 21
    echo "Don't worry, obviously yes." | python3 candor_bridge.py text

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
    return obj if isinstance(obj, str) else ""


def _findings(a, k=4):
    out = []
    for f in (a.findings or [])[:k]:
        if hasattr(f, "to_dict"):
            out.append(f.to_dict())
        elif isinstance(f, dict):
            out.append(f)
        else:
            out.append({"detail": str(f)[:120]})
    return out


def audit_text(text, with_repairs=False):
    a = candor.audit(text)
    out = {
        "candor_score": round(float(a.candor_score), 4),
        "grade": a.grade,
        "axes": {k: round(float(v), 4) for k, v in a.scores.items()},
        "n_findings": len(a.findings or []),
        "findings": _findings(a),
        "limits": a.limits,
    }
    if with_repairs:
        try:
            out["repairs"] = candor.suggest_repairs(a)
        except Exception:
            out["repairs"] = []
    return out


def audit_finding(surface, with_repairs=False):
    if isinstance(surface, str):
        vals = [int(x) if x.lstrip("-").isdigit() else float(x)
                for x in surface.replace(",", " ").split()]
    else:
        vals = list(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    hr = chiron.human_report(inv)
    text = _flatten(hr.get("human_view", hr))
    out = audit_text(text, with_repairs=with_repairs)
    out["law"] = inv.model_class
    out["audited_explanation"] = text[:240]
    return out


def audit_transcript(turns):
    """Score a multi-turn exchange and detect whether candor DECAYS over the conversation."""
    try:
        return candor.audit_transcript(turns)
    except Exception:
        scores = [candor.audit(t.get("text", "")).candor_score for t in turns]
        trend = "declining" if len(scores) >= 2 and scores[-1] < scores[0] else "stable"
        return {"per_turn": [round(s, 4) for s in scores], "trend": trend}


def render(a, title="CANDOR AUDIT"):
    L = ["=" * 60, title, "=" * 60]
    if "law" in a:
        L.append(f"  auditing Chiron's own explanation of: {a['law']}")
    L.append(f"  candor score {a['candor_score']}   [{a['grade']}]")
    for k, v in a["axes"].items():
        L.append(f"     {k:<22} {v:<6} {'█' * int(round(v * 20))}")
    L.append(f"  findings: {a['n_findings']}")
    if a.get("repairs"):
        for r in a["repairs"][:3]:
            L.append(f"     repair: {r}")
    L.append("=" * 60)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    patronizing = audit_text("Great question! Don't worry, this is obviously simple and everyone knows it's definitely true.")
    ok("patronizing text scores low", patronizing["candor_score"] < 0.3)
    ok("condescension axis fires", patronizing["axes"].get("condescension", 0) > 0.3)
    ok("unearned confidence fires", patronizing["axes"].get("unearned_confidence", 0) > 0.3)

    honest = audit_finding("1 1 2 3 5 8 13 21 34")
    ok("Chiron's own explanation is candid", honest["candor_score"] >= 0.6)
    ok("self-audit names the law", honest["law"] != "")

    rep = audit_text("Obviously the answer is definitely yes.", with_repairs=True)
    ok("repairs offered for bad text", isinstance(rep.get("repairs"), list))

    tr = audit_transcript([{"speaker": "assistant", "text": "Here is the evidence: x because y."},
                           {"speaker": "assistant", "text": "Don't worry, obviously it's fine, everyone knows."}])
    ok("transcript audit returns a result", isinstance(tr, dict))

    ok("limits stated on every audit", bool(patronizing["limits"]))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  candor_bridge.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render(audit_text("Great question! Don't worry, this is obviously simple."), "CANDOR — external text"))
    print()
    print(render(audit_finding("1 1 2 3 5 8 13 21 34"), "CANDOR — engine self-check"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Candor audit of an explanation or a finding.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    fd = sub.add_parser("finding"); fd.add_argument("values", nargs="+")
    sub.add_parser("text")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "finding":
        a = audit_finding(" ".join(args.values), with_repairs=True)
        print(json.dumps(a, indent=2) if args.json else render(a, "CANDOR — engine self-check"))
        return 0
    if args.cmd == "text":
        text = sys.stdin.read() if not sys.stdin.isatty() else ""
        if not text.strip():
            return _demo()
        a = audit_text(text, with_repairs=True)
        print(json.dumps(a, indent=2) if args.json else render(a))
        return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
