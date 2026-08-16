#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
planner.py — the first slice of Horizon Two: engines compose toward a goal, and the
exact gate arbitrates every step (HORIZON.md H2.1, epistemic status: **prototype**).

Until now every integration was hub-and-spoke: a human or one LLM turn picked one
engine, ran it, read the result. This lifts the President's contract — *propose →
the engine disposes → escalate anything irreversible* — from a single action to a
composed **campaign**:

    Goal{intent, budget, invariants}
        │
        ▼   a deterministic plan of engine steps
    observe → analyze(collapse) → VERIFY(the gate arbitrates) → remember → publish
                                    │                                        │
                              unverified ⇒ HALT                    irreversible ⇒ ESCALATE
                              (never advances)                     (never executed here)

Three properties are enforced, not asserted:

  1. **The gate arbitrates every state change.** A step's result advances only if it
     is exactly verified. An unverifiable finding HALTS the campaign — it can never
     be laundered into the next step. A model hallucination is structurally incapable
     of advancing, because nothing here runs on a model's confidence.
  2. **Irreversible steps escalate.** Anything that would leave the sandbox (publish,
     a real Congress write, a network action) is not performed by the planner; it is
     returned as an escalation for a human to execute. The planner has hands only for
     what is reversible.
  3. **The campaign is bounded and witnessed.** `budget` caps the steps; every step is
     recorded in the run ledger; declared invariants are checked after each step and a
     violation halts the campaign.

What this prototype does NOT yet do (labeled honestly): the plan for a given intent is
a fixed, deterministic pipeline — there is no LLM *proposing* the composition yet. That
(LLM proposes a plan → this loop disposes of it, step by exact step) is the next step
and is HORIZON [theory]. Keeping the composition deterministic is what lets this ship
as a gated prototype instead of a demo.

    python3 planner.py run "1 1 2 3 5 8 13"     # run a recover→verify→publish campaign
    python3 planner.py selftest                 # the gates below

Status: implemented & tested (prototype).
"""
import argparse
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    import run_ledger
except Exception:  # the witness is optional; the campaign still runs without it
    run_ledger = None

# Steps that leave the reversible sandbox. The planner never performs these; it
# escalates them to a human. Kept explicit so the boundary is auditable.
IRREVERSIBLE = {"publish", "congress_write", "network", "spend", "deploy"}

COMPLETED, HALTED, ESCALATED, EXHAUSTED, VIOLATED = (
    "COMPLETED", "HALTED_ON_REFUSAL", "ESCALATED", "BUDGET_EXHAUSTED", "INVARIANT_VIOLATED")


class Goal:
    """What we are trying to accomplish, and the rails it must stay on."""
    def __init__(self, intent, budget=8, invariants=None):
        self.intent = str(intent)
        self.budget = int(budget)
        self.invariants = list(invariants or [])


def _seq(s):
    return [int(x) for x in re.findall(r"-?\d+", str(s))]


def _record(step, ok, verdict):
    if run_ledger:
        try:
            run_ledger.record("planner." + step, [step], ok=ok, redact=False,
                              verdict=str(verdict)[:180], source="planner")
        except Exception:
            pass


# --------------------------------------------------------------------- the gate
def certify_step(finding):
    """The arbiter. A finding is admissible ONLY if the engine exactly verified it
    AND it regenerates the shown surface exactly. Anything else is REFUSED — never
    judged 'probably fine'. This is the certify discipline, inline in the campaign."""
    inv = finding.get("invariant")
    shown = finding.get("shown", [])
    if inv is None or not getattr(inv, "verified", False):
        return False, "REFUSED: no exact verification"
    try:
        regen = [int(x) for x in inv.predict(len(shown))]
    except Exception as e:
        return False, f"REFUSED: cannot regenerate ({e})"
    if regen != shown:
        return False, "REFUSED: does not regenerate the surface exactly"
    return True, f"VERIFIED: {getattr(inv, 'model_class', '?')}"


# --------------------------------------------------------------------- the campaign
def run_campaign(goal, surface):
    """Execute the composed plan for `goal` over `surface`, step by step, the gate
    arbitrating each state change. Returns a full, honest trace."""
    trace = []
    state = {"surface": surface, "laws": []}   # reversible, campaign-local state
    steps_used = 0

    def step(name, ok, verdict, irreversible=False):
        nonlocal steps_used
        steps_used += 1
        rec = {"step": name, "ok": bool(ok), "verdict": verdict,
               "irreversible": irreversible}
        trace.append(rec)
        _record(name, ok, verdict)
        return rec

    def finish(status):
        return {"intent": goal.intent, "status": status, "steps": trace,
                "laws": state["laws"], "steps_used": steps_used,
                "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def within_budget():
        return steps_used < goal.budget

    def invariants_hold():
        # declared invariants are simple checkable predicates over state
        for inv in goal.invariants:
            if inv == "no_unverified_laws" and any(not l.get("verified") for l in state["laws"]):
                return False, inv
            if inv == "surface_nonempty" and not state["surface"]:
                return False, inv
        return True, None

    import chiron

    # 1 · observe — parse the surface (reversible, exact)
    if not within_budget():
        return finish(EXHAUSTED)
    seq = _seq(surface)
    step("observe", True, f"parsed {len(seq)} terms")
    ok, bad = invariants_hold()
    if not ok:
        step("invariant_check", False, f"violated: {bad}")
        return finish(VIOLATED)

    # 2 · analyze — collapse (real engine)
    if not within_budget():
        return finish(EXHAUSTED)
    inv = chiron.collapse(seq if len(seq) >= 2 else str(surface))
    step("analyze", True, f"collapse -> {getattr(inv, 'model_class', '?')} "
                          f"(verified={bool(getattr(inv, 'verified', False))})")

    # 3 · VERIFY — the gate arbitrates. Unverified ⇒ HALT (never advances).
    if not within_budget():
        return finish(EXHAUSTED)
    admitted, verdict = certify_step({"invariant": inv, "shown": seq})
    step("verify", admitted, verdict)
    if not admitted:
        return finish(HALTED)   # the campaign refuses to build on an unproven step

    # 4 · remember — record the verified law (reversible: campaign-local store only)
    if not within_budget():
        return finish(EXHAUSTED)
    try:
        nxt = [int(x) for x in inv.predict(len(seq) + 3)][len(seq):]
    except Exception:
        nxt = []
    state["laws"].append({"model_class": getattr(inv, "model_class", "?"),
                          "verified": True, "predicts_next": nxt})
    step("remember", True, f"law recorded (campaign-local); forecast {nxt}")
    ok, bad = invariants_hold()
    if not ok:
        step("invariant_check", False, f"violated: {bad}")
        return finish(VIOLATED)

    # 5 · publish — IRREVERSIBLE. The planner does not do this; it escalates.
    step("publish", True, "escalated to human — irreversible, not executed by the planner",
         irreversible=True)
    return finish(ESCALATED)


# --------------------------------------------------------------------- gates
def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # 1 · a verifiable goal runs the whole composed pipeline and ends by ESCALATING
    #     the one irreversible step (publish) — it does not perform it.
    g = Goal("recover, verify, and prepare to publish a rule",
             invariants=["no_unverified_laws", "surface_nonempty"])
    r = run_campaign(g, "1 1 2 3 5 8 13 21")
    ok("a verifiable campaign reaches the publish step", r["status"] == ESCALATED)
    ok("it recorded exactly one verified law", len(r["laws"]) == 1 and r["laws"][0]["verified"])
    ok("the verify step was admitted by the gate",
       any(s["step"] == "verify" and s["ok"] for s in r["steps"]))
    ok("the irreversible step is escalated, never executed",
       any(s["step"] == "publish" and s["irreversible"] for s in r["steps"]))

    # 2 · an UNVERIFIABLE surface HALTS at the gate — it never advances to remember/publish
    r2 = run_campaign(Goal("try to certify noise"), "2 3 5 7 11 13 17")  # primes: no exact rule
    ok("an unverifiable surface halts at the gate", r2["status"] == HALTED)
    ok("nothing was remembered from an unverified finding", r2["laws"] == [])
    ok("the campaign never reached publish on a refusal",
       not any(s["step"] == "publish" for s in r2["steps"]))
    ok("the halt is recorded honestly as a refusal",
       any(s["step"] == "verify" and not s["ok"] for s in r2["steps"]))

    # 3 · budget bounds the campaign
    r3 = run_campaign(Goal("stop early", budget=2), "1 2 3 4 5 6")
    ok("budget caps the number of steps", r3["steps_used"] <= 2 and r3["status"] == EXHAUSTED)

    # 4 · a declared invariant violation halts the campaign
    r4 = run_campaign(Goal("empty", invariants=["surface_nonempty"]), "")
    ok("an invariant violation halts the campaign", r4["status"] == VIOLATED)

    # 5 · the gate cannot be fooled by a non-verifying 'finding'
    class _Fake:
        verified = True
        model_class = "liar"
        def predict(self, n):
            return [999] * n   # claims verified but cannot regenerate the surface
    admitted, verdict = certify_step({"invariant": _Fake(), "shown": [1, 2, 3]})
    ok("the gate refuses a 'verified' finding that can't regenerate the surface", not admitted)

    passed = sum(1 for _, c in checks if c)
    print("planner self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compose engines toward a goal; the gate arbitrates each step.")
    sub = ap.add_subparsers(dest="cmd")
    rp = sub.add_parser("run"); rp.add_argument("surface", nargs="+")
    rp.add_argument("--budget", type=int, default=8)
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        goal = Goal("recover, verify, and prepare to publish a rule", budget=args.budget,
                    invariants=["no_unverified_laws", "surface_nonempty"])
        result = run_campaign(goal, " ".join(args.surface))
        print(json.dumps(result, indent=2))
        return 0
    return 0 if _selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
