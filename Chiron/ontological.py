#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
ontological.py — value and coherence as measured quantities.

The axiological floor: V-Units (how much value a recovered structure carries) and the Harmony
Functional (how coherent a set of measures is). These are operationalizations — value and
coherence read off the quantities Chiron already produces (verification, compression saturation,
residual) — not transcriptions of a metaphysics. Honest by construction: a recovered exact law
scores high V; structureless noise scores low; and harmony is unforgiving (one incoherent
component drags the whole down).

Public API (consumed elsewhere): v_units(surface), harmony(values).

    python3 ontological.py selftest
    python3 ontological.py value 1 1 2 3 5 8 13 21
    python3 ontological.py compare "1 2 4 8 16" "41 19 50 83 6 9"

Framing dial — civilian: value & coherence scoring of evidence. Contractor: mission-value &
concordance scoring across findings.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402


def _nums(s):
    if isinstance(s, str):
        s = s.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in s]


def value_components(surface):
    """The three components of a recovered structure's value, each in [0,1]."""
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    verified = 1.0 if inv.verified else 0.0
    cr = float(inv.compression_ratio)
    saturation = max(0.0, min(1.0, 1.0 - 1.0 / max(1.0, cr)))
    resid = len(getattr(inv, "residual", []) or [])
    fidelity = max(0.0, 1.0 - resid / max(1, len(vals)))
    return inv, {"verification": round(verified, 4), "compression_saturation": round(saturation, 4),
                 "fidelity": round(fidelity, 4)}


def v_units(surface):
    inv, comp = value_components(surface)
    V = sum(comp.values()) / len(comp)
    return {"surface": str(surface)[:40], "model_class": inv.model_class,
            "verified": bool(inv.verified), "V_units": round(float(V), 4),
            "components": comp}


def harmony(values):
    """Coherence of a set of measures: 1 - normalized dispersion. Unforgiving toward outliers."""
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return 1.0
    m = sum(vals) / len(vals)
    if m == 0:
        m = 1e-9
    dispersion = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5 / (abs(m) + 1e-9)
    return round(max(0.0, 1.0 - min(1.0, dispersion)), 4)


def assess(surface):
    v = v_units(surface)
    h = harmony(list(v["components"].values()))
    v["harmony"] = h
    v["fundamental"] = bool(v["V_units"] >= 0.6 and h >= 0.6)
    return v


def compare(surfaces):
    rows = [{"surface": s if isinstance(s, str) else " ".join(map(str, s)),
             "V_units": v_units(s)["V_units"]} for s in surfaces]
    rows.sort(key=lambda r: -r["V_units"])
    return rows


def render(v):
    L = ["=" * 56, "ONTOLOGICAL — V-Units + Harmony", "=" * 56]
    L.append(f"  {v['model_class']} (verified={v['verified']})")
    L.append(f"  components: {v['components']}")
    L.append(f"  V-Units {v['V_units']}   Harmony {v.get('harmony')}   fundamental={v.get('fundamental')}")
    L.append("=" * 56)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    law = v_units("1 1 2 3 5 8 13 21 34")
    noise = v_units("41 19 50 83 6 9 68 12")
    ok("verified law high V", law["V_units"] >= 0.6)
    ok("noise low V", noise["V_units"] < 0.5)
    ok("law V > noise V", law["V_units"] > noise["V_units"])
    ok("three value components", len(law["components"]) == 3)
    ok("components in [0,1]", all(0 <= c <= 1 for c in law["components"].values()))

    ok("harmony of equal values = 1", harmony([0.9, 0.9, 0.9]) == 1.0)
    ok("harmony penalizes an outlier", harmony([0.9, 0.9, 0.1]) < 0.7)
    ok("harmony of single value = 1", harmony([0.5]) == 1.0)

    a = assess("2 4 6 8 10 12")
    ok("fundamental flag computed", isinstance(a["fundamental"], bool))
    c = compare(["1 2 4 8 16 32", "41 19 50 83 6 9"])
    ok("compare ranks law above noise", c[0]["V_units"] >= c[-1]["V_units"])

    passed = sum(1 for _, ck in checks if ck)
    for n, ck in checks:
        if not ck:
            print(f"  FAIL: {n}")
    print(f"  ontological.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 1 2 3 5 8 13 21 34", "2 4 6 8 10 12", "41 19 50 83 6 9 68 12"]:
        print(render(assess(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="V-Units + Harmony over a finding.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    va = sub.add_parser("value"); va.add_argument("values", nargs="+")
    cm = sub.add_parser("compare"); cm.add_argument("surfaces", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "compare":
        print(json.dumps(compare(args.surfaces), indent=2)); return 0
    if args.cmd == "value":
        a = assess(" ".join(args.values))
        print(json.dumps(a, indent=2) if args.json else render(a)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
