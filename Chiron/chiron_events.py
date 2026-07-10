#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
chiron_events — a minimal, deterministic event bus so vault modules can be
COMPOSED (collapse → finding → report) without hand-wiring every step.

STATUS: prototype. The bus mechanics are implemented-and-tested (selftest
below). The bundled pipeline is a demonstration of composition, NOT a new
verification path: nothing in this file stamps anything. All verification
stays inside chiron's collapse/holdout; events may only CARRY the engine's
verdict, never upgrade it. A faithful-transmission gate enforces that.

Design constraints (kept deliberately austere):
  * stdlib only; synchronous; subscribers run in subscription order —
    publish() is a plain ordered function call chain, so runs replay.
  * subscriber exceptions PROPAGATE. A bus that swallows errors is a bus
    that can hide a red gate.
  * no wildcard topics, no threads, no queues — those are new layers; this
    is connective tissue.

Relation to planner.py: the planner is goal-directed composition (a campaign
arbitrated by the gate, HORIZON H2.1); this bus is passive wiring modules can
share. Complementary primitives, one implementation each.

Usage:
    python3 chiron_events.py selftest
    python3 chiron_events.py demo 1 1 2 3 5 8 13 21 34 55 89 144

    from chiron_events import Bus, run_pipeline
    report = run_pipeline([1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144])
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Tuple

__all__ = ["Bus", "wire_collapse_pipeline", "run_pipeline"]


class Bus:
    """Ordered, synchronous publish/subscribe. Deterministic by construction."""

    def __init__(self) -> None:
        self._subs: Dict[str, List[Tuple[int, Callable[[Any], Any]]]] = {}
        self._next = 0
        self.log: List[Tuple[str, Any]] = []      # every publish, in order

    def subscribe(self, topic: str, fn: Callable[[Any], Any]) -> int:
        token = self._next
        self._next += 1
        self._subs.setdefault(topic, []).append((token, fn))
        return token

    def unsubscribe(self, token: int) -> bool:
        for topic, subs in self._subs.items():
            for i, (tok, _) in enumerate(subs):
                if tok == token:
                    del subs[i]
                    return True
        return False

    def publish(self, topic: str, payload: Any) -> List[Any]:
        """Deliver payload to every subscriber in subscription order.
        Returns their results in that order. Exceptions propagate."""
        self.log.append((topic, payload))
        return [fn(payload) for _, fn in self._subs.get(topic, [])]


# ── demonstration pipeline: collapse → finding → report ────────────────────
# Composition the review asked for, expressed as three subscribers. The
# engine's verdict is copied verbatim; the report renderer REFUSES to say
# "verified" unless the Invariant said so.

def wire_collapse_pipeline(bus: Bus) -> List[str]:
    """Attach the demo pipeline to a bus. Returns the report sink (mutated
    in place as findings arrive)."""
    import chiron  # the engine; heavy import, deferred until wiring

    reports: List[str] = []

    def on_sequence(seq):
        inv = chiron.collapse_numeric(seq)
        bus.publish("collapse.finding", {
            "model_class": inv.model_class,
            "verified": bool(inv.verified),        # verbatim, never recomputed
            "explanation": inv.explanation,
        })
        return inv

    def on_finding(f):
        if f["verified"]:
            line = "VERIFIED %s — %s" % (f["model_class"], f["explanation"][:80])
        else:
            line = "ABSTAINED (%s) — engine did not verify; report follows suit" \
                   % f["model_class"]
        bus.publish("report.line", line)
        return line

    def on_report(line):
        reports.append(line)
        return line

    bus.subscribe("collapse.request", on_sequence)
    bus.subscribe("collapse.finding", on_finding)
    bus.subscribe("report.line", on_report)
    return reports


def run_pipeline(seq) -> Dict[str, Any]:
    """One-call composition: sequence in, report + event log out."""
    bus = Bus()
    reports = wire_collapse_pipeline(bus)
    results = bus.publish("collapse.request", list(seq))
    inv = results[0]
    return {"verified": bool(inv.verified), "model_class": inv.model_class,
            "reports": reports, "events": [t for t, _ in bus.log]}


# ── selftest ────────────────────────────────────────────────────────────────

def _selftest() -> int:
    failures: List[str] = []

    def gate(name: str, ok: bool) -> None:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        if not ok:
            failures.append(name)

    # bus mechanics
    bus = Bus()
    seen: List[str] = []
    t1 = bus.subscribe("t", lambda p: seen.append("a" + p) or "a")
    bus.subscribe("t", lambda p: seen.append("b" + p) or "b")
    bus.publish("t", "!")
    gate("subscribers run in subscription order", seen == ["a!", "b!"])
    gate("publish to silent topic returns []", bus.publish("nobody", 0) == [])
    gate("unsubscribe removes exactly one", bus.unsubscribe(t1) and not bus.unsubscribe(t1))
    seen.clear()
    bus.publish("t", "?")
    gate("after unsubscribe only b remains", seen == ["b?"])

    def boom(_):
        raise RuntimeError("boom")
    bus2 = Bus()
    bus2.subscribe("x", boom)
    try:
        bus2.publish("x", None)
        gate("subscriber exceptions propagate (never swallowed)", False)
    except RuntimeError:
        gate("subscriber exceptions propagate (never swallowed)", True)

    # composition: a verifiable sequence flows through as VERIFIED
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    out = run_pipeline(fib)
    gate("pipeline events flow request→finding→report",
         out["events"] == ["collapse.request", "collapse.finding", "report.line"])
    gate("verified sequence reported VERIFIED", out["verified"]
         and out["reports"] and out["reports"][0].startswith("VERIFIED"))

    # honesty: an unverifiable input must flow through as ABSTAINED —
    # the pipeline may never upgrade the engine's verdict.
    soup = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3]
    out2 = run_pipeline(soup)
    gate("engine abstains on patternless input", not out2["verified"])
    gate("report transmits abstention faithfully (no false verify)",
         out2["reports"] and out2["reports"][0].startswith("ABSTAINED"))

    # faithful transmission on both branches
    gate("report flag == engine flag on both cases",
         out["reports"][0].startswith("VERIFIED") == out["verified"]
         and out2["reports"][0].startswith("VERIFIED") == out2["verified"])

    n_pass = 10 - len(failures)
    print("chiron_events selftest: %d/10 gates green" % n_pass)
    return 0 if not failures else 1


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "selftest":
        return _selftest()
    if args[0] == "demo":
        seq = [int(a) for a in args[1:]] or [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
        out = run_pipeline(seq)
        for line in out["reports"]:
            print(line)
        print("events:", " → ".join(out["events"]))
        return 0
    print("unknown command:", args[0], "(try selftest | demo)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
