# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.dgg — exact verification of the 2026 Dinitz–Garg–Goemans cost-conjecture
counterexample (Rybin / GPT-5.6 Pro announcement, July 2026).

WHAT THE CONJECTURE SAID
------------------------
Dinitz, Garg and Goemans proved: any fractional single-source flow can be
rerouted as an *unsplittable* flow (each demand routed entirely on one path)
while exceeding each arc capacity by at most d_max, the largest demand.
Goemans then conjectured that this can be done **without increasing the
cost**. The counterexample below shows it cannot.

WHAT THIS MODULE VERIFIES — exact integer arithmetic, exhaustive, no solver
--------------------------------------------------------------------------
For a 7-node, 9-arc single-source instance it checks, over the integers:

  1. the fractional flow is *feasible*  — conserves at u, v, w and meets
     every demand exactly, with flow equal to capacity on every arc;
  2. every unsplittable routing is enumerated (each of the three terminals
     has exactly two paths, so 2**3 = 8 routings — the whole space, not a
     sample);
  3. among the routings whose congestion is within the DGG allowance
     (load <= capacity + d_max), the **cheapest costs strictly more** than
     the fractional flow.

(1) is the conjecture's hypothesis; (3) denies its conclusion. Because the
routing space is finite and fully enumerated, this is a proof for the
instance, not evidence about it.

Everything is `int`. No floats, no LP solver, no network, and no trust in
anyone else's arithmetic.

SCOPE — what this does NOT claim
--------------------------------
It does not certify the provenance of the announcement, does not establish
that this instance is minimal, and does not resolve any other case of the
unsplittable-flow literature. It verifies the arithmetic of the stated
instances, which stand on their own regardless of who announced them.
"""
from __future__ import annotations

import json
from itertools import product
from typing import Dict, List, Tuple

SCHEMA = "uma.dgg/1"

#: the nine arcs, in canonical order
ARCS: Tuple[str, ...] = (
    "s->t1", "s->t2", "s->u", "u->v", "u->t3",
    "v->t1", "v->w", "w->t2", "w->t3",
)

#: each terminal has exactly two routes: (direct, zero-cost detour)
PATHS: Dict[str, Tuple[List[str], List[str]]] = {
    "t1": (["s->t1"], ["s->u", "u->v", "v->t1"]),
    "t2": (["s->t2"], ["s->u", "u->v", "v->w", "w->t2"]),
    "t3": (["s->u", "u->t3"], ["s->u", "u->v", "v->w", "w->t3"]),
}

TERMINALS: Tuple[str, ...] = ("t1", "t2", "t3")


class DGGError(ValueError):
    """Raised when an instance is not well-formed. Never swallowed."""


# ── instance construction ────────────────────────────────────────────────

def instance(b: int, m: int, g: int,
             unit_costs: Tuple[int, int, int] | None = None) -> dict:
    """Build the (b, m, g) instance of the published 3-parameter family.

    Capacities equal the fractional flow. Costs sit on exactly three arcs
    (the three "direct" routes); every detour arc is free. `unit_costs`
    overrides the family's default (b, b+m, b) — used to reproduce the
    announcement's published cost scaling.

    Raises DGGError if the parameters fall outside the family's stated
    admissibility conditions, so a caller cannot silently verify garbage.
    """
    for name, val in (("b", b), ("m", m), ("g", g)):
        if not isinstance(val, int) or isinstance(val, bool):
            raise DGGError(f"{name} must be an int")
        if val < 1:
            raise DGGError(f"{name} must be >= 1")
    if not m <= b - g:
        raise DGGError("admissibility violated: require m <= b - g")
    if not m * (b - m) > (b + m) * g:
        raise DGGError("admissibility violated: require m(b-m) > (b+m)g")

    cap = {
        "s->t1": b, "s->t2": m + g, "s->u": 2 * b + m - g,
        "u->v": b + m - g, "u->t3": b, "v->t1": m,
        "v->w": b - g, "w->t2": b - m - g, "w->t3": m,
    }
    if any(c < 0 for c in cap.values()):
        raise DGGError("admissibility violated: negative capacity")

    c1, c2, c3 = unit_costs if unit_costs is not None else (b, b + m, b)
    cost = {a: 0 for a in ARCS}
    cost["s->t1"], cost["s->t2"], cost["u->t3"] = c1, c2, c3

    return {
        "b": b, "m": m, "g": g,
        "capacity": cap,
        "cost": cost,
        "demand": {"t1": b + m, "t2": b, "t3": b + m},
        "d_max": b + m,
    }


# ── (1) the fractional flow is feasible ──────────────────────────────────

def fractional_is_feasible(inst: dict) -> bool:
    """Flow == capacity on every arc: conserves at u, v, w and meets demand."""
    cap, dem = inst["capacity"], inst["demand"]
    return (
        cap["s->u"] == cap["u->v"] + cap["u->t3"]          # conservation at u
        and cap["u->v"] == cap["v->t1"] + cap["v->w"]      # conservation at v
        and cap["v->w"] == cap["w->t2"] + cap["w->t3"]     # conservation at w
        and cap["s->t1"] + cap["v->t1"] == dem["t1"]       # demand at t1
        and cap["s->t2"] + cap["w->t2"] == dem["t2"]       # demand at t2
        and cap["u->t3"] + cap["w->t3"] == dem["t3"]       # demand at t3
    )


def fractional_cost(inst: dict) -> int:
    """Cost of the fractional flow: sum over arcs of cost * flow (= capacity)."""
    return sum(inst["cost"][a] * inst["capacity"][a] for a in ARCS)


# ── (2) exhaustive enumeration of every unsplittable routing ─────────────

def enumerate_routings(inst: dict) -> List[dict]:
    """All 2**3 unsplittable routings, with exact load, cost and congestion.

    Returned in a fixed order so the certificate is byte-deterministic.
    """
    cap, cost, dem, d_max = (inst["capacity"], inst["cost"],
                             inst["demand"], inst["d_max"])
    out: List[dict] = []
    for choice in product((0, 1), repeat=len(TERMINALS)):
        load = {a: 0 for a in ARCS}
        total = 0
        for terminal, which in zip(TERMINALS, choice):
            arcs = PATHS[terminal][which]
            for a in arcs:
                load[a] += dem[terminal]
            total += sum(cost[a] for a in arcs) * dem[terminal]
        violation = max(load[a] - cap[a] for a in ARCS)
        out.append({
            "choice": "".join("D" if c == 0 else "z" for c in choice),
            "cost": total,
            "max_violation": violation,
            "within_dgg_allowance": violation <= d_max,
        })
    return out


# ── (3) the refutation ───────────────────────────────────────────────────

def verify(b: int, m: int, g: int,
           unit_costs: Tuple[int, int, int] | None = None) -> dict:
    """Verify the instance refutes the cost conjecture. Returns a certificate.

    `refuted` is True only when the fractional flow is feasible AND at least
    one congestion-admissible unsplittable routing exists AND the cheapest
    such routing costs strictly more than the fractional flow. Anything else
    leaves `refuted` False — the module does not stamp what it did not show.
    """
    inst = instance(b, m, g, unit_costs)
    feasible = fractional_is_feasible(inst)
    frac = fractional_cost(inst)
    routings = enumerate_routings(inst)
    admissible = [r for r in routings if r["within_dgg_allowance"]]
    best = min((r["cost"] for r in admissible), default=None)

    refuted = bool(feasible and best is not None and best > frac)
    return {
        "schema": SCHEMA,
        "parameters": {"b": b, "m": m, "g": g},
        "d_max": inst["d_max"],
        "capacity": inst["capacity"],
        "unit_costs": {"s->t1": inst["cost"]["s->t1"],
                       "s->t2": inst["cost"]["s->t2"],
                       "u->t3": inst["cost"]["u->t3"]},
        "demand": inst["demand"],
        "fractional_feasible": feasible,
        "fractional_cost": frac,
        "routings_enumerated": len(routings),
        "routings_within_allowance": len(admissible),
        "min_unsplittable_cost": best,
        "cost_gap": (best - frac) if best is not None else None,
        "refuted": refuted,
        "method": ("exhaustive enumeration of all 2**3 unsplittable routings; "
                   "exact integer arithmetic; no LP solver, no floats"),
    }


def sweep(max_b: int = 25) -> dict:
    """Verify EVERY admissible (b, m, g) with b <= max_b. Exhaustive, exact.

    A family-wide result: if a single admissible instance failed to refute,
    `all_refute` would be False and the count would show it.
    """
    checked, refuting = 0, 0
    for b in range(2, max_b + 1):
        for m in range(1, b):
            for g in range(1, b):
                try:
                    cert = verify(b, m, g)
                except DGGError:
                    continue
                checked += 1
                refuting += 1 if cert["refuted"] else 0
    return {
        "schema": SCHEMA,
        "max_b": max_b,
        "admissible_instances_checked": checked,
        "instances_refuting": refuting,
        "all_refute": checked > 0 and checked == refuting,
    }


def main() -> int:
    """Emit the certificate for the announced instance plus the family sweep."""
    announced = verify(10, 5, 1, unit_costs=(2, 3, 2))
    family = verify(10, 5, 1)
    print(json.dumps({
        "schema": SCHEMA,
        "announced_instance": announced,
        "same_instance_family_cost_scaling": {
            "fractional_cost": family["fractional_cost"],
            "min_unsplittable_cost": family["min_unsplittable_cost"],
            "note": ("identical structure and identical refutation; costs "
                     "scaled by 5 relative to the announced figures — the "
                     "refutation is invariant under positive cost scaling"),
        },
        "family_sweep": sweep(25),
        "scope": ("verifies the arithmetic of the stated instances only; not "
                  "provenance, not minimality, not any other case in the "
                  "unsplittable-flow literature"),
    }, indent=2))
    return 0
