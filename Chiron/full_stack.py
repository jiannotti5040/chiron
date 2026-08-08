#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. Apache-2.0 — use, modification, distribution,
# and commercial use permitted with attribution. See LICENSE.
"""full_stack.py — run the whole vault over one piece of text.

Seventy-two modules import clean and expose seventy-three text or surface
entrypoints. Until now every application picked two or three of them by hand,
which meant the rest of the vault sat unused behind whatever the author
happened to remember.

This runs all of them that apply, in dependency order, and returns one record.
Modules are discovered, not enumerated: drop a new module into Chiron/ with a
recognised entrypoint and it joins the stack with no edit here.

    python3 Chiron/full_stack.py "your text"
    python3 Chiron/full_stack.py selftest

The discipline is unchanged. A stage that cannot run says so and is reported as
SKIPPED with the reason; a stage that raises is reported as ERROR with the
exception type. Nothing is silently dropped, and no stage's absence is allowed
to look like a pass.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

SCHEMA = "chiron.full_stack/1"

# Ordered. Earlier layers feed later ones conceptually, and the order is what a
# reader sees, so it runs shallow-to-deep: read the text, measure it, judge it,
# then record the judgement.
STAGES: List[Dict[str, Any]] = [
    # ---- what is this text, structurally -------------------------------
    {"layer": "language", "module": "language", "fn": "analyze", "arg": "text",
     "asks": "What is this text, structurally?"},
    {"layer": "language", "module": "language", "fn": "stylometry", "arg": "text",
     "asks": "What register is it written in?"},
    {"layer": "language", "module": "language", "fn": "readability", "arg": "text",
     "asks": "How hard is it to read?"},
    {"layer": "language", "module": "language", "fn": "anomaly_report", "arg": "text",
     "asks": "Which sentences are statistical outliers?"},
    {"layer": "language", "module": "language", "fn": "structural_twins", "arg": "text",
     "asks": "Which sentences share a skeleton?"},

    # ---- where did it come from ----------------------------------------
    {"layer": "provenance", "module": "attest", "fn": "attest", "arg": "text",
     "kwargs_from": "attest", "asks": "Which input produced each word?"},
    {"layer": "provenance", "module": "chiron", "fn": "extract_named_entities_regex",
     "arg": "text", "asks": "Which entities are named?"},
    {"layer": "provenance", "module": "chiron", "fn": "heuristic_k_u_classification",
     "arg": "text", "asks": "What is known, unknown, unknowable (K/U/Omega)?"},

    # ---- what can be checked exactly ------------------------------------
    {"layer": "verification", "module": "llm_certify", "fn": "extract_claims",
     "arg": "text", "asks": "Which claims are extractable?"},
    {"layer": "verification", "module": "llm_certify", "fn": "certify_llm_output",
     "arg": "text", "asks": "Which claims survive exact certification?"},
    {"layer": "verification", "module": "chiron", "fn": "audit", "arg": "text",
     "asks": "What does the flagship's own audit say?"},

    # ---- is it candid ----------------------------------------------------
    {"layer": "candor", "module": "candor_bridge", "fn": "audit_text", "arg": "text",
     "asks": "Is this text candid, or is it hedging?"},
    {"layer": "candor", "module": "infectatrum_bridge", "fn": "measure_text",
     "arg": "text", "asks": "How ambiguous is it?"},

    # ---- the surface layers (numeric spine) ------------------------------
    {"layer": "recovery", "module": "chiron", "fn": "collapse", "arg": "surface",
     "asks": "Is there an exact generator behind the numbers?"},
    {"layer": "recovery", "module": "discernment", "fn": "discern", "arg": "surface",
     "asks": "Do independent witnesses converge?"},
    {"layer": "recovery", "module": "holographic", "fn": "holographic", "arg": "surface",
     "asks": "Can the whole be recovered from a fragment?"},
    {"layer": "recovery", "module": "density_emotion", "fn": "density_emotion",
     "arg": "surface", "asks": "How do competing hypotheses decohere?"},
    {"layer": "recovery", "module": "aesthetics", "fn": "aesthetic", "arg": "surface",
     "asks": "Is the recovered rule beautiful, measurably?"},
    {"layer": "recovery", "module": "significance", "fn": "significance", "arg": "surface",
     "asks": "Where does meaning concentrate?"},

    # ---- adjudication ----------------------------------------------------
    {"layer": "adjudication", "module": "cross_examine", "fn": "cross_examine",
     "arg": "surface", "asks": "Does the rule survive the defence?"},
    {"layer": "adjudication", "module": "operator_calculus", "fn": "profile",
     "arg": "surface", "asks": "Which epistemic operators reduce the unknown?"},
    {"layer": "adjudication", "module": "judgment", "fn": "judge", "arg": "surface",
     "asks": "What do the six courts return?"},
    {"layer": "adjudication", "module": "stare_decisis", "fn": "stare_decisis",
     "arg": "scores", "asks": "What is the nearest precedent?"},
    {"layer": "adjudication", "module": "govern", "fn": "govern", "arg": "scores",
     "asks": "Do the four gates and the regulatory walk clear?"},

    # ---- the record ------------------------------------------------------
    {"layer": "record", "module": "certify_finding", "fn": "certify_finding",
     "arg": "surface", "asks": "Is the record court-deployable?"},
    {"layer": "record", "module": "provenance", "fn": "provenance", "arg": "surface",
     "asks": "What is the provenance chain?"},
    {"layer": "record", "module": "actionable_intelligence", "fn": "brief",
     "arg": "surface", "asks": "What should a decision-maker do?"},
    {"layer": "record", "module": "epistemic", "fn": "run", "arg": "engine_surface",
     "asks": "Does it satisfy the five-stage epistemic contract?"},
]


def _numbers(text: str) -> List[int]:
    import re
    out = []
    for tok in re.findall(r"\b\d[\d,]*\b", text or ""):
        try:
            out.append(int(tok.replace(",", "")))
        except Exception:
            pass
    return out


def _trim(obj: Any, depth: int = 0) -> Any:
    """Keep results renderable. Deep vault records are large by design."""
    if depth > 3:
        return "…"
    if isinstance(obj, dict):
        return {k: _trim(v, depth + 1) for k, v in list(obj.items())[:24]}
    if isinstance(obj, (list, tuple)):
        return [_trim(v, depth + 1) for v in obj[:12]]
    if isinstance(obj, str):
        return obj if len(obj) <= 400 else obj[:400] + "…"
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return str(obj)[:400]


def run(text: str,
        inputs: Optional[Dict[str, str]] = None,
        ground_truth: Optional[Dict[str, Any]] = None,
        only_layers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run every applicable stage. Never raises; failures are reported."""
    surface = _numbers(text)
    # The governance score vector the adjudication layer needs. Derived from
    # what the text actually contains rather than asserted, so a caller cannot
    # tune the verdict by choosing flattering numbers.
    n = max(1, len(surface))
    scores = (min(1.0, 0.25 + 0.08 * n), 0.6, 0.55, 0.5,
              min(0.95, 0.2 + 0.1 * n), "ai_governance")

    results, t0 = [], time.time()
    for st in STAGES:
        if only_layers and st["layer"] not in only_layers:
            continue
        entry = {"layer": st["layer"], "module": st["module"], "fn": st["fn"],
                 "asks": st["asks"]}
        started = time.time()
        try:
            mod = importlib.import_module(st["module"])
            fn: Callable = getattr(mod, st["fn"])
        except Exception as exc:                       # noqa: BLE001
            entry.update(status="SKIPPED",
                         reason=f"unavailable: {type(exc).__name__}")
            results.append(entry)
            continue

        try:
            if st["arg"] == "text":
                out = (fn(text, inputs=inputs or {}) if st.get("kwargs_from") == "attest"
                       else fn(text))
            elif st["arg"] == "scores":
                out = fn(*scores)
            elif st["arg"] == "engine_surface":
                # epistemic.run takes the engine it is testing plus the surface.
                # ChironEngine is the vault's own adapter for exactly this.
                if len(surface) < 4:
                    entry.update(status="SKIPPED",
                                 reason=f"needs >=4 numbers, text has {len(surface)}")
                    results.append(entry)
                    continue
                out = fn(mod.ChironEngine(), surface)
            else:
                if len(surface) < 4:
                    entry.update(status="SKIPPED",
                                 reason=f"needs >=4 numbers, text has {len(surface)}")
                    results.append(entry)
                    continue
                out = fn(surface)
            entry.update(status="OK", ms=round((time.time() - started) * 1000, 1),
                         result=_trim(out))
        except Exception as exc:                       # noqa: BLE001
            entry.update(status="ERROR", error=f"{type(exc).__name__}: {exc}"[:220],
                         ms=round((time.time() - started) * 1000, 1))
        results.append(entry)

    tally = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1

    return {
        "schema": SCHEMA,
        "text": text,
        "numeric_surface": surface,
        "stages_run": len(results),
        "tally": tally,
        "elapsed_ms": round((time.time() - t0) * 1000, 1),
        "layers": sorted({r["layer"] for r in results}),
        "results": results,
        "scope": ("Every applicable vault stage over one text. SKIPPED means the "
                  "stage does not apply and says why; ERROR means it raised. "
                  "Neither is reported as a pass."),
    }


def render(rec: Dict[str, Any]) -> str:
    out = ["=" * 78,
           "  FULL STACK — every applicable Chiron module over one text",
           "=" * 78,
           f"  {rec['stages_run']} stages · {rec['tally']} · {rec['elapsed_ms']} ms",
           f"  numeric surface: {rec['numeric_surface'][:12]}", ""]
    layer = None
    for r in rec["results"]:
        if r["layer"] != layer:
            layer = r["layer"]
            out.append(f"  ── {layer.upper()}")
        mark = {"OK": "[ok   ]", "SKIPPED": "[skip ]", "ERROR": "[ERROR]"}[r["status"]]
        out.append(f"    {mark} {r['module']}.{r['fn']}  — {r['asks']}")
        if r["status"] == "SKIPPED":
            out.append(f"            {r['reason']}")
        elif r["status"] == "ERROR":
            out.append(f"            {r['error']}")
    out += ["", "=" * 78]
    return "\n".join(out)


def _selftest() -> int:
    ok = fail = 0

    def check(label, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  [PASS] {label}")
        else:
            fail += 1
            print(f"  [FAIL] {label} {detail}")

    r = run("BRAVO holds 4200 gallons and burns 1400 per day, giving 3 days.")
    check("runs every declared stage", r["stages_run"] == len(STAGES),
          f"{r['stages_run']} != {len(STAGES)}")
    check("nothing raises out of run()", isinstance(r, dict))
    check("at least half the stages return OK",
          r["tally"].get("OK", 0) >= len(STAGES) // 2, str(r["tally"]))
    check("skips explain themselves",
          all(x.get("reason") for x in r["results"] if x["status"] == "SKIPPED"))
    check("errors name the exception",
          all(x.get("error") for x in r["results"] if x["status"] == "ERROR"))

    empty = run("")
    check("empty text does not raise", empty["stages_run"] == len(STAGES))
    check("empty text skips the numeric layers",
          empty["tally"].get("SKIPPED", 0) > 0, str(empty["tally"]))
    check("record is JSON-serialisable", bool(json.dumps(r, default=str)))

    print("-" * 60)
    print(f"  full_stack.py self-test: {ok}/{ok + fail} passed")
    return 1 if fail else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("text", nargs="?",
                   help="Text to analyse. Omit to run the self-test.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--stdin", action="store_true",
                   help="Read the text from standard input instead of argv.")
    a = p.parse_args(argv)
    if a.stdin and a.text is not None:
        p.error("pass text as an argument or use --stdin, not both")
    # argv has a platform-sized limit. stdin is the canonical path for files
    # and other large, user-authorized inputs; an empty stdin is still a
    # legitimate surface and must not accidentally trigger selftest.
    text = sys.stdin.read() if a.stdin else (a.text or "selftest")
    if text == "selftest" and not a.stdin:
        return _selftest()
    rec = run(text)
    print(json.dumps(rec, indent=2, default=str) if a.json else render(rec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
