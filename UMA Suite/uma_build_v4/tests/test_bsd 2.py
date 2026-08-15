# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Gates for uma.bsd — the exact Birch--Swinnerton-Dyer prediction.

The suite is deliberately split into three kinds of gate:
  * exact arithmetic that must reproduce published invariants;
  * enclosures that must CONTAIN published reals (never equal them);
  * controls that must FAIL when the machinery is sabotaged.
A test file with only the first two kinds proves the code runs, not that it
measures anything.
"""
from fractions import Fraction

import pytest

from uma.bsd import (CONSISTENT, REFUSED, bsd_certificate, l_value_at_1,
                     real_period, sha_analytic_interval)
from uma.bsd.battery import BATTERY, CONTROLS, run_battery
from uma.bsd.curve import (ADDITIVE, NONSPLIT, SPLIT, Curve, Refuse,
                           _MR_DETERMINISTIC_BOUND, _MR_PSI, _MR_WITNESSES,
                           _is_probable_prime)
from uma.bsd.rig import Iv, PI, agm, exp_neg, integers_in, largest_real_root

C11 = (0, -1, 1, -10, -20)       # 11.a2   Delta < 0, torsion 5, Sha 1
C15 = (1, 1, 1, -2160, -39540)   # 15.a1   Delta > 0, torsion 2, Sha 1
C37 = (0, 1, 1, -1873, -31833)   # 37.b1   Delta > 0, torsion 1, Sha 1
C571 = (0, -1, 1, -929, -10595)  # 571.b1  Delta < 0, Sha 4


def encloses(iv, decimal: str) -> bool:
    """Does the proven interval contain the published value?

    Published constants are printed TRUNCATED, so the literal sits at or just
    below the true value by up to one unit in its last place. Our intervals are
    narrower than that (width ~2^-320), so the comparison must allow exactly
    that one unit -- and no more. Widening further would let a genuinely wrong
    interval pass."""
    v = Fraction(decimal)
    ulp = Fraction(1, 10 ** len(decimal.split(".")[1]))
    lo, hi = iv.as_fractions()
    return lo - ulp <= v <= hi + ulp


# ── the interval kernel ─────────────────────────────────────────────────

def test_intervals_contain_their_value():
    a = Iv.exact(Fraction(1, 3))
    lo, hi = a.as_fractions()
    assert lo <= Fraction(1, 3) <= hi


def test_pi_enclosure_is_correct_and_tight():
    assert encloses(PI, "3.14159265358979323846264338327950288419716939937510")
    lo, hi = PI.as_fractions()
    assert Fraction(314159265, 10 ** 8) < lo and hi < Fraction(314159266, 10 ** 8)
    assert hi - lo < Fraction(1, 10 ** 50)


def test_sqrt_encloses():
    two = Iv.exact(2).sqrt()
    lo, hi = two.as_fractions()
    assert lo * lo <= 2 <= hi * hi


def test_agm_matches_known_value():
    # AGM(1, sqrt 2) = 1.1981402347355922074... (Gauss's constant reciprocal)
    g = agm(Iv.exact(1), Iv.exact(2).sqrt())
    assert encloses(g, "1.19814023473559220744")


def test_exp_neg_matches_known_value():
    e1 = exp_neg(Iv.exact(1))
    assert encloses(e1, "0.36787944117144232159552377016146")


def test_largest_real_root_picks_the_largest():
    # (x-1)(x-2)(x-3)
    r = largest_real_root([1, -6, 11, -6])
    lo, hi = r.as_fractions()
    assert lo <= 3 <= hi
    assert lo > Fraction(5, 2)


def test_division_by_straddling_interval_refuses():
    with pytest.raises(ZeroDivisionError):
        Iv.exact(1) / Iv(-1, 1)


def test_sqrt_of_possibly_negative_refuses():
    with pytest.raises(ValueError):
        Iv(-1, 1).sqrt()


# ── the primality kernel _factor leans on ───────────────────────────────
#
# _factor calls _is_probable_prime to decide whether a surviving cofactor may
# be recorded as a prime factor. A false positive there silently corrupts the
# conductor and Tamagawa factorisation, so this kernel is load-bearing for
# every certificate the module emits. It got this wrong once: twelve
# Miller-Rabin witnesses were paired with the thirteen-witness bound, so the
# smallest composite fooling twelve bases sat *below* the range the routine
# claimed to decide, and was reported prime.

PSI_12 = 318_665_857_834_031_151_167_461   # 399165290221 * 798330580441


def test_twelve_base_strong_pseudoprime_is_rejected():
    assert PSI_12 == 399_165_290_221 * 798_330_580_441       # it is composite
    assert not _is_probable_prime(PSI_12)


def test_mr_bound_is_derived_from_its_own_witness_list():
    """The defect class, not the one composite: a bound larger than the
    tabulated psi for the witness count is a licence to stamp a composite."""
    assert _MR_DETERMINISTIC_BOUND == _MR_PSI[len(_MR_WITNESSES)]
    first_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
    assert _MR_WITNESSES == first_primes[:len(_MR_WITNESSES)]


def test_every_tabulated_pseudoprime_is_rejected_below_the_bound():
    for k, psi in _MR_PSI.items():
        if psi < _MR_DETERMINISTIC_BOUND:
            assert not _is_probable_prime(psi), f"psi_{k} stamped prime"


def test_primality_kernel_agrees_with_primus():
    """UMA keeps its own copy so uma.bsd stays self-contained. That is only
    safe while the two tables agree, so pin them together here rather than
    trusting a comment."""
    primus_certify = pytest.importorskip(
        "primus.certify", reason="Primus not installed in this environment")
    assert _MR_WITNESSES == primus_certify._MR_WITNESSES
    assert _MR_PSI == primus_certify._MR_PSI
    assert _MR_DETERMINISTIC_BOUND == primus_certify._MR_DETERMINISTIC_BOUND


# ── exact curve arithmetic ──────────────────────────────────────────────

def test_weierstrass_identity_holds():
    for ainvs in (C11, C15, C37, C571):
        E = Curve(ainvs)
        assert E.c4 ** 3 - E.c6 ** 2 == 1728 * E.disc


def test_conductors_and_discriminants():
    for label, ainvs, N, disc, *_ in BATTERY:
        E = Curve(ainvs)
        assert E.disc == disc, label
        assert E.conductor() == N, label


def test_ap_matches_x0_11_eta_product():
    # a_n of X_0(11) = q prod (1-q^n)^2 (1-q^11n)^2
    E = Curve(C11)
    assert [E.ap(p) for p in (2, 3, 5, 7, 13, 17, 19)] == [-2, -1, 1, -2, 4, -2, 0]
    assert E.ap(11) == 1  # split multiplicative


def test_hecke_multiplicativity_is_consistent():
    E = Curve(C11)
    a = E.an_upto(200)
    assert a[6] == a[2] * a[3]
    assert a[4] == a[2] * a[2] - 2
    assert a[35] == a[5] * a[7]


def test_torsion_orders():
    for label, ainvs, _, _, tors, *_ in BATTERY:
        assert Curve(ainvs).torsion_order() == tors, label


def test_tamagawa_products():
    for label, ainvs, _, _, _, tam, *_ in BATTERY:
        assert Curve(ainvs).tamagawa_product() == tam, label


def test_root_numbers_are_plus_one_on_rank_zero_battery():
    for label, ainvs, *_ in BATTERY:
        assert Curve(ainvs).root_number() == 1, label


def test_rank_one_curve_has_root_number_minus_one():
    assert Curve((0, 0, 1, -1, 0)).root_number() == -1     # 37.a1, rank 1


def test_minimality_is_proven_not_assumed():
    proof = Curve(C11).certify_minimal()
    assert proof and all("v_" in v for v in proof.values())


# ── enclosures must contain, not equal ──────────────────────────────────

def test_real_period_contains_published_value():
    for label, ainvs, _, _, _, _, omega_s, _, _ in BATTERY:
        assert encloses(real_period(Curve(ainvs)), omega_s), label


def test_l_value_contains_published_value():
    for label, ainvs, _, _, _, _, _, l1_s, _ in BATTERY:
        assert encloses(l_value_at_1(Curve(ainvs)), l1_s), label


def test_period_handles_both_signs_of_discriminant():
    assert Curve(C11).disc < 0 and Curve(C15).disc > 0
    assert real_period(Curve(C11)).is_positive()
    assert real_period(Curve(C15)).is_positive()


# ── the verdict ─────────────────────────────────────────────────────────

def test_sha_is_pinned_to_the_published_integer():
    for label, ainvs, _, _, _, _, _, _, sha in BATTERY:
        cert = bsd_certificate(ainvs, label=label)
        assert cert["verdict"] == CONSISTENT, (label, cert.get("reason"))
        assert cert["sha_analytic"] == sha, label


def test_pinning_admits_exactly_one_integer():
    for label, ainvs, *_ in BATTERY:
        cert = bsd_certificate(ainvs, label=label)
        assert len(cert["integers_in_enclosure"]) == 1, label


def test_no_battery_curve_refutes_bsd():
    ok, rows = run_battery()
    assert ok
    assert all(r["verdict"] == CONSISTENT for r in rows)


def test_supplied_invariant_that_disagrees_is_refused():
    E = Curve(C11)
    with pytest.raises(Refuse):
        sha_analytic_interval(E, torsion=4)      # true torsion is 5
    with pytest.raises(Refuse):
        sha_analytic_interval(E, tamagawa=7)     # true product is 5


# ── controls: the machinery must be able to fail ────────────────────────

def test_all_controls_pass():
    for name, fn in CONTROLS.items():
        assert fn(), name


def test_additive_reduction_is_refused_not_estimated():
    cert = bsd_certificate((0, 0, 1, 0, 0))       # 27.a3, additive at 3
    assert cert["verdict"] == REFUSED
    assert "additive" in cert["reason"]


def test_odd_analytic_rank_is_refused():
    cert = bsd_certificate((0, 0, 1, -1, 0))      # 37.a1, rank 1
    assert cert["verdict"] == REFUSED
    assert "root number" in cert["reason"]


def test_singular_curve_is_refused():
    cert = bsd_certificate((0, 0, 0, 0, 0))
    assert cert["verdict"] == REFUSED


def test_halving_the_period_produces_a_non_square():
    """The factor-of-2 trap on Delta > 0: the wrong convention yields the
    integer 2, which the Cassels square test rejects."""
    E = Curve(C15)
    om = real_period(E)
    half = Iv(om.lo // 2, -((-om.hi) // 2))
    l1 = l_value_at_1(E)
    got = integers_in(l1.scale_int(E.torsion_order() ** 2) /
                      half.scale_int(E.tamagawa_product()))
    assert got == [2]


def test_perturbing_a_coefficient_changes_the_answer():
    base = bsd_certificate(C11)
    pert = bsd_certificate((0, -1, 1, -10, -19))
    assert (base.get("sha_analytic"), base["verdict"]) != \
           (pert.get("sha_analytic"), pert["verdict"]) or \
           base["conductor"] != pert.get("conductor")
