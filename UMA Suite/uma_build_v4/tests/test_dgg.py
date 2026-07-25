# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Exact-arithmetic gates for uma.dgg — the 2026 Dinitz-Garg-Goemans
cost-conjecture counterexample, verified by this suite's own integer
arithmetic rather than cited.

The discipline mirrors tests/test_jacobian.py: prove the machinery works,
prove it can FAIL (discrimination controls), and only then assert the
theorem.

Run with: pytest tests/test_dgg.py -v
"""
from __future__ import annotations

import pytest

from uma.dgg import (ARCS, DGGError, PATHS, enumerate_routings,
                     fractional_cost, fractional_is_feasible, instance,
                     sweep, verify)


# ── engine sanity: the machinery must be right before the theorem is ─────

def test_instance_has_seven_nodes_and_nine_arcs():
    """The published counterexample is 7 nodes, 9 arcs — no more, no less."""
    assert len(ARCS) == 9
    nodes = set()
    for arc in ARCS:
        tail, head = arc.split("->")
        nodes.add(tail)
        nodes.add(head)
    assert nodes == {"s", "u", "v", "w", "t1", "t2", "t3"}


def test_every_path_uses_only_declared_arcs():
    """No route may traverse an arc that does not exist."""
    for terminal, (direct, detour) in PATHS.items():
        for route in (direct, detour):
            assert all(a in ARCS for a in route), terminal


def test_enumeration_is_exhaustive_and_deterministic():
    """2**3 = 8 routings, every time, in a fixed order."""
    inst = instance(10, 5, 1)
    first = enumerate_routings(inst)
    assert len(first) == 8
    assert [r["choice"] for r in first] == [r["choice"]
                                            for r in enumerate_routings(inst)]


def test_all_arithmetic_is_integer():
    """No float may appear anywhere on the verification path."""
    cert = verify(10, 5, 1, unit_costs=(2, 3, 2))
    for key in ("fractional_cost", "min_unsplittable_cost", "cost_gap", "d_max"):
        assert isinstance(cert[key], int), key
    assert all(isinstance(v, int) for v in cert["capacity"].values())


# ── admissibility: garbage in must raise, never silently verify ──────────

def test_inadmissible_parameters_raise():
    """m <= b - g and m(b-m) > (b+m)g are enforced, not assumed."""
    with pytest.raises(DGGError):
        instance(3, 1, 1)          # m(b-m)=2 is not > (b+m)g=4
    with pytest.raises(DGGError):
        instance(5, 5, 1)          # m <= b - g violated
    with pytest.raises(DGGError):
        instance(0, 1, 1)          # b >= 1 violated
    with pytest.raises(DGGError):
        instance(10, 5, True)      # bools are not ints here


# ── the hypothesis: the fractional flow really is feasible ───────────────

def test_fractional_flow_conserves_and_meets_demand():
    """Conservation at u, v, w and exact demand at t1, t2, t3."""
    assert fractional_is_feasible(instance(10, 5, 1))
    assert fractional_is_feasible(instance(7, 2, 1))


def test_broken_flow_is_detected_as_infeasible():
    """DISCRIMINATION: perturb one capacity and feasibility must fail."""
    inst = instance(10, 5, 1)
    inst["capacity"]["v->w"] += 1          # breaks conservation at v and w
    assert not fractional_is_feasible(inst)


# ── the announced instance, exactly ──────────────────────────────────────

def test_announced_instance_reproduces_published_costs():
    """b=10, m=5, g=1 under the announced cost scaling: 58 fractional, 60 min."""
    cert = verify(10, 5, 1, unit_costs=(2, 3, 2))
    assert cert["fractional_cost"] == 58
    assert cert["min_unsplittable_cost"] == 60
    assert cert["cost_gap"] == 2
    assert cert["refuted"] is True


def test_announced_instance_reproduces_published_congestion_thresholds():
    """capacity + d_max on the spine = 39, 29, 24 — three independent numbers."""
    cert = verify(10, 5, 1, unit_costs=(2, 3, 2))
    cap, d_max = cert["capacity"], cert["d_max"]
    assert d_max == 15
    assert cap["s->u"] + d_max == 39
    assert cap["u->v"] + d_max == 29
    assert cap["v->w"] + d_max == 24


def test_refutation_is_invariant_under_cost_scaling():
    """Same instance, family cost scaling: still refuted, gap scales by 5."""
    announced = verify(10, 5, 1, unit_costs=(2, 3, 2))
    family = verify(10, 5, 1)
    assert family["refuted"] is True
    assert family["fractional_cost"] == 5 * announced["fractional_cost"]
    assert family["min_unsplittable_cost"] == 5 * announced["min_unsplittable_cost"]


# ── DISCRIMINATION: the gate must be able to say "not refuted" ───────────

def test_unbounded_congestion_allowance_does_NOT_refute():
    """If congestion were free, the all-detour routing costs 0 and the
    conjecture would stand. The verifier must report refuted=False — the
    refutation depends on the DGG allowance, not on wishful accounting."""
    inst = instance(10, 5, 1, unit_costs=(2, 3, 2))
    routings = enumerate_routings(inst)
    all_detour = [r for r in routings if r["choice"] == "zzz"][0]
    assert all_detour["cost"] == 0
    assert all_detour["within_dgg_allowance"] is False   # exceeds cap + d_max
    assert all_detour["max_violation"] > inst["d_max"]


def test_zero_costs_do_not_refute():
    """DISCRIMINATION: with all costs zero, nothing is more expensive than
    the fractional flow, so the verifier must NOT stamp a refutation."""
    cert = verify(10, 5, 1, unit_costs=(0, 0, 0))
    assert cert["fractional_cost"] == 0
    assert cert["min_unsplittable_cost"] == 0
    assert cert["refuted"] is False


# ── the family: every admissible instance, exhaustively ──────────────────

def test_smallest_admissible_instance_refutes():
    """b=7, m=2, g=1 — the smallest admissible triple — refutes exactly."""
    cert = verify(7, 2, 1)
    assert cert["refuted"] is True
    assert cert["fractional_cost"] == 125
    assert cert["min_unsplittable_cost"] == 126


def test_entire_family_refutes_under_exhaustive_sweep():
    """Every admissible (b, m, g) with b <= 25 refutes — none is an accident."""
    result = sweep(25)
    assert result["admissible_instances_checked"] == 456
    assert result["instances_refuting"] == 456
    assert result["all_refute"] is True


def test_certificate_states_its_own_scope():
    """The certificate must carry its method, so a reader cannot over-read it."""
    cert = verify(10, 5, 1, unit_costs=(2, 3, 2))
    assert "exhaustive" in cert["method"]
    assert "no floats" in cert["method"]
    assert cert["routings_enumerated"] == 8
