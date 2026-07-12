#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
pipeline — compose the vault's engines into whatever validation-and-check
system you need, declared as data, arbitrated by the exact gate.

The vault is a box of engines. This lets you WIRE them: run one, run several
as a team over one input, or fan a swarm across many inputs — and get back a
single signed verdict whose rule is dead simple and never a lie:

    the pipeline VERIFIES only if every required stage verified;
    any refusal or refutation makes the whole thing abstain or fail.

No stage can upgrade another's verdict; stages only carry results forward.
That is the same contract every engine already keeps, lifted to a system you
design.

A pipeline is a list of STAGES. Each stage names a COMPONENT (an engine
capability) and says whether it is `required` (default true) or advisory.
Components (all exact, all already in the vault):

    collapse        recover+prove the rule behind a numeric/string surface
    cross_examine   adversarially attack a recovered rule; report what holds
    certify         judge the checkable claims in a TEXT (VERIFIED/REFUTED/REFUSED)
    govern          clear a finding against a hardcoded regime (gate)
    candor          audit language for patronization / over-assertion

Modes:
    chain   stages run in order over ONE input; stop on a required failure
    team    every stage runs over the SAME input; verdict = AND of required
    swarm   a chain (or single component) fanned across MANY inputs

    python3 pipeline.py demo
    python3 pipeline.py selftest
    python3 pipeline.py run '{"mode":"chain","input":"1 1 2 3 5 8 13 21 34 55",
                              "stages":[{"component":"collapse"},
                                        {"component":"cross_examine"}]}'
    echo '<spec-json>' | python3 pipeline.py run -

Build specs in Python with the fluent helper:

    from pipeline import Pipeline
    result = (Pipeline("chain")
              .collapse().cross_examine()
              .run("1 1 2 3 5 8 13 21 34 55"))
    result["verified"]     # True only if every required stage verified

stdlib + the vault's own engines. Deterministic given its inputs.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── components: each maps (input) -> a normalized stage result ──────────────
# A stage result is always {ok, verified, verdict, detail}. `verified` is the
# strong claim (exact proof); `ok` means "the stage ran and did not fail its
# own contract" (a clean refusal is ok=True, verified=False).


def _c_collapse(surface: Any, **_) -> Dict[str, Any]:
    import chiron
    inv = (chiron.collapse(surface) if not _is_seq(surface)
           else chiron.collapse_numeric(_as_seq(surface)))
    v = bool(getattr(inv, "verified", False))
    return {"ok": True, "verified": v, "carry": inv,
            "verdict": ("VERIFIED %s" % inv.model_class) if v
            else ("no exact rule (%s)" % inv.model_class),
            "detail": {"model_class": inv.model_class}}


def _c_cross_examine(surface: Any, carry=None, **_) -> Dict[str, Any]:
    import cross_examine
    rep = cross_examine.cross_examine(_as_seq(surface) if _is_seq(surface) else surface)
    # cross_examine's real signal: reasonable_doubt False AND the winner was
    # itself verified. An injunction (active) is a hard stop.
    winner_ok = bool((rep.get("winner") or {}).get("verified"))
    held = winner_ok and not rep.get("reasonable_doubt", True) \
        and not (rep.get("injunction") or {}).get("active", False)
    return {"ok": not (rep.get("injunction") or {}).get("active", False),
            "verified": held, "carry": rep,
            "verdict": rep.get("verdict", "cross-examined")[:80],
            "detail": {"reasonable_doubt": rep.get("reasonable_doubt"),
                       "doubt_reasons": rep.get("doubt_reasons", [])}}


def _c_certify(text: Any, **_) -> Dict[str, Any]:
    sys.path.insert(0, os.path.normpath(os.path.join(_HERE, os.pardir, "Primus", "src")))
    from primus import certify
    cert = certify(str(text))
    cnt = cert["counts"]
    v = cnt["checkable"] > 0 and cnt["refuted"] == 0 and cnt["verified"] > 0
    return {"ok": cnt["refuted"] == 0, "verified": v, "carry": cert,
            "verdict": cert["verdict"][:120],
            "detail": {"counts": cnt, "coverage": cert["coverage"]}}


def _c_govern(surface: Any, scores: Optional[Dict] = None, **_) -> Dict[str, Any]:
    import govern
    s = scores or {"Cx": 0.2, "Ar": 0.1, "Hp": 0.1, "Mc": 0.1, "V": 0.1}
    out = govern.govern(s["Cx"], s["Ar"], s["Hp"], s["Mc"], s["V"],
                        domain=str((_ or {}).get("domain", "general")))
    cleared = str(out.get("verdict", "")).upper().startswith(("PASS", "CLEAR", "OK", "ALLOW"))
    return {"ok": True, "verified": cleared, "carry": out,
            "verdict": str(out.get("verdict", "governed")),
            "detail": {"verdict": out.get("verdict")}}


def _c_candor(text: Any, **_) -> Dict[str, Any]:
    import chiron
    a = chiron.audit(str(text))
    score = float(getattr(a, "candor_score", getattr(a, "score", 0.0)))
    return {"ok": True, "verified": score >= 0.75, "carry": a,
            "verdict": "candid (%.2f)" % score if score >= 0.75
            else "patronizing/over-asserted (%.2f)" % score,
            "detail": {"candor_score": round(score, 4)}}


COMPONENTS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "collapse": _c_collapse,
    "cross_examine": _c_cross_examine,
    "certify": _c_certify,
    "govern": _c_govern,
    "candor": _c_candor,
}

# which components consume a TEXT vs a numeric/structured SURFACE
_TEXT_COMPONENTS = {"certify", "candor"}


def _is_seq(x: Any) -> bool:
    if isinstance(x, (list, tuple)):
        return True
    if isinstance(x, str):
        toks = x.replace(",", " ").split()
        return len(toks) >= 2 and all(_isnum(t) for t in toks)
    return False


def _isnum(t: str) -> bool:
    try:
        float(t.strip().lstrip("-"))
        return True
    except ValueError:
        return "/" in t and all(p.strip().isdigit() for p in t.split("/", 1))


def _as_seq(x: Any) -> List:
    if isinstance(x, (list, tuple)):
        return list(x)
    return [float(t) if ("." in t or "/" in t) else int(t)
            for t in str(x).replace(",", " ").split()]


# ── the engine: run stages under the AND-of-required rule ───────────────────

def _run_stages(stages: List[Dict], inp: Any, mode: str) -> Dict[str, Any]:
    ran, carry = [], None
    for st in stages:
        name = st["component"]
        if name not in COMPONENTS:
            ran.append({"component": name, "ok": False, "verified": False,
                        "required": st.get("required", True),
                        "verdict": "unknown component", "detail": {}})
            if mode == "chain" and st.get("required", True):
                break
            continue
        res = COMPONENTS[name](inp, carry=carry, scores=st.get("scores"),
                               domain=st.get("domain"))
        res["component"] = name
        res["required"] = st.get("required", True)
        if mode == "chain":
            carry = res.get("carry")            # thread the result forward
        ran.append({k: v for k, v in res.items() if k != "carry"})
        if mode == "chain" and res.get("required", True) and not res["ok"]:
            break                               # a required stage failed hard

    required = [r for r in ran if r["required"]]
    all_required_verified = bool(required) and all(r["verified"] for r in required)
    any_required_failed = any(not r["ok"] for r in required)
    if any_required_failed:
        verdict = "FAILED"
    elif all_required_verified:
        verdict = "VERIFIED"
    else:
        verdict = "ABSTAINED"
    return {"mode": mode, "verified": verdict == "VERIFIED", "verdict": verdict,
            "stages": ran,
            "summary": "%d stage(s): %d verified, %d clean-refused, %d failed" % (
                len(ran), sum(r["verified"] for r in ran),
                sum(r["ok"] and not r["verified"] for r in ran),
                sum(not r["ok"] for r in ran))}


def run(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Run a pipeline spec. Modes: chain | team | swarm."""
    mode = spec.get("mode", "chain")
    stages = spec.get("stages") or [{"component": spec.get("component", "collapse")}]
    if mode == "swarm":
        inputs = spec.get("inputs") or []
        runs = [{"input": _short(i), **_run_stages(stages, i, "chain")} for i in inputs]
        n_ver = sum(r["verified"] for r in runs)
        return {"mode": "swarm", "n": len(runs), "verified_count": n_ver,
                "all_verified": bool(runs) and n_ver == len(runs), "runs": runs}
    return _run_stages(stages, spec["input"], "team" if mode == "team" else "chain")


def _short(x: Any) -> str:
    s = x if isinstance(x, str) else json.dumps(x)
    return s if len(s) <= 40 else s[:37] + "..."


# ── fluent builder ──────────────────────────────────────────────────────────

class Pipeline:
    """Build a spec in Python: Pipeline('chain').collapse().cross_examine()."""

    def __init__(self, mode: str = "chain"):
        self.mode = mode
        self.stages: List[Dict] = []

    def _add(self, comp: str, **kw) -> "Pipeline":
        self.stages.append({"component": comp, **kw})
        return self

    def collapse(self, required=True): return self._add("collapse", required=required)
    def cross_examine(self, required=True): return self._add("cross_examine", required=required)
    def certify(self, required=True): return self._add("certify", required=required)
    def govern(self, required=True, **kw): return self._add("govern", required=required, **kw)
    def candor(self, required=True): return self._add("candor", required=required)

    def spec(self, inp=None, inputs=None) -> Dict:
        s: Dict[str, Any] = {"mode": self.mode, "stages": self.stages}
        if inputs is not None:
            s["inputs"] = inputs
        if inp is not None:
            s["input"] = inp
        return s

    def run(self, inp=None, inputs=None) -> Dict:
        return run(self.spec(inp=inp, inputs=inputs))


# ── CLI ──────────────────────────────────────────────────────────────────────

def _print(res: Dict) -> None:
    if res.get("mode") == "swarm":
        print("SWARM — %d/%d inputs verified" % (res["verified_count"], res["n"]))
        for r in res["runs"]:
            print("  [%s] %-40s %s" % ("PASS" if r["verified"] else "····",
                                       r["input"], r["verdict"]))
        return
    print("PIPELINE (%s) -> %s" % (res["mode"], res["verdict"]))
    for st in res["stages"]:
        mark = "PASS" if st["verified"] else ("ok  " if st["ok"] else "FAIL")
        req = "" if st["required"] else " (advisory)"
        print("  [%s] %-14s %s%s" % (mark, st["component"], st["verdict"], req))
    print("  " + res["summary"])


def _demo() -> int:
    print("=== a chain: recover a rule, then attack it ===")
    _print((Pipeline("chain").collapse().cross_examine()
            ).run("1 1 2 3 5 8 13 21 34 55"))
    print("\n=== a team: certify AND candor over one text ===")
    _print((Pipeline("team").certify().candor()
            ).run("The sum of 2 and 3 is 5. Obviously you already knew that."))
    print("\n=== a swarm: one chain fanned across many sequences ===")
    _print((Pipeline("swarm").collapse()
            ).run(inputs=["1 1 2 3 5 8 13 21 34 55",   # Fibonacci -> verify
                          "2 4 6 8 10 12 14 16",        # arithmetic -> verify
                          "4 6 8 9 10 12 14 15 16 18 20 21"]))  # composites -> abstain
    return 0


def _selftest() -> int:
    ok = 0
    fails: List[str] = []

    def gate(name, cond):
        nonlocal ok
        print("  [%s] %s" % ("PASS" if cond else "FAIL", name))
        ok += bool(cond)
        if not cond:
            fails.append(name)

    fib = "1 1 2 3 5 8 13 21 34 55"
    r = Pipeline("chain").collapse().run(fib)
    gate("chain: Fibonacci collapse verifies", r["verified"])

    r = Pipeline("chain").collapse().run("4 6 8 9 10 12 14 15 16 18 20 21")
    gate("chain: composites-12 does NOT verify (honest abstain)", not r["verified"])

    r = Pipeline("team").certify().run("2+2 = 5")
    gate("team: a refuted claim fails the pipeline", not r["verified"]
         and r["verdict"] in ("FAILED", "ABSTAINED"))

    r = Pipeline("team").certify().run("17*3 = 51")
    gate("team: a verified claim passes", r["verified"])

    r = Pipeline("swarm").collapse().run(
        inputs=[fib, "2 4 6 8 10 12 14 16", "4 6 8 9 10 12 14 15 16 18 20 21"])
    gate("swarm: 2 of 3 verify (Fib + arithmetic yes, composites no)",
         r["verified_count"] == 2 and not r["all_verified"])

    adv = Pipeline("chain").collapse().cross_examine(required=False).run(fib)
    gate("advisory stage cannot sink a verified chain", adv["verified"])

    unk = run({"mode": "chain", "input": fib, "stages": [{"component": "nope"}]})
    gate("unknown component fails safe (never a false verify)", not unk["verified"])

    print("pipeline selftest: %d/7 gates green" % ok)
    return 0 if not fails else 1


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "demo":
        return _demo()
    if args[0] == "selftest":
        return _selftest()
    if args[0] == "run":
        raw = sys.stdin.read() if len(args) > 1 and args[1] == "-" else (
            args[1] if len(args) > 1 else "")
        if not raw.strip():
            print("usage: pipeline.py run '<spec-json>'  (or: ... run -)", file=sys.stderr)
            return 2
        try:
            spec = json.loads(raw)
        except json.JSONDecodeError as e:
            print("bad spec JSON:", e, file=sys.stderr)
            return 2
        res = run(spec)
        if "--json" in args:
            print(json.dumps(res, indent=2, default=str))
        else:
            _print(res)
        return 0
    print("unknown command:", args[0], "(try demo | selftest | run)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
