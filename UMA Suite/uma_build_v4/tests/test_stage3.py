# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
tests/test_stage3.py -- Stage 3 perturbative analysis correctness.
"""
from __future__ import annotations
import math
import numpy as np
import pytest

from uma.rsls import MemoryConfig
from uma.rsls.stage3 import (
    whitham_subcharacteristic, whitham_margin,
    dispersion_polynomial, find_poles, all_poles_stable,
    IsotropisationParams, pseudospectral_envelope_satisfied,
    reflection_coefficient, reflection_spectrum,
    wigner_delay, echo_spacing,
    detectability_bound, macroscopic_ell_star_lower_bound,
)


class TestWhitham:
    def test_default_config_subluminal(self):
        cfg = MemoryConfig()
        assert whitham_subcharacteristic(cfg)
        assert whitham_margin(cfg) > 0

    def test_superluminal_config_fails(self):
        # Configure mu, tau_J, tau_M to give c_diff > 1
        cfg = MemoryConfig(mu=10.0, tau_J=0.1, tau_M=0.1)
        assert not whitham_subcharacteristic(cfg)

    def test_all_poles_stable_default(self):
        cfg = MemoryConfig()
        ks = np.linspace(0.1, 100, 50)
        assert all_poles_stable(ks, cfg)


class TestDispersion:
    def test_polynomial_degree(self):
        cfg = MemoryConfig()
        coeffs = dispersion_polynomial(1.0, cfg)
        assert len(coeffs) == 3   # tau_J omega^2 + i omega - mu k^2

    def test_poles_have_negative_imaginary_part(self):
        cfg = MemoryConfig()
        for k in [0.1, 1.0, 10.0, 100.0]:
            roots = find_poles(k, cfg)
            assert np.all(roots.imag <= 1e-12), (
                f"k={k}: poles {roots} have Im > 0 (unstable)"
            )

    def test_zero_k_yields_pure_decay(self):
        """At k=0 the dispersion reduces to tau_J omega^2 + i omega = 0,
        giving omega = 0 and omega = -i/tau_J."""
        cfg = MemoryConfig()
        roots = find_poles(0.0, cfg)
        # One root at zero, one at -i/tau_J
        assert any(abs(r) < 1e-10 for r in roots)
        decay_root = max(roots, key=lambda r: abs(r))
        assert abs(decay_root.imag - (-1.0 / cfg.tau_J)) < 1e-10


class TestPseudospectral:
    def test_chi_below_one_stable(self):
        p = IsotropisationParams(sigma_D=0.5, Gamma_iso=1.0)
        assert pseudospectral_envelope_satisfied(p)

    def test_chi_above_one_unstable(self):
        p = IsotropisationParams(sigma_D=2.0, Gamma_iso=1.0)
        assert not pseudospectral_envelope_satisfied(p)


class TestReflectionAndDelay:
    def test_chi_zero_perfect_absorber(self):
        p = IsotropisationParams(sigma_D=0.0, Gamma_iso=1.0)
        R = reflection_coefficient(omega=1.0, p=p, tau_J=0.15)
        assert abs(R) < 1e-10

    def test_chi_nonzero_partial_reflection(self):
        p = IsotropisationParams(sigma_D=0.8, Gamma_iso=1.0)
        R = reflection_coefficient(omega=1.0, p=p, tau_J=0.15)
        assert abs(R) > 0.01

    def test_wigner_delay_finite(self):
        p = IsotropisationParams(sigma_D=0.5, Gamma_iso=1.0)
        omegas = np.linspace(0.5, 3.0, 100)
        tau_W = wigner_delay(omegas, p, tau_J=0.15)
        assert np.all(np.isfinite(tau_W))


class TestEchoSpacing:
    def test_echo_includes_lag(self):
        dt = echo_spacing(ell_star=1.0, r_photon=3.0, tau_M=0.5)
        # Geom = 2 * (3 - 1) = 4; total = 4 + 0.5 = 4.5
        assert abs(dt - 4.5) < 1e-10

    def test_smaller_ell_gives_longer_echo(self):
        dt1 = echo_spacing(ell_star=0.1, r_photon=3.0, tau_M=0.0)
        dt2 = echo_spacing(ell_star=1.0, r_photon=3.0, tau_M=0.0)
        assert dt1 > dt2


class TestDetectability:
    def test_planck_scale_undetectable(self):
        # Setting ell_star very small => exponential attenuation huge
        assert not detectability_bound(
            M_adm=30.0, ell_star=1e-30, Gamma_kerr=0.05
        )

    def test_macroscopic_ell_detectable(self):
        # ell_star ~ M_adm should be trivially detectable
        assert detectability_bound(
            M_adm=30.0, ell_star=10.0, Gamma_kerr=0.05
        )

    def test_bound_solves_consistently(self):
        # The macroscopic_ell_star bound should give an ell_* that
        # *just* satisfies the detectability bound
        M = 30.0
        Gamma = 0.05
        ell_min = macroscopic_ell_star_lower_bound(M, Gamma)
        # Check the bound is in a sensible range (much smaller than M_adm)
        assert 0 < ell_min < M
